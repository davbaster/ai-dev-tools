# Agent Relay

Agent Relay is a small FastAPI service for registering agents, delivering one
task at a time, and recording results. The Compose setup runs the API and
PostgreSQL together. Workers execute tasks on their own machines. The included
worker deterministically returns `input.upper()`.

## Run with Docker Compose

```bash
docker compose up --build --detach
docker compose ps
```

Compose starts the API and the `postgres` database service. The API waits until
PostgreSQL is healthy before starting. Open <http://127.0.0.1:8000/> for the
token-based local dashboard. `GET /health` is a liveness check and `GET /ready`
checks database connectivity and schema.

The database is stored in the named `postgres_data` volume. `docker compose
down` stops the services and keeps the data; `docker compose down --volumes`
also deletes it. Compose uses the local development credentials
`agent_relay` / `agent_relay_local` by default. Set `POSTGRES_USER`,
`POSTGRES_PASSWORD`, and `POSTGRES_DB` in a `.env` file before starting if you
need different credentials. Keep the password URL-safe because Compose uses it
inside `RELAY_DATABASE_URL`.

If host port 8000 is already in use, choose another API port before starting:

```powershell
$env:RELAY_HOST_PORT = "8002"
docker compose up --build --detach
```

Then open <http://127.0.0.1:8002/>. To view API logs, run
`docker compose logs --follow agent-relay`.

For running Uvicorn directly on the host, first start PostgreSQL with
`docker compose up --detach postgres`, then run from this directory:

```powershell
uv sync
$env:RELAY_DATABASE_URL = "postgresql+psycopg://agent_relay:agent_relay_local@127.0.0.1:5432/agent_relay"
uv run uvicorn main:app --reload
```

Register two identities and send a task:

```bash
alice=$(curl -sS -X POST http://127.0.0.1:8000/api/v1/agents \
  -H 'content-type: application/json' -d '{"name":"alice"}')
bob=$(curl -sS -X POST http://127.0.0.1:8000/api/v1/agents \
  -H 'content-type: application/json' -d '{"name":"uppercase"}')
```

The response contains each agent's secret `token` once. Keep it outside source
control. Use `Authorization: Bearer <token>` for all subsequent API calls;
registration is the only unauthenticated endpoint. For a shared installation,
set `RELAY_ENROLLMENT_SECRET` and send it as `X-Enrollment-Secret` when
registering.

## Run the deterministic worker

The worker can register itself and save credentials in a mode-0600 JSON file:

```bash
uv run python main.py worker \
  --base-url http://127.0.0.1:8000 \
  --name uppercase \
  --credentials ./uppercase-credentials.json \
  --worker-id laptop-1
```

For failure/redelivery demonstrations, make local execution intentionally slow
and stop the process after one completion:

```bash
uv run python main.py worker --credentials ./uppercase-credentials.json \
  --slow-seconds 75 --worker-id slow-laptop
```

The worker heartbeats during long work. Killing it leaves the claim leased;
after the 60-second lease expires, another worker can claim the task with a new
token and incremented attempt number. `RELAY_LEASE_SECONDS` and
`RELAY_MAX_ATTEMPTS` are configurable server settings.

An existing credential can also be supplied explicitly (the token is not
written to disk):

```bash
uv run python main.py worker --agent-id agent_123 --token agt_… --worker-id laptop-2
```

## Storage and delivery behavior

`database.py` contains the SQLAlchemy models and PostgreSQL transaction setup.
`storage.py` contains task, claim, and recovery operations; routes and request
models are kept in `main.py` and `schemas.py`. Claims lock available task rows
with `FOR UPDATE SKIP LOCKED`, so multiple API processes can safely serve
workers without overlapping active claims.

Claims are at-least-once and leased for 60 seconds by default. Heartbeats extend
an active lease. A completion or failure must include the recipient's bearer
token and claim token. Repeating the exact terminal request with that claim
token is idempotent; a stale token or different result receives `409`.

## Verify

Start the database services, then run the protocol tests:

```bash
docker compose up --detach postgres
uv sync
uv run pytest -q
```

The protocol tests reset the dedicated `agent_relay_test` database. Do not set
`RELAY_DATABASE_URL` to the application database when running them. To use a
different test database, set `RELAY_TEST_DATABASE_URL` instead.

### Live API and PostgreSQL integration test

The opt-in integration test runs the first acceptance scenario against the
running Compose API, then queries PostgreSQL to verify the task, attempt, and
hashed credentials. Start the full Compose stack, then run these commands in
PowerShell:

```powershell
$env:RELAY_INTEGRATION_BASE_URL = "http://127.0.0.1:8000"
$env:RELAY_INTEGRATION_DATABASE_URL = "postgresql+psycopg://agent_relay:agent_relay_local@127.0.0.1:5432/agent_relay"
uv run pytest -q -m integration test_relay_integration.py
```

It creates new agent and task records in the application database and does not
delete or reset existing data.

This local setup does not include Kubernetes, CI, external brokers, or an LLM.
