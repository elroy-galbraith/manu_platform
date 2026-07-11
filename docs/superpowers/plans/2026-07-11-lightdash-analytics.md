# Lightdash Analytics Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lightdash OSS in the Compose stack with a dbt-declared semantic layer and four dashboards-as-code replicating the PoC demo's use cases, connected as `svc_analytics` so the trust model holds end-to-end.

**Architecture:** Lightdash + headless-browser containers join the existing stack; the Lightdash app DB lives in the existing Postgres instance (own database + role); the semantic layer is `config.meta` blocks on published dbt models scoped by a `lightdash` tag; charts/dashboards are YAML in `transform/lightdash/` pushed via the Lightdash CLI. Spec: `docs/superpowers/specs/2026-07-11-lightdash-analytics-design.md`.

**Tech Stack:** Lightdash OSS (pinned tag), ghcr.io/browserless/chromium:v2.24.3, `@lightdash/cli` (npm, pinned to server version), existing dbt/Postgres/pytest stack.

## Global Constraints

- Lightdash server image tag is **pinned** (resolved in Task 2 via `gh api repos/lightdash/lightdash/releases/latest --jq .tag_name`); the npm CLI is pinned to the **same version**. Never `latest` in committed files.
- Headless browser image: `ghcr.io/browserless/chromium:v2.24.3` (Lightdash-docs-recommended pin).
- Lightdash on host port `${LIGHTDASH_PORT:-8080}`, **loopback-only** (both `127.0.0.1:` and `[::1]:` mappings, same pattern as Postgres).
- Dev defaults (overridable, never commit real values): `LIGHTDASH_PG_PASSWORD=lightdash_dev`, `LIGHTDASH_SECRET=jmea_dev_lightdash_secret`, `LIGHTDASH_SITE_URL=http://localhost:8080`.
- Warehouse connection user is **svc_analytics** — never `transform` or the admin. The smoke test asserts this.
- Catalog scoping: published models carry dbt tag `lightdash`; Lightdash Table Configuration = "Show models with any of these tags" → `lightdash`. Staging/intermediate must not appear in the UI catalog.
- Seed quarter/vars unchanged; `scripts/generate_seed_data.py` is never modified.
- All commands from repo root; dbt commands carry `--project-dir transform --profiles-dir transform`; work on a feature branch (`feature/lightdash-analytics`).
- Existing suites must stay green throughout: `uv run pytest` (21 + new tests), `uv run dbt build` (55 + new results).

---

### Task 1: Lightdash application database + role

**Files:**
- Create: `infra/postgres/init/04_lightdash_db.sh`
- Modify: `infra/compose/docker-compose.yml` (postgres service env: add `LIGHTDASH_PG_PASSWORD`)
- Modify: `.env.example` (append Lightdash block)
- Test: `tests/test_db_bootstrap.py` (extend)

**Interfaces:**
- Produces: database `lightdash` owned by login role `lightdash` (password env `LIGHTDASH_PG_PASSWORD`, dev default `lightdash_dev`) in the existing Postgres instance. Idempotent script usable on fresh volumes (init) AND existing volumes (`docker exec`). Task 2's lightdash service connects to it.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_db_bootstrap.py`:

```python
def test_lightdash_app_db_exists():
    with connect("jmea_admin") as conn:
        dbs = {r[0] for r in conn.execute("select datname from pg_database").fetchall()}
        roles = {r[0] for r in conn.execute("select rolname from pg_roles").fetchall()}
    assert "lightdash" in dbs
    assert "lightdash" in roles
```

Run: `uv run pytest tests/test_db_bootstrap.py::test_lightdash_app_db_exists -v`
Expected: FAIL — `'lightdash' in dbs` assertion error.

- [ ] **Step 2: Write `infra/postgres/init/04_lightdash_db.sh`**

(`$$` must be escaped `\$\$` inside the unquoted heredoc or bash expands it as the PID.)

```bash
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
```

Then: `git update-index --chmod=+x infra/postgres/init/04_lightdash_db.sh` after `git add` (repo convention: shell scripts carry the exec bit).

- [ ] **Step 3: Add the env var to the postgres service**

In `infra/compose/docker-compose.yml`, postgres service `environment:` block, after `SVC_MATCHING_PASSWORD`:

```yaml
      LIGHTDASH_PG_PASSWORD: ${LIGHTDASH_PG_PASSWORD:-lightdash_dev}
```

- [ ] **Step 4: Append to `.env.example`**

