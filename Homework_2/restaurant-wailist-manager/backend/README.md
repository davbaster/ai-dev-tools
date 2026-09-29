# HostBoard backend

FastAPI backend for the HostBoard waitlist manager. The current implementation uses an in-memory mock store and is intended to be replaced with a real database later.

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
