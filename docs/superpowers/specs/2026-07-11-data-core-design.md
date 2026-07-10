# Data Core — Design Spec

Date: 2026-07-11
Status: Approved design, pending implementation plan
Parent: [JMEA_Platform_Design_Strawman.md](../../JMEA_Platform_Design_Strawman.md) · Related: [ADR-0002](../../adr/0002-use-lightdash-for-analytics.md), [ADR-0003](../../adr/0003-terraform-gcp-hosting.md)

## 1. Goal and scope

First buildable sub-project of Phase 1: the governed data foundation every other component reads from. Postgres 16 with raw → staging → published schemas, seed data loaded, the readiness rubric implemented in dbt, and the three-tier trust model enforced by database grants — plus the Terraform/Compose infrastructure to run it locally and on GCP.

**In scope:** Docker Compose (Postgres only, for now), Terraform for GCP, normalized raw schema, seed loader, dbt project (staging/intermediate/published), Postgres roles and grants, k-anonymity views, test suite.

**Out of scope (later sub-projects):** matching service (FastAPI), Lightdash deployment and dashboards, Budibase portal, nginx/TLS, workforce seed data, row-level security within `raw`.

## 2. Decisions already made

| Decision | Choice | Why |
| :--- | :--- | :--- |
| First slice | Data core before UI layers | Foundation everything reads from; fully testable without UI |
| Target env | Local Docker Desktop now, VM-portable | Same Compose files deploy to the GCP VM unchanged |
| Scoring home | dbt computes; generator output is the test oracle | Rubric lives in the auditable semantic layer (see §6 nuance) |
| Schema shape | Strawman's normalized entities, loader explodes flat seed rows | Budibase/matching plug in later without rework |
| Tooling split | dbt-maximal: Python loads raw only; all transformation in dbt | Logic lands in the layer Lightdash reads (ADR-0002) |
| Hosting | Terraform-provisioned GCP VM, containerized Postgres, GCS backups | ADR-0003 |

## 3. Repository layout

```text
infra/
  terraform/                  # GCP: e2-small VM (var-driven), static IP, firewall,
                              #   service account, GCS backup bucket, startup script
  compose/docker-compose.yml  # postgres:16 with healthcheck; later services join here
  postgres/init/              # 01_schemas.sql, 02_roles.sql (container init)
scripts/
  generate_seed_data.py       # unchanged — emits scored output used as oracle
  load_seed.py                # NEW: explodes generator CSVs into raw tables
transform/                    # dbt project (dbt-core + dbt-postgres)
  models/staging/             # stg_* per raw entity
  models/intermediate/        # int_readiness_scores
  models/published/           # pub_private / pub_aggregate / pub_matching
  seeds/expected_scores.csv   # generator's scores, for fixture tests only
  tests/                      # custom data tests (fixture match, k-anonymity)
tests/                        # pytest: role isolation, loader idempotency
pyproject.toml                # uv-managed: dbt-postgres, psycopg, pytest
.env.example                  # all config env-driven; no secrets committed
```

## 4. Raw schema (normalized entities)

Loader synthesizes one submission row per member for a single seed quarter (2026-Q2).

| Table | Key fields | From generator |
| :--- | :--- | :--- |
| member | member_id PK, company, sector, parish, lat/lon, employees, size_band, lead_time_days, export_status, export_markets | members.csv |
| product | member_id FK, product_name | split `products` |
| capacity_submission | member_id FK, quarter, capacity, unit, utilization_pct | members.csv |
| certification | member_id FK, cert_type, verification_status ('unverified' at seed) | split `certifications` |
| energy_submission | member_id FK, quarter, monthly_kwh, generator_share_pct, cost_jmd, energy_pct_of_prod_cost, renewable_adoption | members.csv |
| readiness_assessment | member_id FK, quarter, score_packaging, score_logistics, score_quality_systems, score_export_history | members.csv (see §6) |
| buyer_request | request_id PK, buyer, buyer_type, location, products_needed, sector, required_cert, monthly_volume, volume_unit, max_lead_time_days | buyer_requests.csv |
| visibility_setting | member_id FK, field_group, tier (1/2/3), changed_at | `matching_opt_in` → tier 3 row |
| workforce_submission | member_id FK, quarter, employment, vacancies, skills_gaps | empty (no seed data) |

