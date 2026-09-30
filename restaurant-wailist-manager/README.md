# HostBoard — Restaurant Waitlist Manager

HostBoard is a real-time waitlist and floor management application designed for restaurant host stands and managers. It provides a live queue, table occupancy tracking, role-based workflows, and service day history.

---

## Prerequisites

Before starting, ensure you have the following installed on your machine:
- **Python 3.12+** and [**uv**](https://docs.astral.sh/uv/) package manager
- **Node.js 18+** and **npm**

---

## Getting Started

### 1. Start the Backend (FastAPI)

From the project root directory, run:

```powershell
cd .\restaurant-wailist-manager\backend
uv sync --dev
uv run uvicorn app.main:app --reload --port 8000
```

- **API Base URL**: <http://localhost:8000/>
- **Interactive Swagger Docs**: <http://localhost:8000/docs>
- **ReDoc**: <http://localhost:8000/redoc>

The backend persists data with SQLAlchemy. By default, it initializes `backend/hostboard.db`, a local SQLite database populated with development seed data (tables, sample waitlist entries, and demo staff accounts). `DATABASE_URL` can select another SQLAlchemy database, provided its driver is installed and supported by the current code.

---

### 2. Start the Frontend (React + Vite)

In a separate terminal, run:

```powershell
cd .\restaurant-wailist-manager\frontend
npm install
npm run dev
```

- **Frontend Application**: <http://localhost:5173/>

The frontend automatically connects to the FastAPI backend at `http://localhost:8000` (and proxies `/api` requests during development).

---

## How to Log In

The system includes pre-seeded demo accounts for both roles. Open <http://localhost:5173/> in your browser to log in:

### Host Account (Operational Floor Access)
- **Email**: `luca@juneandpine.com` (or `nora@juneandpine.com`)
- **Password**: `demo1234`
- **Role**: Host
- **Access**: Manages the live waitlist, adds walk-ins, updates party info, seats guests at tables, and cancels entries.

### Manager Account (Full Control & Administration)
- **Email**: `maya@juneandpine.com`
- **Password**: `demo1234`
- **Role**: Manager
- **Access**: Includes all Host features plus restaurant settings (open/closed toggle), table inventory management, and staff account administration.

---

## Basic Usage Guide

### 1. Managing the Live Waitlist (Host & Manager)
- **Add a Party**: Click the **"Add party"** button. Enter the guest's name, phone number, party size, seating preference (*Dining room*, *Patio*, *Bar*, or *No preference*), and optional notes (e.g., high chair, anniversary). Submitted parties appear in the queue in FIFO (First-In, First-Served) order.
- **Duplicate Detection**: Entering a phone number already in the active line displays an inline warning, allowing hosts to verify the party while still permitting the entry.
- **Edit Party Details**: Click the edit icon on any waiting card to update party size, seating preference, or notes. The party's original queue position is always preserved.
- **Seat a Party**: When a table is ready, click **"Seat"** on the party's card. Choose an available table from the modal (tables too small for the party size are disabled). Confirming marks the party as `seated` and updates the table's status to `Occupied`.
- **Mark a Table as Free (Table Turnover)**: When a seated party finishes their meal, hosts and managers can free the table:
  - From the **Waitlist view**: Click any occupied table in the right-hand **"Table pulse"** rail to open the confirmation modal and mark it free.
  - From **Today's history**: Click **"Free table"** next to any currently occupied dining party.
  - From **Manager Settings > Tables**: Click **"Free table"** in the room inventory list.
  Once freed, the table immediately returns to `Available` status for waiting guests while the party record remains safely filed in today's completed history.
- **Cancel a Party**: If a guest walks away or cancels, click the cancel icon. The party moves out of the active line into today's history log.

### 2. Viewing Service History
- Click **"History"** in the sidebar to review all parties completed during the current service day (`seated` or `cancelled`).
- Displays timestamps, assigned tables, and the staff member who seated or cancelled the party. Active seated tables feature a quick **"Free table"** button once dining finishes.

### 3. Manager Controls (Manager Only)
Click **"Settings"** in the sidebar (visible only when logged in as Manager):
- **Restaurant Tab**: Update the restaurant name or toggle **"Accept new parties"** (open/closed). When closed, existing waiting parties can still be seated or cancelled, but new arrivals are paused.
- **Tables Tab**: View room inventory and table availability. Click **"Add table"** to add new tables with specified seating capacities and areas. Edit tables to change capacity or toggle active availability.
- **Staff Tab**: View staff accounts. Click **"Add staff"** to create new host or manager accounts. Click **"Disable"** / **"Enable"** to toggle account access (the system prevents disabling the last active manager).

---

## Running the Tests

Four automated verification suites are available. Run the relevant suite for your change, or all four for a full check:

### 1. Backend Tests (Pytest)
Tests API endpoints, session authentication, role permissions, seating and table release, database behavior, and CORS headers. Tests use isolated stores; do not configure them to use a development database containing data you need:
```powershell
cd .\restaurant-wailist-manager\backend
uv run pytest
```

### 2. Frontend Unit Tests (Node Test Runner)
Tests API field mapping, payload formatting, session handling, and API error parsing:
```powershell
cd .\restaurant-wailist-manager\frontend
npm test
```

### 3. Live End-to-End Integration Test
Starts a live FastAPI server and exercises real HTTP requests through the frontend `backendApi.js` client:
```powershell
cd .\restaurant-wailist-manager
node test-connection.mjs
```

### 4. Agent Relay API and PostgreSQL Integration Test
This opt-in test registers two uniquely named agents, sends and completes a task through the live Agent Relay HTTP API, then checks the persisted agent, task, and attempt records in PostgreSQL. It adds test records and does not clear or reset the live database.

Start Agent Relay and make its API and PostgreSQL reachable locally. With the local kind cluster selected, run these commands in separate terminals:

```powershell
kubectl -n agent-relay port-forward service/agent-relay 8001:8000
kubectl -n agent-relay port-forward service/postgres 15432:5432
```

From the `ai-dev-tools` repository root, run the test using Agent Relay's Python environment (which includes `psycopg`):

```powershell
uv run --project .\agent-relay pytest -p no:cacheprovider .\restaurant-wailist-manager\backend\tests\test_agent_relay_integration.py
```

By default, the test connects to `http://127.0.0.1:8001` and `postgresql+psycopg://relay:relay-local-only@127.0.0.1:15432/agent_relay`, matching the local kind setup. If these default endpoints are unavailable, pytest skips the test. Set `AGENT_RELAY_INTEGRATION_BASE_URL` and/or `AGENT_RELAY_INTEGRATION_DATABASE_URL` to override them; when either is explicitly set, connection failures fail the test instead of skipping. The test performs real writes, so use a development Agent Relay database.
