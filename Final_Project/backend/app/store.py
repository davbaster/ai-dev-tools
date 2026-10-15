from __future__ import annotations

from contextvars import ContextVar, Token
from datetime import date, datetime, timedelta, timezone
from typing import Any, Generic, Iterator, TypeVar
from zoneinfo import ZoneInfo

from pwdlib import PasswordHash
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.database import Base, create_app_engine, create_session_factory
from app.models import Area, Entry, Restaurant, Table, TableAssignment, User, UserSession, utc_now

T = TypeVar("T", bound=Base)
password_hash = PasswordHash.recommended()


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


class ModelCollectionProxy(Generic[T]):
    """Dict-like proxy over a SQLAlchemy model table."""

    def __init__(self, store: SQLAlchemyStore, model: type[T], pk_attr: str = "id") -> None:
        self.store = store
        self.model = model
        self.pk_attr = pk_attr

    def values(self) -> list[T]:
        return list(self.store.session.scalars(select(self.model)).all())

    def get(self, key: str, default: Any = None) -> T | None:
        item = self.store.session.get(self.model, key)
        return item if item is not None else default

    def __getitem__(self, key: str) -> T:
        item = self.store.session.get(self.model, key)
        if item is None:
            raise KeyError(key)
        return item

    def __setitem__(self, key: str, item: T) -> None:
        self.store.session.add(item)
        self.store.session.flush()

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return self.store.session.get(self.model, key) is not None

    def __len__(self) -> int:
        stmt = select(func.count()).select_from(self.model)
        return self.store.session.scalar(stmt) or 0

    def __iter__(self) -> Iterator[str]:
        pk_col = getattr(self.model, self.pk_attr)
        return iter(self.store.session.scalars(select(pk_col)).all())

    def items(self) -> list[tuple[str, T]]:
        return [(getattr(item, self.pk_attr), item) for item in self.values()]


class SessionStore:
    """Dict-like proxy for user sessions stored in the database."""

    def __init__(self, store: SQLAlchemyStore) -> None:
        self.store = store

    def get(self, token: str, default: Any = None) -> str | None:
        sess = self.store.session.get(UserSession, token)
        return sess.user_id if sess else default

    def __getitem__(self, token: str) -> str:
        val = self.get(token)
        if val is None:
            raise KeyError(token)
        return val

    def __setitem__(self, token: str, user_id: str) -> None:
        sess = self.store.session.get(UserSession, token)
        if sess:
            sess.user_id = user_id
        else:
            sess = UserSession(token=token, user_id=user_id, created_at=utc_now())
            self.store.session.add(sess)
        self.store.session.flush()

    def pop(self, token: str, default: Any = None) -> Any:
        sess = self.store.session.get(UserSession, token)
        if sess:
            user_id = sess.user_id
            self.store.session.delete(sess)
            self.store.session.flush()
            return user_id
        return default

    def __contains__(self, token: object) -> bool:
        if not isinstance(token, str):
            return False
        return self.store.session.get(UserSession, token) is not None