Deliberately **not** raw tables: `readiness_score` (dbt computes it), `match` (matching-service sub-project). Generator's `matches.csv` is not loaded.

`spare_capacity`, `readiness_score`, `readiness_band`, and the derivable subscores are **dropped by the loader** (`monthly_energy_cost_jmd` stays — it is genuinely submitted data in production; the generator only derives it because it is simulating) — they are derived values and recomputing them is the transformation layer's job.

## 5. dbt layers

- **staging** (`stg_*`): typing, trimming, dedup; one model per raw entity; materialized as views in the `staging` schema.
- **intermediate**: `int_readiness_scores` implements the §4 rubric — weighted composite (certifications 25%, export history 20%, packaging 15%, logistics 15%, quality systems 15%, capacity headroom 10%) and band assignment (≥75 Export Ready, 55–74 Near Ready, 35–54 Developing, <35 Early Stage). `int_spare_capacity` lives here too.
- **published**: three schemas, each a dbt model directory with schema-level grants config:
  - `pub_private` — full member detail joined with scores; readable by member/admin-facing services only.
  - `pub_aggregate` — sector/parish-level aggregates; every view carries `HAVING COUNT(DISTINCT member_id) >= 5`.
  - `pub_matching` — supplier detail restricted to members with a `visibility_setting` tier-3 row for the matching field group.

## 6. Scoring: derivable vs. assessed subscores

Discovered during design: of the six readiness subscores, only some are derivable from raw data. The split is explicit:

- **dbt computes from raw data:** `score_certifications` (from the certification table: 20 + 20·count + 10 if HACCP/FSSC 22000, capped 100) and `score_capacity_headroom` (from utilization: min(100, (100−util)·1.8 + 20)).
- **Raw assessment inputs:** `score_packaging`, `score_logistics`, `score_quality_systems`, `score_export_history` load into `readiness_assessment` — in production these come from JMEA's assessment workflow; in seed data they come from the generator.
- **dbt always computes** the weighted composite and band.

The fixture test (§8) verifies the two recomputed subscores, the composite, and the band against the generator's values for all 72 members.

## 7. Trust model enforcement

Roles created by `02_roles.sql`; grants re-applied by dbt's grants config on every build so rebuilt relations never silently lose ACLs.

| Role | Grants | Future consumer |
| :--- | :--- | :--- |
| app_portal | INSERT/UPDATE on `raw` only | Budibase |
| transform | read `raw`; owns staging/intermediate/published | dbt |
| svc_analytics | SELECT on `pub_private`, `pub_aggregate`, `pub_matching` | Lightdash |
| svc_matching | SELECT on `pub_matching` only | FastAPI matching |

Load-bearing property: `svc_analytics` and `svc_matching` have **no grant path to `raw`** — the strawman §5 claim, made testable. Row-level security within `raw` is deferred (only JMEA admins hold the portal credential at pilot scale) and noted as a hardening step for the Budibase sub-project.

## 8. Testing

1. **dbt tests** — schema tests (unique, not_null, accepted_values on bands/sectors/tiers, relationships on FKs) plus two custom data tests: *fixture match* (zero rows where `int_readiness_scores` disagrees with the `expected_scores` seed) and *k-anonymity* (zero `pub_aggregate` cells with <5 firms).
2. **pytest role isolation** — connects as each service role and asserts the negative space: `svc_analytics` and `svc_matching` selecting from `raw.member` must raise `insufficient_privilege`; `svc_matching` reading `pub_private` must fail; `app_portal` reading `pub_*` must fail.
3. **pytest loader checks** — loader is truncate-and-reload in one transaction; running twice yields identical row counts; row counts match generator output (72 members, 15 buyer requests).

## 9. Error handling

Boring by design: the loader fails loudly on schema drift (explicit column lists, no silent coercion); Compose healthcheck gates the loader on Postgres readiness; dbt test failures fail the build; Terraform state is local for now (single operator), with a documented path to a GCS state bucket when a second operator appears.

## 10. Success criteria

- Fresh clone → `docker compose up` → `uv run scripts/load_seed.py` → `dbt build` → `pytest`: all green on this Windows machine.
- `terraform apply` stands up a GCP e2-small whose startup script reaches the same green state, with a nightly `pg_dump` landing in the GCS bucket.
- A reviewer can trace any published number back through dbt models to raw rows — no logic outside the repo.
