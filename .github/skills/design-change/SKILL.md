---
name: design-change
description: Create production-grade architecture evidence for a compiled requirement set, including affected components, ADRs, interfaces, data consistency, threat model, failure modes, capacity, observability, migration, rollout, and rollback. Use only after requirements pass the specification gate.
---

# Design Change

1. Read the requirement set, repository architecture, dependency boundaries, and existing ADRs.
2. Identify affected components, callers, consumers, data stores, messages, scheduled jobs, and operational controls.
3. Evaluate at least two viable designs for high-risk changes and record trade-offs.
4. Define transactional boundaries, idempotency, ordering, concurrency, time semantics, numeric precision, and reconciliation.
5. Define authentication, authorization, auditability, data classification, encryption, secrets, and abuse cases.
6. Define capacity assumptions, latency budgets, failure isolation, observability, migration, rollout, and rollback.
7. Map every design decision to requirement IDs.
8. Record unresolved decisions and block implementation when any critical design question remains open.

Prefer incremental, reversible changes. Never approve architecture based only on the implementer's proposed code.

Draft `design.json`, `threat-model.json`, and `rollback-plan.json` payloads
under `.github/sdlc/runs/<change-id>/work/`. Record them through
`sdlc_engine.py record-artifact` as producer `solution-architect`; never edit
run state or envelopes directly.
