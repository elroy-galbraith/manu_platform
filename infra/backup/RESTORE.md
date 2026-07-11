# Restore runbook (ADR-0003)

Nightly `pg_dump_to_gcs.sh` ships a gzipped, `--clean --if-exists` logical
backup to the Terraform-created GCS bucket. `--clean --if-exists` means the
dump itself drops-and-recreates objects, so it can be replayed straight over
a database whose roles/schemas were (re-)created by the Postgres init scripts
on a fresh volume — no manual cleanup needed first.

## Restore steps

1. List available backups:

       gcloud storage ls gs://<bucket>/

2. Download the latest one (or copy straight into a pipe, per step 3):

       gcloud storage cp gs://<bucket>/pg_dump_<STAMP>.sql.gz dump.sql.gz

3. Restore into the running `jmea_postgres` container:

       gunzip -c dump.sql.gz | docker exec -i jmea_postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

   `--clean --if-exists` in the dump makes this idempotent: existing
   objects are dropped and recreated, so it's safe to run against a
   container that just initialized from the init scripts (fresh volume)
   or one that already has data.

4. Verify the restore:

       uv run dbt build --project-dir transform --profiles-dir transform
       uv run pytest

   Both must be green before considering the restore complete.

## Backup health check

Periodically confirm a recent backup actually exists (the upload script
itself exits non-zero if the GCS object goes missing, but also spot-check):

    gcloud storage ls -l gs://<bucket>/ | tail

Confirm the newest object's timestamp is less than 25 hours old.
