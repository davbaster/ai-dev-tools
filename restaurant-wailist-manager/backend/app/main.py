from __future__ import annotations

import secrets
from typing import Annotated, Any

from fastapi import Cookie, Depends, FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from pwdlib import PasswordHash

from app.store import Entry, MockStore, Table, User, iso, utc_now


class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str, fields: dict[str, list[str]] | None = None) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.fields = fields


class LoginPayload(BaseModel):
    identifier: str = Field(min_length=1)
    password: str = Field(min_length=1)


class PartyPayload(BaseModel):
    guest_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=7, max_length=40)
    party_size: int = Field(ge=1)
    seating_preference: str | None = None
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("guest_name", "phone", mode="before")
    @classmethod
    def require_non_blank(cls, value: Any) -> Any:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("This field is required.")
        return value.strip()


class PartyPatch(BaseModel):
    guest_name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, min_length=7, max_length=40)
    party_size: int | None = Field(default=None, ge=1)
    seating_preference: str | None = None
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("guest_name", "phone", mode="before")
    @classmethod
    def strip_optional_text(cls, value: Any) -> Any:
        if value is None:
            return value
        if not isinstance(value, str) or not value.strip():
            raise ValueError("This field cannot be blank.")
        return value.strip()


class SeatPayload(BaseModel):
    table_id: str = Field(min_length=1)


class TablePayload(BaseModel):
    name: str = Field(min_length=1, max_length=20)
    capacity: int = Field(ge=1)
    area_id: str | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class TablePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=20)
    capacity: int | None = Field(default=None, ge=1)
    area_id: str | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def strip_optional_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class RestaurantPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_open: bool | None = None
    service_label: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("name", "service_label")
    @classmethod
    def strip_optional_setting(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class StaffPayload(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    identifier: str = Field(min_length=3, max_length=255)
    role: str = Field(pattern="^(host|manager)$")

    @field_validator("name", "identifier")
    @classmethod
    def strip_staff_text(cls, value: str) -> str:
        return value.strip()


class StaffStatusPayload(BaseModel):
    is_active: bool


password_hash = PasswordHash.recommended()
app = FastAPI(title="HostBoard API", version="0.1.0", docs_url="/docs", redoc_url="/redoc")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.store = MockStore()
sessions: dict[str, str] = {}


@app.exception_handler(APIError)
async def api_error_handler(_: Request, error: APIError) -> Response:
    body: dict[str, object] = {"error": {"code": error.code, "message": error.message}}
    if error.fields:
        body["error"]["fields"] = error.fields  # type: ignore[index]
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=error.status_code, content=body)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, error: RequestValidationError) -> Response:
    fields: dict[str, list[str]] = {}
    for item in error.errors():
        location = item.get("loc", ())
        field = str(location[-1]) if location else "request"
        fields.setdefault(field, []).append(str(item.get("msg", "Invalid value.")))
    return await api_error_handler(_, APIError(422, "validation_error", "Review the highlighted fields.", fields))


def get_store() -> MockStore:
    return app.state.store


def public_user(user: User) -> dict[str, object]:
    return get_store().user_public(user)


def get_current_user(hostboard_session: Annotated[str | None, Cookie()] = None) -> User:
    user_id = sessions.get(hostboard_session) if hostboard_session else None
    user = get_store().get_user(user_id) if user_id else None
    if not user or not user.is_active:
        raise APIError(401, "unauthorized", "Authentication is required.")
    return user


