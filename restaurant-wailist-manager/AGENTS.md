# HostBoard agent guide

HostBoard is a single-restaurant waitlist and floor-management app for staff. Read this file first, then consult `_docs/specs.md` for product behavior and the code for the current implementation. Keep the documentation aligned with the running implementation; if a spec conflicts with code or the user’s current request, call out the mismatch and follow the explicitly approved direction.

## Project layout

- `backend/app/main.py`: FastAPI routes, request/response schemas, authentication, permissions, and app setup.
- `backend/app/store.py`: SQLAlchemy-backed domain operations and the test store.
- `backend/app/models.py`, `backend/app/database.py`: ORM models, engine configuration, sessions, and SQLite setup.
- `backend/tests/`: backend API, database, and frontend-contract tests.
- `frontend/src/api/backendApi.js`: centralized HTTP client and snake_case/camelCase mapping. Keep backend calls here.
- `frontend/src/App.jsx`, `main.jsx`, `styles.css`: application UI and styling.
- `frontend/src/api/backendApi.test.js`: frontend API client tests (Node test runner).
- `_docs/specs.md`: product requirements and domain rules.
- `_docs/backend-specs.md`: historical/recommended contract document. It currently describes a Django design; the implemented backend is FastAPI, so verify it against code before relying on its stack or implementation claims.
- `test-connection.mjs`: live HTTP integration flow through the actual frontend API client.

## Working approach

1. Inspect the relevant implementation and product spec before changing behavior. Follow an existing code path end to end (UI → `backendApi.js` → route → store/model) when working on a feature.
2. Make the smallest coherent change and preserve established API shapes, authentication, and role checks. Put frontend network behavior and field mapping in `backendApi.js`, not components.
3. Treat server-side validation and authorization as authoritative. UI affordances do not replace backend checks.
4. Preserve unrelated working-tree edits. Do not reset or overwrite local databases or generated/user files as part of routine work.
5. Use UTF-8 for edited files. Update user-facing docs when setup or behavior changes.
6. Do not claim a check passed unless it was run. Run the relevant checks for the change; the commands below cover the full available verification suite.

## Domain invariants

- Queue order is FIFO by server-side creation timestamp. Editing a waiting entry must not change its original position.
- Only waiting entries may be edited, seated, or cancelled. Seated and cancelled entries stay in the service-day history.
- A table must be active, available, and large enough before assignment. Prevent duplicate occupation and keep release behavior consistent with assignment history.
- Duplicate normalized phone numbers are warnings, not a reason to reject a party.
- When the restaurant is closed, reject new parties while allowing staff to manage existing entries.
- Hosts perform service operations. Manager-only settings, table inventory, and staff administration must be enforced by the backend.
- Do not allow disabling the last active manager or deactivating an occupied table.

## Setup and run (PowerShell)

Backend, from `restaurant-wailist-manager/backend`:

```powershell
uv sync --dev
uv run uvicorn app.main:app --reload --port 8000
```

Frontend, in a separate terminal from `restaurant-wailist-manager/frontend`:

```powershell
npm install
npm run dev
```

Open <http://localhost:5173/>. The frontend proxies `/api` to the backend; API docs are at <http://localhost:8000/docs>.

`DATABASE_URL` selects the backend database. Without it, the app uses SQLite at `backend/hostboard.db`. The app creates its schema and seeds development data during setup. Backend tests use an isolated in-memory store; do not point them at a database whose data must be kept. The live integration script starts a test server and should be run with the local backend stopped if port 8000 is occupied.

## Verification commands

Run checks relevant to the change. Full suite:

```powershell
# Backend
cd .\restaurant-wailist-manager\backend
uv run pytest

# Frontend API client
cd ..\frontend
npm test

# Live HTTP integration (from project root)
cd ..
node test-connection.mjs
```

The integration script uses a real HTTP server and exercises host/manager workflows. Inspect its setup before running if your local port or environment has special constraints.

### Agent Relay live API and PostgreSQL integration

`backend/tests/test_agent_relay_integration.py` is a separate opt-in check against a running Agent Relay and its real PostgreSQL database. It registers two uniquely named agents, exchanges and completes a task, and verifies the saved agent/task/attempt rows and hashed claim token. It adds records and does not reset the database. Run it from the `ai-dev-tools` repository root with Agent Relay's environment, which supplies `httpx`, SQLAlchemy, and `psycopg`:

```powershell
kubectl -n agent-relay port-forward service/agent-relay 8001:8000
kubectl -n agent-relay port-forward service/postgres 15432:5432
uv run --project .\agent-relay pytest -p no:cacheprovider .\restaurant-wailist-manager\backend\tests\test_agent_relay_integration.py
```

Run the two `kubectl port-forward` commands in separate terminals and execute pytest in a third. The test defaults to API `http://127.0.0.1:8001` and database `postgresql+psycopg://relay:relay-local-only@127.0.0.1:15432/agent_relay`, matching the local kind manifests. With no environment overrides, it skips if either local service is unavailable. Override either endpoint with `AGENT_RELAY_INTEGRATION_BASE_URL` or `AGENT_RELAY_INTEGRATION_DATABASE_URL`; explicitly configured endpoints are required to work or the test fails. Keep this live-data test separate from the backend unit suite and point it only at a development Relay database.

## Current account examples

Development seed accounts are maintained in `backend/app/store.py`. At the time this guide was written, the README lists Maya Chen (`maya@juneandpine.com`) as manager and Luca Rivera / Nora Bell as hosts, all with the demo password `demo1234`. Confirm the seed implementation before changing or relying on credentials.
