# HostBoard backend

FastAPI backend for the HostBoard waitlist manager. Runtime data is stored using SQLAlchemy and the configured `DATABASE_URL` (SQLite by default; PostgreSQL is supported with psycopg).

## Setup

From this directory:

```powershell
uv sync --dev
```

## Test

```powershell
uv run pytest
```

## Run

```powershell
uv run uvicorn app.main:app --reload --port 8000
```

OpenAPI is defined in `openapi.yaml`. FastAPI also exposes its generated schema at `/docs` and `/openapi.json`.
