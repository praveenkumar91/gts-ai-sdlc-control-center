---
name: verify-evidence
description: Independently verify a change against cited requirements and architecture using traceability, test adequacy, negative cases, property checks, mutation testing, regression analysis, and reproducible evidence. Use after implementation and before release evaluation.
---

# Verify Evidence

1. Derive the verification plan from requirements and invariants, not from the implementer's summary.
2. Confirm every applicable requirement maps to design, code, tests, and a reproducible result.
3. Confirm executed repository and integration gate IDs exactly match the
   frozen per-change verification matrix; reject unplanned, omitted, disabled,
   or remapped gates.
4. Confirm every claimed implementation file is changed between the approved
   base and the exact tested commit.
5. Inspect test assertions to ensure they prove the acceptance criteria rather than only execute code.
6. Add or request negative, boundary, concurrency, retry, recovery, authorization, data integrity, and compatibility tests.
7. Use property-based, mutation, fuzz, performance, or replay testing where the risk policy requires them.
8. Run the complete configured gate set in a clean environment.
9. Record command, tool version, commit SHA, input fixture identity, result, and artifact digest.
10. Return `FAIL` or `INCONCLUSIVE` when evidence is incomplete, flaky, non-reproducible, or contradicted.

Never infer correctness from compilation, coverage percentage, or the existence of a test alone.

Draft `verification-report.json` and `quality-gates.json` payloads under the
run's `work/` directory. Record them through `sdlc_engine.py record-artifact`
as producer `verification`. Do not modify implementation evidence or run state.
