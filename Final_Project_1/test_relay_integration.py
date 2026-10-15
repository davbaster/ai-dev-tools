"""Opt-in live HTTP and PostgreSQL integration coverage for SPEC scenario 1."""

from __future__ import annotations

import os
import uuid

import httpx
import pytest
from sqlalchemy import create_engine, text


@pytest.mark.integration
def test_two_agents_exchange_task_and_result_over_live_api_and_postgresql() -> None:
    """Exercise a running API and query the PostgreSQL rows it persists."""
    base_url = os.getenv("RELAY_INTEGRATION_BASE_URL")
    database_url = os.getenv("RELAY_INTEGRATION_DATABASE_URL")
    if not base_url or not database_url:
        pytest.skip("Set RELAY_INTEGRATION_BASE_URL and RELAY_INTEGRATION_DATABASE_URL to run this test.")

    suffix = uuid.uuid4().hex[:12]
    task_input = f"Return exactly RELAY_OK for integration run {suffix}."
    with httpx.Client(base_url=base_url, timeout=10) as client:
        ready = client.get("/ready")
        assert ready.status_code == 200

        sender_response = client.post("/api/v1/agents", json={"name": f"integration-sender-{suffix}"})
        assert sender_response.status_code == 201
        sender = sender_response.json()
        sender_headers = {"Authorization": f"Bearer {sender['token']}"}

        recipient_response = client.post("/api/v1/agents", json={"name": f"integration-recipient-{suffix}"})
        assert recipient_response.status_code == 201
        recipient = recipient_response.json()
        recipient_headers = {"Authorization": f"Bearer {recipient['token']}"}

        task_response = client.post(
            "/api/v1/tasks",
            headers=sender_headers,
            json={"to": recipient["agent_id"], "input": task_input},
        )
        assert task_response.status_code == 201
        task_id = task_response.json()["task_id"]

        claim_response = client.post(
            "/api/v1/tasks/claim",
            headers=recipient_headers,
            json={"worker_id": f"integration-worker-{suffix}", "wait_seconds": 0},
        )
        assert claim_response.status_code == 200
        claim = claim_response.json()
        assert claim["task_id"] == task_id
        assert claim["input"] == task_input

        complete_response = client.post(
            f"/api/v1/tasks/{task_id}/complete",
            headers=recipient_headers,
            json={"claim_token": claim["claim_token"], "output": "RELAY_OK"},
        )
        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "completed"

        result_response = client.get(f"/api/v1/tasks/{task_id}", headers=sender_headers)
        assert result_response.status_code == 200
        result = result_response.json()
        assert result["status"] == "completed"
        assert result["output"] == "RELAY_OK"

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as database:
            stored_task = database.execute(
                text(
                    "SELECT sender_id, recipient_id, input, status, output "
                    "FROM tasks WHERE id = :task_id"
                ),
                {"task_id": task_id},
            ).one()
            assert tuple(stored_task) == (
                sender["agent_id"],
                recipient["agent_id"],
                task_input,
                "completed",
                "RELAY_OK",
            )

            stored_attempt = database.execute(
                text("SELECT worker_id, outcome, claim_token_hash FROM attempts WHERE task_id = :task_id"),
                {"task_id": task_id},
            ).one()
            assert stored_attempt[0:2] == (f"integration-worker-{suffix}", "completed")
            assert stored_attempt[2] != claim["claim_token"]

            stored_agent_tokens = database.execute(
                text("SELECT id, token_hash FROM agents WHERE id IN (:sender_id, :recipient_id)"),
                {"sender_id": sender["agent_id"], "recipient_id": recipient["agent_id"]},
            ).all()
            hashes = {agent_id: token_hash for agent_id, token_hash in stored_agent_tokens}
            assert len(hashes) == 2
            assert hashes[sender["agent_id"]] != sender["token"]
            assert hashes[recipient["agent_id"]] != recipient["token"]
    finally:
        engine.dispose()
