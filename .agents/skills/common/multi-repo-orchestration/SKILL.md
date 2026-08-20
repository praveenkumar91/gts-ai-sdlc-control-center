---
name: multi-repo-orchestration
description: "Coordinate one software change across multiple repositories above the existing GTS, P7, and T7 orchestrators. Use when repository impact is unknown or a feature, defect, contract, GUI, migration, or integration change may touch more than one repository. Do not use for a clearly read-only question or a deliberately single-repository phase."
---

# Multi-repository orchestration

This is a thin, agent-only control layer. It selects and orders repository work; it does not replace the existing GTS, P7, T7, Ralph, testing, review, build, or PR agents. Do not invoke a Python policy kernel, custom hook, repository catalog, digest protocol, or external control-plane application.

## Keep the work visible

Create exactly these seven todo items in the parent chat before searching or delegating. Do not add an intake wrapper, separate final-status item, subagent item, or any eighth item. Update the seven items after every transition:

1. Clarify request and read authoritative sources
2. Select impacted repositories
3. Compose the cross-repository plan
4. Review, revise, and re-review the plan
5. Human Gate 1
6. Implement and validate dependency waves
7. Verify closure, prepare draft PRs, and Human Gate 2

Show a compact status table in chat. Detailed evidence may live in a change-plan folder, but the current stage, discovered and active repositories, blockers, review findings, wave progress, and next action must remain visible to the user.

## Requirements before repositories

- Cite each material obligation to a DFS, FSD, DTS, SRQ, Jira item, approved design, supplied file, or explicit user statement.
- Separate facts, assumptions, and open decisions. Never silently turn an assumption into a requirement.
- If the available material cannot determine observable behaviour, scope, compatibility, security, GUI acceptance, or another material decision, stop as `BLOCKED_SPEC` and ask the smallest focused question. Continue from the same stage when the user answers.
- A prose GUI requirement can define behaviour. Exact visual matching additionally needs a design, screenshot, or approved current-screen baseline.

## Discover the workspace before selecting impact

Use the VS Code workspace as the primary repository inventory. Enumerate every distinct Git top-level directory inside every workspace folder with read-only editor, filesystem, and Git operations. Include ordinary clones and Git worktrees, resolve canonical paths, and deduplicate nested or repeated roots. Never search outside the supplied workspace roots and never scan an entire drive or user profile.

For every discovered repository, collect a lightweight runtime snapshot before deep-reading source:

- canonical repository path and origin remote when present;
- exact 40-character `HEAD`, current branch, and clean or dirty status;
- root manifests, language/build indicators, CODEOWNERS, and top-level tracked paths;
- local `.github/copilot-instructions.md`, `.github/instructions/**`, `.github/agents`, `.agents/skills`, and `AGENTS.md` locations;
- ownership, components, contracts, and dependencies that can be evidenced from those files.

Do not open every source file, launch one agent per repository, or run builds and tests during discovery. A workspace containing 90 repositories produces 90 lightweight snapshot rows, not 90 deep analyses or workers.

If no repositories are found, a repository named by the request is absent, a required producer or consumer cannot be located, or the available workspace cannot establish a complete project boundary, keep Stage 2 `BLOCKED_SPEC`. Show what was found and ask once for the smallest useful input: a parent folder to add to the workspace, a `.code-workspace` file, local repository paths, or Git URLs. Prefer one parent folder over asking the user to type dozens of repositories. Treat the supplied set as authoritative for that change only; do not persist a custom central catalog.

For remote-only entries, inspect provider metadata when available and do not clone the whole list. Deep-read or clone only repositories that remain plausible impact candidates, using a user-approved workspace location. If required access or a usable location is missing, ask the focused access or path question.

## Select impact from runtime evidence

Classify every discovered repository as:

- `IMPLEMENTATION`: code or configuration must change.
- `VALIDATION_ONLY`: must be built or tested against the change but should not be edited.
- `CONTEXT_ONLY`: needed to understand a contract or dependency.
- `NOT_IMPACTED`: no evidence-backed impact.

Use ownership paths, produced and consumed contracts, dependencies, system, components, tracked paths, manifests, local expertise, and requirement citations to justify selection. Deep-read source only for plausible candidates and record the strongest evidence-backed exclusion reason for every other repository.