```bash
# --- Lightdash (analytics layer) ---
LIGHTDASH_PG_PASSWORD=lightdash_dev
LIGHTDASH_SECRET=jmea_dev_lightdash_secret
LIGHTDASH_PORT=8080
LIGHTDASH_SITE_URL=http://localhost:8080
# Set after one-time bootstrap (see README): personal access token + project UUID
LIGHTDASH_URL=http://localhost:8080
LIGHTDASH_PAT=
LIGHTDASH_PROJECT=
```

- [ ] **Step 5: Apply to the running (existing-volume) stack and verify**

```bash
docker compose -f infra/compose/docker-compose.yml up -d postgres --wait   # picks up new env var
docker exec jmea_postgres bash /docker-entrypoint-initdb.d/04_lightdash_db.sh
docker exec jmea_postgres bash /docker-entrypoint-initdb.d/04_lightdash_db.sh  # second run proves idempotency (no error)
```

Run: `uv run pytest tests/test_db_bootstrap.py -v` → 4 passed. Then full suite: `uv run pytest` → 22 passed.

- [ ] **Step 6: Commit**

```bash
git add infra/postgres/init/04_lightdash_db.sh infra/compose/docker-compose.yml .env.example tests/test_db_bootstrap.py
git update-index --chmod=+x infra/postgres/init/04_lightdash_db.sh
git commit -m "feat: lightdash app database and role (idempotent bootstrap)"
```

---

### Task 2: Lightdash + headless-browser Compose services

**Files:**
- Modify: `infra/compose/docker-compose.yml` (two new services)
- Test: `tests/test_lightdash.py` (health test only, in this task)

**Interfaces:**
- Consumes: `lightdash` DB/role (Task 1).
- Produces: Lightdash UI/API at `http://localhost:8080` (`/api/v1/health` returns 200), healthchecked service `lightdash`, service `headless-browser`. Tasks 5-7 depend on this URL.

- [ ] **Step 1: Resolve and pin the Lightdash version**

```bash
gh api repos/lightdash/lightdash/releases/latest --jq .tag_name
```

Record the tag (e.g. `0.NNNN.N`). Use it verbatim as `lightdash/lightdash:<TAG>` below and in Task 4's CLI install. If `gh` cannot reach the API, use `docker pull lightdash/lightdash:latest` then `docker image inspect lightdash/lightdash:latest --format '{{index .Config.Labels "org.opencontainers.image.version"}}'`.

- [ ] **Step 2: Write the failing health test**

Create `tests/test_lightdash.py`:

```python
import urllib.request


BASE = "http://localhost:8080"


def test_lightdash_health():
    with urllib.request.urlopen(f"{BASE}/api/v1/health", timeout=10) as r:
        assert r.status == 200
```

(BASE becomes env-driven in Task 7; hardcoded here is fine for the failing-test step.)

Run: `uv run pytest tests/test_lightdash.py -v`
Expected: FAIL — URLError, connection refused.

- [ ] **Step 3: Add the services to `infra/compose/docker-compose.yml`**

Append under `services:` (replace `<TAG>` with the pinned tag from Step 1):

```yaml
  headless-browser:
    image: ghcr.io/browserless/chromium:v2.24.3
    restart: unless-stopped

  lightdash:
    image: lightdash/lightdash:<TAG>
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      PGHOST: postgres
      PGPORT: 5432
      PGUSER: lightdash
      PGPASSWORD: ${LIGHTDASH_PG_PASSWORD:-lightdash_dev}
      PGDATABASE: lightdash
      LIGHTDASH_SECRET: ${LIGHTDASH_SECRET:-jmea_dev_lightdash_secret}
      SECURE_COOKIES: "false"
      TRUST_PROXY: "false"
      PORT: 8080
      SITE_URL: ${LIGHTDASH_SITE_URL:-http://localhost:8080}
      HEADLESS_BROWSER_HOST: headless-browser
      HEADLESS_BROWSER_PORT: 3000
    ports:
      - "127.0.0.1:${LIGHTDASH_PORT:-8080}:8080"
      - "[::1]:${LIGHTDASH_PORT:-8080}:8080"
    volumes:
      - ../../transform:/usr/app/dbt:ro
    healthcheck:
      test: ["CMD", "node", "-e", "fetch('http://localhost:8080/api/v1/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]
      interval: 10s
      timeout: 5s
      retries: 18
      start_period: 60s
```

