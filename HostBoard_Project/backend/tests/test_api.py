from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store import MockStore


@pytest.fixture()
def client():
    app.state.store = MockStore()
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, identifier: str = "maya@juneandpine.com"):
    response = client.post(
        "/api/auth/login/",
        json={"identifier": identifier, "password": "demo1234"},
    )
    assert response.status_code == 200
    return response


def test_login_session_and_logout(client):
    response = login(client)

    assert response.json()["user"]["role"] == "manager"
    session = client.get("/api/auth/session/")
    assert session.status_code == 200
    assert session.json()["user"]["identifier"] == "maya@juneandpine.com"

    logout = client.post("/api/auth/logout/")
    assert logout.status_code == 204
    assert client.get("/api/auth/session/").status_code == 401


def test_invalid_login_is_generic_and_unauthenticated_dashboard_is_blocked(client):
    response = client.post(
        "/api/auth/login/",
        json={"identifier": "unknown@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"
    assert client.get("/api/dashboard/").status_code == 401


def test_host_can_read_dashboard_but_cannot_manage_settings(client):
    login(client, "luca@juneandpine.com")

    dashboard = client.get("/api/dashboard/")
    assert dashboard.status_code == 200
    assert dashboard.json()["users"] == []
    assert len(dashboard.json()["entries"]) >= 4

    settings = client.patch("/api/settings/restaurant/", json={"name": "Nope"})
    assert settings.status_code == 403
    assert settings.json()["error"]["code"] == "forbidden"

    tables = client.post(
        "/api/tables/",
        json={"name": "P99", "capacity": 2, "area_id": "area-2"},
    )
    assert tables.status_code == 403


def test_manager_dashboard_includes_staff_for_the_settings_screen(client):
    login(client)
    dashboard = client.get("/api/dashboard/")

    assert dashboard.status_code == 200
    assert {user["role"] for user in dashboard.json()["users"]} == {"host", "manager"}


def test_create_party_returns_duplicate_phone_warning_and_preserves_fifo_position(client):
    login(client, "luca@juneandpine.com")
    before = client.get("/api/dashboard/").json()["entries"]
    first = next(entry for entry in before if entry["status"] == "waiting")

    response = client.post(
        "/api/waitlist/",
        json={
            "guest_name": "Second Olivia",
            "phone": first["phone"],
            "party_size": 2,
            "seating_preference": "Patio",
            "notes": "Duplicate check",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["entry"]["status"] == "waiting"
    assert body["warnings"][0]["code"] == "duplicate_phone"

    entry_id = body["entry"]["id"]
    original_created_at = body["entry"]["created_at"]
    update = client.patch(
        f"/api/waitlist/{entry_id}/",
        json={"guest_name": "Updated Olivia", "party_size": 3},
    )
    assert update.status_code == 200
    assert update.json()["entry"]["guest_name"] == "Updated Olivia"
    assert update.json()["entry"]["created_at"] == original_created_at


def test_closed_restaurant_rejects_new_party(client):
    login(client)
    assert client.patch("/api/settings/restaurant/", json={"is_open": False}).status_code == 200

    response = client.post(
        "/api/waitlist/",
        json={
            "guest_name": "Late Guest",
            "phone": "(718) 555-0100",
            "party_size": 2,
            "seating_preference": None,
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "restaurant_closed"


def test_cancel_party_moves_it_to_history(client):
    login(client, "luca@juneandpine.com")
    created = client.post(
        "/api/waitlist/",
        json={
            "guest_name": "Cancel Me",
            "phone": "(718) 555-0101",
            "party_size": 2,
            "seating_preference": None,
        },
    ).json()["entry"]

    cancelled = client.post(f"/api/waitlist/{created['id']}/cancel/")
    assert cancelled.status_code == 200
    assert cancelled.json()["entry"]["status"] == "cancelled"

    dashboard = client.get("/api/dashboard/").json()
    assert all(entry["id"] != created["id"] for entry in dashboard["entries"] if entry["status"] == "waiting")
    assert any(entry["id"] == created["id"] and entry["status"] == "cancelled" for entry in dashboard["entries"])


def test_seat_party_checks_capacity_and_assigns_table_atomically(client):
    login(client, "luca@juneandpine.com")
    created = client.post(
        "/api/waitlist/",
        json={
            "guest_name": "Large Party",
            "phone": "(718) 555-0102",
            "party_size": 5,
            "seating_preference": None,
        },
    ).json()["entry"]

    too_small = client.post(
        f"/api/waitlist/{created['id']}/seat/",
        json={"table_id": "table-2"},
    )
    assert too_small.status_code == 409
    assert too_small.json()["error"]["code"] == "table_too_small"

    seated = client.post(
        f"/api/waitlist/{created['id']}/seat/",
        json={"table_id": "table-6"},
    )
    assert seated.status_code == 200
    assert seated.json()["entry"]["status"] == "seated"
    assert seated.json()["entry"]["assigned_table_id"] == "table-6"

    second = client.post(
        "/api/waitlist/",
        json={
            "guest_name": "Another Party",
            "phone": "(718) 555-0103",
            "party_size": 2,
            "seating_preference": None,
        },
    ).json()["entry"]
    unavailable = client.post(
        f"/api/waitlist/{second['id']}/seat/",
        json={"table_id": "table-6"},
    )
    assert unavailable.status_code == 409
    assert unavailable.json()["error"]["code"] == "table_unavailable"


def test_manager_can_manage_tables_and_staff(client):
    login(client)
    created_table = client.post(
        "/api/tables/",
        json={"name": "P99", "capacity": 2, "area_id": "area-2"},
    )
    assert created_table.status_code == 201
    table_id = created_table.json()["table"]["id"]

    updated_table = client.patch(
        f"/api/tables/{table_id}/",
        json={"capacity": 4, "is_active": False},
    )
    assert updated_table.status_code == 200
    assert updated_table.json()["table"]["availability"] == "inactive"

    created_staff = client.post(
        "/api/staff/",
        json={"name": "New Host", "identifier": "new@juneandpine.com", "role": "host"},
    )
    assert created_staff.status_code == 201
    staff_id = created_staff.json()["user"]["id"]

    disabled = client.post(f"/api/staff/{staff_id}/status/", json={"is_active": False})
    assert disabled.status_code == 200
    assert disabled.json()["user"]["is_active"] is False


def test_last_manager_cannot_be_disabled(client):
    login(client)
    response = client.post("/api/staff/user-1/status/", json={"is_active": False})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "last_manager_required"


def test_invalid_waitlist_input_returns_structured_validation_error(client):
    login(client)
    response = client.post(
        "/api/waitlist/",
        json={
            "guest_name": "",
            "phone": "12",
            "party_size": 0,
            "seating_preference": None,
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "party_size" in response.json()["error"]["fields"]


def test_host_and_manager_can_release_occupied_table(client):
    login(client, "luca@juneandpine.com")

    # Table-1 is seeded as occupied by entry-5
    dash_before = client.get("/api/dashboard/").json()
    t1 = next(t for t in dash_before["tables"] if t["id"] == "table-1")
    assert t1["availability"] == "occupied"

    # Host releases table-1
    release_resp = client.post("/api/tables/table-1/release/")
    assert release_resp.status_code == 200
    assert release_resp.json()["table"]["availability"] == "available"
    assert release_resp.json()["table"]["current_party"] is None

    # Verify table-1 is now available on the dashboard
    dash_after = client.get("/api/dashboard/").json()
    t1_after = next(t for t in dash_after["tables"] if t["id"] == "table-1")
    assert t1_after["availability"] == "available"

    # Verify entry-5 is still seated in history
    entry_5 = next(e for e in dash_after["entries"] if e["id"] == "entry-5")
    assert entry_5["status"] == "seated"
    assert entry_5["is_table_occupied"] is False

    # Now table-1 can be seated again by a new party
    new_party = client.post(
        "/api/waitlist/",
        json={"guest_name": "New Guest", "phone": "(555) 123-9999", "party_size": 2},
    ).json()["entry"]
    seat_again = client.post(
        f"/api/waitlist/{new_party['id']}/seat/",
        json={"table_id": "table-1"},
    )
    assert seat_again.status_code == 200
    assert seat_again.json()["entry"]["status"] == "seated"

    # Manager can also release the table
    login(client, "maya@juneandpine.com")
    manager_release = client.post("/api/tables/table-1/release/")
    assert manager_release.status_code == 200
    assert manager_release.json()["table"]["availability"] == "available"


def test_release_table_validations(client):
    # Unauthenticated request rejected
    assert client.post("/api/tables/table-1/release/").status_code == 401

    login(client, "luca@juneandpine.com")

    # Non-existent table returns 404
    not_found = client.post("/api/tables/table-999/release/")
    assert not_found.status_code == 404
    assert not_found.json()["error"]["code"] == "not_found"

    # Table-2 is available; releasing it returns 409 table_not_occupied
    not_occupied = client.post("/api/tables/table-2/release/")
    assert not_occupied.status_code == 409
    assert not_occupied.json()["error"]["code"] == "table_not_occupied"

