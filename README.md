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

## Deploy (GCP, per ADR-0003)

    cd infra/terraform
    terraform init
    terraform apply -var project_id=YOUR_PROJECT -var admin_cidr=YOUR_IP/32

Then SSH in, clone this repo to `/opt/jmea`, create `/opt/jmea/.env` from
`.env.example` with real passwords, and run the same quickstart commands.
Nightly `pg_dump` ships to the Terraform-created GCS bucket (30-day retention).

## Layout

    infra/      terraform (GCP) + docker compose + postgres init SQL
    scripts/    seed generator, fixture extractor, raw loader
    transform/  dbt: staging → intermediate → pub_private / pub_aggregate / pub_matching
    tests/      pytest: bootstrap, loader, role-isolation (trust model)
    docs/       strawman, ADRs, specs, plans
