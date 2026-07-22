---
name: t7-code-review
description: "Use when: reviewing a T7 code change (C++, Python, shell, SQL, Java GUI). Extends the shared code-review discipline with T7-specific retained gates — the mandatory unit-test discipline, spec-conformance (DFS/SRQ/SIR), component-boundary context, and the Core-Engine hot-path rule — while delegating the code-review concerns themselves to the code-review-lens brain."
systems: [t7]
extends: skills/common/code-review
---

# T7 Code Review

This skill **extends `skills/common/code-review`** — follow that shared discipline (process, holistic
assessment, false-positive avoidance, severity→verdict, scope-to-change, coverage ledger, fail-safe)
and apply the T7-specific rules and **retained gates** below.

- **Code-review concerns** (correctness, quality, security, performance, guideline, dependency,
  intent, boundary/concurrency) → delegate to **`code-review-lens`** (pass `repo`, e.g.
  `gts.eurex.gateway.outboundfi`, so repo-scoped `ARCH-###`/`CONC-###` rules and the SonarQube key
  resolve).
- **Codebase navigation** → `t7-code`. **Specs** → `t7-spec`. **Component map / ownership /
  terminology** → `t7-knowledge-base`. **Guideline lookup/explanation** → `coding-guidelines`.
  Never call `t7codebase` / `t7spec` / `codereviewer-lens` MCP tools directly — delegate to the skill.

## Retained gates (T7 owns these — lens does not)

### 1. Unit-test discipline (mandatory — BLOCKER if absent/inadequate)
- **Presence**: every new/modified public method has tests. If none exist for the changed code, raise
  an immediate BLOCKER ("No unit tests provided for changed code").
- **Coverage**: at least one positive and one negative/edge-case test per changed public method.
- **Independence**: tests must not share mutable state or depend on execution order.
- **No tautological tests**: assert observable behaviour, not a mirror of the implementation.
- **Naming**: describe scenario + expected outcome (e.g. `test_givenExpiredOrder_whenMatchAttempted_thenRejected`).
- **Mocking discipline**: only external dependencies of the class under test are mocked — never the
  class under test itself.
- **Framework consistency**: use the component's established framework (GoogleTest / Catch2 for C++,
  pytest for Python, JUnit 5 for Java).
- **Passing status**: failing/skipped tests reported by the developer are a BLOCKER unless justified.

### 2. Spec-conformance
When the change implements a DFS/SRQ/SIR, validate the implementation against it via `t7-spec`
(lens does not consume T7 specs). Record the spec doc IDs consulted. A material deviation from the
spec is a BLOCKER.

### 3. Component-boundary context
Resolve each changed file's component + owning team via `t7-knowledge-base` (Component Map,
Ownership). Feed the `repo` to `code-review-lens` so `check_architecture_rules` fires; flag any
cross-team boundary crossing to the owning team.

### 4. Core-Engine hot-path rule
No exceptions thrown on the Core-Engine hot path. Treat a violation as **must-fix** even if lens rates
it lower.

## T7 verdict tightening

Per `common/code-review`'s severity→verdict, T7 **blocks earlier**: an `ARCH-###` boundary violation,
a Core-Engine hot-path exception, a missing/inadequate unit test, or a material spec deviation is
**must-fix** (`CHANGES_REQUIRED`) — not advisory.

## Reviewer status (for the orchestrator)

| Status | Meaning | Orchestrator action |
|--------|---------|---------------------|
| **APPROVED** | Correct + standards-compliant; lens `pass`; all retained gates pass | Proceed |
| **APPROVED_WITH_COMMENTS** | Non-blocking remarks only (lens `warn`, no failed gate) | Developer may address optionally |
| **CHANGES_REQUIRED** | Any must-fix (lens `block`, failed test/spec/boundary/hot-path gate) | Re-dispatch to developer |
| **NEEDS_CONTEXT** | Missing info, or **lens unreachable** (fail-safe) | Orchestrator provides context / escalates |
| **BLOCKED** | Cannot review — architectural/dependency blocker | Escalate to user |

Never return APPROVED / APPROVED_WITH_COMMENTS while any CHANGES_REQUIRED item is unresolved, or if
lens was unreachable.

## Output

Use the `common/code-review` output skeleton, plus a **Unit Test Coverage** table (test file · covers
· framework · new tests · all pass? · verdict) and a **Deviations from Design Intent / Spec** section.
Report code-review findings with their lens `rule_id` + `source`; report retained-gate findings as
`Source: unit-test | spec | boundary | hot-path`.
