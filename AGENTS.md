# Repository Guidelines

## Teacher Mode
- The project owner is learning fullstack development.
- Prefer mentor-style guidance and explain implementation choices unless explicitly asked for code-only execution.

## Current Objective
- Complete backend foundation (`crud.py`).
- Create initial Alembic migration baseline.
- Set up automated backend testing.

## AI Operational Mandates (Memory Persistence)
- Commit trigger: run `git add .` and `git commit` only when the exact phrase `commit code` is provided.
- Commit messages:
  - Use Conventional Commits (`feat:`, `fix:`, `chore:`, etc.).
  - Do not mention `GEMINI.md`, `ROADMAP.md`, `TECH_STACK.md`, or `GIT_NOTES.md`.
  - Match message detail to scope (short for small, structured for large).
  - Describe only net changes since the last commit.
- Push policy: never run `git push`; user handles remote pushes.
- Persistence: after each commit, update the “Last Successful Commit” section below.

## Syntax & Implementation Instructions
- Always refer to a student’s parent as a `guardian` in backend code and docs.
- Follow best practices for each language, framework, and package.

## Last Successful Commit
- Commit Hash: `3e9e45c`
- Changes Summary: moved shared enums into `enums.py` and updated `models.py`.

## Read on Startup
At startup or memory refresh, review:
- `GEMINI.md`
- `ROADMAP.md`
- `TECH_STACK.md`
- `attendanceflow.txt` (for attendance validation and logic alignment)

Keep those files synchronized with current implementation and only mark work complete when fully implemented.

## Project Overview
LogTender is a high-performance daycare attendance app for a single provider.
- Goal: check-in/check-out in under 10 seconds.
- Performance target: live updates in under 2 seconds.

## Technology Stack
- Frontend: React (TypeScript) + Tailwind
- Backend: Python + FastAPI
- Database: PostgreSQL
- Infrastructure: Docker / Docker Compose
- Package managers: `uv` (Python), `npm` (JavaScript)

## Implementation Status
Completed:
- Dockerized PostgreSQL with persistent volume.
- Backend initialized with FastAPI structure under `backend/app/`.
- Core schema/model groundwork including attendance flow document.
- Pydantic schemas finalized in `backend/app/schemas.py`.
- Alembic initialized and configured for migrations.

In progress / next:
- Implement CRUD layer.
- Create initial Alembic migration baseline.
- Add automated tests with Pytest.
- Implement secure, auditable guardian PIN reset flow.
- Initialize frontend app.

## Project Structure
- `backend/app/`: API entry, models, schemas, CRUD, DB config.
- `frontend/`: planned React app.
- `docker-compose.yml`: local infrastructure.
- `.env`: local secrets (ignored).
- `attendanceflow.txt`: attendance behavior and audit-flow reference.
