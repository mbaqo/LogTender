# Backend

FastAPI backend for LogTender with SQLAlchemy models, Pydantic schemas, and Alembic migrations.

## Setup
1. Ensure `.env` exists at the repo root with `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and `DATABASE_URL`.
2. Install dependencies:
   ```bash
   uv sync
   ```
3. Run migrations:
   ```bash
   alembic upgrade head
   ```

## Status
- Schemas finalized (`app/schemas.py`).
- Alembic configured (`alembic/env.py`, `alembic.ini`).
- CRUD foundation implemented for users, students, guardians, attendance, notes, and guardian PIN resets.
- Automated CRUD tests are available under `app/tests/`.

## Tests
Run the backend test suite:
```bash
pytest
```

Backend tests require a dedicated PostgreSQL test database and will fail if
`DATABASE_URL_TEST` is not set.

To confirm the suite is using the test database, run:
```bash
pytest -s
```
During startup, the test session will use `DATABASE_URL_TEST` as the active
`DATABASE_URL`, so any app code imported by the tests connects to the same
database URL.

If you want a quick manual check, run:
```bash
python -c "from app.tests.conftest import _DATABASE_URL_TEST; print(_DATABASE_URL_TEST)"
```

Attendance days use `ATTENDANCE_TIMEZONE`, defaulting to `America/Los_Angeles`.
