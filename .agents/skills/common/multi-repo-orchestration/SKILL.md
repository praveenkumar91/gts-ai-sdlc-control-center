---
name: multi-repo-orchestration
description: "Coordinate one software change across multiple repositories above the existing GTS, P7, and T7 orchestrators. Use when repository impact is unknown or a feature, defect, contract, GUI, migration, or integration change may touch more than one repository. Do not use for a clearly read-only question or a deliberately single-repository phase."
---

# Multi-repository orchestration

This is a thin, agent-only control layer. It selects and orders repository work; it does not replace the existing GTS, P7, T7, Ralph, testing, review, build, or PR agents. Do not invoke a Python policy kernel, custom hook, digest protocol, or external control-plane application.

## Keep the work visible

Create exactly these seven todo items in the parent chat before searching or delegating. Do not add an intake wrapper, separate final-status item, subagent item, or any eighth item. Update the seven items after every transition:

1. Clarify request and read authoritative sources
2. Select impacted repositories
3. Compose the cross-repository plan
4. Review, revise, and re-review the plan
5. Human Gate 1
6. Implement and validate dependency waves
7. Verify closure, prepare draft PRs, and Human Gate 2

Show a compact status table in chat. Detailed evidence may live in a change-plan folder, but the current stage, active repositories, blockers, review findings, wave progress, and next action must remain visible to the user.

## Requirements before repositories

- Cite each material obligation to a DFS, FSD, DTS, SRQ, Jira item, approved design, supplied file, or explicit user statement.
- Separate facts, assumptions, and open decisions. Never silently turn an assumption into a requirement.
- If the available material cannot determine observable behaviour, scope, compatibility, security, GUI acceptance, or another material decision, stop as `BLOCKED_SPEC` and ask the smallest focused question. Continue from the same stage when the user answers.
- A prose GUI requirement can define behaviour. Exact visual matching additionally needs a design, screenshot, or approved current-screen baseline.

## Select from metadata, then read source

Read only `.github/gts-repositories.json` for program limits and repository metadata. Validate that it contains a `repositories` array and that its declared size is within `limits.maxCatalogRepositories`. Do not search for a second catalog, legacy descriptor directory, graph, schema, hook, script, run, audit, or pilot artifact. Do not open every repository's source and do not launch one agent per catalog entry.

Classify descriptors as:

- `IMPLEMENTATION`: code or configuration must change.
- `VALIDATION_ONLY`: must be built or tested against the change but should not be edited.
- `CONTEXT_ONLY`: needed to understand a contract or dependency.
- `NOT_IMPACTED`: no evidence-backed impact.

Use ownership paths, produced and consumed contracts, dependencies, system, components, lifecycle, and requirement citations to justify selection. Deep-read or checkout only the active subset. A catalog of 90 repositories with three affected repositories creates three repository workers, not 90.

Before Stage 3 can complete, every `IMPLEMENTATION` or `VALIDATION_ONLY` repository must have a readable registered catalog entry containing its repository ID, system, owners, immutable base revision, and either a resolvable local checkout or registered remote. User-supplied provisional metadata may support impact analysis, but it does not replace this execution identity. If any required entry, revision, checkout, remote, or ownership fact is missing, keep Stage 3 blocked and return `BLOCKED_SPEC` or `INCONCLUSIVE` with the exact missing field. Do not manufacture a repository identity or continue to plan review.

## Plan and independent review

Create a versioned Markdown plan under `.github/change-plans/<change-id>/` using editor tools. Create that folder only for a real change that permits plan artifacts; do not add placeholder run or audit directories. Verify that the path exists and is readable before naming it as a plan artifact. A no-edit dry run may use a clearly labelled `Chat Plan Revision <N>`, but must never display a file path that was not created. The plan must include:

- cited requirement IDs and acceptance checks;
- active and excluded repositories with reasons;
- one bounded task per implementation repository;
- contracts, compatibility, migrations, dependencies, and execution waves;
- unit, component, contract, integration, security, performance, operational, rollback, and GUI evidence only where applicable;
- explicit forbidden scope and unresolved risks.

Ask GTS for one domain-planning response per affected system so the existing P7/T7 planners and architects contribute. Pass only the frozen requirement sources, selected catalog entries, registered revisions, and explicitly allowed local customization paths. Planning agents must not compensate for a missing catalog entry or checkout by searching unrelated workspace files.

Every required response must be `System-Plan: READY`. A `BLOCKED_SPEC` or `INCONCLUSIVE` system response keeps Stage 3 blocked: propagate its focused blocker and stop before plan review or Human Gate 1. Never replace a blocked specialist response with parent-authored domain assumptions.

After all required system plans are ready, invoke the independent program plan reviewer. On `REVISE`, address the required findings, increment the plan revision, and review the complete new revision again. Do not repeat an approved review without a real plan or requirement change. Stop after three unsuccessful review cycles as `INCONCLUSIVE` and show the remaining findings.

Human Gate 1 applies only to the latest independently approved plan revision backed by ready system plans and registered repository identities. No product-code edit starts before the user explicitly approves that revision.

## Dispatch through GTS

After Gate 1, send one bounded envelope per active implementation repository to `gts-orchestrator`. GTS selects P7, T7, or the generic repository worker and loads the repository's local instructions, agents, and skills as additive expertise.

```text
Multi-Repo-Worker: true
Change-Id: <id>
Plan-Revision: <number>
Repository-Id: <id>
System: <P7 | T7 | other>
Repository-Path: <registered path or AUTO>
Base-Revision: <registered revision>
Task-Id: <id>
Requirement-Ids: <ids>
Acceptance-Criteria: <observable checks>
Architecture-Constraints: <contracts and decisions>
Required-Evidence: <applicable tests, review, build, security, GUI, integration>
Attempt: <1..configured maximum>
Forbidden-Scope: <paths, repositories, and behaviours not approved>
Local-Customizations: <registered instruction, agent, and skill paths>
```

Run dependency-ready repositories in waves and parallelize only independent work. Serialize shared contracts, databases, schemas, environments, and integration baselines. A worker that discovers new scope returns `SCOPE_CHANGE`; revise and re-review the plan instead of editing the extra repository. Retry a failed task only when evidence identifies a concrete repair, with at most two repair attempts by default.

## Close against the plan

Invoke the independent program verifier after all waves. It must map every requirement to changed paths and evidence, and every changed path back to an approved task. Missing, stale, skipped, flaky, or inaccessible mandatory evidence is `INCONCLUSIVE`, not `PASS`.

Prepare linked draft PRs only after closure passes. Human Gate 2 occurs before approval, merge, release, deployment, or delivery. Never self-approve or bypass CODEOWNERS, CI, branch protection, or repository policy.

Report exactly one final status: `PASS`, `FAIL`, `INCONCLUSIVE`, or `BLOCKED_SPEC`. No finite agent workflow guarantees defect-free software.
