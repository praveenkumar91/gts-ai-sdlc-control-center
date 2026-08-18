---
name: sdlc-debugging
description: "Generic systematic debugging skill. Use when: investigating a bug, tracing unexpected behaviour, diagnosing production issues, or performing root-cause analysis before implementing a fix. Applies to any system."
argument-hint: "Describe the bug or unexpected behaviour to investigate"
systems: [all]
---

# Systematic Debugging Skill

A structured root-cause-first debugging protocol applicable to any system.

## Protocol

### Phase 1 — Reproduce
1. Confirm the bug is reproducible with a minimal test case
2. Document exact steps to reproduce (inputs, environment, version)
3. Capture the actual vs expected output

### Phase 2 — Isolate
1. Identify the component boundary where the failure occurs
2. Use binary search / bisect to narrow to the smallest failing unit
3. Check: Was this ever working? What changed recently? (git log, git bisect)

### Phase 3 — Hypothesize
1. List 2-3 candidate root causes ranked by likelihood
2. For each hypothesis, state: "If this is the cause, then {observable symptom} would also be true"
3. Eliminate hypotheses by checking observables before writing any fix

### Phase 4 — Verify Root Cause
1. Write a failing test that captures the exact bug before touching production code
2. Confirm the test fails for the right reason
3. Only proceed to fix once root cause is confirmed

### Phase 5 — Fix & Confirm
1. Implement the minimal fix for the confirmed root cause
2. Run the failing test — it must now pass
3. Run the full test suite — no regressions
4. Document the root cause and fix in the commit message body

## Rules
- Never fix a symptom — always fix the root cause
- Never modify production code before writing a failing test
- If the bug cannot be reproduced, do not attempt a fix — gather more information first
