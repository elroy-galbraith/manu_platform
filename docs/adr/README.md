# Architecture Decision Records

This folder holds the project's Architecture Decision Records (ADRs) — short documents capturing each significant decision, the context that forced it, and the consequences we accepted. They are the project's memory: when someone asks "why Lightdash and not Metabase?" a year from now, the answer lives here, not in a chat log.

## Conventions

- One decision per file, numbered sequentially: `NNNN-short-kebab-title.md`.
- Statuses: **Proposed** → **Accepted** → (possibly) **Superseded by ADR-NNNN** or **Deprecated**. Never delete or rewrite an accepted ADR — write a new one that supersedes it. The history of changed minds is part of the record.
- Keep them short. If an ADR needs more than a page, the decision probably needs to be split.
- Write ADRs at decision time, not retroactively in batches — the context section is worthless once the context is forgotten.

## Template

```markdown
# NNNN. Title (verb phrase: "Use X for Y")

Date: YYYY-MM-DD
Status: Accepted

## Context
What situation forces a decision? Constraints, budget, prior decisions.

## Decision
What we chose, stated plainly.

## Consequences
What becomes easier, what becomes harder, what we're betting on.
```

## Index

- [0001](0001-record-architecture-decisions.md) — Record architecture decisions
- [0002](0002-use-lightdash-for-analytics.md) — Use Lightdash instead of Metabase for the analytics layer
