#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE app_portal LOGIN PASSWORD '${APP_PORTAL_PASSWORD}';
    CREATE ROLE transform LOGIN PASSWORD '${TRANSFORM_PASSWORD}';
    CREATE ROLE svc_analytics LOGIN PASSWORD '${SVC_ANALYTICS_PASSWORD}';
    CREATE ROLE svc_matching LOGIN PASSWORD '${SVC_MATCHING_PASSWORD}';

    -- portal: write-only into raw
    GRANT USAGE ON SCHEMA raw TO app_portal;
    GRANT INSERT, UPDATE ON ALL TABLES IN SCHEMA raw TO app_portal;
    ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT INSERT, UPDATE ON TABLES TO app_portal;

    -- transform (dbt): read raw, own everything downstream
    GRANT USAGE ON SCHEMA raw TO transform;
    GRANT SELECT ON ALL TABLES IN SCHEMA raw TO transform;
    ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT ON TABLES TO transform;
    ALTER SCHEMA staging OWNER TO transform;
    ALTER SCHEMA intermediate OWNER TO transform;
    ALTER SCHEMA fixtures OWNER TO transform;
    ALTER SCHEMA pub_private OWNER TO transform;
    ALTER SCHEMA pub_aggregate OWNER TO transform;
    ALTER SCHEMA pub_matching OWNER TO transform;

    -- service roles: USAGE on published schemas only; SELECT arrives via dbt grants config
    GRANT USAGE ON SCHEMA pub_private, pub_aggregate, pub_matching TO svc_analytics;
    GRANT USAGE ON SCHEMA pub_matching TO svc_matching;
EOSQL
