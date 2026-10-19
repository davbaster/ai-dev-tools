# HostBoard Backend Specifications

## 1. Purpose

This document defines the backend contract required by the HostBoard frontend in `restaurant-wailist-manager/frontend/`.

The current frontend uses `src/api/mockApi.js` as a local replacement for these backend calls. The backend must preserve the same user-visible behavior while moving authentication, authorization, persistence, validation, ordering, and concurrency control to the server.

The MVP is a single-restaurant, staff-only waitlist system. Guests do not authenticate, join the queue, or receive notifications.

## 2. Recommended Backend Stack

The workspace already uses Python and has `uv` available. The recommended implementation is:

- Python managed with `uv`.
- Django for the web framework and ORM.
- Django REST Framework for JSON API endpoints and serializers.
- Django's password hashing and session authentication.
- SQLite for local development, with PostgreSQL recommended for deployment.

The API should be served under `/api/`. During local development, configure the Vite dev server to proxy `/api` to Django so browser requests remain same-origin from the frontend's perspective.

The backend must remain independent of the mock implementation. The frontend should eventually replace `mockApi` methods with `fetch` calls against these endpoints without changing the UI behavior.

## 3. Backend Responsibilities

The backend is responsible for:

- Authenticating staff users.
- Enforcing host and manager permissions server-side.
- Scoping all operational data to the configured restaurant and service day.
- Validating and normalizing request data.
- Returning stable IDs and timestamps.
- Preserving FIFO order after edits.
- Preventing a table from being assigned twice concurrently.
- Recording the staff member responsible for mutations.
- Returning structured validation and conflict errors.
- Managing service-day rollover and current-day history retention.

The frontend is responsible for presentation, local form state, optimistic visual feedback only when safe, and refreshing the dashboard after successful mutations.

## 4. Authentication and Sessions

### 4.1 Login

`POST /api/auth/login/`

Request:

```json
{
  "identifier": "maya@juneandpine.com",
  "password": "demo1234"
}
```

Behavior:

- Match the identifier case-insensitively after trimming whitespace.
- Reject inactive users.
- Authenticate using Django's password hasher.
- Create an authenticated HttpOnly session cookie.
- Return the authenticated user summary.

Response `200`:

```json
{
  "user": {
    "id": "user-1",
    "name": "Maya Chen",
    "identifier": "maya@juneandpine.com",
    "role": "manager"
  }
}
```

Invalid credentials return `401`:

```json
{
  "error": {
    "code": "invalid_credentials",
    "message": "The identifier or password is incorrect."
  }
}
```

Do not reveal whether the identifier exists or whether the account is disabled.

### 4.2 Current session

`GET /api/auth/session/`

- Return the same user summary as login for an authenticated request.
- Return `401` when there is no active session.
- Never return a password, password hash, or temporary password.

### 4.3 Logout

`POST /api/auth/logout/`

- Invalidate the current session.
- Return `204`.
- Be idempotent for an already expired session.

### 4.4 Authentication security

- Use HttpOnly, Secure cookies in production.
- Use SameSite protection appropriate to the deployment topology.
- Protect all state-changing endpoints against CSRF when using cookie authentication.
- Apply login throttling or rate limiting before production.
- Log authentication failures without logging passwords.

## 5. Roles and Permissions

The backend supports two roles:

- `host`: operates the live waitlist and views current-day history.
- `manager`: all host capabilities plus restaurant, table, and staff administration.

Permission enforcement must happen in Django/DRF permissions, not only in the frontend navigation.

| Capability | Host | Manager |
|---|---:|---:|
| View dashboard | Yes | Yes |
| Add a waiting party | Yes | Yes |
| Edit a waiting party | Yes | Yes |
| Cancel a waiting party | Yes | Yes |
| Seat a waiting party | Yes | Yes |
| View current-day history | Yes | Yes |
| View table availability | Yes | Yes |
| Create/edit/deactivate tables | No | Yes |
| Edit restaurant settings | No | Yes |
| Create/disable staff accounts | No | Yes |
| Change staff roles | No | Yes |

Protect the last active manager account from being disabled or demoted. Return `409 last_manager_required` when an operation would leave the restaurant without an active manager.

## 6. Tenant and Service-Day Scope

