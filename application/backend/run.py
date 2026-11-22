# application/backend/run.py
import os
import sys
import argparse
import subprocess
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
DJANGO_DIR = BACKEND_DIR / "django_core"
FASTAPI_DIR = BACKEND_DIR / "fastapi_core"


def _run(cmd, cwd, env, label):
    """اجرای یک دستور و بررسی موفقیت آن."""
    print(f"▶️  {label}")
    result = subprocess.run(cmd, cwd=str(cwd), env=env)
    if result.returncode != 0:
        print(f"❌ {label} failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    print(f"✅ {label} done\n")


def _seed_if_available(env):
    """اجرای seed_all یا seed_demo — هر کدام که موجود بود."""
    candidates = [
        ["seed_all", "--quiet"],
        ["seed_all"],
        ["seed_demo", "--quiet"],
        ["seed_demo"],
    ]
    for args in candidates:
        check = subprocess.run(
            [sys.executable, "manage.py", "help", args[0]],
            cwd=str(DJANGO_DIR),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if check.returncode == 0:
            _run([sys.executable, "manage.py"] + args, DJANGO_DIR, env,
                 f"Seeding database via '{' '.join(args)}'")
            return
    print("⚠️  No seed command found (seed_all/seed_demo). Skipping seed.\n")


def _reset_database(env):
    """پاک‌سازی کامل دیتابیس و اجرای migrate + seed از صفر."""
    print("🧨 Resetting database (drop all tables & re-create)...\n")

    # 1) drop all tables from the DB
    #    سریع‌ترین و مطمئن‌ترین راه: flush --noinput
    #    (اگر خواستی دیتابیس کاملاً drop شود، پایین کامنت شده)
    _run(
        [sys.executable, "manage.py", "flush", "--noinput"],
        DJANGO_DIR, env, "Flushing all data from database"
    )

    # --- گزینه جایگزین: حذف کامل جداول (migrate zero) ---
    # _run([sys.executable, "manage.py", "migrate", "zero", "--noinput"],
    #      DJANGO_DIR, env, "Unapplying all migrations")

    # 2) migrate از صفر
    _run(
        [sys.executable, "manage.py", "migrate", "--noinput"],
        DJANGO_DIR, env, "Running migrations"
    )

    # 3) seed
    _seed_if_available(env)

    print("✅ Database reset & re-seeded.\n")


def main():
    parser = argparse.ArgumentParser(description="Run Bonyan Melk backend services.")
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Drop all data, re-run migrations, and re-seed the database before starting.",
    )
    args = parser.parse_args()

    env = os.environ.copy()
    env["PYTHONPATH"] = (
        f"{BACKEND_DIR}{os.pathsep}{DJANGO_DIR}{os.pathsep}{FASTAPI_DIR}{os.pathsep}"
        + env.get("PYTHONPATH", "")
    )
    env["DJANGO_SETTINGS_MODULE"] = "config.settings.development"

    # فقط اگر کاربر خواسته، دیتابیس را ریست کن
    if args.reset_db:
        _reset_database(env)
    else:
        print("ℹ️  Skipping database reset (pass --reset-db to wipe & re-seed).\n")

    print("⏳ Starting servers...\n")

    # Django
    django_cmd = [
        sys.executable, "-m", "uvicorn", "config.asgi:application",
        "--host", "0.0.0.0", "--port", "8010", "--reload"
    ]
    print("🚀 [Django] Running on port 8010...")
    p_django = subprocess.Popen(django_cmd, cwd=str(DJANGO_DIR), env=env)

    # FastAPI
    fastapi_cmd = [
        sys.executable, "-m", "uvicorn", "app.main:app",
        "--host", "0.0.0.0", "--port", "8020", "--reload"
    ]
    print("🚀 [FastAPI] Running on port 8020...\n")
    p_fastapi = subprocess.Popen(fastapi_cmd, cwd=str(FASTAPI_DIR), env=env)

    try:
        p_django.wait()
        p_fastapi.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down servers...")
        p_django.terminate()
        p_fastapi.terminate()
        p_django.wait()
        p_fastapi.wait()
        print("✅ Both servers stopped cleanly.")


if __name__ == "__main__":
    main()
    
    
    
# python run.py
# python run.py --reset-db




# def parse_database_url(url: str) -> dict:
#     parsed = urlparse(url)
#     if parsed.scheme in ("postgres", "postgresql"):
#         query_params = {k: v[-1] for k, v in parse_qs(parsed.query).items() if v}
#         db_config = {
#             "ENGINE": "django.db.backends.postgresql",
#             "NAME": "real_state",
#             "USER": "postgres",
#             "PASSWORD": "Mb@1401",
#             "HOST": "localhost",
#             "PORT": "5432",
#             "CONN_MAX_AGE": 60,
#             "CONN_HEALTH_CHECKS": True,
#         }
#         if query_params:
#             db_config["OPTIONS"] = query_params
#         return db_config
#     raise ValueError(
#         f"Unsupported DATABASE_URL scheme '{parsed.scheme}'. PostgreSQL is strictly required."
#     )
