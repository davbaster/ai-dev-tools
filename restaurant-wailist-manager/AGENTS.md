# AGENTS.md — HostBoard (Restaurant Waitlist Manager)

This document provides context, technical specifications, domain rules, operational commands, and coding guidelines for AI agents (such as Google Antigravity, OpenAI Codex, Anthropic Claude) working in this repository.

---

## 1. Project Overview

**HostBoard** is a real-time restaurant waitlist and floor management application designed for host stands and managers during live meal services.

### Core Capabilities
- **Live Waitlist Queue**: First-in, first-served (FIFO) queue for walk-in parties. Supports party size, seating preference (Dining room, Patio, Bar), and operational notes (allergies, high chairs, celebrations).
- **Floor & Table Assignment**: Tracks real-time table occupancy, matching party sizes with table capacities in active seating areas.
- **Role-Based Access Control**:
  - `host`: Operates the board (adds, edits, cancels, seats parties).
  - `manager`: Full host capabilities plus room settings, table inventory CRUD, and staff account management.
- **Service Day Scoping & History**: Differentiates active waiting parties from completed history (`seated` or `cancelled`) for the active service day.

---

## 2. Architecture & Technology Stack

```
restaurant-wailist-manager/
├── backend/                  # FastAPI (Python 3.13) + SQLAlchemy 2.0
│   ├── app/
│   │   ├── database.py       # Database-agnostic engine, sessionmaker, UTCDateTime, DATABASE_URL config
│   │   ├── models.py         # SQLAlchemy ORM models (Restaurant, Area, Table, User, Entry, TableAssignment, UserSession)
│   │   ├── main.py           # FastAPI routes, Pydantic schemas, auth cookies, CORS, session middleware
│   │   └── store.py          # SQLAlchemyStore domain store & in-memory MockStore for testing
│   ├── tests/
│   │   ├── test_api.py       # API unit tests (auth, permissions, status transitions)
│   │   ├── test_database.py  # Database engine, persistence, foreign keys, transactions, FIFO ordering
│   │   └── test_frontend_integration.py # CORS preflight & frontend API contract flows
│   └── pyproject.toml        # uv package configuration & dependencies
├── frontend/                 # React 19 + Vite 8
│   ├── src/
│   │   ├── api/
│   │   │   ├── backendApi.js # Centralized HTTP client, camelCase <-> snake_case mappers
│   │   │   └── backendApi.test.js # Frontend unit tests (Node test runner)
│   │   ├── App.jsx           # Main UI shell, views, modals, and mutation flows
│   │   ├── main.jsx          # React DOM entry point
│   │   └── styles.css        # Modular design system styling
│   ├── vite.config.js        # Vite dev server with proxy to backend (:8000)
│   └── package.json          # Node dependencies & test scripts
├── _docs/                    # Product and technical specifications
│   ├── specs.md              # Functional specifications
│   └── backend-specs.md      # Detailed backend API contract & architecture spec
├── test-connection.mjs       # Live end-to-end HTTP integration test runner
└── README.md                 # Human-facing quickstart & documentation
```

### Stack Details
- **Backend**: FastAPI, SQLAlchemy 2.0, Pydantic v2, `pwdlib[argon2]`, `uvicorn`, managed via `uv`.
- **Database**: Database-agnostic persistence layer using SQLAlchemy ORM. Configurable via `DATABASE_URL` environment variable (defaults to SQLite `sqlite:///./hostboard.db`; supports PostgreSQL, MySQL, and other SQL dialects without code changes).
- **Frontend**: React 19, Lucide React icons, Vite 8, native ES modules.
- **Authentication**: HTTP-only session cookies (`hostboard_session`) backed by persistent database sessions in `user_sessions` table.
- **CORS & Proxying**:
  - Backend allows origins `http://localhost:5173` and `http://127.0.0.1:5173` with credentials.
  - Frontend dev server proxies `/api` requests to `http://localhost:8000`.

---

## 3. Environment Setup & Run Commands

All commands below assume execution from the workspace root (`c:\DATA\Cursos\ai-dev-tools`) or inside `restaurant-wailist-manager`.

### Backend
```powershell
cd .\restaurant-wailist-manager\backend
uv sync --dev
uv run uvicorn app.main:app --reload --port 8000
```
- API Docs (Swagger): <http://localhost:8000/docs>
- Openapi Schema: <http://localhost:8000/openapi.json>

### Frontend
```powershell
cd .\restaurant-wailist-manager\frontend
npm install
npm run dev
```
- Local Application: <http://localhost:5173/>

---

## 4. Test Suites & Verification

Always run all three test suites before submitting or finalizing any code changes:

### 1. Backend Pytest
Verifies status transitions, authentication, authorization, validation, FIFO ordering, and CORS headers:
```powershell
cd .\restaurant-wailist-manager\backend
uv run pytest
```

### 2. Frontend Unit Tests (Node Test Runner)
Tests API client mappers, payload transformation, session handling, and structured error parsing:
```powershell
cd .\restaurant-wailist-manager\frontend
npm test
```