The MVP has one restaurant, but every operational model should still carry a `restaurant_id` or an equivalent foreign key so multi-location support can be added later without rewriting the domain model.

### 6.1 Restaurant settings

Required fields:

- `id`
- `name`
- `is_open`
- `timezone`
- `service_label`
- `created_at`
- `updated_at`

Initial seed values:

```json
{
  "name": "June & Pine",
  "is_open": true,
  "timezone": "America/New_York",
  "service_label": "Dinner service"
}
```

### 6.2 Service day

A service day is identified by the restaurant's local date, not the server's UTC date.

Fields:

- `id`
- `restaurant_id`
- `service_date`
- `opened_at`, nullable
- `closed_at`, nullable
- `created_at`
- `updated_at`

Rules:

- Resolve the current service day using `RestaurantSettings.timezone`.
- Create the current service-day row lazily if it does not exist.
- Queue and history queries must always include the current service day.
- A new service day must not show previous-day entries in the active queue.
- Previous-day retention is configurable; the MVP may retain records in the database while hiding them from the current-day UI.

## 7. Domain Models

### 7.1 Staff user

Use Django's user model or a custom user model with these additional fields:

- `id`
- `name`
- `identifier` or email, unique case-insensitively
- `password_hash`
- `role`: `host` or `manager`
- `is_active`
- `created_at`
- `updated_at`

Do not expose password-related fields through API serializers.

### 7.2 Seating area

Fields:

- `id`
- `restaurant_id`
- `name`
- `is_active`
- `sort_order`
- `created_at`
- `updated_at`

Seed areas:

- Dining room
- Patio
- Bar

The frontend currently uses seating areas as the party preference list. Keep the API response stable by returning active areas in display order.

### 7.3 Table

Fields:

- `id`
- `restaurant_id`
- `name`
- `capacity`
- `area_id`, nullable
- `is_active`
- `created_at`
- `updated_at`

Constraints:

- `capacity` must be a positive integer.
- `name` must be unique within a restaurant.
- Inactive tables remain stored so historical assignments remain readable.
- Inactive tables cannot be selected for new seating.

The frontend derives occupancy from seated waitlist entries. The backend should return an explicit `availability` field in dashboard table responses so the frontend does not need to reproduce concurrency-sensitive logic.

Example table response:

```json
{
  "id": "table-4",
  "name": "T04",
  "capacity": 4,
  "area_id": "area-2",
  "is_active": true,
  "availability": "available"
}
```

Allowed availability values: `available`, `occupied`, `inactive`.

### 7.4 Waitlist entry

Fields:

- `id`
- `restaurant_id`
- `service_day_id`
- `guest_name`
- `phone_display`
- `phone_normalized`
- `party_size`
- `seating_preference`, nullable
- `notes`, nullable
- `status`: `waiting`, `seated`, or `cancelled`
- `created_at`
- `updated_at`
- `seated_at`, nullable
- `cancelled_at`, nullable
- `created_by_id`
- `updated_by_id`, nullable
- `completed_by_id`, nullable
- `assigned_table_id`, nullable

Rules:

- `guest_name` is required after trimming.
- `phone_display` preserves the staff-entered display value.
- `phone_normalized` is used for duplicate detection and indexed for active-entry lookups.
- `party_size` must be a positive integer.
- `seating_preference` must be `null` or reference an active configured area; `No preference` may be represented as `null`.
- `notes` is optional and must have a reasonable maximum length, such as 500 characters.
- Queue order is `created_at ASC, id ASC`.
- Editing a waiting entry must not change `created_at`.
- Seated and cancelled entries are read-only through the MVP API.

## 8. Waitlist State Transitions

Allowed transitions:

```text
waiting -> seated
waiting -> cancelled
```

Disallowed transitions:

```text
seated -> waiting
cancelled -> waiting
seated -> cancelled
cancelled -> seated
```

The server must reject invalid transitions with `409 invalid_status_transition`.

### 8.1 Duplicate phone behavior

A phone match among active `waiting` entries is a warning, not a validation failure.

The create and update responses should include:

```json
{
  "warnings": [
    {
      "code": "duplicate_phone",
      "message": "Another active party uses this phone number.",
      "matching_entries": [
        {
          "id": "entry-1",
          "guest_name": "Olivia Park"
        }
      ]
    }
  ]
}
```

