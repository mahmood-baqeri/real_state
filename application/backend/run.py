# Path: backend/run.py

# application/backend/run.py
import os
import sys
import subprocess
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
DJANGO_DIR = BACKEND_DIR / "django_core"
FASTAPI_DIR = BACKEND_DIR / "fastapi_core"

def main():
    env = os.environ.copy()

    env["PYTHONPATH"] = f"{BACKEND_DIR}{os.pathsep}{DJANGO_DIR}{os.pathsep}{FASTAPI_DIR}{os.pathsep}" + env.get("PYTHONPATH", "")
    env["DJANGO_SETTINGS_MODULE"] = "config.settings.development"

    print("⏳ Starting servers with the configured PostgreSQL database...\n")

    # 1. Django
    django_cmd = [
        sys.executable, "-m", "uvicorn", "config.asgi:application",
        "--host", "0.0.0.0", "--port", "8010", "--reload"
    ]
    print("🚀 [Django] Running on port 8010...")
    p_django = subprocess.Popen(django_cmd, cwd=str(DJANGO_DIR), env=env)

    # 2. FastAPI
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