def require_manager(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "manager":
        raise APIError(403, "forbidden", "Manager access is required.")
    return user


def entry_or_404(entry_id: str) -> Entry:
    entry = get_store().get_entry(entry_id)
    if not entry or entry.service_date != get_store().current_service_date():
        raise APIError(404, "not_found", "Waitlist entry not found.")
    return entry


def table_or_404(table_id: str) -> Table:
    table = get_store().get_table(table_id)
    if not table:
        raise APIError(404, "not_found", "Table not found.")
    return table


def area_exists(area_id: str | None) -> None:
    if area_id is not None and not get_store().active_area(area_id):
        raise APIError(422, "validation_error", "Review the highlighted fields.", {"area_id": ["Area not found."]})


def response_entry(entry: Entry) -> dict[str, object]:
    return {"entry": get_store().entry_public(entry)}


def duplicate_warnings(phone: str, excluded_id: str | None = None) -> list[dict[str, object]]:
    normalized = get_store().normalize_phone(phone)
    matches = [
        entry for entry in get_store().entries_for_current_day()
        if entry.status == "waiting" and entry.id != excluded_id and entry.phone_normalized == normalized
    ]
    if not matches:
        return []
    return [{
        "code": "duplicate_phone",
        "message": "Another active party uses this phone number.",
        "matching_entries": [{"id": entry.id, "guest_name": entry.guest_name} for entry in matches],
    }]


@app.post("/api/auth/login/", status_code=200)
def login(payload: LoginPayload, response: Response) -> dict[str, object]:
    user = get_store().find_user_by_identifier(payload.identifier)
    valid_password = False
    if user:
        try:
            valid_password = password_hash.verify(payload.password, user.password_hash)
        except Exception:
            valid_password = False
    if not user or not user.is_active or not valid_password:
        raise APIError(401, "invalid_credentials", "The identifier or password is incorrect.")
    token = secrets.token_urlsafe(32)
    sessions[token] = user.id
    response.set_cookie("hostboard_session", token, httponly=True, samesite="lax")
    return {"user": public_user(user)}


@app.get("/api/auth/session/")
def session(user: Annotated[User, Depends(get_current_user)]) -> dict[str, object]:
    return {"user": public_user(user)}


@app.post("/api/auth/logout/", status_code=204)
def logout(response: Response, hostboard_session: Annotated[str | None, Cookie()] = None) -> None:
    if hostboard_session:
        sessions.pop(hostboard_session, None)
    response.delete_cookie("hostboard_session")


@app.get("/api/dashboard/")
def dashboard(user: Annotated[User, Depends(get_current_user)], include: str | None = None) -> dict[str, object]:
    return get_store().dashboard_public(include_users=user.role == "manager" and include in (None, "users"))


@app.post("/api/waitlist/", status_code=201)
def create_waitlist_entry(payload: PartyPayload, user: Annotated[User, Depends(get_current_user)]) -> dict[str, object]:
    store = get_store()
    if not store.restaurant.is_open:
        raise APIError(409, "restaurant_closed", "The restaurant is closed to new parties.")
    preference = store.active_preference(payload.seating_preference)
    if payload.seating_preference is not None and preference is None and payload.seating_preference.casefold() != "no preference":
        raise APIError(422, "validation_error", "Review the highlighted fields.", {"seating_preference": ["Area not found."]})
    entry_id = store.new_id("entry", store.entries)
    entry = Entry(
        id=entry_id,
        service_date=store.current_service_date(),
        guest_name=payload.guest_name,
        phone_display=payload.phone,
        phone_normalized=store.normalize_phone(payload.phone),
        party_size=payload.party_size,
        seating_preference=preference,
        notes=payload.notes.strip() if payload.notes else None,
        status="waiting",
        created_at=utc_now(),
        updated_at=None,
        created_by_id=user.id,
    )
    store.entries[entry.id] = entry
    return {"entry": store.entry_public(entry), "warnings": duplicate_warnings(payload.phone, entry.id)}


@app.patch("/api/waitlist/{entry_id}/")
def update_waitlist_entry(entry_id: str, payload: PartyPatch, user: Annotated[User, Depends(get_current_user)]) -> dict[str, object]:
    store = get_store()
    entry = entry_or_404(entry_id)
    if entry.status != "waiting":
        raise APIError(409, "invalid_status_transition", "Only waiting parties can be edited.")
    changes = payload.model_dump(exclude_unset=True)
    if "seating_preference" in changes:
        preference = store.active_preference(changes["seating_preference"])
        if changes["seating_preference"] is not None and preference is None and changes["seating_preference"].casefold() != "no preference":
            raise APIError(422, "validation_error", "Review the highlighted fields.", {"seating_preference": ["Area not found."]})
        changes["seating_preference"] = preference
    if "phone" in changes:
        entry.phone_display = changes["phone"]
        entry.phone_normalized = store.normalize_phone(changes["phone"])
    if "guest_name" in changes:
        entry.guest_name = changes["guest_name"]
    if "party_size" in changes:
        entry.party_size = changes["party_size"]
    if "notes" in changes:
        entry.notes = changes["notes"].strip() if changes["notes"] else None
    if "seating_preference" in changes:
        entry.seating_preference = changes["seating_preference"]
    entry.updated_at = utc_now()
    entry.updated_by_id = user.id
    return {"entry": store.entry_public(entry), "warnings": duplicate_warnings(entry.phone_display, entry.id)}


@app.post("/api/waitlist/{entry_id}/cancel/")
def cancel_waitlist_entry(entry_id: str, user: Annotated[User, Depends(get_current_user)]) -> dict[str, object]:
    entry = entry_or_404(entry_id)
    if entry.status != "waiting":
        raise APIError(409, "invalid_status_transition", "Only waiting parties can be cancelled.")
    entry.status = "cancelled"
    entry.cancelled_at = utc_now()
    entry.completed_by_id = user.id
    entry.updated_at = utc_now()
    return response_entry(entry)


@app.post("/api/waitlist/{entry_id}/seat/")
def seat_waitlist_entry(entry_id: str, payload: SeatPayload, user: Annotated[User, Depends(get_current_user)]) -> dict[str, object]:
    store = get_store()
    entry = entry_or_404(entry_id)
    table = table_or_404(payload.table_id)
    if entry.status != "waiting":
        raise APIError(409, "invalid_status_transition", "Only waiting parties can be seated.")
    if not table.is_active or store.is_table_occupied(table.id):
        raise APIError(409, "table_unavailable", "That table is no longer available.")
    if table.capacity < entry.party_size:
        raise APIError(409, "table_too_small", "That table is too small for this party.")
    entry.status = "seated"
    entry.assigned_table_id = table.id
    entry.seated_at = utc_now()
    entry.completed_by_id = user.id
    entry.updated_at = utc_now()
    store.assign_table(table.id, entry.id, user.id)
    return response_entry(entry)


@app.get("/api/tables/")
def list_tables(_: Annotated[User, Depends(get_current_user)]) -> dict[str, object]:
    store = get_store()
    return {"tables": [store.table_public(table) for table in store.tables.values()]}


@app.post("/api/tables/", status_code=201)
def create_table(payload: TablePayload, _: Annotated[User, Depends(require_manager)]) -> dict[str, object]:
    store = get_store()
    area_exists(payload.area_id)
    if any(table.name.casefold() == payload.name.casefold() for table in store.tables.values()):
        raise APIError(409, "duplicate_table_name", "A table with that name already exists.")
    table_id = store.new_id("table", store.tables)
    table = Table(table_id, payload.name, payload.capacity, payload.area_id, created_at=utc_now(), updated_at=utc_now())
    store.tables[table.id] = table
    return {"table": store.table_public(table)}


@app.patch("/api/tables/{table_id}/")
def update_table(table_id: str, payload: TablePatch, _: Annotated[User, Depends(require_manager)]) -> dict[str, object]:
    store = get_store()
    table = table_or_404(table_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise APIError(422, "validation_error", "Provide at least one table field to update.")
    if changes.get("is_active") is False and store.is_table_occupied(table.id):
        raise APIError(409, "table_occupied", "Occupied tables cannot be deactivated.")
    if "name" in changes and any(other.id != table.id and other.name.casefold() == changes["name"].casefold() for other in store.tables.values()):
        raise APIError(409, "duplicate_table_name", "A table with that name already exists.")
    area_exists(changes.get("area_id", table.area_id))
    if "capacity" in changes and any(entry.status == "seated" and entry.assigned_table_id == table.id and entry.party_size > changes["capacity"] for entry in store.entries.values()):
        raise APIError(409, "table_capacity_conflict", "The new capacity is smaller than an existing seating.")
    for field in ("name", "capacity", "area_id", "is_active"):
        if field in changes:
            setattr(table, field, changes[field])
    table.updated_at = utc_now()
    return {"table": store.table_public(table)}


@app.post("/api/tables/{table_id}/release/")
def release_table(table_id: str, user: Annotated[User, Depends(get_current_user)]) -> dict[str, object]:
    store = get_store()
    table = table_or_404(table_id)
    if not store.is_table_occupied(table.id):
        raise APIError(409, "table_not_occupied", "That table is not currently occupied.")
    store.release_table(table.id, user.id)
    return {
        "table": store.table_public(table),
        "message": f"Table {table.name} is now available.",
    }


@app.get("/api/settings/restaurant/")
def get_restaurant_settings(_: Annotated[User, Depends(get_current_user)]) -> dict[str, object]:
    return {"restaurant": get_store().restaurant_public()}


@app.patch("/api/settings/restaurant/")
def update_restaurant_settings(payload: RestaurantPatch, _: Annotated[User, Depends(require_manager)]) -> dict[str, object]:
    store = get_store()
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(store.restaurant, field, value)
    store.restaurant.updated_at = utc_now()
    return {"restaurant": store.restaurant_public()}


@app.get("/api/staff/")
def list_staff(_: Annotated[User, Depends(require_manager)]) -> dict[str, object]:
    store = get_store()
    return {"users": [store.user_public(user) for user in store.users.values()]}


@app.post("/api/staff/", status_code=201)
def create_staff(payload: StaffPayload, _: Annotated[User, Depends(require_manager)]) -> dict[str, object]:
    store = get_store()
    if store.find_user_by_identifier(payload.identifier):
        raise APIError(409, "duplicate_identifier", "A staff account with that identifier already exists.")
    user_id = store.new_id("user", store.users)
    now = utc_now()
    user = User(user_id, payload.name, payload.identifier, payload.role, password_hash.hash(secrets.token_urlsafe(16)), created_at=now, updated_at=now)
    store.users[user.id] = user
    return {"user": store.user_public(user)}


@app.post("/api/staff/{user_id}/status/")
def update_staff_status(user_id: str, payload: StaffStatusPayload, _: Annotated[User, Depends(require_manager)]) -> dict[str, object]:
    store = get_store()
    user = store.get_user(user_id)
    if not user:
        raise APIError(404, "not_found", "Staff account not found.")
    if user.role == "manager" and user.is_active and not payload.is_active and store.active_manager_count() <= 1:
        raise APIError(409, "last_manager_required", "At least one active manager is required.")
    user.is_active = payload.is_active
    user.updated_at = utc_now()
    return {"user": store.user_public(user)}


@app.post("/api/staff/{user_id}/password-reset/", status_code=204)
def reset_staff_password(user_id: str, _: Annotated[User, Depends(require_manager)]) -> None:
    user = get_store().get_user(user_id)
    if not user:
        raise APIError(404, "not_found", "Staff account not found.")
    user.password_hash = password_hash.hash(secrets.token_urlsafe(16))
    user.updated_at = utc_now()
