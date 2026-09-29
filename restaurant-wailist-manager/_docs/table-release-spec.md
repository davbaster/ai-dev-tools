# Specification: Table Release & Turnover Management

## 1. Summary

In live restaurant operations, after a party is seated at a table, they dine for a period of time and eventually pay and depart. Once the party finishes, the table must be bussed and marked as **free** (available) so the host stand can assign it to another waiting party during the same service day.

This specification addresses the **Table Release Gap** by introducing explicit table release capabilities for hosts and managers.

---

## 2. User Stories

1. **Host releases a table**: As a host, when a seated party finishes their meal and leaves the table, I want to mark the table as free so that it becomes available for seating new walk-in parties.
2. **Manager releases a table**: As a manager, I want to release any occupied table from the floor overview or table settings so that the room inventory accurately reflects real-time availability.
3. **Preserve dining history**: As a host or manager, when I free an occupied table, the original waitlist record for the party must remain safely preserved in today's completed history as `seated`.

---

## 3. Domain Model & Invariants

### 3.1 TableAssignment Model

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

### 3.2 Invariants

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

## 4. API Endpoints

### 4.1 Release Table

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

## 5. Frontend & UI Requirements

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
