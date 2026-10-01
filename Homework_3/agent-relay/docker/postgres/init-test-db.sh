#!/bin/sh
set -eu

test_database=agent_relay_test
if [ "$test_database" != "$POSTGRES_DB" ]; then
    psql --set ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
        --command "CREATE DATABASE $test_database"
fi
