from .base import *  # noqa: F401, F403

DEBUG = True

if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise RuntimeError("PostgreSQL is strictly required in development as well as production.")
