#!/bin/bash
# Nightly logical backup of the containerized Postgres to GCS (ADR-0003).
set -euo pipefail

BUCKET="$(cat /etc/jmea_backup_bucket)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
[ -f /opt/jmea/.env ] && . /opt/jmea/.env

OBJECT="gs://${BUCKET}/pg_dump_${STAMP}.sql.gz"

docker exec jmea_postgres pg_dump \
  --clean --if-exists \
  -U "${POSTGRES_USER:-jmea_admin}" -d "${POSTGRES_DB:-jmea}" \
  | gzip \
  | gcloud storage cp - "${OBJECT}"

if ! gcloud storage ls "${OBJECT}" >/dev/null 2>&1; then
  echo "backup FAILED: ${OBJECT} not found in GCS after upload" >&2
  exit 1
fi

echo "backup complete: pg_dump_${STAMP}.sql.gz"
