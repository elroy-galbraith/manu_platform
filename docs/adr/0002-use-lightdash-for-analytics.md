# 0002. Use Lightdash instead of Metabase for the analytics layer

Date: 2026-07-11
Status: Accepted

## Context

The original strawman chose Metabase OSS for the analytics layer, on "fastest to ship, easiest for JMEA staff to self-serve" grounds. But dashboards and visualizations on this project will be built and maintained primarily by AI agents, and Metabase fights that workflow: dashboards live as rows in its internal application database, built through the GUI. The REST API exists but requires assembling verbose, partly undocumented internal JSON (visualization settings, dashcard layouts) with no good way to review or verify the result, and dashboards-as-code via serialization export/import is a paid feature on Metabase.

Separately, the stack already commits to dbt for transformation, which left dbt models and Metabase dashboard definitions as two disconnected worlds with duplicated semantics.

## Decision

Use Lightdash OSS (self-hosted, in the same Docker Compose stack) as the analytics layer. Its semantic layer is the dbt project itself — dimensions and metrics are declared in dbt model YAML — and charts/dashboards round-trip as YAML in the repo via the Lightdash CLI (`lightdash download` / `lightdash upload`).

## Consequences

- **Agent-buildable analytics**: every visualization is plain text in git — writable, diffable, reviewable, and CI-validatable by agents. This was the deciding factor.
- **One source of truth**: the dbt models that implement readiness scoring, k-anonymity, and the published schemas are also the analytics catalog. The §5 trust model is unchanged — Lightdash connects with credentials scoped to the published schemas only.
- **Self-serve changes shape**: staff explore only dimensions/metrics someone has declared in YAML, rather than clicking around raw tables Metabase-style. We treat this as a feature (it enforces the governed-schema discipline), with agent-handled requests closing the loop for new cuts of data. Metabase remains the fallback if GUI-first self-serve becomes a hard requirement.
- **Smaller community** than Metabase; mitigated by the fact that the load-bearing semantics live in dbt, not in Lightdash-specific artifacts.
- Ops footprint is equivalent: one Lightdash container (plus an optional headless-browser container for scheduled chart exports), sharing the Postgres instance with its own database.
