# Restaurant Waitlist Manager Specifications

## 1. Product Summary

Restaurant Waitlist Manager is a desktop web application for restaurant hosts and managers to operate a walk-in waitlist during a service day. Staff can add parties, maintain the queue, view available tables, seat parties, and keep a same-day record of queue activity.

The MVP is intentionally operational and staff-only. Guests do not log in, join the queue, or receive notifications from the application.

## 2. MVP Goals

- Make adding a party fast and reliable at the host stand.
- Keep the active waitlist ordered by FIFO rules.
- Give hosts enough table information to select an available table manually.
- Let staff move parties from waiting to seated or cancelled.
- Let managers configure tables, staff accounts, and basic restaurant settings.
- Preserve the day's activity for operational review while keeping retention limited to the current day.

## 3. Non-Goals

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

## 4. Users and Permissions

### 4.1 Host

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

### 4.2 Manager

Managers have all host permissions and can also:

- Create, edit, activate, and deactivate tables.
- Create, disable, and reset staff accounts.
- Configure the restaurant name, open/closed status, and default seating preferences.
- Review the current day's waitlist activity.

The MVP uses two roles: `host` and `manager`.

## 5. Core Concepts

### 5.1 Service day

A service day is the current operational day for the restaurant. Active and completed entries are associated with that day. At the start of a new service day, the previous day's entries are archived or hidden from the live queue according to the retention policy.

### 5.2 Party

A party is a group waiting to be seated. Required party information:

- Guest name.
- Phone number.
- Party size.
- Seating preference.

Optional information:

- Staff notes.

The supported seating preferences should be configurable from a controlled list. The initial list is assumed to include `no preference`, `indoor`, `patio`, and `bar` if those areas exist in the restaurant.

### 5.3 Table

A table is an individual seating resource configured by a manager.

Each table has:

- Display name or number.
- Seating capacity.
- Seating preference/area, when applicable.
- Active or inactive status.
- Current availability status.

The host selects a table manually when seating a party. The application must show enough information for the host to avoid selecting an unavailable or undersized table.

## 6. Party Lifecycle

The MVP supports these statuses:

- `waiting`: The party is active in the queue.
- `seated`: The party has been assigned a table and removed from the active queue.
- `cancelled`: The party left the queue without being seated.

Only `waiting` parties appear in the active queue.

A waiting party can transition to `seated` or `cancelled`. A seated or cancelled party cannot return to `waiting` in the MVP; staff must create a new entry if needed.

## 7. Functional Requirements

### FR-1 Authentication

- The application must require staff authentication before showing restaurant operations.
- A user signs in with a username or email and password.
- The application must provide sign-out.
- Disabled staff accounts must not be able to sign in.
- Unauthorized users must not access queue, table, staff, or settings data.

### FR-2 Active waitlist

- The application must show all `waiting` parties for the current service day.
- Parties must be ordered by creation time, oldest first.
- Each queue row must show at least: position, guest name, party size, phone number, seating preference, time added, and notes when present.
- The queue must make the next party visually obvious without hiding other waiting parties.
- The active queue must update after adding, editing, seating, or cancelling a party.

### FR-3 Add a party

- A host or manager must be able to add a party from the active waitlist view.
- Guest name, phone number, party size, and seating preference are required.
- Party size must be a positive whole number.
- The phone number must be stored in a normalized format suitable for comparison.
- The application must warn when another active party uses the same phone number, but must allow the new party to be saved.
- A new party receives the next FIFO position based on its creation time.
- The form must prevent accidental duplicate submission.
- Successful creation must return the user to, or visibly update, the active queue.

### FR-4 Edit a party

- A host or manager must be able to edit a party while it is `waiting`.
- Editable fields include guest name, phone number, party size, seating preference, and notes.
- Editing must not change the party's original queue position or creation time.
- The duplicate-phone warning must also apply when editing a phone number.
- Seated and cancelled entries are read-only in the MVP.

### FR-5 Cancel a party

- A host or manager must be able to cancel a waiting party.
- The application must require confirmation before cancellation.
- A cancelled party must disappear from the active queue.
- The cancellation must remain visible in the current-day history with its status and timestamp.

