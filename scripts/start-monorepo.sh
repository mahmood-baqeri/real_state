#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DJANGO_DIR="$ROOT_DIR/backend/django_core"
FASTAPI_DIR="$ROOT_DIR/backend/fastapi_core"

if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
  PY_BIN="$ROOT_DIR/.venv/bin/python"
elif [ -x "/opt/pyvenv/bin/python" ]; then
  PY_BIN="/opt/pyvenv/bin/python"
else
  PY_BIN="$(command -v python3)"
fi

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

"$PY_BIN" - <<'PYEOF'
import os, psycopg2
conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=3)
conn.close()
PYEOF

(cd "$DJANGO_DIR" && "$PY_BIN" manage.py migrate --noinput)
if [ "${DJANGO_SETTINGS_MODULE}" = "config.settings.development" ]; then
  (cd "$DJANGO_DIR" && "$PY_BIN" manage.py seed_demo --quiet)
else
  (cd "$DJANGO_DIR" && "$PY_BIN" manage.py bootstrap_platform --quiet)
fi

pkill -f "uvicorn .* --host 127.0.0.1 --port 8020" >/dev/null 2>&1 || true

(cd "$FASTAPI_DIR" && exec "$PY_BIN" -m uvicorn main:app --host 127.0.0.1 --port 8020) &
FASTAPI_PID=$!

cleanup() {
  kill "$FASTAPI_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

for _ in $(seq 1 25); do
  if curl -fsS "http://127.0.0.1:8020/api/v1/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.4
done

exec npm --prefix "$ROOT_DIR/frontend" run start
