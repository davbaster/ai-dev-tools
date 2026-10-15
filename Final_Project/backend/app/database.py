from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import DateTime, Engine, TypeDecorator, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


class UTCDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            else:
                value = value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


def get_default_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        backend_dir = Path(__file__).resolve().parent.parent
        db_path = backend_dir / "hostboard.db"
        url = f"sqlite:///{db_path}"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def create_app_engine(database_url: str | None = None, is_test: bool = False) -> Engine:
    url = database_url or get_default_database_url()
    connect_args: dict[str, object] = {}

    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if is_test or url in ("sqlite://", "sqlite:///:memory:"):
            engine = create_engine(
                url,
                connect_args=connect_args,
                poolclass=StaticPool,
            )
        else:
            engine = create_engine(url, connect_args=connect_args)

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection: object, connection_record: object) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine

    return create_engine(url)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