### FR-6 Table inventory

- Managers must be able to create a table with a name/number, capacity, area or seating preference, and active status.
- Managers must be able to edit table details.
- Managers must be able to deactivate a table without deleting its current-day references.
- Inactive tables must not be selectable for new seating actions.
- A table cannot be selected for more than one currently seated party at a time.
- Hosts must be able to view active tables and their availability.

### FR-7 Seat a party

- A host or manager must be able to start a seating action for a waiting party.
- The application must show active available tables for selection.
- The application must show table capacity and area/preference before confirmation.
- The host selects the table; the application does not auto-assign or reorder the queue.
- The selected table must be marked occupied and the party must become `seated` in one atomic operation.
- A party cannot be seated if the selected table is inactive or already occupied.
- A seated party must leave the active waitlist.
- The current-day record must retain the party, selected table, seating timestamp, and staff member who performed the action.

### FR-8 Current-day history

- Staff must be able to view seated and cancelled entries from the current service day.
- History must show party details, final status, relevant timestamp, and responsible staff member.
- History must not be mixed into the active waiting queue.
- Previous service-day history is out of scope for the MVP UI and may be archived or deleted according to the final retention implementation.

### FR-9 Manager settings

Managers must be able to:

- Set the restaurant display name.
- Set the restaurant open/closed status.
- Configure available seating preferences/areas.
- Manage table inventory.
- Manage staff accounts and roles.

A closed restaurant may continue to display the current queue to authenticated staff, but the application should prevent adding new parties unless a manager reopens it. This rule is an assumption to confirm before implementation.

### FR-10 Staff account management

- Managers must be able to create a staff account with a name, login identifier, role, and temporary password or reset flow.
- Managers must be able to disable a staff account.
- Managers must be able to reset a staff member's password.
- A manager must not accidentally remove the last active manager account.
- Staff account changes must take effect on the next authenticated request or session refresh.

## 8. Primary Workflows

### 8.1 Add a waiting party

1. Host opens the active waitlist.
2. Host selects `Add party`.
3. Host enters name, phone, party size, seating preference, and optional notes.
4. The application validates required fields.
5. If the phone matches an active party, the application shows a warning.
6. Host confirms the save.
7. The application creates the party with status `waiting` and places it at the end of the queue.

### 8.2 Seat a party

1. Host selects a waiting party.
2. Host selects `Seat party`.
3. The application shows active available tables.
4. Host selects a table and confirms.
5. The application marks the table occupied and the party seated atomically.
6. The party leaves the active queue and appears in current-day history.

### 8.3 Cancel a party

1. Host selects a waiting party.
2. Host selects `Cancel`.
3. The application asks for confirmation.
4. Host confirms.
5. The application sets the status to `cancelled`, records the timestamp and staff member, and removes the party from the active queue.

### 8.4 Configure a table

1. Manager opens table settings.
2. Manager creates or edits a table.
3. Manager enters the table identifier, capacity, and area/preference.
4. Manager saves the table.
5. The table becomes available for host selection when active and unoccupied.

## 9. Suggested Data Model

### User

- `id`
- `name`
- `login_identifier`
- `password_hash`
- `role`: `host` or `manager`
- `is_active`
- `created_at`
- `updated_at`

### RestaurantSettings

- `id`
- `name`
- `is_open`
- `timezone`
- `created_at`
- `updated_at`

### SeatingArea

- `id`
- `name`
- `is_active`
- `created_at`
- `updated_at`

### Table

- `id`
- `restaurant_id`
- `name_or_number`
- `capacity`
- `seating_area_id`, nullable
- `is_active`
- `created_at`
- `updated_at`

### ServiceDay

- `id`
- `restaurant_id`
- `date`
- `opened_at`, nullable
- `closed_at`, nullable

### WaitlistEntry

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

### Operational constraints

- Active queue queries must filter by the current service day and `status = waiting`.
- Queue ordering must use `created_at` plus a stable tie-breaker such as `id`.
- A table must have at most one active seating assignment.
- A phone duplicate check applies to active waiting entries and generates a warning, not a validation error.
- Party size and table capacity must be positive integers.

## 10. Screens and Interface Requirements

