# Agent-only multi-repository orchestration validation

**Validation date:** 2026-08-20

**Branch:** `test/private-github-vscode-pilot`

**Company-history base:** `55b9a92`

## Current scope

This report covers the workspace-first, agent-only orchestration path used by GitHub Copilot Chat in VS Code.
The parent discovers Git repositories from the actual workspace, selects impact, freezes exact repository
snapshots in a reviewed plan, and reuses the original GTS/P7/T7 specialists. It does not certify a Deutsche
Börse/Eurex production application or claim defect-free delivery.

## Current static validation

| Check | Result |
|---|---|
| `program-orchestrator`, GTS, P7, T7 and repository-worker agent files exist | PASS |
| `multi-repo-orchestration` skill passes the skill validator | PASS |
| No central repository catalog or `.github/sdlc` directory remains | PASS |
| Workspace discovery is metadata-only and bounded to VS Code workspace roots | PASS |
| Incomplete workspace fallback asks for a parent folder, workspace file, paths or Git URLs | PASS |
| Selected repositories require exact commits, dirty states, owners and usable paths | PASS |
| Plan review and Human Gate 1 require frozen repository snapshots | PASS |
| Python policy-kernel and custom-hook runtime are absent from the active path | PASS |
| `git diff --check` reports no content errors | PASS |

## Historical VS Code findings

The first three-repository planning fixture exposed three real fail-open defects: the parent created a substitute
plan after GTS returned `BLOCKED_SPEC`, the independent reviewer approved without execution identities, and Human
Gate 1 was displayed as open. No files or GitHub state were changed. That run took 3 minutes 26 seconds and 4.3
Copilot credits because domain agents searched unrelated workspace material.

The corrected catalog-based version was then reloaded and repeated as a negative control. It created exactly
seven visible stages, stopped at Stage 2 with `BLOCKED_SPEC`, reported the missing execution identity, invoked no
domain planner or reviewer, created no plan artifact, and did not open Human Gate 1 or edit files.

Those historical results motivated the current rules, but they do not by themselves validate the new
workspace-first discovery implementation.

## Workspace-first behavior to validate

| Scenario | Required result | Current result |
|---|---|---|
| Workspace contains only this control repository while request names missing T7/P7 repositories | Inventory the real workspace, report what was found, then stop at Stage 2 and ask for a parent folder, workspace file, paths or URLs | INCONCLUSIVE — Windows-control helper could not activate VS Code after one refresh and retry; no UI input was sent |
| Workspace contains three real repositories | Snapshot all three, classify all three, deep-read only plausible candidates and freeze exact commits in the plan | PENDING |
| Workspace contains many unrelated repositories | Inventory metadata for all, record exclusions, and do not start one worker per repository | PENDING |
| Active repository changes after plan approval | Invalidate Human Gate 1 and return to review | PENDING |
| Remote-only repository list is supplied | Inspect metadata first and do not clone the entire list | PENDING |

The VS Code window was uniquely identified and running, but activation failed both before and after the one
permitted recovery attempt. The test was stopped without submitting a prompt or changing UI state. This is an
automation-harness limitation, not evidence that the workspace-first behavior passed or failed.

## Required company-environment acceptance

1. Open representative T7/P7 repositories through a common parent folder or multi-root VS Code workspace.
2. Verify corporate Git/SSH, Jira, Confluence, specification and codebase access.
3. Run the incomplete-workspace negative control and confirm Stage 2 asks for repository locations without
   invoking domain planners or review.
4. Run one planning-only three-repository change through approved Human Gate 1 and verify exact snapshot drift
   detection.
5. Run controlled implementation tests for C++ and Node/TypeScript repositories, including contract,
   integration, GUI accessibility and visual evidence.
6. Verify linked draft PRs, CODEOWNERS, CI, branch protection and Human Gate 2 without self-approval.

Until the current live scenarios and company-environment checks pass, the production-adoption result is
`INCONCLUSIVE`.