### 3. Live End-to-End HTTP Integration Test
Spins up a live FastAPI test server on an isolated port and exercises full host and manager workflows using the actual `backendApi.js` client over the network:
```powershell
cd .\restaurant-wailist-manager
node test-connection.mjs
```

---

## 5. Domain Rules & Invariants

When implementing or modifying features, agents **must strictly preserve** these invariants:

1. **FIFO Position Invariance**:
   - Queue position is determined strictly by the server-side `created_at` timestamp.
   - Editing party details (`PATCH /api/waitlist/{id}/`) **must not** modify `created_at` or change the party's position in line.
2. **Terminal State Immutability**:
   - Only `waiting` parties can be edited, seated, or cancelled.
   - Once an entry is `seated` or `cancelled`, it is immutable. Any attempt to modify or transition it must return `409 invalid_status_transition`.
3. **Table Seating Rules**:
   - A table can be assigned to a party only if:
     - `table.is_active == True`
     - Table is not already occupied (`table.id not in occupied_table_ids`)
     - `table.capacity >= party.party_size` (violating this returns `409 table_too_small`).
   - If already occupied or inactive, return `409 table_unavailable`.
4. **Duplicate Phone Detection**:
   - Phone numbers are normalized to numeric digits for matching (`phone_normalized`).
   - Duplicate phone numbers within the current service day produce a warning (`duplicate_phone`), but **do not block** the request.
5. **Restaurant Closed Status**:
   - When `restaurant.is_open == False`, new entries (`POST /api/waitlist/`) must be rejected with `409 restaurant_closed`.
   - Viewing the board, updating existing waiting parties, seating, and cancellations remain allowed while closed.
6. **Table Release & Turnover**:
   - Both **hosts** and **managers** can mark an occupied table as free via `POST /api/tables/{table_id}/release/`.
   - Releasing a table closes the active `TableAssignment` (`released_at = utc_now()`) and returns the table to `available`.
   - The waitlist entry remains in `seated` status in today's completed history (it is not put back into the queue).
   - Releasing an unoccupied table must return `409 table_not_occupied`.
7. **Manager Invariants**:
   - At least one active manager must exist at all times. Disabling the last active manager must return `409 last_manager_required`.
   - Occupied tables cannot be deactivated (`409 table_occupied`).
   - Table names must be unique case-insensitively (`409 duplicate_table_name`).

---

## 6. API & Data Contract Conventions

The frontend and backend use differing naming conventions. All transformations are encapsulated in `frontend/src/api/backendApi.js`:

| Concept | Backend Field (`snake_case`) | Frontend Field (`camelCase`) |
|---|---|---|
| Waitlist Entry | `guest_name` | `guestName` |
| | `party_size` | `partySize` |
| | `seating_preference` | `seatingPreference` (null mapped to `'No preference'`) |
| | `created_at` | `createdAt` |
| | `assigned_table_id` | `assignedTableId` |
| | `created_by` | `createdBy` |
| Table | `area_id` | `areaId` |
| | `is_active` | `isActive` |
| | `availability` | `availability` (`'available'`, `'occupied'`, `'inactive'`) |
| Restaurant | `is_open` | `isOpen` |
| | `service_label` | `serviceLabel` |
| User | `is_active` | `isActive` |

### Error Response Contract
Backend errors must adhere to this predictable structure:
```json
{
  "error": {
    "code": "validation_error",
    "message": "Review the highlighted fields.",
    "fields": {
      "phone": ["Phone number must be at least 7 digits."]
    }
  }
}
```

---

## 7. Demo Accounts & Seed Data

Development seeds are defined in `backend/app/store.py`:

| Role | Name | Email (Identifier) | Password | Access Scope |
|---|---|---|---|---|
| **Manager** | Maya Chen | `maya@juneandpine.com` | `demo1234` | Full access (waitlist, tables, settings, staff) |
| **Host** | Luca Rivera | `luca@juneandpine.com` | `demo1234` | Waitlist operations only |
| **Host** | Nora Bell | `nora@juneandpine.com` | `demo1234` | Waitlist operations only |

---

## 8. Development Guidelines for Agents

- **File Encoding**: Always ensure new or modified files are saved in standard **UTF-8** (avoid UTF-16LE / BOM).
- **Backend Storage**: The backend uses a database-agnostic persistence layer built with SQLAlchemy 2.0 (`app/store.py`, `app/models.py`, `app/database.py`). It connects to SQLite by default (`hostboard.db`) and supports any relational SQL engine via `DATABASE_URL`. Testing uses `MockStore`, an isolated in-memory SQLite store with `StaticPool` that resets schema and seed data cleanly on each test run.
- **Frontend State**: The UI reads session info from `backendApi.getSession()` and refreshes dashboard data via `api.getDashboard()` after mutations. Keep API interactions centralized within `backendApi.js`.
- **Pre-commit Checks**: Run `npm test`, `uv run pytest`, and `node test-connection.mjs` before concluding any feature or bug fix.