Before Stage 3 can complete, every `IMPLEMENTATION` or `VALIDATION_ONLY` repository must have a verified Git root, canonical path or approved remote, accountable owner from CODEOWNERS/local evidence or explicit user confirmation, exact current commit, system route, and relevant local customizations. User-supplied provisional names may guide discovery but do not establish execution identity. If any required fact is missing, return `BLOCKED_SPEC` or `INCONCLUSIVE` with the exact missing field; do not manufacture identity or continue to plan review.

## Freeze the plan and review it independently

Create a versioned Markdown plan under `.github/change-plans/<change-id>/` using editor tools. Create that folder only for a real change that permits plan artifacts; do not add placeholder run or audit directories. Verify that the path exists and is readable before naming it. A no-edit dry run may use a clearly labelled `Chat Plan Revision <N>`, but must never display a file path that was not created.

The plan must freeze the exact runtime snapshot for every active repository and include:

- cited requirement IDs and observable acceptance checks;
- discovered, active, and excluded repositories with reasons;
- canonical path or remote, exact base commit, branch, dirty status, and accountable owner for each active repository;
- one bounded task per implementation repository;
- contracts, compatibility, migrations, dependencies, and execution waves;
- unit, component, contract, integration, security, performance, operational, rollback, and GUI evidence only where applicable;
- explicit forbidden scope and unresolved risks.

Ask GTS for one domain-planning response per affected system so the existing P7/T7 planners and architects contribute. Pass only the frozen requirement sources, selected runtime snapshots, exact commits, and explicitly allowed local customization paths. Planning agents must not compensate for a missing repository or checkout by searching outside the supplied workspace.

Every required response must be `System-Plan: READY`. A `BLOCKED_SPEC` or `INCONCLUSIVE` response keeps Stage 3 blocked: propagate its focused blocker and stop before plan review or Human Gate 1. Never replace a blocked specialist response with parent-authored domain assumptions.

After all system plans are ready, invoke the independent program plan reviewer. On `REVISE`, address the required findings, increment the plan revision, and review the complete new revision again. Stop after three unsuccessful review cycles as `INCONCLUSIVE` and show the remaining findings.

Human Gate 1 applies only to the latest independently approved plan revision backed by ready system plans and frozen repository snapshots. Immediately before implementation, re-resolve each active repository's commit and dirty status. Any difference from the approved snapshot invalidates approval and returns to plan review. No product-code edit starts before explicit approval.

## Dispatch through GTS

After Gate 1, send one bounded envelope per active implementation repository to `gts-orchestrator`. GTS selects P7, T7, or the generic repository worker and loads the repository's local instructions, agents, and skills as additive expertise.

```text
Multi-Repo-Worker: true
Change-Id: <id>
Plan-Revision: <number>
Repository-Id: <canonical path or remote-derived stable ID>
System: <P7 | T7 | other>
Repository-Path: <verified canonical or isolated path>
Base-Revision: <plan-frozen 40-character commit>
Task-Id: <id>
Requirement-Ids: <ids>
Acceptance-Criteria: <observable checks>
Architecture-Constraints: <contracts and decisions>
Required-Evidence: <applicable tests, review, build, security, GUI, integration>
Attempt: <1..2 by default>
Forbidden-Scope: <paths, repositories, and behaviours not approved>
Local-Customizations: <discovered instruction, agent, and skill paths>
```

Run dependency-ready repositories in waves with at most four workers in parallel by default. Serialize shared contracts, databases, schemas, environments, and integration baselines. A worker that discovers new scope returns `SCOPE_CHANGE`; revise and re-review the plan instead of editing the extra repository. Retry only when evidence identifies a concrete bounded repair, at most twice by default.

## Close against the plan

Invoke the independent program verifier after all waves. It must map every requirement to changed paths and evidence, and every changed path back to an approved task. Missing, stale, skipped, flaky, or inaccessible mandatory evidence is `INCONCLUSIVE`, not `PASS`.

Prepare linked draft PRs only after closure passes. Human Gate 2 occurs before approval, merge, release, deployment, or delivery. Never self-approve or bypass CODEOWNERS, CI, branch protection, or repository policy.

Report exactly one final status: `PASS`, `FAIL`, `INCONCLUSIVE`, or `BLOCKED_SPEC`. No finite agent workflow guarantees defect-free software.
