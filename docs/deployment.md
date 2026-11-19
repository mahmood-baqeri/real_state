# Local Deployment and Production Notes

## Local Compose stack

1. Copy `application/.env.example` to `application/.env`.
2. Replace `DJANGO_SECRET_KEY`, `JWT_SIGNING_KEY`, and `POSTGRES_PASSWORD`.
   Generate the two signing keys independently; each must contain at least 50
   characters for Django and 32 characters for JWT.
3. From `application/`, run:

   ```sh
   docker compose up --build -d
   ```

The local stack exposes the app at `http://localhost:8080`, PostgreSQL at
`127.0.0.1:5433`, and Redis at `127.0.0.1:6380`. The PostgreSQL init hook
creates the dedicated `POSTGRES_TEST_DB` database on first initialization.
The Postgres and Redis data volumes are persistent; `docker compose down -v`
deletes them and must only be used when intentionally discarding local data.

## Backend tests

Set `TEST_DATABASE_URL` to the dedicated PostgreSQL test database. Do not point
it at a development or production database. The test settings reject SQLite and
fail early when this variable is missing.

```sh
cd application/backend/django_core
python -m pytest

cd ../fastapi_core
python -m pytest
```

The application-level `.env` is loaded by Django settings and FastAPI settings.
For CI, provide `TEST_DATABASE_URL` through the job environment and create that
database before running tests.

## Production TLS

The Compose Nginx service is a local HTTP entry point, not a complete public
TLS deployment. Put it behind a trusted TLS-terminating reverse proxy or add
managed certificates before exposing the service publicly. In a TLS deployment,
set `DJANGO_SECURE_SSL_REDIRECT=1` and
`DJANGO_SECURE_HSTS_SECONDS=31536000`; the reverse proxy must preserve the
trusted `X-Forwarded-Proto: https` header. Keep the application, PostgreSQL,
and Redis services on a private network and use unique secrets rather than the
example values.
