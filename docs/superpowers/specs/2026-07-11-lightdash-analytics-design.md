# Lightdash Analytics Layer — Design Spec

Date: 2026-07-11
Status: Approved design, pending implementation plan
Parent: [JMEA_Platform_Design_Strawman.md](../../JMEA_Platform_Design_Strawman.md) · Related: [ADR-0002](../../adr/0002-use-lightdash-for-analytics.md), [data core spec](2026-07-11-data-core-design.md)

## 1. Goal and scope

Second sub-project of Phase 1: the analytics layer over the merged data core. Lightdash OSS joins the Compose stack, the dbt published models gain a declared semantic layer, and four dashboards-as-code replicate the PoC HTML demo's first-stage use cases. Primary audience is the **JMEA pitch demo** — presenter-driven, polished; staff self-serve is a bonus, not a requirement.

**In scope:** Lightdash + headless-browser containers, Lightdash app DB in the existing Postgres instance, one-time bootstrap doc, semantic layer (`meta:` blocks in dbt YAML), two small dbt additions (below), four dashboards as YAML, `lightdash validate` gate, pytest smoke suite, README/ops updates.

**Out of scope:** GCP deploy (config stays VM-ready; actual `terraform apply` is separate), geographic map visuals (the HTML PoC keeps the map moment; Lightdash has no map chart — revisit only if JMEA makes it a hard requirement), staff onboarding/user management beyond one admin + one viewer account, embedding, alerts/scheduled deliveries, the FastAPI matching service.

## 2. Decisions

| Decision | Choice | Why |
| :--- | :--- | :--- |
| Audience now | Pitch demo first | Shapes polish vs. catalog breadth |
| Capacity-map story | Non-map visuals; HTML PoC retained for the map | Lightdash has no geo chart; zero engineering now |
| Environment | Local in existing Compose stack, VM-ready | Same pattern as data core |
| Authoring | Code-canonical via Lightdash CLI | Repo is source of truth (ADR-0002); UI only for one-time bootstrap |
| Warehouse credentials | `svc_analytics` | Trust model holds by construction — dashboards physically cannot read raw/staging |

## 3. Stack changes

- `infra/compose/docker-compose.yml` gains `lightdash` (official image, **pinned version**) and `headless-browser` services; Lightdash on loopback port 8080 (env-overridable), env-driven config with dev defaults, named volume for Lightdash storage.
- Init SQL gains a `lightdash` application database (same Postgres instance, own database; a `lightdash` login role owning it). The warehouse connection inside Lightdash uses `svc_analytics`/`pub_*` — the app DB role and the warehouse role are distinct.
- One-time bootstrap (documented in README, ~5 minutes): create org + admin user in the UI, create the project pointing at the dbt repo path with `svc_analytics` warehouse credentials, mint a personal access token for the CLI. Everything after that is CLI: `lightdash deploy` (semantic layer), `lightdash upload` (content), `lightdash validate` (gate).

## 4. dbt additions

1. **`pub_matching.buyer_request`** — thin published view over `stg_buyer_request` (buyer demand is needed by the matching dashboard and was never published; it contains no member-confidential data). Lands in `transform/models/published/matching/` so the existing folder-level grants apply (`svc_analytics` + `svc_matching`). Standard schema tests (unique/not_null `request_id`).
2. **`pub_aggregate.reference_stats`** — dbt seed carrying the strawman §8 real-data anchors (Jamaica exports, manufacturing GDP share, commercial electricity US$/kWh with comparators, food import bill, US$350M substitutable estimate), one row per stat with `stat_key, label, value, unit, year_or_asof, source, provenance` where `provenance` ∈ {real, simulated}. Exposed as a published model (seed → thin view in `published/aggregate/`) so grants apply.

**k-anonymity statement:** neither addition weakens the trust model. `buyer_request` is buyer-side data (no member fields); `reference_stats` is public data. The k≥5 guard applies to member aggregates only and is untouched; `assert_k_anonymity` continues to cover `sector_summary` and `sector_energy`.

## 5. Semantic layer

Declared in the existing dbt YAML (`transform/models/published/schema.yml` + new models' YAML) via Lightdash `meta:` blocks — no new tooling. Every metric carries `label` and `description` (the hover-docs where the auditable-rubric story is told).

- **Catalog scoping:** only published models appear in Lightdash. Mechanism (tag-based table selection vs. "models with metrics" mode) is pinned at plan time against current Lightdash docs; the requirement is behavioral — staging/intermediate models must not be visible in the UI catalog.
- **Metrics (indicative):** member counts; total/spare capacity (by unit); avg utilization; readiness score averages and band counts; kWh, energy cost, generator-share and cost-share aggregates; buyer demand volumes; tier-3 supplier counts; cert-coverage counts.

## 6. Dashboards (YAML under `transform/lightdash/`)

| Dashboard | Use case | Reads | Key content |
| :--- | :--- | :--- | :--- |
| Capacity Overview | Capacity mapping (non-map) | member_profile, sector_summary | Stat tiles (members, spare capacity, avg utilization); spare-by-sector bar; utilization distribution; parish table; size-band breakdown |
| Tourism & Buyer Matching | Tourism matching | supplier_directory, buyer_request, reference_stats | Demand by sector/buyer type vs tier-3 spare capacity; required-cert coverage; lead-time fit table; US$350M substitutable headline |
| Export Readiness | Export readiness | member_profile, sector_summary | Band distribution; subscore grouped bars; readiness by sector; near-ready pipeline table |
| Energy Burden | Energy burden | sector_energy, member_profile, reference_stats | kWh + cost-share by sector; generator dependence; renewable adoption; JM vs comparator US$/kWh headline |

Charts follow the repo's dataviz discipline (clear labels, no unexplained abbreviations, provenance noted where reference stats appear). All charts execute as `svc_analytics`; k-suppressed aggregate cells stay suppressed in the UI.

## 7. Validation and testing

1. **`lightdash validate`** against the project — repeatable content gate (broken refs, YAML drift), run like `dbt build`.
2. **pytest smoke suite** (new `tests/test_lightdash.py`): health endpoint returns OK; API lists exactly the four dashboards; warehouse connection user is `svc_analytics` (asserted via the Lightdash API) — extends the §5 trust guarantee to the analytics surface.
3. **dbt**: standard schema tests on the new view + seed; full `dbt build` stays green (oracle, k-anonymity, completeness untouched).

## 8. Error handling & ops

- Compose healthchecks on lightdash (its HTTP health endpoint); Lightdash version pinned — upgrades are deliberate diffs, not `latest` drift.
- Footprint: ~1.5–2 GB additional RAM. Fine locally; **when this deploys, bump `infra/terraform/variables.tf` `machine_type` default to `e2-standard-2`** per ADR-0003's staged sizing (change ships in this sub-project as a var-default edit; applies at next `terraform apply`).
- Bootstrap secrets (Lightdash `SECRET` env, admin password, PAT) follow the `.env` discipline from the data core — dev defaults baked, real values exported per the README's `set -a` pattern.

## 9. Success criteria

- Fresh stack: `docker compose up` brings Postgres + Lightdash healthy; one documented bootstrap; `lightdash deploy && lightdash upload && lightdash validate` all clean from the repo.
- The four dashboards render over the seeded warehouse with correct headline numbers (spot-checked against the PoC demo/generator output).
- `uv run pytest` green including the new smoke suite; `dbt build` green (now including the two additions).
- A reviewer can trace any number on any dashboard to a dbt model in the repo — no UI-only definitions.
