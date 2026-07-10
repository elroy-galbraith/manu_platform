# 0001. Record architecture decisions

Date: 2026-07-11
Status: Accepted

## Context

The platform design starts from a deliberately opinionated strawman ([JMEA_Platform_Design_Strawman.md](../JMEA_Platform_Design_Strawman.md)) whose purpose is to be disagreed with. As decisions are revisited — component swaps, scope changes, discoveries from the JMEA sessions — the strawman gets edited in place, and the reasoning behind each change would otherwise be lost. The project is also built with heavy AI-agent involvement; agents (and future humans) need durable, greppable context for why things are the way they are.

## Decision

Maintain Architecture Decision Records in `docs/adr/`, one file per decision, following the conventions in [README.md](README.md). Any change that alters the strawman's architecture, component choices, data model, or trust model gets an ADR at the time the decision is made. The strawman remains the current-state design document; ADRs are the changelog of reasoning.

## Consequences

- The strawman can stay clean and current without losing decision history.
- Agents working on the codebase can read the ADR index to absorb project context cheaply.
- Small overhead per decision (~15 minutes), which experience says pays for itself the first time a decision is re-litigated.
