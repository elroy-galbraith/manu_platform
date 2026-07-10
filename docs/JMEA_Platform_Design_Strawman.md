**AEON TECHNOLOGY SOLUTIONS · INTERNAL STRAWMAN · JULY 2026**

**JMEA Industry Intelligence Platform**

Platform Design Strawman & PoC Demo Companion

# **1 · Purpose of this strawman**

This document is a deliberately opinionated first design for the platform proposed to JMEA. It exists to force decisions: every choice below is stated as a recommendation with its trade-off, so the team can disagree with something concrete rather than debate in the abstract. It is paired with a working proof-of-concept demo (single-file HTML dashboard) and a seed dataset covering the four first-stage use cases in the proposal: capacity mapping, tourism matching, export readiness, and energy burden.

One number shapes the whole design: the proposal prices Phases 1–3 development at J$2.5M (\~US$16,000). At that budget, building a bespoke platform from scratch is not viable. The architecture must be an assembly of proven open-source components, with custom code confined to the pieces that differentiate the platform — the matching engine, readiness scoring, and the member trust model.

# **2 · Architecture overview**

Five layers, all deployable on a single VM with Docker Compose in Phase 1, separable later if usage justifies it.

| Layer | Role | Component |
| :---- | :---- | :---- |
| Collection | Member portal: forms, CSV upload, admin approval queue, quarterly reminders | Budibase (OSS app builder) \+ custom validation rules |
| Storage | Governed central warehouse; raw → staged → published schemas | PostgreSQL 16 (managed instance) |
| Transformation | Validation, readiness scoring, aggregation views, k-anonymity enforcement | dbt-core \+ lightweight Python ingestion jobs |
| Analytics | Role-scoped dashboards, executive views, sector benchmarks — defined as code alongside dbt | Lightdash OSS |
| Custom services | Matching engine, export readiness API, later: policy simulator, AI assistant | FastAPI (Python), one small service |

Operating flow mirrors the proposal's operating logic: members submit or upload data through the portal; JMEA admins validate high-value fields; dbt transforms publish only what each visibility tier permits; Lightdash and the matching service read exclusively from the published schema. Nothing downstream can touch raw member submissions.

# **3 · Build vs. assemble decisions**

Curated to realistic options only; recommended choice listed first in each row with the trade-off stated.

| Module | Recommendation | Alternative & trade-off |
| :---- | :---- | :---- |
| Member portal / CRM-style collection | Budibase — forms, RBAC, approval workflows out of the box | NocoDB is better as an Airtable-style admin grid but weaker for member-facing forms; fully custom portal costs 4–6 weeks the budget doesn't have |
| Warehouse | PostgreSQL — boring, cheap, DPA-compliant hosting available regionally | A cloud warehouse (BigQuery et al.) is overkill at hundreds of rows and complicates data-residency conversations |
| Ingestion / pipelines | Custom Python jobs \+ dbt — data volumes are tiny; a scheduler and 300 lines of Python suffice | Airbyte/Meltano add container sprawl and upgrade churn for connectors this project mostly doesn't need; adopt later only for trade-data APIs if worthwhile |
| Dashboards | Lightdash OSS — dashboards-as-code (YAML in the repo), semantic layer unified with dbt, buildable and maintainable by AI agents under version control | Metabase OSS is the fallback if GUI-first self-serve for staff becomes a hard requirement, but its dashboards live in an internal app DB (dashboards-as-code is a paid feature) and are awkward for agents to build; see ADR-0002 |
| Matching engine | Custom FastAPI service — this is core IP; scoring must be transparent and explainable to members | No credible OSS 'supplier matching' base exists; keep the scoring rubric in SQL/Python, not a black box |
| Auth & roles | Application-level roles in Budibase \+ Lightdash spaces/roles | Keycloak gives real SSO but is heavy ops for a 5-role system; defer until partner/buyer logins scale |
| Trade data | Scheduled pulls: UN Comtrade, WITS, World Bank APIs into reference schema | Manual quarterly CSV loads are acceptable Phase 1 fallback — these sources update slowly |
| AI assistant (Phase 3\) | Claude API with retrieval over the published schema \+ policy docs | Self-hosted LLM avoids per-query cost but is unrealistic at this budget and quality bar |

# **4 · Core data model**

Ten entities carry the whole MVP. Field-level detail lives in the seed data files that accompany this document.

