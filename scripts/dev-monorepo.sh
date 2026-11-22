#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DJANGO_DIR="$ROOT_DIR/backend/django_core"
FASTAPI_DIR="$ROOT_DIR/backend/fastapi_core"

# Load root .env if present
if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

# Auto-install required OS packages on fresh Debian/Ubuntu containers if running as root
if [ "$(id -u)" -eq 0 ] && command -v apt-get >/dev/null 2>&1; then
  NEED_APT=0
  python3 -m ensurepip --version >/dev/null 2>&1 || NEED_APT=1
  command -v redis-server >/dev/null 2>&1 || NEED_APT=1
  [ -d /usr/lib/postgresql ] || NEED_APT=1
  if [ "$NEED_APT" -eq 1 ]; then
    echo "[bonyan-melk] Installing system runtime packages (PostgreSQL, Redis, python3-venv)..."
    apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
      -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--path-exclude=/var/log/*" \
      postgresql postgresql-contrib redis-server python3-venv python3-pip libpq-dev >/dev/null
  fi
fi

# Resolve Python interpreter cleanly: workspace .venv -> /opt/pyvenv -> python3
if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
  PY_BIN="$ROOT_DIR/.venv/bin/python"
elif [ -x "/opt/pyvenv/bin/python" ]; then
  PY_BIN="/opt/pyvenv/bin/python"
else
  PY_BIN="$(command -v python3)"
fi

if ! "$PY_BIN" -c "import django, fastapi, pydantic_settings, uvicorn, psycopg2, redis" >/dev/null 2>&1; then
  echo "[bonyan-melk] Installing backend dependencies into .venv..."
  if [ ! -x "$ROOT_DIR/.venv/bin/pip" ]; then
    rm -rf "$ROOT_DIR/.venv"
    python3 -m venv "$ROOT_DIR/.venv"
  fi
  "$ROOT_DIR/.venv/bin/pip" install --no-cache-dir --quiet -r "$ROOT_DIR/backend/requirements.txt"
  PY_BIN="$ROOT_DIR/.venv/bin/python"
fi

if [ ! -x "$ROOT_DIR/frontend/node_modules/.bin/next" ]; then
  echo "[bonyan-melk] Installing frontend dependencies..."
  npm --prefix "$ROOT_DIR/frontend" install --no-audit --no-fund
fi

# Auto-start local PostgreSQL & Redis if installed in container and not yet running
PG_CTL_BIN=""
PG_DATA_DIR=""
PG_CONF_FILE=""
for ver in 15 16 14; do
  if [ -x "/usr/lib/postgresql/$ver/bin/pg_ctl" ]; then
    PG_CTL_BIN="/usr/lib/postgresql/$ver/bin/pg_ctl"
    PG_DATA_DIR="/var/lib/postgresql/$ver/main"
    if [ ! -d "$PG_DATA_DIR" ] || [ ! -f "$PG_DATA_DIR/PG_VERSION" ]; then
      mkdir -p "$PG_DATA_DIR"
      chown -R postgres:postgres /var/lib/postgresql
      su -s /bin/bash postgres -c "/usr/lib/postgresql/$ver/bin/initdb -D '$PG_DATA_DIR' --encoding=UTF8 --locale=C.UTF-8 >/dev/null"
    fi
    if [ -f "/etc/postgresql/$ver/main/postgresql.conf" ]; then
      PG_CONF_FILE="/etc/postgresql/$ver/main/postgresql.conf"
    fi
    break
  fi
done

if [ -n "$PG_CTL_BIN" ]; then
  mkdir -p /var/run/postgresql
  chown -R postgres:postgres /var/run/postgresql /var/lib/postgresql
  if ! su -s /bin/bash postgres -c "$PG_CTL_BIN -D $PG_DATA_DIR status" >/dev/null 2>&1; then
    PG_OPTS="-k /var/run/postgresql -p 5432 -h 127.0.0.1"
    if [ -n "$PG_CONF_FILE" ]; then
      PG_OPTS="-c config_file=$PG_CONF_FILE $PG_OPTS"
    fi
    su -s /bin/bash postgres -c "$PG_CTL_BIN -D $PG_DATA_DIR -l /tmp/postgres.log -o '$PG_OPTS' start"
  fi
  su -s /bin/bash postgres -c "psql -h /var/run/postgresql -tc \"SELECT 1 FROM pg_roles WHERE rolname='realestate_user'\" | grep -q 1 || psql -h /var/run/postgresql -c \"CREATE USER realestate_user WITH PASSWORD 'realestate_pass' SUPERUSER;\"" >/dev/null 2>&1 || true
  su -s /bin/bash postgres -c "psql -h /var/run/postgresql -tc \"SELECT 1 FROM pg_database WHERE datname='realestate_db'\" | grep -q 1 || psql -h /var/run/postgresql -c \"CREATE DATABASE realestate_db OWNER realestate_user;\"" >/dev/null 2>&1 || true
fi

if command -v redis-server >/dev/null 2>&1; then
  if ! redis-cli ping >/dev/null 2>&1; then
    redis-server --daemonize yes --dir /tmp --logfile /tmp/redis.log
  fi
fi

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.development}"
export BACKEND_DIR="$DJANGO_DIR"
export INTERNAL_FASTAPI_URL="http://127.0.0.1:8020"
export DATABASE_URL="${DATABASE_URL:-postgresql://realestate_user:realestate_pass@127.0.0.1:5432/realestate_db}"
export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"

# Verify PostgreSQL connectivity (PostgreSQL is strictly required; SQLite is forbidden)
if ! "$PY_BIN" - <<'PYEOF'
import os, psycopg2
conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=3)
conn.close()
PYEOF
then
  echo "[bonyan-melk] ERROR: PostgreSQL is required and unreachable at DATABASE_URL." >&2
  exit 1
fi
echo "[bonyan-melk] Connected to PostgreSQL via DATABASE_URL."

# Migrate & idempotently seed demo data in development
(cd "$DJANGO_DIR" && "$PY_BIN" manage.py migrate --noinput && "$PY_BIN" manage.py seed_demo --quiet)

# Stop any stale listeners
pkill -f "uvicorn .* --host 127.0.0.1 --port 8020" >/dev/null 2>&1 || true
pkill -f "celery -A config worker" >/dev/null 2>&1 || true

# Start Celery Worker for asynchronous panorama stitching, 3D geometry & scan processing
(cd "$DJANGO_DIR" && exec "$PY_BIN" -m celery -A config worker -l info --concurrency=2 --logfile=/tmp/celery-worker.log) &
CELERY_PID=$!

# Start FastAPI Core Web API Service (Port 8020)
(cd "$FASTAPI_DIR" && exec "$PY_BIN" -m uvicorn main:app --host 127.0.0.1 --port 8020) &
FASTAPI_PID=$!

cleanup() {
  kill "$FASTAPI_PID" >/dev/null 2>&1 || true
  kill "$CELERY_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

for _ in $(seq 1 25); do
  if curl -fsS "http://127.0.0.1:8020/api/v1/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.4
done

exec npm --prefix "$ROOT_DIR/frontend" run dev
