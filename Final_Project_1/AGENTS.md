# Agent Relay development notes

## Runtime

- PostgreSQL is the application's only supported database.
- Use `docker compose up --build --detach` to run the API with the Compose
  database service named `postgres`.
- Compose persists PostgreSQL data in the `postgres_data` volume. Use
  `docker compose down` to stop the services while keeping the database.
- Compose's default password is for local development. Set `POSTGRES_USER`,
  `POSTGRES_PASSWORD`, and `POSTGRES_DB` in a local `.env` file for a custom
  setup; keep the password URL-safe because it is embedded in the SQLAlchemy
  URL.
- The API reads `RELAY_DATABASE_URL` first, then `DATABASE_URL`, and otherwise
  uses the local PostgreSQL URL documented in `README.md`.

## Database changes

- Keep task state transitions inside PostgreSQL transactions.
- Lock task rows before attempt rows in claim, heartbeat, completion, and lease
  recovery paths. Claims use `FOR UPDATE SKIP LOCKED` to avoid overlapping work
  across API processes.
- Agent and claim credentials must remain hashed in the database and must not
  appear in logs or dashboard responses.
- Update `SPEC.md` when a storage change affects protocol behavior.

## Tests

- Start PostgreSQL with `docker compose up --detach postgres` before running
  the protocol test suite.
- `test_agent_relay.py` drops and recreates tables in the dedicated
  `agent_relay_test` database. Never point `RELAY_DATABASE_URL` at the app's
  `agent_relay` database for that test file. Set `RELAY_TEST_DATABASE_URL` to
  another disposable PostgreSQL database if needed.
- `test_relay_integration.py` is opt-in. It sends requests to the running API
  at `RELAY_INTEGRATION_BASE_URL` and checks the same PostgreSQL database using
  `RELAY_INTEGRATION_DATABASE_URL`. It leaves the created acceptance records
  in place.
- See `README.md` for the commands to run both test paths.
