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
- CRUD layer and automated tests are next.