The frontend may save the entry after showing this warning.

## 9. Dashboard API

### 9.1 Get dashboard

`GET /api/dashboard/`

Optional query parameters:

- `service_date=YYYY-MM-DD` for manager diagnostics only; default is current service day.
- `include=users` should be restricted to managers. Hosts do not need the full staff list.

Response `200`:

```json
{
  "restaurant": {
    "id": "restaurant-1",
    "name": "June & Pine",
    "is_open": true,
    "timezone": "America/New_York",
    "service_label": "Dinner service"
  },
  "service_day": {
    "id": "service-day-2026-09-28",
    "date": "2026-09-28"
  },
  "areas": [],
  "tables": [],
  "entries": [],
  "users": []
}
```

Response rules:

- `entries` includes current-day waiting, seated, and cancelled entries.
- Sort entries by `created_at ASC, id ASC`; the frontend separates active queue and history.
- Include `assigned_table` summary for seated entries.
- Include `created_by`, `updated_by`, and `completed_by` display summaries where the current user is authorized to see them.
- Return an empty `users` array or omit it for hosts; do not leak staff administration data.
- Compute table `availability` on the server.

A future implementation may split this into smaller endpoints, but the aggregate endpoint matches the current frontend refresh model and is acceptable for the MVP.

## 10. Waitlist Endpoints

### 10.1 Create entry

`POST /api/waitlist/`

Request:

```json
{
  "guest_name": "Rina Alvarez",
  "phone": "(718) 555-0199",
  "party_size": 3,
  "seating_preference": "Patio",
  "notes": "Window if possible"
}
```

Behavior:

- Require an authenticated host or manager.
- Resolve the current service day.
- Reject new entries when the restaurant is closed, unless the closed-state policy is explicitly changed.
- Normalize the phone number before storing.
- Create the entry with status `waiting` and the server timestamp.
- Record the authenticated user as `created_by`.
- Return duplicate-phone warnings without blocking creation.

Response `201`:

```json
{
  "entry": {},
  "warnings": []
}
```

### 10.2 Update entry

`PATCH /api/waitlist/{entry_id}/`

Accepted fields:

```json
{
  "guest_name": "Rina Alvarez",
  "phone": "(718) 555-0199",
  "party_size": 3,
  "seating_preference": "Patio",
  "notes": "Window if possible"
}
```

Rules:

- Only `waiting` entries may be edited.
- Preserve `created_at` and FIFO position.
- Record `updated_at` and `updated_by`.
- Return duplicate-phone warnings as with create.

### 10.3 Cancel entry

`POST /api/waitlist/{entry_id}/cancel/`

- Require an authenticated host or manager.
- Only a waiting entry can be cancelled.
- Set `status = cancelled`, `cancelled_at`, and `completed_by`.
- Return the updated entry.
- A confirmation dialog is a frontend concern; the server operation is irreversible in the MVP.

Response `200`:

```json
{
  "entry": {}
}
```

### 10.4 Seat entry

`POST /api/waitlist/{entry_id}/seat/`

Request:

```json
{
  "table_id": "table-4"
}
```

The operation must be atomic:

1. Begin a database transaction.
2. Lock the waitlist entry and selected table row.
3. Verify the entry is still `waiting`.
4. Verify the table is active.
5. Verify the table has no active assignment.
6. Verify `table.capacity >= entry.party_size`.
7. Set the entry to `seated`, assign the table, set `seated_at`, and record `completed_by`.
8. Commit the transaction.

If another request wins the table first, return `409 table_unavailable`. Never return success for a partially completed party/table update.

Possible conflict response:

```json
{
  "error": {
    "code": "table_unavailable",
    "message": "That table is no longer available."
  }
}
```

Possible capacity response:

```json
{
  "error": {
    "code": "table_too_small",
    "message": "That table is too small for this party."
  }
}
```

## 11. Table Administration Endpoints

Manager-only endpoints:

### 11.1 List tables

`GET /api/tables/`

Return active and inactive tables with current availability, capacity, and area summary.

### 11.2 Create table

`POST /api/tables/`

Request:

```json
{
  "name": "P01",
  "capacity": 2,
  "area_id": "area-2"
}
```

