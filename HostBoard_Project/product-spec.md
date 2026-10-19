# HostBoard Product Specification

> Consolidated on 2026-10-14 from the specifications formerly maintained in `_docs/`.

## Contents

- [Product and functional requirements](#restaurant-waitlist-manager-specifications)
- [Backend and API contract](#hostboard-backend-specifications)
- [Table release and turnover](#specification-table-release--turnover-management)


## Restaurant Waitlist Manager Specifications

### 1. Product Summary

Restaurant Waitlist Manager is a desktop web application for restaurant hosts and managers to operate a walk-in waitlist during a service day. Staff can add parties, maintain the queue, view available tables, seat parties, and keep a same-day record of queue activity.

The MVP is intentionally operational and staff-only. Guests do not log in, join the queue, or receive notifications from the application.

### 2. MVP Goals

- Make adding a party fast and reliable at the host stand.
- Keep the active waitlist ordered by FIFO rules.
- Give hosts enough table information to select an available table manually.
- Let staff move parties from waiting to seated or cancelled.
- Let managers configure tables, staff accounts, and basic restaurant settings.
- Preserve the day's activity for operational review while keeping retention limited to the current day.

### 3. Non-Goals

The MVP does not include:

- Guest-facing queue signup or wait-status pages.
- SMS, email, push, or other external notifications.
- Reservations or reservation/walk-in conflict management.
- Multiple restaurant locations.
- Automatic wait-time estimates.
- Automatic table assignment or optimization.
- Analytics dashboards or historical reporting beyond the current day's records.
- A visual floor plan.
- Payments, ordering, loyalty, or CRM features.

### 4. Users and Permissions

#### 4.1 Host

Hosts operate the live queue.

Hosts can:

- Sign in and sign out.
- View the active waitlist.
- Add a waiting party.
- Edit a waiting party.
- See duplicate-phone warnings.
- View available tables and table capacities.
- Select a table and mark a party as seated.
- Cancel a waiting party.
- View current-day completed entries.

Hosts cannot:

- Manage staff accounts.
- Create or edit table inventory.
- Change restaurant settings.

#### 4.2 Manager

Managers have all host permissions and can also:

- Create, edit, activate, and deactivate tables.
- Create, disable, and reset staff accounts.
- Configure the restaurant name, open/closed status, and default seating preferences.
- Review the current day's waitlist activity.

The MVP uses two roles: `host` and `manager`.

### 5. Core Concepts

#### 5.1 Service day

A service day is the current operational day for the restaurant. Active and completed entries are associated with that day. At the start of a new service day, the previous day's entries are archived or hidden from the live queue according to the retention policy.

#### 5.2 Party

A party is a group waiting to be seated. Required party information:

- Guest name.
- Phone number.
- Party size.
- Seating preference.

Optional information:

- Staff notes.

The supported seating preferences should be configurable from a controlled list. The initial list is assumed to include `no preference`, `indoor`, `patio`, and `bar` if those areas exist in the restaurant.

#### 5.3 Table

A table is an individual seating resource configured by a manager.

Each table has:

- Display name or number.
- Seating capacity.
- Seating preference/area, when applicable.
- Active or inactive status.
- Current availability status.

The host selects a table manually when seating a party. The application must show enough information for the host to avoid selecting an unavailable or undersized table.

### 6. Party Lifecycle

The MVP supports these statuses:

- `waiting`: The party is active in the queue.
- `seated`: The party has been assigned a table and removed from the active queue.
- `cancelled`: The party left the queue without being seated.

Only `waiting` parties appear in the active queue.

A waiting party can transition to `seated` or `cancelled`. A seated or cancelled party cannot return to `waiting` in the MVP; staff must create a new entry if needed.

### 7. Functional Requirements

#### FR-1 Authentication

- The application must require staff authentication before showing restaurant operations.
- A user signs in with a username or email and password.
- The application must provide sign-out.
- Disabled staff accounts must not be able to sign in.
- Unauthorized users must not access queue, table, staff, or settings data.

#### FR-2 Active waitlist

- The application must show all `waiting` parties for the current service day.
- Parties must be ordered by creation time, oldest first.
- Each queue row must show at least: position, guest name, party size, phone number, seating preference, time added, and notes when present.
- The queue must make the next party visually obvious without hiding other waiting parties.
- The active queue must update after adding, editing, seating, or cancelling a party.

#### FR-3 Add a party

- A host or manager must be able to add a party from the active waitlist view.
- Guest name, phone number, party size, and seating preference are required.
- Party size must be a positive whole number.
- The phone number must be stored in a normalized format suitable for comparison.
- The application must warn when another active party uses the same phone number, but must allow the new party to be saved.
- A new party receives the next FIFO position based on its creation time.
- The form must prevent accidental duplicate submission.
- Successful creation must return the user to, or visibly update, the active queue.

#### FR-4 Edit a party

- A host or manager must be able to edit a party while it is `waiting`.
- Editable fields include guest name, phone number, party size, seating preference, and notes.
- Editing must not change the party's original queue position or creation time.
- The duplicate-phone warning must also apply when editing a phone number.
- Seated and cancelled entries are read-only in the MVP.

#### FR-5 Cancel a party

- A host or manager must be able to cancel a waiting party.
- The application must require confirmation before cancellation.
- A cancelled party must disappear from the active queue.
- The cancellation must remain visible in the current-day history with its status and timestamp.

#### FR-6 Table inventory

- Managers must be able to create a table with a name/number, capacity, area or seating preference, and active status.
- Managers must be able to edit table details.
- Managers must be able to deactivate a table without deleting its current-day references.
- Inactive tables must not be selectable for new seating actions.
- A table cannot be selected for more than one currently seated party at a time.
- Hosts must be able to view active tables and their availability.

#### FR-7 Seat a party

- A host or manager must be able to start a seating action for a waiting party.
- The application must show active available tables for selection.
- The application must show table capacity and area/preference before confirmation.
- The host selects the table; the application does not auto-assign or reorder the queue.
- The selected table must be marked occupied and the party must become `seated` in one atomic operation.
- A party cannot be seated if the selected table is inactive or already occupied.
- A seated party must leave the active waitlist.
- The current-day record must retain the party, selected table, seating timestamp, and staff member who performed the action.

#### FR-8 Current-day history

- Staff must be able to view seated and cancelled entries from the current service day.
- History must show party details, final status, relevant timestamp, and responsible staff member.
- History must not be mixed into the active waiting queue.
- Previous service-day history is out of scope for the MVP UI and may be archived or deleted according to the final retention implementation.

#### FR-9 Manager settings

Managers must be able to:

- Set the restaurant display name.
- Set the restaurant open/closed status.
- Configure available seating preferences/areas.
- Manage table inventory.
- Manage staff accounts and roles.

A closed restaurant may continue to display the current queue to authenticated staff, but the application should prevent adding new parties unless a manager reopens it. This rule is an assumption to confirm before implementation.

#### FR-10 Staff account management

- Managers must be able to create a staff account with a name, login identifier, role, and temporary password or reset flow.
- Managers must be able to disable a staff account.
- Managers must be able to reset a staff member's password.
- A manager must not accidentally remove the last active manager account.
- Staff account changes must take effect on the next authenticated request or session refresh.

### 8. Primary Workflows

#### 8.1 Add a waiting party

1. Host opens the active waitlist.
2. Host selects `Add party`.
3. Host enters name, phone, party size, seating preference, and optional notes.
4. The application validates required fields.
5. If the phone matches an active party, the application shows a warning.
6. Host confirms the save.
7. The application creates the party with status `waiting` and places it at the end of the queue.

#### 8.2 Seat a party

1. Host selects a waiting party.
2. Host selects `Seat party`.
3. The application shows active available tables.
4. Host selects a table and confirms.
5. The application marks the table occupied and the party seated atomically.
6. The party leaves the active queue and appears in current-day history.

#### 8.3 Cancel a party

1. Host selects a waiting party.
2. Host selects `Cancel`.
3. The application asks for confirmation.
4. Host confirms.
5. The application sets the status to `cancelled`, records the timestamp and staff member, and removes the party from the active queue.

#### 8.4 Configure a table

1. Manager opens table settings.
2. Manager creates or edits a table.
3. Manager enters the table identifier, capacity, and area/preference.
4. Manager saves the table.
5. The table becomes available for host selection when active and unoccupied.

### 9. Suggested Data Model

#### User

- `id`
- `name`
- `login_identifier`
- `password_hash`
- `role`: `host` or `manager`
- `is_active`
- `created_at`
- `updated_at`

#### RestaurantSettings

- `id`
- `name`
- `is_open`
- `timezone`
- `created_at`
- `updated_at`

#### SeatingArea

- `id`
- `name`
- `is_active`
- `created_at`
- `updated_at`

#### Table

- `id`
- `restaurant_id`
- `name_or_number`
- `capacity`
- `seating_area_id`, nullable
- `is_active`
- `created_at`
- `updated_at`

#### ServiceDay

- `id`
- `restaurant_id`
- `date`
- `opened_at`, nullable
- `closed_at`, nullable

#### WaitlistEntry

- `id`
- `service_day_id`
- `guest_name`
- `phone_number`
- `party_size`
- `seating_preference`, nullable
- `notes`, nullable
- `status`: `waiting`, `seated`, or `cancelled`
- `created_at`
- `updated_at`
- `seated_at`, nullable
- `cancelled_at`, nullable
- `created_by_user_id`
- `updated_by_user_id`, nullable
- `completed_by_user_id`, nullable
- `assigned_table_id`, nullable

#### Operational constraints

- Active queue queries must filter by the current service day and `status = waiting`.
- Queue ordering must use `created_at` plus a stable tie-breaker such as `id`.
- A table must have at most one active seating assignment.
- A phone duplicate check applies to active waiting entries and generates a warning, not a validation error.
- Party size and table capacity must be positive integers.

### 10. Screens and Interface Requirements

#### Login

- Login identifier field.
- Password field.
- Clear validation and authentication error states.
- No operational data visible before authentication.

#### Active waitlist

- Restaurant name and open/closed indicator.
- Current service date.
- Primary `Add party` action.
- Ordered queue with clear positions.
- Actions for edit, seat, and cancel.
- Link or tab to current-day history.
- Link to settings for managers only.
- Empty state when no parties are waiting.
- Loading, validation, permission, and save-error states.

#### Party form

- Name input.
- Phone input.
- Party-size numeric input.
- Seating-preference select.
- Notes textarea.
- Duplicate-phone warning state.
- Save and cancel actions.
- Inline validation that preserves entered values.

#### Seating flow

- Party summary.
- Available table list.
- Table identifier, capacity, area, and availability.
- Confirmation action.
- Clear error if a table became occupied while the screen was open.

#### Current-day history

- Separate waiting, seated, and cancelled status presentation.
- Timestamp and responsible staff member.
- Empty state.

#### Manager settings

- Restaurant settings.
- Table inventory.
- Staff accounts.
- Permission restrictions for host users.

The primary operating environment is a desktop browser at a host stand. The interface should remain usable at common laptop and desktop widths, but tablet optimization is not a release requirement.

### 11. Non-Functional Requirements

#### Performance

- The active waitlist should load in under two seconds under normal single-restaurant operating conditions.
- Add, edit, cancel, and seat actions should show confirmation or an actionable error within two seconds under normal conditions.
- The queue should not require a full page reload after routine actions.

#### Reliability and consistency

- Seating must update both the party and table state atomically.
- Concurrent attempts to use one table must result in only one successful assignment.
- The application must not silently lose a party after a failed save.
- Destructive or irreversible actions must require confirmation.

#### Security

- Passwords must be stored using a modern password-hashing mechanism.
- Authenticated requests must enforce role permissions server-side.
- Guest phone numbers and notes must not be exposed to unauthenticated users.
- Forms that mutate data must be protected against cross-site request forgery where applicable.
- Input must be validated and escaped to prevent injection and script execution.

#### Accessibility

- All controls must be keyboard reachable.
- Form fields must have programmatic labels.
- Status and validation messages must be understandable without color alone.
- Focus state must remain visible.
- Confirmation dialogs must be operable by keyboard.

#### Auditability

- Mutating operations must record the responsible staff member and timestamp.
- The application should log authentication failures and permission failures without logging raw passwords.

### 12. Acceptance Criteria

#### Queue operation

- A host can sign in and see the current day's active queue.
- A host can add a valid party and see it at the end of the queue.
- A host can edit a waiting party without changing its position.
- A host can cancel a party after confirmation and see it removed from the active queue.
- A host can seat a party by selecting an available table.
- A seated party no longer appears in the active queue and appears in history.

#### Queue rules

- Parties are displayed oldest first.
- Duplicate phone numbers produce a warning but do not block saving.
- A party cannot be seated at an inactive or occupied table.
- Two simultaneous seating actions cannot assign the same table.

#### Permissions

- A host cannot access manager settings or mutate table/staff configuration.
- A manager can manage tables, staff accounts, and restaurant settings.
- Disabled users cannot sign in.

#### Data and history

- Current-day seated and cancelled entries remain viewable with their final status.
- Every seating and cancellation records a timestamp and staff member.
- Starting a new service day does not place old entries in the new active queue.

### 13. Open Decisions and Assumptions

The following items should be confirmed before implementation:

1. Exact service-day rollover time and restaurant timezone.
2. Whether closing the restaurant blocks adding new parties. This spec currently assumes yes.
3. Exact seating preference values and whether each table may support more than one preference.
4. Phone-number format and normalization rules by country/region.
5. Table release behavior: Implemented via explicit turnover action `POST /api/tables/{table_id}/release/` and `TableAssignment` records. Releasing a table clears the table's occupied state while keeping the seated entry in current-day history. See the Table Release & Turnover Management section of this document.
6. Whether managers can edit or delete current-day entries. This spec currently treats seated and cancelled entries as read-only.
7. Whether the first manager account is seeded administratively or created through an initial setup flow.
8. Whether same-day history should be archived, deleted, or retained in the database but hidden after the day ends.

### 14. Future Enhancements

- Guest-facing waitlist signup and status tracking.
- SMS or email notifications.
- No-show status and configurable grace periods.
- Automatic wait estimates.
- Table recommendations based on party size and seating preference.
- Table combinations for large parties.
- Reservations.
- Multi-location support.
- Historical analytics and operational reporting.
- Tablet-optimized and mobile host workflows.


## HostBoard Backend Specifications

### 1. Purpose

This document defines the backend contract required by the HostBoard frontend in `restaurant-wailist-manager/frontend/`.

The current frontend uses `src/api/mockApi.js` as a local replacement for these backend calls. The backend must preserve the same user-visible behavior while moving authentication, authorization, persistence, validation, ordering, and concurrency control to the server.

The MVP is a single-restaurant, staff-only waitlist system. Guests do not authenticate, join the queue, or receive notifications.

### 2. Recommended Backend Stack

The workspace already uses Python and has `uv` available. The recommended implementation is:

- Python managed with `uv`.
- Django for the web framework and ORM.
- Django REST Framework for JSON API endpoints and serializers.
- Django's password hashing and session authentication.
- SQLite for local development, with PostgreSQL recommended for deployment.

The API should be served under `/api/`. During local development, configure the Vite dev server to proxy `/api` to Django so browser requests remain same-origin from the frontend's perspective.

The backend must remain independent of the mock implementation. The frontend should eventually replace `mockApi` methods with `fetch` calls against these endpoints without changing the UI behavior.

### 3. Backend Responsibilities

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

### 4. Authentication and Sessions

#### 4.1 Login

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

#### 4.2 Current session

`GET /api/auth/session/`

- Return the same user summary as login for an authenticated request.
- Return `401` when there is no active session.
- Never return a password, password hash, or temporary password.

#### 4.3 Logout

`POST /api/auth/logout/`

- Invalidate the current session.
- Return `204`.
- Be idempotent for an already expired session.

#### 4.4 Authentication security

- Use HttpOnly, Secure cookies in production.
- Use SameSite protection appropriate to the deployment topology.
- Protect all state-changing endpoints against CSRF when using cookie authentication.
- Apply login throttling or rate limiting before production.
- Log authentication failures without logging passwords.

### 5. Roles and Permissions

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

### 6. Tenant and Service-Day Scope

The MVP has one restaurant, but every operational model should still carry a `restaurant_id` or an equivalent foreign key so multi-location support can be added later without rewriting the domain model.

#### 6.1 Restaurant settings

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

#### 6.2 Service day

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

### 7. Domain Models

#### 7.1 Staff user

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

#### 7.2 Seating area

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

#### 7.3 Table

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

#### 7.4 Waitlist entry

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

### 8. Waitlist State Transitions

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

#### 8.1 Duplicate phone behavior

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

### 9. Dashboard API

#### 9.1 Get dashboard

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

### 10. Waitlist Endpoints

#### 10.1 Create entry

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

#### 10.2 Update entry

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

#### 10.3 Cancel entry

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

#### 10.4 Seat entry

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

### 11. Table Administration Endpoints

Manager-only endpoints:

#### 11.1 List tables

`GET /api/tables/`

Return active and inactive tables with current availability, capacity, and area summary.

#### 11.2 Create table

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

#### 11.3 Update table

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

### 12. Restaurant Settings Endpoints

Manager-only:

#### 12.1 Read settings

`GET /api/settings/restaurant/`

#### 12.2 Update settings

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

### 13. Seating Area Endpoints

Manager-only configuration endpoints:

- `GET /api/areas/`
- `POST /api/areas/`
- `PATCH /api/areas/{area_id}/`

The frontend currently displays areas from the dashboard and does not yet expose area CRUD controls. Implement read support for the current UI; write support can be delivered with the manager settings expansion.

### 14. Staff Administration Endpoints

Manager-only:

#### 14.1 List staff

`GET /api/staff/`

Return name, identifier, role, active status, and timestamps. Never return passwords.

#### 14.2 Create staff

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

#### 14.3 Enable or disable staff

`POST /api/staff/{user_id}/status/`

Request:

```json
{
  "is_active": false
}
```

Reject disabling the last active manager with `409 last_manager_required`.

#### 14.4 Reset password

`POST /api/staff/{user_id}/password-reset/`

This endpoint is required by the product specification even though the current frontend does not expose a reset action.

### 15. Error Contract

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

### 16. Audit Log

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

### 17. Table Release & Turnover (Implemented)

The application provides an explicit table turnover action:

- **Model**: `TableAssignment(id, table_id, waitlist_entry_id, assigned_at, assigned_by_id, released_at, released_by_id)`.
- **Occupancy Rule**: A table is occupied when it has an assignment where `released_at IS NULL`.
- **Endpoint**: `POST /api/tables/{table_id}/release/`.
- **Permissions**: Authenticated hosts and managers.
- **Invariants**:
  - The waitlist entry remains in `seated` status in current-day history; releasing the table does not put the party back into the waiting line.
  - If the table is not currently occupied, the endpoint returns `409 table_not_occupied`.
  - Once released, the table immediately becomes `available` for new seating assignments.
- **Full Specification**: See the Table Release & Turnover Management section of this document.

### 18. Frontend Migration Map

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

### 19. Seed Data for Local Development

The backend development seed should create:

#### Restaurant

- Name: June & Pine
- Timezone: America/New_York
- Service label: Dinner service
- Open: true

#### Manager

- Name: Maya Chen
- Identifier: `maya@juneandpine.com`
- Role: `manager`
- Development password: `demo1234`

#### Hosts

- Luca Rivera, `luca@juneandpine.com`, role `host`
- Nora Bell, `nora@juneandpine.com`, role `host`
- Development password for both: `demo1234`

The shared demo password is for local development only. Do not use it in a deployed environment.

#### Tables and entries

Seed the table and waitlist records represented in `src/api/mockApi.js` so the real backend presents the same first-run experience as the current frontend demo.

### 20. Backend Acceptance Criteria

#### Authentication

- A valid active staff user can log in and retrieve the current session.
- An invalid or inactive user receives the same generic `401` response.
- Logout invalidates the session.
- Hosts cannot call manager-only endpoints successfully.

#### Queue

- A host can create, edit, cancel, and seat a waiting party.
- FIFO position is based on server `created_at` and does not change after edits.
- Duplicate phone numbers create a warning and do not block the request.
- Closed restaurants reject new entries with a structured conflict.
- Seated and cancelled entries cannot be edited or transitioned back to waiting.

#### Tables

- Hosts can read table availability.
- Managers can create, edit, activate, and deactivate tables.
- A table that is inactive, occupied, or too small cannot be selected.
- Concurrent seat requests cannot successfully assign the same table twice.

#### History and audit

- Seated and cancelled entries remain visible for the current service day.
- History includes final status, timestamps, assigned table when seated, and responsible staff member.
- Mutating operations record the acting staff user.
- A new service day does not include previous-day entries in the active queue.

### 21. Implementation Order

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


## Specification: Table Release & Turnover Management

### 1. Summary

In live restaurant operations, after a party is seated at a table, they dine for a period of time and eventually pay and depart. Once the party finishes, the table must be bussed and marked as **free** (available) so the host stand can assign it to another waiting party during the same service day.

This specification addresses the **Table Release Gap** by introducing explicit table release capabilities for hosts and managers.

---

### 2. User Stories

1. **Host releases a table**: As a host, when a seated party finishes their meal and leaves the table, I want to mark the table as free so that it becomes available for seating new walk-in parties.
2. **Manager releases a table**: As a manager, I want to release any occupied table from the floor overview or table settings so that the room inventory accurately reflects real-time availability.
3. **Preserve dining history**: As a host or manager, when I free an occupied table, the original waitlist record for the party must remain safely preserved in today's completed history as `seated`.

---

### 3. Domain Model & Invariants

#### 3.1 TableAssignment Model

To track dining lifecycles and table turnover without mutating the terminal waitlist entry state:

```python
class TableAssignment:
    id: str                 # Unique assignment identifier (e.g., "assignment-1")
    table_id: str           # References Table.id
    waitlist_entry_id: str  # References Entry.id
    assigned_at: datetime   # Timestamp when party was seated
    assigned_by_id: str     # User.id of the host/manager who seated the party
    released_at: datetime | None = None   # Timestamp when table was freed
    released_by_id: str | None = None # User.id of the host/manager who freed the table
```

#### 3.2 Invariants

1. **Single Active Assignment**: A table can have at most **one** active assignment (`released_at IS NULL`) at any given time.
2. **Occupancy Rule**:
   - A table is `occupied` if it has an assignment where `released_at IS NULL`.
   - A table is `available` if it is active (`is_active == True`) and has no assignment where `released_at IS NULL`.
   - A table is `inactive` if `is_active == False`.
3. **Waitlist Entry Immobility**:
   - Releasing a table **must never** reopen or modify the waitlist entry status back to `waiting`. The entry remains `seated` in current-day history.
4. **Permissions**:
   - Both **hosts** and **managers** are authorized to release occupied tables.
5. **Conflict Protection**:
   - Attempting to release a table that is not occupied must return `409 table_not_occupied`.
   - Attempting to seat a party at an occupied table must return `409 table_unavailable`.

---

### 4. API Endpoints

#### 4.1 Release Table

`POST /api/tables/{table_id}/release/`

**Authorization**: Authenticated host or manager.

**Path Parameters**:
- `table_id` (string, required): The ID of the table to mark as free.

**Responses**:

- **200 OK**: Table freed successfully.
  ```json
  {
    "table": {
      "id": "table-1",
      "name": "T01",
      "capacity": 2,
      "area_id": "area-1",
      "is_active": true,
      "availability": "available",
      "current_party": null
    },
    "message": "Table T01 is now free and available."
  }
  ```

- **401 Unauthorized**: Authentication session missing or invalid.
- **404 Not Found**: Table ID does not exist.
  ```json
  {
    "error": {
      "code": "not_found",
      "message": "Table not found."
    }
  }
  ```
- **409 Conflict**: Table is not currently occupied.
  ```json
  {
    "error": {
      "code": "table_not_occupied",
      "message": "That table is not currently occupied."
    }
  }
  ```

---

### 5. Frontend & UI Requirements

1. **Waitlist Floor Overview (Mini-Table Grid)**:
   - Occupied tables in the floor rail indicate occupied status with current party details where available.
   - Clicking an occupied table or its action opens a confirmation modal: *"Free Table {name}?"*.
2. **Current-Day History**:
   - Seated parties whose table is still occupied show a *"Free table"* action button.
   - Once freed, the button reflects that the table has been released.
3. **Manager Table Inventory**:
   - In Table Settings, occupied tables include a *"Free table"* quick action.
4. **Confirmation Modal**:
   - Asks for staff confirmation before releasing a table to prevent accidental clicks.
   - Notifies the user with a toast: *"Table {name} is now available."*
   - Refreshes the dashboard data automatically upon completion.


