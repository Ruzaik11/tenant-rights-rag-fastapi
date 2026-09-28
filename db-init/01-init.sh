#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;

    CREATE ROLE trh_ingest LOGIN PASSWORD '${TRH_INGEST_PASSWORD}';
    CREATE ROLE trh_api    LOGIN PASSWORD '${TRH_API_PASSWORD}';

    GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO trh_ingest, trh_api;
    GRANT USAGE, CREATE ON SCHEMA public TO trh_ingest;
    GRANT USAGE ON SCHEMA public TO trh_api;

    -- Tables that trh_ingest creates later are automatically read-only for trh_api
    ALTER DEFAULT PRIVILEGES FOR ROLE trh_ingest IN SCHEMA public
        GRANT SELECT ON TABLES TO trh_api;
EOSQL