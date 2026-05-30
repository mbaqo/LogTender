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

By default, tests use an isolated in-memory SQLite database for fast local feedback.
Set `DATABASE_URL_TEST` to run the same CRUD tests against a dedicated PostgreSQL test database.

Attendance days use `ATTENDANCE_TIMEZONE`, defaulting to `America/Los_Angeles`.