| Entity | Key fields | Source |
| :---- | :---- | :---- |
| member | company, sector, parish, size band, contacts | Member portal |
| product | member → products, category mapping (HS-aligned) | Member portal |
| capacity\_submission | capacity, utilization, spare capacity, lead time, quarter | Member portal, quarterly |
| certification | type, issuer, expiry, verification status | Portal \+ JMEA validation |
| energy\_submission | monthly kWh, cost, generator share, renewables, quarter | Member portal, quarterly |
| workforce\_submission | employment, vacancies, skills gaps | Member portal |
| buyer\_request | buyer, type, products needed, volume, required certs, lead time | JMEA staff / buyer intake |
| match | request × member, component scores, status, outcome | Matching service |
| readiness\_score | six sub-scores, composite, band, action items, as-of date | dbt model |
| visibility\_setting | member × field-group → tier (1/2/3), changed-at audit | Member portal |

Two scoring rubrics are the platform's analytical heart and are implemented identically in the PoC demo so JMEA can inspect them:

* **Export readiness (0–100):** certifications 25%, export history 20%, packaging & labelling 15%, logistics 15%, quality systems 15%, capacity headroom 10%. Bands: Export Ready ≥75, Near Ready 55–74, Developing 35–54, Early Stage \<35.

* **Buyer–supplier match (0–100):** product fit 35%, certification compliance 25%, capacity coverage 25%, lead-time fit 15%. Only Tier-3 opted-in members are ever shown to buyers; others appear to JMEA staff as anonymized potential.

# **5 · Trust model implementation**

The proposal's three-tier visibility model is enforced in the database, not in the UI. Every field group carries a member-controlled tier. dbt builds three published schemas: pub\_private (member \+ admin only), pub\_aggregate (sector-level views with a k-anonymity rule — no aggregate cell published unless it contains at least 5 firms), and pub\_matching (Tier-3 opt-ins only). Lightdash and the matching service have database credentials scoped to the published schemas and physically cannot query raw submissions. This makes the confidentiality promise auditable — a stronger claim in front of members than a policy document.

# **6 · Hosting & running cost sketch**

Phase 1 runs on a single Terraform-provisioned Google Cloud VM (Docker Compose: Budibase, Lightdash, FastAPI, nginx), starting at e2-small (~US$13/month) for the data core and scaling to e2-standard-2 (4 vCPU / 8 GB, ~US$49/month) when the full stack lands. Postgres 16 runs in the Compose stack with a nightly pg\_dump to a GCS bucket rather than as a managed instance (see ADR-0003); Cloud SQL is the fallback if operational load grows. Domain and TLS effectively free. Total under US$60/month at full Phase 1 scale, which sits inside the J$1.5M annual maintenance line with substantial room for support labour. Jamaica DPA posture: JMEA as data controller, Aeon as processor, data hosted in-region or US-East with a data-processing agreement; audit trail via Postgres logical replication of the raw schema.

# **7 · PoC → production path**

| Stage | What exists | What it proves |
| :---- | :---- | :---- |
| PoC (now) | Single-file HTML dashboard, 72 simulated members, 15 buyer requests, real trade & energy reference data | The four first-stage use cases are demonstrable and the scoring rubrics survive scrutiny |
| Pilot (Phase 1\) | Budibase portal \+ Postgres \+ dbt \+ Lightdash; 20–30 real members across priority sectors | Members will actually submit data; validation workflow works; first real dashboards |
| Phase 2 | Matching service live for tourism buyers; export readiness scorecards with action plans | Deals attributable to the platform — the renewal argument |
| Phase 3 | Energy analytics at scale, policy simulator, AI assistant over published schema | JMEA as manufacturing intelligence authority |

# **8 · Seed data provenance**

The PoC deliberately mixes simulated and real data, and labels which is which:

* **Simulated:** 72 member firms across the proposal's priority sectors (names are fictional Jamaican place-name composites; no real company is depicted), their capacity, certifications, energy submissions, readiness scores, and 15 buyer requests with computed matches. Deterministic generator script included — regenerate or rescale at will.

* **Real:** Jamaica exports US$1,867M (2024) and US$2,002M (2023, STATIN); manufacturing ≈8.5% of GDP with US$961M export earnings (2022); commercial electricity US$0.238/kWh (Sep 2025\) vs US$0.128 in the US; food import bill ≈US$1.3B (2024) with ≈60% flowing to hotels/restaurants and US$350M estimated as substitutable by local production — the tourism-linkage headline.

Files: seed-data/members.csv, buyer\_requests.csv, matches.csv, jmea\_poc.db (SQLite), seed\_data.json (embedded in the demo), generate\_seed\_data.py.

# **9 · Open questions for the discovery session**

* How many of JMEA's \~400 members have data in any structured form today? Pilot sector choice should follow the answer.

* Does JMEA staff or Aeon operate the validation queue in year one? Determines admin UX investment.

* Will buyers (hotels, distributors) get logins in Phase 2, or does JMEA broker all introductions? Changes the auth decision in §3.

* Is there an existing JMEA member census/survey that can seed the registry before members self-serve?