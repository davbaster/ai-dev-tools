import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store import MockStore


@pytest.fixture()
def client():
    app.state.store = MockStore()
    with TestClient(app) as test_client:
        yield test_client


def test_cors_headers_for_frontend_origin(client: TestClient):
    """Verify that CORS preflight and actual requests allow the Vite frontend origin."""
    preflight = client.options(
        "/api/waitlist/",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert preflight.headers.get("access-control-allow-credentials") == "true"

    preflight_127 = client.options(
        "/api/dashboard/",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert preflight_127.status_code == 200
    assert preflight_127.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"
    assert preflight_127.headers.get("access-control-allow-credentials") == "true"


def test_frontend_host_flow_integration(client: TestClient):
    """Simulate the complete Host user flow as called by frontend/src/api/backendApi.js."""
    # 1. Host login
    login_resp = client.post(
        "/api/auth/login/",
        json={"identifier": "luca@juneandpine.com", "password": "demo1234"},
        headers={"Origin": "http://localhost:5173"},
    )
    assert login_resp.status_code == 200
    user_data = login_resp.json()["user"]
    assert user_data["name"] == "Luca Rivera"
    assert user_data["role"] == "host"
    assert "hostboard_session" in login_resp.cookies

    # 2. Load dashboard
    dashboard_resp = client.get("/api/dashboard/", headers={"Origin": "http://localhost:5173"})
    assert dashboard_resp.status_code == 200
    dash = dashboard_resp.json()
    assert dash["restaurant"]["name"] == "June & Pine"
    assert dash["restaurant"]["is_open"] is True
    assert len(dash["tables"]) > 0
    assert len(dash["areas"]) > 0

    # 3. Create a party (New arrival)
    create_resp = client.post(
        "/api/waitlist/",
        json={
            "guest_name": "Frontend Test Guest",
            "phone": "(555) 019-9999",
            "party_size": 2,
            "seating_preference": "Patio",
            "notes": "Window preferred",
        },
        headers={"Origin": "http://localhost:5173"},
    )
    assert create_resp.status_code == 201
    created_entry = create_resp.json()["entry"]
    assert created_entry["guest_name"] == "Frontend Test Guest"
    assert created_entry["party_size"] == 2
    assert created_entry["seating_preference"] == "Patio"
    assert created_entry["status"] == "waiting"
    entry_id = created_entry["id"]

    # 4. Edit party details
    update_resp = client.patch(
        f"/api/waitlist/{entry_id}/",
        json={
            "guest_name": "Frontend Test Guest Updated",
            "phone": "(555) 019-9999",
            "party_size": 3,
            "seating_preference": "Patio",
            "notes": "High chair needed",
        },
        headers={"Origin": "http://localhost:5173"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["entry"]["party_size"] == 3
    assert update_resp.json()["entry"]["notes"] == "High chair needed"

    # 5. Seat the party at an available table (Table T03 has capacity 4)
    seat_resp = client.post(
        f"/api/waitlist/{entry_id}/seat/",
        json={"table_id": "table-3"},
        headers={"Origin": "http://localhost:5173"},
    )
    assert seat_resp.status_code == 200
    assert seat_resp.json()["entry"]["status"] == "seated"
    assert seat_resp.json()["entry"]["assigned_table_id"] == "table-3"

    # 6. Verify dashboard reflects table is now occupied
    refreshed_dash = client.get("/api/dashboard/").json()
    t3 = next(t for t in refreshed_dash["tables"] if t["id"] == "table-3")
    assert t3["availability"] == "occupied"

    # 7. Release table-3 when party finishes dining
    release_resp = client.post("/api/tables/table-3/release/", headers={"Origin": "http://localhost:5173"})
    assert release_resp.status_code == 200
    assert release_resp.json()["table"]["availability"] == "available"

    dash_freed = client.get("/api/dashboard/").json()
    t3_freed = next(t for t in dash_freed["tables"] if t["id"] == "table-3")
    assert t3_freed["availability"] == "available"
    assert next(e for e in dash_freed["entries"] if e["id"] == entry_id)["status"] == "seated"

    # 8. Add another party and cancel them
    cancel_party = client.post(
        "/api/waitlist/",
        json={
            "guest_name": "Walkout Party",
            "phone": "(555) 019-8888",
            "party_size": 2,
            "seating_preference": None,
        },
    ).json()["entry"]

    cancel_resp = client.post(f"/api/waitlist/{cancel_party['id']}/cancel/")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["entry"]["status"] == "cancelled"

    # 8. Logout
    logout_resp = client.post("/api/auth/logout/")
    assert logout_resp.status_code == 204
    assert client.get("/api/dashboard/").status_code == 401


def test_frontend_manager_settings_flow_integration(client: TestClient):
    """Simulate manager settings actions performed from the frontend."""
    # 1. Manager login
    client.post(
        "/api/auth/login/",
        json={"identifier": "maya@juneandpine.com", "password": "demo1234"},
    )

    # 2. Update restaurant settings
    settings_resp = client.patch(
        "/api/settings/restaurant/",
        json={"name": "June & Pine Updated", "is_open": True},
    )
    assert settings_resp.status_code == 200
    assert settings_resp.json()["restaurant"]["name"] == "June & Pine Updated"

    # 3. Create table
    table_resp = client.post(
        "/api/tables/",
        json={"name": "P10", "capacity": 6, "area_id": "area-2"},
    )
    assert table_resp.status_code == 201
    new_table_id = table_resp.json()["table"]["id"]

    # 4. Update table
    update_table_resp = client.patch(
        f"/api/tables/{new_table_id}/",
        json={"name": "P10", "capacity": 8, "area_id": "area-2", "is_active": True},
    )
    assert update_table_resp.status_code == 200
    assert update_table_resp.json()["table"]["capacity"] == 8

    # 5. Create staff account
    staff_resp = client.post(
        "/api/staff/",
        json={"name": "Alex Mercer", "identifier": "alex@juneandpine.com", "role": "host"},
    )
    assert staff_resp.status_code == 201
    alex_id = staff_resp.json()["user"]["id"]

    # 6. Toggle staff active status
    toggle_resp = client.post(
        f"/api/staff/{alex_id}/status/",
        json={"is_active": False},
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["user"]["is_active"] is False
