# 0003. Provision hosting with Terraform on Google Cloud; Postgres stays containerized

Date: 2026-07-11
Status: Accepted

## Context

The strawman's hosting sketch (§6) named a generic "4 vCPU / 8 GB VM plus a small managed Postgres" without committing to a provider or a provisioning method. Hosting will be on Google Cloud (decided during the data-core design session). Hand-configured cloud consoles are unauditable and unreproducible — a poor fit for a project built largely by AI agents, where infrastructure-as-code gives the same reviewability benefits that ADR-0002 sought for dashboards.

A second decision was nested inside: whether Postgres runs as Cloud SQL (the strawman's "managed Postgres") or as a container in the Compose stack on the VM.

## Decision

- **Terraform** provisions all GCP resources: compute instance, static IP, firewall rules, service account, GCS backup bucket, and a startup script that installs Docker and brings up the Compose stack. Lives in `infra/terraform/`.
- **Docker Compose remains the runtime layer** — the same Compose files run on a developer machine and on the VM. Terraform provisions; Compose runs.
- **Postgres 16 runs in the Compose stack**, not Cloud SQL, with its data on a named volume backed by the VM's persistent disk and a nightly `pg_dump` shipped to the GCS bucket.
- Instance size starts at **e2-small** (~US$13/month) for the data core, moving to **e2-standard-2** (4 vCPU / 8 GB, ~US$49/month) when Budibase, Lightdash, and the matching service land — the class §6 budgeted.

## Consequences

- Environments are reproducible and reviewable: `terraform apply` from a clean checkout recreates the whole footprint, and infra changes go through the same diff-and-review flow as code.
- Local dev and cloud are identical at the runtime layer — no Cloud SQL auth-proxy divergence.
- Running costs drop to roughly half the strawman's US$120/month ceiling at full Phase 1 scale.
- We own backup and restore. Mitigations: nightly `pg_dump` to GCS with restore steps documented and tested; data volumes are hundreds of rows at pilot scale.
- A VM outage takes the database down with the apps — accepted at pilot scale. **Cloud SQL remains the fallback** if operational load or availability requirements grow; the trust-model roles and grants work identically there, so migration cost is confined to Terraform and connection config.
- Jamaica DPA posture from §6 is unchanged: GCP `us-east1` satisfies the "US-East with a data-processing agreement" arrangement.