class SQLAlchemyStore:
    """Database-agnostic domain store backed by SQLAlchemy."""

    _session_ctx: ContextVar[Session | None] = ContextVar("_session_ctx", default=None)

    def __init__(self, database_url: str | None = None, is_test: bool = False, engine: Engine | None = None) -> None:
        self.engine = engine or create_app_engine(database_url=database_url, is_test=is_test)
        self.session_factory = create_session_factory(self.engine)
        self._internal_session: Session | None = None

        self.tables = ModelCollectionProxy(self, Table)
        self.entries = ModelCollectionProxy(self, Entry)
        self.users = ModelCollectionProxy(self, User)
        self.areas = ModelCollectionProxy(self, Area)
        self.assignments = ModelCollectionProxy(self, TableAssignment)
        self.sessions = SessionStore(self)

        # Initialize schema if tables don't exist yet
        Base.metadata.create_all(self.engine)
        if not self._has_restaurant():
            self.seed_defaults()

    @property
    def session(self) -> Session:
        ctx_session = self._session_ctx.get()
        if ctx_session is not None:
            return ctx_session
        if self._internal_session is None or not self._internal_session.is_active:
            self._internal_session = self.session_factory()
        return self._internal_session

    def create_request_session(self) -> Session:
        return self.session_factory()

    def set_session(self, session: Session) -> Token[Session | None]:
        return self._session_ctx.set(session)

    def reset_session(self, token: Token[Session | None]) -> None:
        self._session_ctx.reset(token)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def close(self) -> None:
        if self._internal_session is not None:
            self._internal_session.close()
            self._internal_session = None

    def _has_restaurant(self) -> bool:
        stmt = select(func.count(Restaurant.id))
        return (self.session.scalar(stmt) or 0) > 0

    @property
    def restaurant(self) -> Restaurant:
        rest = self.session.scalars(select(Restaurant)).first()
        if not rest:
            self.seed_defaults()
            rest = self.session.scalars(select(Restaurant)).first()
        assert rest is not None
        return rest

    def reset(self) -> None:
        """Drop all tables and re-create initial seed data."""
        self.close()
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.seed_defaults()

    def seed_defaults(self) -> None:
        now = utc_now()
        restaurant = Restaurant(
            id="restaurant-1",
            name="June & Pine",
            is_open=True,
            timezone="America/New_York",
            service_label="Dinner service",
            created_at=now,
            updated_at=now,
        )
        self.session.add(restaurant)

        areas = [
            Area("area-1", "Dining room", is_active=True, sort_order=1),
            Area("area-2", "Patio", is_active=True, sort_order=2),
            Area("area-3", "Bar", is_active=True, sort_order=3),
        ]
        self.session.add_all(areas)

        tables = [
            Table("table-1", "T01", 2, "area-1"),
            Table("table-2", "T02", 2, "area-1"),
            Table("table-3", "T03", 4, "area-1"),
            Table("table-4", "T04", 4, "area-2"),
            Table("table-5", "B01", 3, "area-3"),
            Table("table-6", "T05", 6, "area-1"),
            Table("table-7", "T06", 6, "area-1", is_active=False),
        ]
        self.session.add_all(tables)

        users = [
            User("user-1", "Maya Chen", "maya@juneandpine.com", "manager", password_hash.hash("demo1234"), created_at=now, updated_at=now),
            User("user-2", "Luca Rivera", "luca@juneandpine.com", "host", password_hash.hash("demo1234"), created_at=now, updated_at=now),
            User("user-3", "Nora Bell", "nora@juneandpine.com", "host", password_hash.hash("demo1234"), created_at=now, updated_at=now),
        ]
        self.session.add_all(users)
        self.session.flush()

        current_date = datetime.now(ZoneInfo("America/New_York")).date()

        def make_entry(
            entry_id: str,
            guest_name: str,
            phone: str,
            party_size: int,
            seating_preference: str | None,
            notes: str | None,
            status: str,
            minutes_ago: int,
            created_by_id: str,
            table_id: str | None = None,
            status_minutes_ago: int | None = None,
            completed_by_id: str | None = None,
        ) -> Entry:
            created_at = utc_now() - timedelta(minutes=minutes_ago)
            completed_at = utc_now() - timedelta(minutes=status_minutes_ago) if status_minutes_ago is not None else None
            return Entry(
                id=entry_id,
                service_date=current_date,
                guest_name=guest_name,
                phone_display=phone,
                phone_normalized=self.normalize_phone(phone),
                party_size=party_size,
                seating_preference=seating_preference,
                notes=notes,
                status=status,
                created_at=created_at,
                updated_at=None,
                created_by_id=created_by_id,
                seated_at=completed_at if status == "seated" else None,
                cancelled_at=completed_at if status == "cancelled" else None,
                completed_by_id=completed_by_id,
                assigned_table_id=table_id,
            )

        entries = [
            make_entry("entry-1", "Olivia Park", "(917) 555-0142", 2, "Patio", "Celebrating an anniversary", "waiting", 36, "user-2"),
            make_entry("entry-2", "Theo Martin", "(646) 555-0188", 4, None, None, "waiting", 29, "user-2"),
            make_entry("entry-3", "Grace & Eli", "(212) 555-0194", 2, "Dining room", "High chair needed", "waiting", 17, "user-3"),
            make_entry("entry-4", "Marcus Lee", "(917) 555-0110", 5, "Dining room", None, "waiting", 9, "user-2"),
            make_entry("entry-5", "Jamie Wilson", "(347) 555-0162", 2, "Bar", None, "seated", 58, "user-2", table_id="table-1", status_minutes_ago=42, completed_by_id="user-1"),
            make_entry("entry-6", "Ari Patel", "(917) 555-0126", 3, None, "Will split check", "cancelled", 74, "user-2", status_minutes_ago=51, completed_by_id="user-2"),
        ]
        self.session.add_all(entries)
        self.session.flush()

        assignment = TableAssignment(
            id="assignment-1",
            table_id="table-1",
            waitlist_entry_id="entry-5",
            assigned_at=now - timedelta(minutes=42),
            assigned_by_id="user-1",
        )
        self.session.add(assignment)
        self.session.commit()

    def current_service_date(self) -> date:
        tz_name = self.restaurant.timezone if self._has_restaurant() else "America/New_York"
        return datetime.now(ZoneInfo(tz_name)).date()

    @staticmethod
    def normalize_phone(phone: str) -> str:
        return "".join(character for character in phone if character.isdigit())

    def find_user_by_identifier(self, identifier: str) -> User | None:
        normalized = identifier.strip().casefold()
        stmt = select(User).where(func.lower(User.identifier) == normalized)
        return self.session.scalars(stmt).first()

    def get_user(self, user_id: str | None) -> User | None:
        if not user_id:
            return None
        return self.session.get(User, user_id)

    def get_entry(self, entry_id: str | None) -> Entry | None:
        if not entry_id:
            return None
        return self.session.get(Entry, entry_id)

    def get_table(self, table_id: str | None) -> Table | None:
        if not table_id:
            return None
        return self.session.get(Table, table_id)

    def entries_for_current_day(self) -> list[Entry]:
        service_date = self.current_service_date()
        stmt = (
            select(Entry)
            .where(Entry.service_date == service_date)
            .order_by(Entry.created_at.asc(), Entry.id.asc())
        )
        return list(self.session.scalars(stmt).all())

    def occupied_table_ids(self) -> set[str]:
        stmt = select(TableAssignment.table_id).where(TableAssignment.released_at.is_(None))
        return set(self.session.scalars(stmt).all())

    def is_table_occupied(self, table_id: str) -> bool:
        stmt = (
            select(func.count(TableAssignment.id))
            .where(TableAssignment.table_id == table_id, TableAssignment.released_at.is_(None))
        )
        return (self.session.scalar(stmt) or 0) > 0

    def active_assignment_for_table(self, table_id: str) -> TableAssignment | None:
        stmt = (
            select(TableAssignment)
            .where(TableAssignment.table_id == table_id, TableAssignment.released_at.is_(None))
        )
        return self.session.scalars(stmt).first()

    def active_assignment_for_entry(self, entry_id: str) -> TableAssignment | None:
        stmt = (
            select(TableAssignment)
            .where(TableAssignment.waitlist_entry_id == entry_id, TableAssignment.released_at.is_(None))
        )
        return self.session.scalars(stmt).first()

    def assign_table(self, table_id: str, entry_id: str, user_id: str) -> TableAssignment:
        assignment_id = self.new_id("assignment")
        assignment = TableAssignment(
            id=assignment_id,
            table_id=table_id,
            waitlist_entry_id=entry_id,
            assigned_at=utc_now(),
            assigned_by_id=user_id,
        )
        self.session.add(assignment)
        self.session.flush()
        return assignment

    def release_table(self, table_id: str, user_id: str) -> TableAssignment | None:
        assignment = self.active_assignment_for_table(table_id)
        if not assignment:
            return None
        assignment.released_at = utc_now()
        assignment.released_by_id = user_id
        self.session.flush()
        return assignment

    def active_manager_count(self) -> int:
        stmt = select(func.count(User.id)).where(User.role == "manager", User.is_active.is_(True))
        return self.session.scalar(stmt) or 0

    def new_id(self, prefix: str, collection: Any = None) -> str:
        model_map = {
            "entry": Entry,
            "table": Table,
            "user": User,
            "assignment": TableAssignment,
            "area": Area,
        }
        model = model_map.get(prefix)
        if model:
            ids = set(self.session.scalars(select(model.id)).all())
        elif collection is not None and hasattr(collection, "values"):
            ids = {item.id for item in collection.values() if hasattr(item, "id")}
        else:
            ids = set()

        max_num = 0
        for item_id in ids:
            if isinstance(item_id, str) and item_id.startswith(f"{prefix}-"):
                suffix = item_id[len(prefix) + 1:]
                if suffix.isdigit():
                    max_num = max(max_num, int(suffix))
        candidate = f"{prefix}-{max_num + 1}"
        while candidate in ids:
            max_num += 1
            candidate = f"{prefix}-{max_num}"
        return candidate

    def active_area(self, area_id: str | None) -> Area | None:
        if not area_id:
            return None
        area = self.session.get(Area, area_id)
        return area if area and area.is_active else None

    def active_preference(self, preference: str | None) -> str | None:
        if preference is None or preference.casefold() == "no preference":
            return None
        stmt = select(Area).where(Area.is_active.is_(True), func.lower(Area.name) == preference.strip().casefold())
        area = self.session.scalars(stmt).first()
        return area.name if area else None

    def user_public(self, user: User) -> dict[str, object]:
        return {
            "id": user.id,
            "name": user.name,
            "identifier": user.identifier,
            "role": user.role,
            "is_active": user.is_active,
        }

    def entry_public(self, entry: Entry) -> dict[str, object]:
        created_by = self.get_user(entry.created_by_id)
        completed_by = self.get_user(entry.completed_by_id) if entry.completed_by_id else None
        active_assignment = self.active_assignment_for_entry(entry.id)
        return {
            "id": entry.id,
            "guest_name": entry.guest_name,
            "phone": entry.phone_display,
            "party_size": entry.party_size,
            "seating_preference": entry.seating_preference,
            "notes": entry.notes,
            "status": entry.status,
            "created_at": iso(entry.created_at),
            "updated_at": iso(entry.updated_at),
            "seated_at": iso(entry.seated_at),
            "cancelled_at": iso(entry.cancelled_at),
            "assigned_table_id": entry.assigned_table_id,
            "is_table_occupied": active_assignment is not None,
            "created_by": created_by.name if created_by else None,
            "completed_by": completed_by.name if completed_by else None,
        }

    def table_public(self, table: Table) -> dict[str, object]:
        assignment = self.active_assignment_for_table(table.id)
        is_occupied = assignment is not None
        if not table.is_active:
            availability = "inactive"
        elif is_occupied:
            availability = "occupied"
        else:
            availability = "available"
        entry = self.get_entry(assignment.waitlist_entry_id) if assignment else None
        return {
            "id": table.id,
            "name": table.name,
            "capacity": table.capacity,
            "area_id": table.area_id,
            "is_active": table.is_active,
            "availability": availability,
            "current_party": {
                "id": entry.id,
                "guest_name": entry.guest_name,
                "party_size": entry.party_size,
            } if entry else None,
        }

    def restaurant_public(self) -> dict[str, object]:
        rest = self.restaurant
        return {
            "id": rest.id,
            "name": rest.name,
            "is_open": rest.is_open,
            "timezone": rest.timezone,
            "service_label": rest.service_label,
        }

    def dashboard_public(self, include_users: bool) -> dict[str, object]:
        service_date = self.current_service_date()
        areas_stmt = select(Area).where(Area.is_active.is_(True)).order_by(Area.sort_order.asc())
        areas = self.session.scalars(areas_stmt).all()
        tables = self.session.scalars(select(Table)).all()
        entries = self.entries_for_current_day()
        users = self.session.scalars(select(User)).all() if include_users else []

        return {
            "restaurant": self.restaurant_public(),
            "service_day": {"id": f"service-day-{service_date.isoformat()}", "date": service_date.isoformat()},
            "areas": [
                {"id": area.id, "name": area.name, "is_active": area.is_active}
                for area in areas
            ],
            "tables": [self.table_public(table) for table in tables],
            "entries": [self.entry_public(entry) for entry in entries],
            "users": [self.user_public(user) for user in users],
        }


class MockStore(SQLAlchemyStore):
    """Isolated in-memory SQLite store for tests and development mocks."""

    def __init__(self, database_url: str = "sqlite:///:memory:") -> None:
        super().__init__(database_url=database_url, is_test=True)
        self.reset()
