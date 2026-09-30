"""Opt-in live integration check for the Agent Relay API and PostgreSQL DB.

Run with the Agent Relay project environment (it supplies psycopg). By default,
the test targets the local API at port 8001 and the PostgreSQL port-forward at
port 15432, using the development credentials in the local kind manifests. If
neither URL is overridden and those services are unavailable, the test skips.
Set either environment variable below to override its local default:

    AGENT_RELAY_INTEGRATION_BASE_URL=http://127.0.0.1:8001
    AGENT_RELAY_INTEGRATION_DATABASE_URL=postgresql+psycopg://...

From the repository root in PowerShell, run:

    uv run --project .\agent-relay pytest -p no:cacheprovider .\restaurant-wailist-manager\backend\tests\test_agent_relay_integration.py

The test only creates uniquely named agents and one completed task. It does
not reset or delete data from the live service or database.
"""

from __future__ import annotations

import os
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


def test_two_agents_exchange_task_and_result_through_live_api_and_database():
    base_url_env = os.getenv("AGENT_RELAY_INTEGRATION_BASE_URL")
    database_url_env = os.getenv("AGENT_RELAY_INTEGRATION_DATABASE_URL")
    using_local_defaults = not base_url_env and not database_url_env
    base_url = base_url_env or "http://127.0.0.1:8001"
    database_url = database_url_env or (
        "postgresql+psycopg://relay:relay-local-only@127.0.0.1:15432/agent_relay"
    )

    pytest.importorskip("psycopg", reason="The live PostgreSQL check needs psycopg.")

    run_id = uuid4().hex
    sender_name = f"integration-sender-{run_id}"
    worker_name = f"integration-worker-{run_id}"
    task_input = "Convert 23 degrees Celsius to Fahrenheit and show the formula."
    task_output = "23 C = 73.4 F (23 * 9/5 + 32)."
    engine = create_engine(database_url, pool_pre_ping=True)

    try:
        with httpx.Client(base_url=base_url.rstrip("/"), timeout=30) as client:
            if using_local_defaults:
                try:
                    ready = client.get("/ready")
                    ready.raise_for_status()
                    with engine.connect() as connection:
                        connection.execute(text("SELECT 1"))
                except (httpx.HTTPError, SQLAlchemyError) as exc:
                    pytest.skip(f"Local Agent Relay API or PostgreSQL is unavailable: {exc}")

            sender_response = client.post(
                "/api/v1/agents",
                json={"name": sender_name, "description": "Live integration test sender"},
            )
            assert sender_response.status_code == 201, sender_response.text
            sender = sender_response.json()

            worker_response = client.post(
                "/api/v1/agents",
                json={"name": worker_name, "description": "Live integration test recipient"},
            )
            assert worker_response.status_code == 201, worker_response.text
            worker = worker_response.json()

            sender_headers = {"Authorization": f"Bearer {sender['token']}"}
            worker_headers = {"Authorization": f"Bearer {worker['token']}"}

            task_response = client.post(
                "/api/v1/tasks",
                headers=sender_headers,
                json={"to": worker["agent_id"], "input": task_input},
            )
            assert task_response.status_code == 201, task_response.text
            task = task_response.json()

            claim_response = client.post(
                "/api/v1/tasks/claim",
                headers=worker_headers,
                json={"worker_id": worker_name, "wait_seconds": 0},
            )
            assert claim_response.status_code == 200, claim_response.text
            claim = claim_response.json()
            assert claim["task_id"] == task["task_id"]
            assert claim["input"] == task_input

            complete_response = client.post(
                f"/api/v1/tasks/{task['task_id']}/complete",
                headers=worker_headers,
                json={"claim_token": claim["claim_token"], "output": task_output},
            )
            assert complete_response.status_code == 200, complete_response.text

            sender_view_response = client.get(
                f"/api/v1/tasks/{task['task_id']}", headers=sender_headers
            )
            assert sender_view_response.status_code == 200, sender_view_response.text
            sender_view = sender_view_response.json()
            assert sender_view["status"] == "completed"
            assert sender_view["output"] == task_output
            assert sender_view["attempt_count"] == 1

        # Verify that the API results are persisted in the same real database.
        with engine.connect() as connection:
            agents = connection.execute(
                text(
                    "SELECT id, name, token_hash FROM agents "
                    "WHERE id IN (:sender_id, :worker_id)"
                ),
                {"sender_id": sender["agent_id"], "worker_id": worker["agent_id"]},
            ).mappings().all()
            assert {row["id"] for row in agents} == {
                sender["agent_id"],
                worker["agent_id"],
            }
            assert {row["name"] for row in agents} == {sender_name, worker_name}
            assert all(row["token_hash"] not in {sender["token"], worker["token"]} for row in agents)

            persisted_task = connection.execute(
                text(
                    "SELECT sender_id, recipient_id, input, status, output, attempt_count "
                    "FROM tasks WHERE id = :task_id"
                ),
                {"task_id": task["task_id"]},
            ).mappings().one()
            assert persisted_task["sender_id"] == sender["agent_id"]
            assert persisted_task["recipient_id"] == worker["agent_id"]
            assert persisted_task["input"] == task_input
            assert persisted_task["status"] == "completed"
            assert persisted_task["output"] == task_output
            assert persisted_task["attempt_count"] == 1

            attempt = connection.execute(
                text(
                    "SELECT attempt_number, worker_id, outcome, terminal_action, claim_token_hash "
                    "FROM attempts WHERE task_id = :task_id"
                ),
                {"task_id": task["task_id"]},
            ).mappings().one()
            assert attempt["attempt_number"] == 1
            assert attempt["worker_id"] == worker_name
            assert attempt["outcome"] == "completed"
            assert attempt["terminal_action"] == "complete"
            assert attempt["claim_token_hash"] != claim["claim_token"]
    finally:
        engine.dispose()