### Login

- Login identifier field.
- Password field.
- Clear validation and authentication error states.
- No operational data visible before authentication.

### Active waitlist

- Restaurant name and open/closed indicator.
- Current service date.
- Primary `Add party` action.
- Ordered queue with clear positions.
- Actions for edit, seat, and cancel.
- Link or tab to current-day history.
- Link to settings for managers only.
- Empty state when no parties are waiting.
- Loading, validation, permission, and save-error states.

### Party form

- Name input.
- Phone input.
- Party-size numeric input.
- Seating-preference select.
- Notes textarea.
- Duplicate-phone warning state.
- Save and cancel actions.
- Inline validation that preserves entered values.

### Seating flow

- Party summary.
- Available table list.
- Table identifier, capacity, area, and availability.
- Confirmation action.
- Clear error if a table became occupied while the screen was open.

### Current-day history

- Separate waiting, seated, and cancelled status presentation.
- Timestamp and responsible staff member.
- Empty state.

### Manager settings

- Restaurant settings.
- Table inventory.
- Staff accounts.
- Permission restrictions for host users.

The primary operating environment is a desktop browser at a host stand. The interface should remain usable at common laptop and desktop widths, but tablet optimization is not a release requirement.

## 11. Non-Functional Requirements

### Performance

- The active waitlist should load in under two seconds under normal single-restaurant operating conditions.
- Add, edit, cancel, and seat actions should show confirmation or an actionable error within two seconds under normal conditions.
- The queue should not require a full page reload after routine actions.

### Reliability and consistency

- Seating must update both the party and table state atomically.
- Concurrent attempts to use one table must result in only one successful assignment.
- The application must not silently lose a party after a failed save.
- Destructive or irreversible actions must require confirmation.

### Security

- Passwords must be stored using a modern password-hashing mechanism.
- Authenticated requests must enforce role permissions server-side.
- Guest phone numbers and notes must not be exposed to unauthenticated users.
- Forms that mutate data must be protected against cross-site request forgery where applicable.
- Input must be validated and escaped to prevent injection and script execution.

### Accessibility

- All controls must be keyboard reachable.
- Form fields must have programmatic labels.
- Status and validation messages must be understandable without color alone.
- Focus state must remain visible.
- Confirmation dialogs must be operable by keyboard.

### Auditability

- Mutating operations must record the responsible staff member and timestamp.
- The application should log authentication failures and permission failures without logging raw passwords.

## 12. Acceptance Criteria

### Queue operation

- A host can sign in and see the current day's active queue.
- A host can add a valid party and see it at the end of the queue.
- A host can edit a waiting party without changing its position.
- A host can cancel a party after confirmation and see it removed from the active queue.
- A host can seat a party by selecting an available table.
- A seated party no longer appears in the active queue and appears in history.

### Queue rules

- Parties are displayed oldest first.
- Duplicate phone numbers produce a warning but do not block saving.
- A party cannot be seated at an inactive or occupied table.
- Two simultaneous seating actions cannot assign the same table.

### Permissions

- A host cannot access manager settings or mutate table/staff configuration.
- A manager can manage tables, staff accounts, and restaurant settings.
- Disabled users cannot sign in.

### Data and history

- Current-day seated and cancelled entries remain viewable with their final status.
- Every seating and cancellation records a timestamp and staff member.
- Starting a new service day does not place old entries in the new active queue.

## 13. Open Decisions and Assumptions

The following items should be confirmed before implementation:

1. Exact service-day rollover time and restaurant timezone.
2. Whether closing the restaurant blocks adding new parties. This spec currently assumes yes.
3. Exact seating preference values and whether each table may support more than one preference.
4. Phone-number format and normalization rules by country/region.
5. Whether a table becomes available automatically when a seated party is marked complete. The MVP has no separate `completed` action; table-release behavior must therefore be defined before implementation.
6. Whether managers can edit or delete current-day entries. This spec currently treats seated and cancelled entries as read-only.
7. Whether the first manager account is seeded administratively or created through an initial setup flow.
8. Whether same-day history should be archived, deleted, or retained in the database but hidden after the day ends.

## 14. Future Enhancements

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
