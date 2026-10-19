from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base, UTCDateTime


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(String(64), primary_key=True)
    name = Column(String(120), nullable=False)
    is_open = Column(Boolean, nullable=False, default=True)
    timezone = Column(String(64), nullable=False, default="America/New_York")
    service_label = Column(String(80), nullable=False, default="Dinner service")
    created_at = Column(UTCDateTime, nullable=False, default=utc_now)
    updated_at = Column(UTCDateTime, nullable=False, default=utc_now)

    def __init__(
        self,
        id: str,
        name: str,
        is_open: bool = True,
        timezone: str = "America/New_York",
        service_label: str = "Dinner service",
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        **kwargs: Any,
    ) -> None:
        now = utc_now()
        super().__init__(
            id=id,
            name=name,
            is_open=is_open,
            timezone=timezone,
            service_label=service_label,
            created_at=created_at or now,
            updated_at=updated_at or now,
            **kwargs,
        )


class Area(Base):
    __tablename__ = "areas"

    id = Column(String(64), primary_key=True)
    name = Column(String(120), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)

    tables = relationship("Table", back_populates="area")

    def __init__(
        self,
        id: str,
        name: str,
        is_active: bool = True,
        sort_order: int = 0,
        **kwargs: Any,
    ) -> None:
        super().__init__(id=id, name=name, is_active=is_active, sort_order=sort_order, **kwargs)


class Table(Base):
    __tablename__ = "tables"

    id = Column(String(64), primary_key=True)
    name = Column(String(64), nullable=False)
    capacity = Column(Integer, nullable=False)
    area_id = Column(String(64), ForeignKey("areas.id"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(UTCDateTime, nullable=True)
    updated_at = Column(UTCDateTime, nullable=True)

    area = relationship("Area", back_populates="tables")
    assignments = relationship("TableAssignment", back_populates="table")

    def __init__(
        self,
        id: str,
        name: str,
        capacity: int,
        area_id: str | None = None,
        is_active: bool = True,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            id=id,
            name=name,
            capacity=capacity,
            area_id=area_id,
            is_active=is_active,
            created_at=created_at,
            updated_at=updated_at,
            **kwargs,
        )


class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True)
    name = Column(String(120), nullable=False)
    identifier = Column(String(255), nullable=False, unique=True, index=True)
    role = Column(String(32), nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(UTCDateTime, nullable=True)
    updated_at = Column(UTCDateTime, nullable=True)

    def __init__(
        self,
        id: str,
        name: str,
        identifier: str,
        role: str,
        password_hash: str,
        is_active: bool = True,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            id=id,
            name=name,
            identifier=identifier,
            role=role,
            password_hash=password_hash,
            is_active=is_active,
            created_at=created_at,
            updated_at=updated_at,
            **kwargs,
        )


class Entry(Base):
    __tablename__ = "waitlist_entries"

    id = Column(String(64), primary_key=True)
    service_date = Column(Date, nullable=False, index=True)
    guest_name = Column(String(120), nullable=False)
    phone_display = Column(String(40), nullable=False)
    phone_normalized = Column(String(40), nullable=False, index=True)
    party_size = Column(Integer, nullable=False)
    seating_preference = Column(String(120), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="waiting", index=True)
    created_at = Column(UTCDateTime, nullable=False, index=True)
    updated_at = Column(UTCDateTime, nullable=True)
    created_by_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    updated_by_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    seated_at = Column(UTCDateTime, nullable=True)
    cancelled_at = Column(UTCDateTime, nullable=True)
    completed_by_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    assigned_table_id = Column(String(64), ForeignKey("tables.id"), nullable=True)

    def __init__(
        self,
        id: str,
        service_date: date,
        guest_name: str,
        phone_display: str,
        phone_normalized: str,
        party_size: int,
        seating_preference: str | None = None,
        notes: str | None = None,
        status: str = "waiting",
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        created_by_id: str | None = None,
        updated_by_id: str | None = None,
        seated_at: datetime | None = None,
        cancelled_at: datetime | None = None,
        completed_by_id: str | None = None,
        assigned_table_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            id=id,
            service_date=service_date,
            guest_name=guest_name,
            phone_display=phone_display,
            phone_normalized=phone_normalized,
            party_size=party_size,
            seating_preference=seating_preference,
            notes=notes,
            status=status,
            created_at=created_at or utc_now(),
            updated_at=updated_at,
            created_by_id=created_by_id,
            updated_by_id=updated_by_id,
            seated_at=seated_at,
            cancelled_at=cancelled_at,
            completed_by_id=completed_by_id,
            assigned_table_id=assigned_table_id,
            **kwargs,
        )


class TableAssignment(Base):
    __tablename__ = "table_assignments"

    id = Column(String(64), primary_key=True)
    table_id = Column(String(64), ForeignKey("tables.id"), nullable=False, index=True)
    waitlist_entry_id = Column(String(64), ForeignKey("waitlist_entries.id"), nullable=False, index=True)
    assigned_at = Column(UTCDateTime, nullable=False)
    assigned_by_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    released_at = Column(UTCDateTime, nullable=True, index=True)
    released_by_id = Column(String(64), ForeignKey("users.id"), nullable=True)

    table = relationship("Table", back_populates="assignments")

    def __init__(
        self,
        id: str,
        table_id: str,
        waitlist_entry_id: str,
        assigned_at: datetime,
        assigned_by_id: str,
        released_at: datetime | None = None,
        released_by_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            id=id,
            table_id=table_id,
            waitlist_entry_id=waitlist_entry_id,
            assigned_at=assigned_at,
            assigned_by_id=assigned_by_id,
            released_at=released_at,
            released_by_id=released_by_id,
            **kwargs,
        )


class UserSession(Base):
    __tablename__ = "user_sessions"

    token = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(UTCDateTime, nullable=False, default=utc_now)

    def __init__(
        self,
        token: str,
        user_id: str,
        created_at: datetime | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            token=token,
            user_id=user_id,
            created_at=created_at or utc_now(),
            **kwargs,
        )
