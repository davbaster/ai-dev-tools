from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from app.database import get_default_database_url
from app.models import Entry, Table, utc_now
from app.store import MockStore, SQLAlchemyStore


def test_database_url_normalization(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Verify that postgres:// legacy URLs are normalized to postgresql://."""
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost:5432/mydb")
    assert get_default_database_url() == "postgresql://user:pass@localhost:5432/mydb"

    monkeypatch.delenv("DATABASE_URL", raising=False)
    default_url = get_default_database_url()
    assert default_url.startswith("sqlite:///")
    assert "hostboard.db" in default_url


def test_foreign_key_enforcement_in_sqlite(tmp_path: Path):
    """Verify that foreign key constraints are enforced by the engine."""
    db_file = tmp_path / "fk_test.db"
    store = SQLAlchemyStore(database_url=f"sqlite:///{db_file}")

    # Attempt to insert an entry referencing a non-existent user should fail
    invalid_entry = Entry(
        id="invalid-entry",
        service_date=store.current_service_date(),
        guest_name="Ghost User Entry",
        phone_display="(555) 000-0000",
        phone_normalized="5550000000",
        party_size=2,
        created_by_id="non-existent-user-999",
    )
    store.session.add(invalid_entry)
    with pytest.raises(IntegrityError):
        store.session.commit()
    store.session.rollback()
    store.close()


def test_data_persistence_across_store_restarts(tmp_path: Path):
    """Verify that records persist to disk and can be read by a new store instance."""
    db_file = tmp_path / "persistent.db"
    db_url = f"sqlite:///{db_file}"

    # Instance 1: write data
    store1 = SQLAlchemyStore(database_url=db_url)
    assert len(store1.tables) == 7
    assert len(store1.entries) == 6

    # Add a custom table and custom session
    custom_table = Table("table-custom", "VIP-1", 8, "area-1", is_active=True, created_at=utc_now(), updated_at=utc_now())
    store1.tables["table-custom"] = custom_table
    store1.sessions["test-token-123"] = "user-1"
    store1.commit()
    store1.close()

    # Instance 2: open the same database file (simulates app restart)
    store2 = SQLAlchemyStore(database_url=db_url)
    loaded_table = store2.get_table("table-custom")
    assert loaded_table is not None
    assert loaded_table.name == "VIP-1"
    assert loaded_table.capacity == 8

    # Verify session persisted
    assert store2.sessions.get("test-token-123") == "user-1"
    store2.close()


def test_table_assignment_and_release_lifecycle():
    """Verify TableAssignment database lifecycle and release tracking."""
    store = MockStore()

    # Table-2 is initially available
    assert not store.is_table_occupied("table-2")
    assert store.active_assignment_for_table("table-2") is None

    # Assign table-2 to entry-1
    assignment = store.assign_table("table-2", "entry-1", "user-2")
    store.commit()
    assert assignment.id.startswith("assignment-")
    assert assignment.table_id == "table-2"
    assert assignment.waitlist_entry_id == "entry-1"
    assert assignment.released_at is None
    assert store.is_table_occupied("table-2")

    # Release table-2
    released = store.release_table("table-2", "user-1")
    store.commit()
    assert released is not None
    assert released.released_at is not None
    assert released.released_by_id == "user-1"
    assert not store.is_table_occupied("table-2")
    assert store.active_assignment_for_table("table-2") is None
    store.close()


def test_fifo_ordering_at_query_level():
    """Verify that entries_for_current_day returns records strictly ordered by created_at."""
    store = MockStore()
    current_date = store.current_service_date()
    now = utc_now()

    # Insert entries with explicit past timestamps
    e1 = Entry(
        id="fifo-1",
        service_date=current_date,
        guest_name="FIFO First",
        phone_display="(555) 111-1111",
        phone_normalized="5551111111",
        party_size=2,
        status="waiting",
        created_at=now - timedelta(minutes=10),
        created_by_id="user-2",
    )
    e2 = Entry(
        id="fifo-2",
        service_date=current_date,
        guest_name="FIFO Second",
        phone_display="(555) 222-2222",
        phone_normalized="5552222222",
        party_size=4,
        status="waiting",
        created_at=now - timedelta(minutes=5),
        created_by_id="user-2",
    )
    store.session.add_all([e2, e1])  # Add in reverse order
    store.commit()

    day_entries = store.entries_for_current_day()
    fifo_entries = [e for e in day_entries if e.id in ("fifo-1", "fifo-2")]
    assert len(fifo_entries) == 2
    assert fifo_entries[0].id == "fifo-1"
    assert fifo_entries[1].id == "fifo-2"
    store.close()


def test_new_id_generation_handles_gaps_and_increments():
    """Verify that new_id generates monotonic IDs without collisions."""
    store = MockStore()

    # Table IDs 1-7 exist, next should be table-8
    assert store.new_id("table", store.tables) == "table-8"

    # Insert table-10 directly creating a gap
    t10 = Table("table-10", "T10", 4, "area-1", is_active=True, created_at=utc_now(), updated_at=utc_now())
    store.session.add(t10)
    store.commit()

    # Next table ID should be table-11
    assert store.new_id("table", store.tables) == "table-11"
    store.close()
