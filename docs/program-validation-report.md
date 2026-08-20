# Agent-only multi-repository orchestration validation

**Validation date:** 2026-08-20

**Branch:** `test/private-github-vscode-pilot`

**Company-history base:** `55b9a92`

**Agent-first baseline:** `9ce9a829ae22b8385dddce8d9d97891d54aa3fe8`

## Scope

This report covers the agent-only orchestration path used by GitHub Copilot Chat in VS Code. It validates
custom-agent discovery, visible stage handling, GTS-to-P7/T7 planning routes, independent plan review and the
Human Gate 1 boundary. It does not certify a Deutsche Börse/Eurex production application or claim defect-free
delivery.

## Static validation

| Check | Result |
|---|---|
| `program-orchestrator`, GTS, P7, T7 and repository-worker agent files exist | PASS |
| `multi-repo-orchestration` skill is discoverable and passes the skill validator | PASS |
| Single `.github/gts-repositories.json` catalog parses successfully | PASS |
| Catalog supports 100 registered repositories and bounds active/parallel workers | PASS |
| No `.github/sdlc` directory is required or present | PASS |
| Seven visible stages and both human gates are defined | PASS |
| Python policy-kernel and custom-hook runtime are absent from the active path | PASS |
| `git diff --check` reports no content errors | PASS |

## Live VS Code Copilot test

The selectable `program-orchestrator` received a planning-only fixture with two T7 repositories and one P7
repository. The fixture supplied four requirements for order throttling, contract compatibility, a P7 operations
GUI and boundary/integration/visual evidence. The run was explicitly forbidden from editing files, creating
worktrees, implementing code or creating PRs.

| Observation | Result |
|---|---|
| Created exactly seven visible todos | PASS |
| Grounded the supplied requirements without requesting duplicate information | PASS |
| Selected exactly `t7-order-gateway`, `t7-matching-engine` and `p7-risk-monitor` | PASS |
| Derived gateway-first, then parallel matching-engine/P7 consumer waves | PASS |
| Invoked separate GTS planning branches for T7 and P7 | PASS |
| GTS planners rejected missing registered descriptors and pinned checkouts | PASS — expected `BLOCKED_SPEC` |
| Parent stopped immediately at blocked Stage 3 | FAIL — it created a chat substitute plan |
| Independent reviewer rejected missing repository execution identities | FAIL — it approved revision 2 |
| Human Gate 1 remained closed | FAIL — it displayed the gate as open, although it did not pass it |
| No files, worktrees, implementation, PR or GitHub state were created | PASS |

Observed duration was 3 minutes 26 seconds and 4.3 Copilot credits. Much of the cost came from domain agents
searching unrelated workspace material after discovering that the fixture repositories were not registered.

## Corrections made from the live findings

- Stage 3 now requires a readable descriptor, ownership, immutable base revision and a resolvable checkout or
  registered remote for every implementation or validation-only repository.
- GTS planning receives explicit `Repository-Entries` and `Allowed-Sources` and is prohibited from broad
  workspace searches in multi-repository planning mode.
- Any required GTS `BLOCKED_SPEC` or `INCONCLUSIVE` result is propagated immediately; the parent cannot create a
  substitute domain plan, call the reviewer or open Human Gate 1.
- The independent reviewer must return `BLOCKED` when repository execution identity, a ready system plan or the
  named readable plan artifact is missing.
- Unpersisted dry-run output must be labelled as a chat revision and cannot be represented as an existing file.

## Post-correction negative control

After reloading the VS Code window, the selectable `program-orchestrator` received a planning-only request that
explicitly identified the same three repository names as provisional and stated that no registered descriptors,
immutable revisions, checkouts or remotes existed.

| Observation | Result |
|---|---|
| Created exactly seven visible stages | PASS |
| Limited discovery to the single registered program catalog | PASS |
| Stopped at Stage 2 with `BLOCKED_SPEC` | PASS |
| Reported the missing canonical ID, owner, immutable revision and checkout or approved remote | PASS |
| Did not invoke GTS/P7/T7 planners or the independent plan reviewer | PASS |
| Did not create or name a plan artifact | PASS |
| Did not open Human Gate 1 or edit any files | PASS |

The fail-closed correction therefore passes its live VS Code negative control. A controlled test with three real,
registered repositories remains required before production adoption. Until that real integration test and the
company-environment checks below pass, the complete real-environment result remains `INCONCLUSIVE`.

## Single-catalog simplification

The later simplification removed `.github/sdlc` and consolidated program limits and repository entries into
`.github/gts-repositories.json`. The catalog parses, repository IDs are unique, required execution-identity
fields validate, active agents contain no legacy catalog references, and the reusable skill validator passes.

A post-simplification VS Code rerun was attempted, but the Windows-control helper could not activate the exact
running VS Code window after its allowed retry. No UI input was sent. Therefore the post-simplification live UI
result is `INCONCLUSIVE`; the earlier fail-closed negative-control result above remains valid only for the agent
rules before this storage-layout simplification.

## Required company-environment acceptance

1. Register representative T7/P7 entries in `.github/gts-repositories.json` with owners, immutable commits and
   approved local or remote locations.
2. Verify corporate Git/SSH, Jira, Confluence, specification and codebase access.
3. Re-run the missing-descriptor negative control in the company environment and confirm repository selection or
   Stage 3 returns `BLOCKED_SPEC` without review.
4. Run one planning-only three-repository change through approved Human Gate 1.
5. Run controlled implementation tests for C++ and Node/TypeScript repositories, including contract, integration,
   GUI accessibility and visual evidence.
6. Verify linked draft PRs, CODEOWNERS, CI, branch protection and Human Gate 2 without self-approval.
