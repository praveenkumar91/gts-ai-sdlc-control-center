---
name: validate-gui-change
description: Derive and verify a production GUI acceptance contract from prose, DFS/FSD requirements, designs, or approved baselines. Use for frontend, Vite, TypeScript, browser, component, accessibility, responsive, visual-regression, or end-to-end changes, especially when requirements describe behavior but provide no screens.
---

# Validate a GUI change

Treat prose as behavioral input, not an exact visual oracle. Build a cited UI contract before implementation.

## Establish the contract

Derive:

- actors, permissions and user journeys;
- visible content and financial display invariants;
- normal, loading, empty, partial, error, timeout, offline and unauthorized states;
- validation, confirmation, cancellation and double-submit behavior;
- keyboard, focus and accessibility expectations;
- supported browsers, devices, resolutions, locale, timezone and theme;
- measurable performance budgets.

If appearance is normative but no approved design system, design or reference image exists, produce candidate wireframes and stop at `BLOCKED_SPEC`. Human Gate 1 must approve the visual baseline. Never silently choose a generated screen as correct.

Read [gui-evidence-contract.md](references/gui-evidence-contract.md) for required evidence.

## Verify independently

Derive tests from the approved UI contract, not from implementation details. Require component tests, end-to-end journeys, screenshot comparison, responsive/browser projects, automated accessibility, keyboard/focus checks and financial-format invariants.

Generate screenshots, diffs, Playwright traces and videos in a stable CI image. Treat a missing baseline, missing viewport, unexpected diff or inaccessible state as a blocking result.

Do not update snapshots, relax pixel thresholds, hide dynamic regions, disable accessibility rules or change requirements to make a test pass. Baseline changes require the same reviewed plan digest.

Return `PASS`, `FAIL`, `INCONCLUSIVE` or `BLOCKED_SPEC` with requirement IDs, exact commit, browser/viewport matrix, commands, results and evidence paths.