The server sets `is_active = true` unless an explicit manager-only import flow says otherwise.

### 11.3 Update table

`PATCH /api/tables/{table_id}/`

Request may include:

```json
{
  "name": "P01",
  "capacity": 2,
  "area_id": "area-2",
  "is_active": true
}
```

Rules:

- Do not delete tables that appear in current-day or historical assignments.
- Deactivating an occupied table must be rejected with `409 table_occupied` or allowed only after its assignment is resolved. The implementation must choose one policy explicitly.
- Capacity changes must not invalidate an existing assignment without an explicit manager workflow.

## 12. Restaurant Settings Endpoints

Manager-only:

### 12.1 Read settings

`GET /api/settings/restaurant/`

### 12.2 Update settings

`PATCH /api/settings/restaurant/`

Request:

```json
{
  "name": "June & Pine",
  "is_open": true,
  "service_label": "Dinner service"
}
```

Rules:

- `timezone` should be changed only through a controlled administrative operation because it affects service-day boundaries.
- When `is_open = false`, authenticated staff may continue reading the queue and history, but creating new parties returns `409 restaurant_closed`.
- The setting update must record the manager and timestamp in the audit log.

## 13. Seating Area Endpoints

Manager-only configuration endpoints:

- `GET /api/areas/`
- `POST /api/areas/`
- `PATCH /api/areas/{area_id}/`

The frontend currently displays areas from the dashboard and does not yet expose area CRUD controls. Implement read support for the current UI; write support can be delivered with the manager settings expansion.

## 14. Staff Administration Endpoints

Manager-only:

### 14.1 List staff

`GET /api/staff/`

Return name, identifier, role, active status, and timestamps. Never return passwords.

### 14.2 Create staff

`POST /api/staff/`

Request:

```json
{
  "name": "Nora Bell",
  "identifier": "nora@juneandpine.com",
  "role": "host"
}
```

The current frontend has no password field, so the backend must create the account in one of these ways:

- Preferred: create an inactive or invite-pending account and issue a one-time password setup link.
- Local MVP: create a temporary random password and return it once over a protected manager response.

Do not silently create a usable account with a known shared password in production.

### 14.3 Enable or disable staff

`POST /api/staff/{user_id}/status/`

Request:

```json
{
  "is_active": false
}
```

Reject disabling the last active manager with `409 last_manager_required`.

### 14.4 Reset password

`POST /api/staff/{user_id}/password-reset/`

This endpoint is required by the product specification even though the current frontend does not expose a reset action.

## 15. Error Contract