(The postgres service name is `postgres` — confirm against the existing file; `PGHOST` must match the service name. Dual loopback binding follows the repo's established pattern for Windows `localhost`→`::1` resolution.)

- [ ] **Step 4: Start and verify**

```bash
docker compose -f infra/compose/docker-compose.yml up -d --wait
```

Expected: `lightdash` reaches healthy (first boot runs DB migrations — allow the start_period). Then:

Run: `uv run pytest tests/test_lightdash.py -v` → 1 passed. Full suite: `uv run pytest` → 23 passed.

- [ ] **Step 5: Commit**

```bash
git add infra/compose/docker-compose.yml tests/test_lightdash.py
git commit -m "feat: lightdash and headless-browser services (pinned, loopback-only)"
```

---

### Task 3: dbt additions — published buyer_request view + reference_stats seed

**Files:**
- Create: `transform/models/published/matching/buyer_request.sql`
- Create: `transform/seeds/seed_reference_stats.csv`
- Create: `transform/models/published/aggregate/reference_stats.sql`
- Modify: `transform/seeds/properties.yml` (add seed config)
- Modify: `transform/models/published/schema.yml` (tests for both new models)

**Interfaces:**
- Consumes: `stg_buyer_request` (existing), `published/matching` + `published/aggregate` folder grants (existing dbt_project.yml config).
- Produces: `pub_matching.buyer_request` (columns: request_id, buyer, buyer_type, location, products_needed, sector, required_cert, monthly_volume, volume_unit, max_lead_time_days) and `pub_aggregate.reference_stats` (columns: stat_key, label, value, unit, year_or_asof, source, provenance). Task 4 declares metrics on these; Task 6 charts read them.

- [ ] **Step 1: Write `transform/models/published/matching/buyer_request.sql`**

```sql
select
    request_id,
    buyer,
    buyer_type,
    location,
    products_needed,
    sector,
    required_cert,
    monthly_volume,
    volume_unit,
    max_lead_time_days
from {{ ref('stg_buyer_request') }}
```

- [ ] **Step 2: Write `transform/seeds/seed_reference_stats.csv`**

(Values from strawman §8 / the generator's `reference` dict — all `real` provenance.)

```csv
stat_key,label,value,unit,year_or_asof,source,provenance
jm_total_exports_2024,Jamaica total exports 2024,1867.2,USD millions,2024,STATIN via MFAFT,real
jm_total_exports_2023,Jamaica total exports 2023,2001.8,USD millions,2023,STATIN via MFAFT,real
mfg_gdp_share,Manufacturing share of GDP,8.5,percent,2022,Do Business Jamaica / PIOJ,real
mfg_export_earnings,Manufacturing export earnings,961.3,USD millions,2022,Do Business Jamaica,real
electricity_jm,Commercial electricity - Jamaica,0.238,USD per kWh,Sep 2025,GlobalPetrolPrices.com,real
electricity_us,Commercial electricity - USA,0.128,USD per kWh,Sep 2025,GlobalPetrolPrices.com,real
electricity_tt,Commercial electricity - Trinidad & Tobago,0.05,USD per kWh,Sep 2025,GlobalPetrolPrices.com,real
electricity_dr,Commercial electricity - Dominican Republic,0.19,USD per kWh,Sep 2025,GlobalPetrolPrices.com,real
electricity_bb,Commercial electricity - Barbados,0.30,USD per kWh,Sep 2025,GlobalPetrolPrices.com,real
food_import_bill,National food import bill,1300,USD millions,2024,USDA FAS / Ministry of Agriculture,real
hri_food_import_share,Food imports flowing to hotels and restaurants,60,percent,2024,USDA FAS,real
substitutable_imports,Est. imports substitutable by local production,350,USD millions,2024,USDA FAS / Gleaner,real
```

- [ ] **Step 3: Write `transform/models/published/aggregate/reference_stats.sql`**

```sql
select
    stat_key,
    label,
    value,
    unit,
    year_or_asof,
    source,
    provenance
from {{ ref('seed_reference_stats') }}
```

- [ ] **Step 4: Append to `transform/seeds/properties.yml`**

```yaml
  - name: seed_reference_stats
    config:
      column_types:
        stat_key: text
        label: text
        value: numeric
        unit: text
        year_or_asof: text
        source: text
        provenance: text
```

- [ ] **Step 5: Append tests to `transform/models/published/schema.yml`**

```yaml
  - name: buyer_request
    columns:
      - name: request_id
        tests: [unique, not_null]
  - name: reference_stats
    columns:
      - name: stat_key
        tests: [unique, not_null]
      - name: provenance
        tests:
          - not_null
          - accepted_values:
              values: ["real", "simulated"]
```

- [ ] **Step 6: Build and verify**

Run: `uv run dbt build --project-dir transform --profiles-dir transform`
Expected: `Completed successfully` — 2 new models + 1 new seed + 5 new tests on top of the existing 55 (new total 63). k-anonymity, oracle, and completeness tests untouched and passing.

Sanity-check grants applied by the folder config: `uv run pytest tests/test_role_isolation.py -v` → 14 passed (existing matrix unaffected). Then add the two new ALLOWED rows to `tests/test_role_isolation.py`:

```python
    ("svc_analytics", "pub_aggregate.reference_stats"),
    ("svc_matching", "pub_matching.buyer_request"),
```

Run: `uv run pytest tests/test_role_isolation.py -v` → 16 passed.

- [ ] **Step 7: Commit**

```bash
git add transform/ tests/test_role_isolation.py
git commit -m "feat: published buyer_request view and reference_stats seed for dashboards"
```

---

### Task 4: Semantic layer — tags, metrics, CLI install

**Files:**
- Modify: `transform/dbt_project.yml` (tag published models)
- Modify: `transform/models/published/schema.yml` (config.meta blocks)
- Modify: `transform/profiles.yml` (add `lightdash` target using svc_analytics)

**Interfaces:**
- Consumes: published models (Tasks 3 + data core).
- Produces: dbt tag `lightdash` on all published models; metrics with these exact IDs (Task 6 charts reference them as `<table>_<metric>`): member_profile → `total_members, total_spare_capacity, avg_utilization_pct, avg_readiness_score, total_monthly_kwh, avg_energy_cost_share`; supplier_directory → `tier3_suppliers, tier3_spare_capacity, avg_lead_time_days`; buyer_request → `buyer_requests, total_monthly_volume`; reference_stats → `stat_value`. Profiles target `lightdash` (user svc_analytics). Lightdash CLI installed, pinned.

- [ ] **Step 1: Tag published models**

In `transform/dbt_project.yml`, under `models: jmea_transform: published:` add one line (folder-level, inherits to all published models):

```yaml
      +tags: ["lightdash"]
```

- [ ] **Step 2: Add metric meta blocks to `transform/models/published/schema.yml`**

First check the dbt version: `uv run dbt --version`. For dbt-core ≥1.10 use the `config: meta:` nesting shown below; if 1.9.x, put `meta:` directly on the model (same content) — whichever form produces zero deprecation warnings wins.

Add to the existing model entries (merge into current YAML — do not duplicate model names):

```yaml
  - name: member_profile
    config:
      meta:
        label: "Members"
        metrics:
          total_members:
            type: count_distinct
            sql: ${member_id}
            label: "Members"
            description: "Count of distinct member firms"
          total_spare_capacity:
            type: sum
            sql: ${spare_capacity}
            label: "Total spare capacity"
            description: "Sum of spare capacity; only comparable within one capacity unit — filter or group by Capacity unit"
          avg_utilization_pct:
            type: average
            sql: ${utilization_pct}
            round: 1
            label: "Avg utilization %"
            description: "Mean reported capacity utilization for the current quarter"
          avg_readiness_score:
            type: average
            sql: ${readiness_score}
            round: 1
            label: "Avg readiness score"
            description: "Mean export readiness composite (0-100); rubric weights: certs 25%, export history 20%, packaging/logistics/quality 15% each, capacity headroom 10%"
          total_monthly_kwh:
            type: sum
            sql: ${monthly_kwh}
            label: "Total monthly kWh"
            description: "Sum of reported monthly electricity consumption"
          avg_energy_cost_share:
            type: average
            sql: ${energy_pct_of_prod_cost}
            round: 1
            label: "Avg energy % of production cost"
            description: "Mean share of production cost spent on energy"
  - name: supplier_directory
    config:
      meta:
        label: "Matching directory (tier-3 opt-ins)"
        metrics:
          tier3_suppliers:
            type: count_distinct
            sql: ${member_id}
            label: "Opted-in suppliers"
            description: "Members visible to buyers (visibility tier 3)"
          tier3_spare_capacity:
            type: sum
            sql: ${spare_capacity}
            label: "Opted-in spare capacity"
            description: "Spare capacity across tier-3 members; unit-scoped like total spare capacity"
          avg_lead_time_days:
            type: average
            sql: ${lead_time_days}
            round: 1
            label: "Avg lead time (days)"
  - name: buyer_request
    config:
      meta:
        label: "Buyer requests"
        metrics:
          buyer_requests:
            type: count_distinct
            sql: ${request_id}
            label: "Buyer requests"
          total_monthly_volume:
            type: sum
            sql: ${monthly_volume}
            label: "Total monthly volume requested"
            description: "Sum across volume units — filter by Volume unit for comparable numbers"
  - name: reference_stats
    config:
      meta:
        label: "Reference stats (real-world anchors)"
        metrics:
          stat_value:
            type: max
            sql: ${value}
            label: "Value"
            description: "The stat's value; filter to a single stat_key per tile"
```

- [ ] **Step 3: Add the `lightdash` profiles target**

In `transform/profiles.yml`, under `outputs:` add:

```yaml
    lightdash:
      type: postgres
      host: "{{ env_var('JMEA_DB_HOST', 'localhost') }}"
      port: "{{ env_var('JMEA_DB_PORT', '5433') | as_number }}"
      user: svc_analytics
      password: "{{ env_var('SVC_ANALYTICS_PASSWORD', 'analytics_dev') }}"
      dbname: "{{ env_var('JMEA_DB_NAME', 'jmea') }}"
      schema: staging
      threads: 4
```

(This target exists so `lightdash deploy --create` copies **svc_analytics** into the project's warehouse connection. The `generate_schema_name` macro means compiled schemas are unchanged regardless of `schema:` here.)

- [ ] **Step 4: Verify dbt still green**

Run: `uv run dbt build --project-dir transform --profiles-dir transform` → `Completed successfully`, same result count as Task 3 (meta/tags change no SQL). Also compile as the new target: `uv run dbt compile --project-dir transform --profiles-dir transform --target lightdash` → succeeds.

- [ ] **Step 5: Install the pinned Lightdash CLI**

```bash
node --version || winget install OpenJS.NodeJS.LTS   # fresh shell after install
npm install -g @lightdash/cli@<TAG>                  # same tag as the server image (Task 2 Step 1)
lightdash --version
```

Expected: version prints and equals the server tag.

- [ ] **Step 6: Commit**

```bash
git add transform/
git commit -m "feat: lightdash semantic layer (tags, metrics, svc_analytics profile target)"
```

---

### Task 5: Bootstrap, project creation, semantic-layer deploy

**Files:**
- Modify: `README.md` (new "Analytics (Lightdash)" section)

**Interfaces:**
- Consumes: running Lightdash (Task 2), semantic layer (Task 4).
- Produces: a Lightdash org + admin user, a project named `JMEA` whose warehouse connection user is svc_analytics, semantic layer deployed, catalog scoped to tag `lightdash`, and env vars `LIGHTDASH_PAT` + `LIGHTDASH_PROJECT` exported for Tasks 6-7.

- [ ] **Step 1: One-time UI bootstrap (manual, ~3 minutes)**

At `http://localhost:8080`: register the admin account (dev: use your email + a dev password; record it in your local `.env` as a comment, never committed). Then Settings → Personal access tokens → create token `cli-dev` → `export LIGHTDASH_PAT=<token>`.

- [ ] **Step 2: CLI login and project creation**

```bash
lightdash login http://localhost:8080 --token "$LIGHTDASH_PAT"
cd transform
lightdash deploy --create --name JMEA --target lightdash
cd ..
```

Expected: project created; output prints the project URL containing the project UUID → `export LIGHTDASH_PROJECT=<uuid>` (also record both in `.env`). If `--target` is not accepted by the installed CLI version, check `lightdash deploy --help` — the flag may be `--profile`/dbt-target passthrough; the requirement is that the created warehouse connection uses the `lightdash` profiles target (svc_analytics).

- [ ] **Step 3: Scope the catalog by tag**

In the Lightdash UI: Project settings → Tables configuration → "Show models with any of these tags" → enter `lightdash` → save.

Verify: the project's Tables list shows exactly 7 tables (member_profile, sector_summary, sector_energy, supplier_directory, buyer_request, reference_stats — plus any published model added since) and **no stg_/int_ tables**.

- [ ] **Step 4: Validate the semantic layer**

```bash
cd transform && lightdash validate && cd ..
```

Expected: no errors (no content exists yet; this validates the deployed tables/metrics).

- [ ] **Step 5: Write the README section**

Append to `README.md` after the Quickstart section:

```markdown
## Analytics (Lightdash)

Lightdash serves dashboards at http://localhost:8080 (loopback-only), reading the
published schemas as `svc_analytics` — it cannot see raw or staging data.

One-time bootstrap: register the admin account in the UI, create a personal access
token (Settings → Personal access tokens), then:

    export LIGHTDASH_PAT=<token>
    lightdash login http://localhost:8080 --token "$LIGHTDASH_PAT"
    cd transform && lightdash deploy --create --name JMEA --target lightdash && cd ..
    # Project settings → Tables configuration → "Show models with any of these tags" → lightdash
    export LIGHTDASH_PROJECT=<project-uuid-from-deploy-output>

Day-to-day (all content lives in the repo — the UI is a viewer):

    cd transform
    lightdash deploy      # push semantic layer changes (dbt YAML)
    lightdash upload --force   # push charts/dashboards from transform/lightdash/
    lightdash validate    # gate: broken refs, drift
    cd ..

Existing stacks (volume predates Lightdash): create the app DB once with
`docker exec jmea_postgres bash /docker-entrypoint-initdb.d/04_lightdash_db.sh`.
```

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs: lightdash bootstrap and content-as-code workflow"
```

---

### Task 6: Four dashboards as code

**Files:**
- Create: `transform/lightdash/charts/*.yml` (17 charts, listed below)
- Create: `transform/lightdash/dashboards/{capacity-overview,tourism-buyer-matching,export-readiness,energy-burden}.yml`

**Interfaces:**
- Consumes: metrics from Task 4 (field IDs are `<table>_<name>`, e.g. `member_profile_total_spare_capacity`; dimensions likewise `member_profile_sector`), project + PAT from Task 5.
- Produces: four dashboards named exactly `Capacity Overview`, `Tourism & Buyer Matching`, `Export Readiness`, `Energy Burden` (Task 7's smoke test asserts these names), in space `JMEA Demo`.

- [ ] **Step 1: Calibrate against the real as-code schema (probe chart)**

The chart/dashboard YAML schema varies slightly across Lightdash versions; calibrate before authoring: in the UI, build ONE throwaway chart (member_profile: metric Members, dimension Sector, bar chart), save it to a new space `JMEA Demo`, then:

```bash
cd transform && lightdash download && cd ..
```

Inspect `transform/lightdash/charts/<probe>.yml` — this is ground truth for `version`, field-ID casing, `metricQuery`, `chartConfig`, and `spaceSlug` shapes. Author all charts below to match its structure exactly, then delete the probe chart file and the probe in the UI.

- [ ] **Step 2: Author the 17 charts**

Exemplar A — bar chart (`transform/lightdash/charts/spare-capacity-by-sector.yml`), adjust to probe schema:

```yaml
name: Spare capacity by sector
description: Sum of current-quarter spare capacity per sector (units uniform within a sector)
tableName: member_profile
metricQuery:
  exploreName: member_profile
  dimensions:
    - member_profile_sector
  metrics:
    - member_profile_total_spare_capacity
  filters: {}
  sorts:
    - fieldId: member_profile_total_spare_capacity
      descending: true
  limit: 500
  tableCalculations: []
chartConfig:
  type: cartesian
  config:
    layout:
      xField: member_profile_sector
      yField:
        - member_profile_total_spare_capacity
    eChartsConfig:
      series:
        - type: bar
          encode:
            xRef:
              field: member_profile_sector
            yRef:
              field: member_profile_total_spare_capacity
tableConfig:
  columnOrder:
    - member_profile_sector
    - member_profile_total_spare_capacity
slug: spare-capacity-by-sector
spaceSlug: jmea-demo
version: 1
```

Exemplar B — big-number tile (`transform/lightdash/charts/substitutable-imports-headline.yml`):

```yaml
name: Substitutable imports (US$M)
description: "Estimated hotel/restaurant food imports substitutable by local production (source: USDA FAS / Gleaner - real data)"
tableName: reference_stats
metricQuery:
  exploreName: reference_stats
  dimensions: []
  metrics:
    - reference_stats_stat_value
  filters:
    dimensions:
      id: filter-substitutable
      and:
        - id: f1
          target:
            fieldId: reference_stats_stat_key
          operator: equals
          values: ["substitutable_imports"]
  sorts: []
  limit: 1
  tableCalculations: []
chartConfig:
  type: big_number
  config:
    label: Substitutable imports (US$M)
chartConfig_note_remove_me: match probe schema for big_number config keys
tableConfig:
  columnOrder:
    - reference_stats_stat_value
slug: substitutable-imports-headline
spaceSlug: jmea-demo
version: 1
```

(Remove the `chartConfig_note_remove_me` line after aligning with the probe; it exists only to mark the one block whose keys most often differ across versions.)

Remaining 15 charts — same structure, exactly these specs:

| slug | table | metrics | dimensions | type | notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| member-count-tile | member_profile | total_members | — | big_number | |
| avg-utilization-tile | member_profile | avg_utilization_pct | — | big_number | |
| utilization-by-sector | member_profile | avg_utilization_pct | sector | bar | sort desc by metric |
| members-by-parish | member_profile | total_members | parish | table | the map stand-in; sort desc |
| members-by-size-band | member_profile | total_members | size_band | bar | |
| demand-by-sector | buyer_request | total_monthly_volume, buyer_requests | sector | bar | grouped |
| demand-by-buyer-type | buyer_request | buyer_requests | buyer_type | bar | |
| tier3-suppliers-tile | supplier_directory | tier3_suppliers | — | big_number | |
| tier3-capacity-by-sector | supplier_directory | tier3_spare_capacity | sector | bar | |
| cert-coverage | supplier_directory | tier3_suppliers | certifications | table | sort desc; description: coverage of certifications among opted-in suppliers |
| lead-time-fit | supplier_directory | avg_lead_time_days | sector | table | |
| readiness-band-distribution | member_profile | total_members | readiness_band | bar | |
| readiness-by-sector | member_profile | avg_readiness_score | sector | bar | sort desc |
| near-ready-pipeline | member_profile | avg_readiness_score | company, sector, readiness_band | table | filter readiness_band = "Near Ready"; sort desc by metric; limit 40 |
| energy-cost-share-by-sector | member_profile | avg_energy_cost_share, avg_utilization_pct | sector | bar | grouped |
| electricity-price-comparison | reference_stats | stat_value | label | bar | filter stat_key IN (electricity_jm, electricity_us, electricity_tt, electricity_dr, electricity_bb); description notes real data + source |
| kwh-by-sector | member_profile | total_monthly_kwh | sector | bar | |

(17 total including the two exemplars. Every chart gets a one-line `description`; charts on reference_stats state provenance in the description.)

- [ ] **Step 3: Author the 4 dashboard YAMLs**

Structure from the probe download (a dashboard YAML lists tiles referencing chart slugs with x/y/w/h grid coords). Exemplar (`transform/lightdash/dashboards/capacity-overview.yml`) — 2 tiles-wide top row of big numbers, charts below, adjust to probe schema:

```yaml
name: Capacity Overview
description: Member capacity mapping for the current quarter (simulated member data)
tiles:
  - type: saved_chart
    properties: {chartSlug: member-count-tile}
    x: 0
    'y': 0
    w: 12
    h: 6
  - type: saved_chart
    properties: {chartSlug: avg-utilization-tile}
    x: 12
    'y': 0
    w: 12
    h: 6
  - type: saved_chart
    properties: {chartSlug: spare-capacity-by-sector}
    x: 0
    'y': 6
    w: 18
    h: 9
  - type: saved_chart
    properties: {chartSlug: utilization-by-sector}
    x: 18
    'y': 6
    w: 18
    h: 9
  - type: saved_chart
    properties: {chartSlug: members-by-parish}
    x: 0
    'y': 15
    w: 18
    h: 9
  - type: saved_chart
    properties: {chartSlug: members-by-size-band}
    x: 18
    'y': 15
    w: 18
    h: 9
slug: capacity-overview
spaceSlug: jmea-demo
version: 1
```

The other three follow identically:
- `tourism-buyer-matching.yml` — name `Tourism & Buyer Matching`; tiles: substitutable-imports-headline + tier3-suppliers-tile (top row), demand-by-sector, tier3-capacity-by-sector, demand-by-buyer-type, cert-coverage, lead-time-fit.
- `export-readiness.yml` — name `Export Readiness`; tiles: readiness-band-distribution, readiness-by-sector, near-ready-pipeline (full-width bottom, h: 12).
- `energy-burden.yml` — name `Energy Burden`; tiles: electricity-price-comparison (top, full width), energy-cost-share-by-sector, kwh-by-sector.

- [ ] **Step 4: Upload and validate**

```bash
cd transform
lightdash upload --force
lightdash validate
cd ..
```

Expected: upload reports 17 charts + 4 dashboards created; validate passes with zero errors. Then eyeball each dashboard in the UI: numbers match the seeded warehouse (spot-check: members = 72; tier-3 suppliers = 42; electricity JM = 0.238).

- [ ] **Step 5: Commit**

```bash
git add transform/lightdash/
git commit -m "feat: four demo dashboards as code (capacity, matching, readiness, energy)"
```

---

### Task 7: Smoke test suite

**Files:**
- Modify: `tests/test_lightdash.py` (replace with full suite)

**Interfaces:**
- Consumes: `LIGHTDASH_URL`/`LIGHTDASH_PAT`/`LIGHTDASH_PROJECT` env (Task 5), dashboards (Task 6).
- Produces: pytest coverage of the analytics surface: health, exactly-these-4-dashboards, warehouse-user-is-svc_analytics.

- [ ] **Step 1: Write the full suite (replaces the Task 2 file)**

```python
import json
import os
import urllib.request

import pytest

BASE = os.environ.get("LIGHTDASH_URL", "http://localhost:8080")
PAT = os.environ.get("LIGHTDASH_PAT", "")
PROJECT = os.environ.get("LIGHTDASH_PROJECT", "")

EXPECTED_DASHBOARDS = {
    "Capacity Overview",
    "Tourism & Buyer Matching",
    "Export Readiness",
    "Energy Burden",
}

needs_bootstrap = pytest.mark.skipif(
    not (PAT and PROJECT),
    reason="LIGHTDASH_PAT/LIGHTDASH_PROJECT not set - run the README bootstrap and export them",
)


def _get(path):
    req = urllib.request.Request(
        f"{BASE}{path}", headers={"Authorization": f"ApiKey {PAT}"}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def test_lightdash_health():
    with urllib.request.urlopen(f"{BASE}/api/v1/health", timeout=10) as r:
        assert r.status == 200


@needs_bootstrap
def test_four_dashboards_exist():
    body = _get(f"/api/v1/projects/{PROJECT}/dashboards")
    names = {d["name"] for d in body["results"]}
    assert EXPECTED_DASHBOARDS <= names


@needs_bootstrap
def test_warehouse_connection_is_svc_analytics():
    body = _get(f"/api/v1/projects/{PROJECT}")
    assert body["results"]["warehouseConnection"]["user"] == "svc_analytics"
```

- [ ] **Step 2: Run with bootstrap env set**

Run: `LIGHTDASH_PAT=... LIGHTDASH_PROJECT=... uv run pytest tests/test_lightdash.py -v`
Expected: 3 passed. (If `warehouseConnection` omits `user` in this Lightdash version's API response, assert on the field the response does expose that identifies the connection user — inspect the JSON and adjust; the requirement is asserting svc_analytics, not the exact key path.)

Full suite: `uv run pytest` → 25 passed (or 23 passed + 2 skipped without the env vars — both acceptable; CI note recorded in README).

- [ ] **Step 3: Commit**

```bash
git add tests/test_lightdash.py
git commit -m "test: lightdash smoke suite (health, dashboards, svc_analytics connection)"
```

---

### Task 8: Terraform sizing bump + final verification

**Files:**
- Modify: `infra/terraform/variables.tf` (machine_type default)

**Interfaces:**
- Consumes: everything.
- Produces: spec §10 success criteria proven end-to-end.

- [ ] **Step 1: Bump the machine type default**

In `infra/terraform/variables.tf`, change the `machine_type` default to `"e2-standard-2"` and update its description to: `"e2-standard-2 (4 vCPU / 8 GB) - required once Lightdash joins the stack (ADR-0003 staged sizing; data-core-only stacks can override to e2-small)"`.

Run: `terraform -chdir=infra/terraform validate && terraform -chdir=infra/terraform fmt -check -recursive`
Expected: valid, fmt exit 0.

- [ ] **Step 2: Full verification sweep**

```bash
docker compose -f infra/compose/docker-compose.yml up -d --wait     # all services healthy
uv run dbt build --project-dir transform --profiles-dir transform  # Completed successfully (63 results)
cd transform && lightdash deploy && lightdash upload --force && lightdash validate && cd ..
uv run pytest                                                       # all passing (25 with bootstrap env)
git status                                                          # nothing unexpected untracked
```

Every command exits 0.

- [ ] **Step 3: Commit**

```bash
git add infra/terraform/variables.tf
git commit -m "feat: bump default GCP machine type for lightdash (ADR-0003 staged sizing)"
```

---

## Plan Self-Review Notes

- **Spec coverage:** §3 stack → Tasks 1-2; §4 dbt additions (+k-anon statement — no aggregate view over member data added, guard untouched) → Task 3; §5 semantic layer + catalog scoping → Tasks 4-5; §6 dashboards → Task 6; §7 validation/testing → Tasks 6-7; §8 ops (pinning, healthcheck, terraform bump, .env discipline) → Tasks 1, 2, 8; §9 success criteria → Task 8.
- **Known-drift acknowledgments (deliberate, not placeholders):** the Lightdash content-as-code YAML schema and two CLI flags are calibrated against the live instance at implementation time (Task 6 Step 1 probe; Task 5 Step 2 `--target` check) because they vary across Lightdash releases; each such step states the invariant requirement the implementer must satisfy.
- **Type consistency:** metric IDs declared in Task 4 match the `<table>_<metric>` field IDs used in Task 6's chart specs; dashboard names in Task 6 match Task 7's `EXPECTED_DASHBOARDS` exactly (incl. the `&` in `Tourism & Buyer Matching`); env var names match across Tasks 1, 5, 7 and `.env.example`.
- **Numbers:** pytest counts — 21 baseline, +1 (Task 1), +1 (Task 2), +2 role rows (Task 3), Task 7 replaces the Task 2 test with 3 → 25 total with bootstrap env. dbt: 55 baseline + 2 models + 1 seed + 5 tests = 63.
