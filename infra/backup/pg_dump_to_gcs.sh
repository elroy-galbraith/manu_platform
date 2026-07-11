#!/bin/bash
# Nightly logical backup of the containerized Postgres to GCS (ADR-0003).
set -euo pipefail

BUCKET="$(cat /etc/jmea_backup_bucket)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
[ -f /opt/jmea/.env ] && . /opt/jmea/.env

docker exec jmea_postgres pg_dump \
  -U "${POSTGRES_USER:-jmea_admin}" -d "${POSTGRES_DB:-jmea}" \
  | gzip \
  | gcloud storage cp - "gs://${BUCKET}/pg_dump_${STAMP}.sql.gz"

echo "backup complete: pg_dump_${STAMP}.sql.gz"