All errors should use a predictable shape:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Review the highlighted fields.",
    "fields": {
      "party_size": ["Party size must be a positive whole number."]
    }
  }
}
```

Recommended status codes:

- `400`: malformed request.
- `401`: unauthenticated or invalid login.
- `403`: authenticated but not authorized for the operation.
- `404`: resource not found or not visible to the user.
- `409`: state or concurrency conflict.
- `422`: semantic validation failure, if the API convention uses 422.
- `429`: rate limited.
- `500`: unexpected server failure; do not expose stack traces.

Recommended error codes:

- `invalid_credentials`
- `validation_error`
- `restaurant_closed`
- `duplicate_identifier`
- `duplicate_table_name`
- `invalid_status_transition`
- `table_unavailable`
- `table_too_small`
- `table_occupied`
- `last_manager_required`
- `not_found`

## 16. Audit Log

Create an audit log for security-sensitive and operational mutations.

Fields:

- `id`
- `restaurant_id`
- `actor_id`
- `action`
- `resource_type`
- `resource_id`
- `metadata` JSON, with phone numbers and notes redacted where practical
- `created_at`

At minimum, log:

- Login failure.
- Login success.
- Party created, edited, cancelled, and seated.
- Table created, edited, activated, and deactivated.
- Restaurant settings changed.
- Staff created, enabled, disabled, role changed, or password reset.

## 17. Table Release & Turnover (Implemented)

The application provides an explicit table turnover action:

- **Model**: `TableAssignment(id, table_id, waitlist_entry_id, assigned_at, assigned_by_id, released_at, released_by_id)`.
- **Occupancy Rule**: A table is occupied when it has an assignment where `released_at IS NULL`.
- **Endpoint**: `POST /api/tables/{table_id}/release/`.
- **Permissions**: Authenticated hosts and managers.
- **Invariants**:
  - The waitlist entry remains in `seated` status in current-day history; releasing the table does not put the party back into the waiting line.
  - If the table is not currently occupied, the endpoint returns `409 table_not_occupied`.
  - Once released, the table immediately becomes `available` for new seating assignments.
- **Full Specification**: Refer to `_docs/table-release-spec.md`.

## 18. Frontend Migration Map

Replace each mock method with an API client method:

| Current mock method | Backend request |
|---|---|
| `getSession()` | `GET /api/auth/session/` |
| `login()` | `POST /api/auth/login/` |
| `logout()` | `POST /api/auth/logout/` |
| `getDashboard()` | `GET /api/dashboard/` |
| `createEntry()` | `POST /api/waitlist/` |
| `updateEntry()` | `PATCH /api/waitlist/{id}/` |
| `cancelEntry()` | `POST /api/waitlist/{id}/cancel/` |
| `seatEntry()` | `POST /api/waitlist/{id}/seat/` |
| `updateRestaurant()` | `PATCH /api/settings/restaurant/` |
| `createTable()` | `POST /api/tables/` |
| `updateTable()` | `PATCH /api/tables/{id}/` |
| `createStaff()` | `POST /api/staff/` |
| `toggleStaff()` | `POST /api/staff/{id}/status/` |

Frontend changes required during migration:

- Replace sessionStorage authentication state with the authenticated server session.
- Replace localStorage state with API responses.
- Handle `401` by returning to the login screen.
- Handle `403`, `409`, and validation errors using the existing toast/form error surfaces.
- Refresh dashboard data after each successful mutation.
- Prefer server-provided `availability`, timestamps, user summaries, and warning codes.
- Do not trust hidden manager navigation as an authorization mechanism.

## 19. Seed Data for Local Development

The backend development seed should create:

### Restaurant

- Name: June & Pine
- Timezone: America/New_York
- Service label: Dinner service
- Open: true

### Manager

- Name: Maya Chen
- Identifier: `maya@juneandpine.com`
- Role: `manager`
- Development password: `demo1234`

### Hosts

- Luca Rivera, `luca@juneandpine.com`, role `host`
- Nora Bell, `nora@juneandpine.com`, role `host`
- Development password for both: `demo1234`

The shared demo password is for local development only. Do not use it in a deployed environment.

### Tables and entries

Seed the table and waitlist records represented in `src/api/mockApi.js` so the real backend presents the same first-run experience as the current frontend demo.

## 20. Backend Acceptance Criteria

### Authentication

- A valid active staff user can log in and retrieve the current session.
- An invalid or inactive user receives the same generic `401` response.
- Logout invalidates the session.
- Hosts cannot call manager-only endpoints successfully.

### Queue

- A host can create, edit, cancel, and seat a waiting party.
- FIFO position is based on server `created_at` and does not change after edits.
- Duplicate phone numbers create a warning and do not block the request.
- Closed restaurants reject new entries with a structured conflict.
- Seated and cancelled entries cannot be edited or transitioned back to waiting.

### Tables

- Hosts can read table availability.
- Managers can create, edit, activate, and deactivate tables.
- A table that is inactive, occupied, or too small cannot be selected.
- Concurrent seat requests cannot successfully assign the same table twice.

### History and audit

- Seated and cancelled entries remain visible for the current service day.
- History includes final status, timestamps, assigned table when seated, and responsible staff member.
- Mutating operations record the acting staff user.
- A new service day does not include previous-day entries in the active queue.

## 21. Implementation Order

1. Create the Django project and configure `uv` dependencies.
2. Add the custom user/profile, restaurant, service-day, seating-area, table, waitlist-entry, and audit models.
3. Add migrations and local seed data.
4. Implement authentication and role permissions.
5. Implement dashboard read and waitlist mutations.
6. Implement transactional seating and table availability.
7. Implement manager settings, table, and staff endpoints.
8. Add API tests for validation, permissions, transitions, service-day scoping, and concurrent seating.
9. Replace the frontend mock API with a single HTTP API client.
10. Resolve the table-release decision before production deployment.
