# JMEA Industry Intelligence Platform

Data platform for the Jamaica Manufacturers and Exporters Association: member
capacity mapping, buyer–supplier matching, export readiness scoring, and energy
analytics. Design: [docs/JMEA_Platform_Design_Strawman.md](docs/JMEA_Platform_Design_Strawman.md) ·
Decisions: [docs/adr/](docs/adr/)

## Quickstart (local)

Prereqs: Docker Desktop, [uv](https://docs.astral.sh/uv/), Python 3.13+.

    uv sync
    docker compose -f infra/compose/docker-compose.yml up -d --wait
    uv run scripts/generate_seed_data.py
    uv run scripts/make_fixtures.py
    uv run scripts/load_seed.py
    uv run dbt build --project-dir transform --profiles-dir transform
    uv run pytest

All green means: 72 simulated members loaded, readiness rubric verified against
the generator oracle, k-anonymity enforced, and the four-role trust model
(`app_portal`, `transform`, `svc_analytics`, `svc_matching`) proven by tests.

Postgres listens on `localhost:5433` (admin: `jmea_admin`/`jmea_dev_admin`, dev only).
To reset everything: `docker compose -f infra/compose/docker-compose.yml down -v`.

## Analytics (Lightdash)

Lightdash serves dashboards at http://localhost:8080 (loopback-only), reading the
published schemas as `svc_analytics` — it cannot see raw or staging data.

Note: `tests/test_lightdash.py::test_warehouse_connection_is_svc_analytics` verifies
the *configured* connection (dbt target + `transform/profiles.yml`), not the live
connection identity — Lightdash's API redacts `warehouseConnection.user`, so no field
directly confirms svc_analytics on the wire.

Commands that need a live warehouse connection (`deploy`, `validate`, `set-warehouse`)
must run through `./scripts/lightdash-cli.sh` instead of a locally-installed `lightdash`:
`transform/profiles.yml`'s `lightdash` target hardcodes `host: postgres` — the
Compose-internal address the Lightdash server itself uses — which only resolves from
inside the Compose network, not from the bare host. The wrapper runs the pinned CLI in
a throwaway container attached to that network so it can resolve `postgres` too.
`upload`/`download` are pure content operations (no DB access) and run directly on the
host with a locally-installed CLI (`npm install -g @lightdash/cli`, same version as
`LIGHTDASH_CLI_VERSION` in the wrapper script).

One-time bootstrap: register the admin account in the UI, create a personal access
token (Settings → Personal access tokens), then:

    export LIGHTDASH_PAT=<token>
    ./scripts/lightdash-cli.sh deploy --create JMEA --target lightdash
    # Project settings → Tables configuration → "Show models with any of these tags" → lightdash
    export LIGHTDASH_PROJECT=<project-uuid-from-deploy-output>
    lightdash login http://localhost:8080 --token "$LIGHTDASH_PAT" --project "$LIGHTDASH_PROJECT"
    # ^ host-side login (separate from the wrapper's in-container login); needed for upload/download below

Day-to-day (all content lives in the repo — the UI is a viewer):

    ./scripts/lightdash-cli.sh deploy --target lightdash     # push semantic layer changes (dbt YAML)
    ./scripts/lightdash-cli.sh validate --target lightdash   # gate: broken refs, drift
    cd transform && lightdash upload --force && cd ..        # push charts/dashboards from transform/lightdash/

Existing stacks (volume predates Lightdash): create the app DB once with
`docker exec jmea_postgres bash /docker-entrypoint-initdb.d/04_lightdash_db.sh`.

## Deploy (GCP, per ADR-0003)

    cd infra/terraform
    terraform init
    terraform apply -var project_id=YOUR_PROJECT -var admin_cidr=YOUR_IP/32

Then SSH in, clone this repo to `/opt/jmea`, create `/opt/jmea/.env` from
`.env.example` with real passwords, then export it before running anything —
`docker compose -f` does NOT read a repo-root `.env`, so skipping this leaves
every tool (compose, loader, dbt, pytest) silently on dev-default credentials:

    set -a; . ./.env; set +a    # export the real credentials — compose -f does NOT read repo-root .env

then run the same quickstart commands.
Nightly `pg_dump` ships to the Terraform-created GCS bucket (30-day retention);
restore steps are in [infra/backup/RESTORE.md](infra/backup/RESTORE.md).

Postgres is bound to loopback only (`127.0.0.1`), so it isn't reachable from
other VMs regardless. The Terraform module here only manages the SSH firewall
rule — the VM otherwise joins GCP's `default` VPC, which carries a pre-existing
`default-allow-internal` rule permitting all project-internal traffic. Review
and tighten or remove that rule if project-internal exposure is unacceptable
for your environment.

## Layout

    infra/      terraform (GCP) + docker compose + postgres init SQL
    scripts/    seed generator, fixture extractor, raw loader
    transform/  dbt: staging → intermediate → pub_private / pub_aggregate / pub_matching
    tests/      pytest: bootstrap, loader, role-isolation (trust model)
    docs/       strawman, ADRs, specs, plans
