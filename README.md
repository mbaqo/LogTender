# LogTender

> Status: In Progress

LogTender is a high-performance daycare attendance platform designed for fast guardian check-in/check-out, real-time provider visibility, and compliance-ready audit records.

## Highlights
- Fast guardian kiosk flow with PIN-based attendance events.
- Event-based attendance architecture for immutable history and corrections.
- Provider dashboard model for live attendance state and daily operations.
- Compliance-oriented audit data design, including event timestamps and signature support.
- Alembic migrations configured for schema tracking.

## Performance Goals
- Check-in/check-out interaction under 10 seconds.
- Live state updates under 2 seconds.

## Architecture
- Frontend: React + TypeScript + Tailwind CSS
- Backend: FastAPI + SQLAlchemy + Pydantic
- Database: PostgreSQL 15
- Infrastructure: Docker + Docker Compose
- Package managers: `uv` (Python), `npm` (JavaScript)

## Repository Layout
- `backend/app/` - API entrypoint, models, schemas, CRUD, config
- `frontend/` - React application
- `docker-compose.yml` - local service orchestration
- `attendanceflow.txt` - attendance behavior and audit-flow reference

## Getting Started
1. Clone the repository.
2. Create `.env` with local configuration values.
3. Start services with Docker Compose.
4. Run backend and frontend development servers.
