#!/bin/bash
# Lightdash application database + role. Idempotent: runs on fresh volumes via
# docker-entrypoint-initdb.d, and on EXISTING volumes via:
#   docker exec jmea_postgres bash /docker-entrypoint-initdb.d/04_lightdash_db.sh
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lightdash') THEN
            CREATE ROLE lightdash LOGIN PASSWORD '${LIGHTDASH_PG_PASSWORD//\'/\'\'}';
        END IF;
    END
    \$\$;
EOSQL

if ! psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -tAc \
    "SELECT 1 FROM pg_database WHERE datname = 'lightdash'" | grep -q 1; then
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
        -c "CREATE DATABASE lightdash OWNER lightdash"
fi
