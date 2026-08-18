---
name: implement-change
description: Implement an approved requirement and architecture package with production-grade code, tests, documentation, observability, migrations, and rollback support. Use only when specification and design gates have passed.
---

# Implement Change

1. Refuse to start without an approved requirement set and design record.
2. Implement in small, reviewable vertical slices and preserve repository conventions.
3. Reference requirement IDs in tests and traceability evidence, not as noisy comments throughout production code.
4. Implement error handling, authorization, auditability, telemetry, timeout, retry, idempotency, and rollback behavior required by the design.
5. Add tests at the lowest effective level plus required integration and contract coverage.
6. Run configured quality gates after each coherent slice.
7. Update the traceability manifest with changed files and test IDs.
8. Report deviations instead of changing requirements or design silently.

Never weaken tests, suppress findings, reduce thresholds, disable scanners, bypass approvals, or alter generated evidence to obtain a pass.

After the implementation and its tests are committed with a clean worktree,
run `sdlc_engine.py bind-commit --actor implementation`. Draft
`implementation-summary.json` and `traceability.json` payloads under the run's
`work/` directory, then record both through the engine as producer
`implementation`.
