# PaperMind

PaperMind is an AI-powered research workspace for organizing papers, folders, chats, and research notes.

This project is still in early development. The current focus is building the backend foundation first, then connecting frontend features on top of tested APIs.

## Project Structure

```text
apps/
  api/      FastAPI backend
  web/      React frontend
  compose.yaml
docs/
```

## Tech Stack

- Frontend: React, Vite, TypeScript, Redux
- Backend: FastAPI, SQLAlchemy, Alembic
- Auth: Clerk
- Database: PostgreSQL
- File storage: S3-compatible storage

## Local Development

Start PostgreSQL:

```bash
cd apps
docker compose up -d
```

Run the backend:

```bash
cd apps/api
uv sync
uv run alembic upgrade head
uv run fastapi dev src/papermind/main.py
```

Run the frontend:

```bash
cd apps/web
npm install
npm run dev
```

## Checks

Backend:

```bash
cd apps/api
uv run ruff check .
uv run pytest
```

Frontend:

```bash
cd apps/web
npm run lint
npm run build
```
