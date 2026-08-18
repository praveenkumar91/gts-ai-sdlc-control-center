---
name: orchestrate-program-change
description: Coordinate a complex change across multiple Git repositories using dependency impact analysis, human plan approval, isolated worktrees, commit-vector evidence, bounded remediation, integration validation, and linked PR approval. Use for program-level features, defects, migrations, DFS/FSD changes, or releases that may affect more than one repository.
---

# Orchestrate a program change

Use `.github/scripts/program_orchestrator.py` as the only writer of program-run state. Never edit program run JSON or event logs manually.

## Plan

Read `.github/sdlc/program.json` and the authoritative sources. Identify only the repositories directly implicated by the requirement and pass them as planning seeds. Allow the deterministic graph to calculate downstream validation and upstream checkout scope.

Immediately mirror the run's `VISIBLE_STEPS.md` in the VS Code todo control and
print it in Chat. Refresh it after every state transition.

Start a run in `AWAITING_CLARIFICATION` and record an intake assessment:

```text
python .github/scripts/program_orchestrator.py assess-intake --change-id <id> --evidence <intake-assessment.json>
```

Use `NEEDS_CLARIFICATION` when authoritative content cannot be read or the
behavior, impacted screens, approved visual baseline, boundaries, failure
behavior or measurable acceptance criteria are incomplete. Show the concrete
questions to the user and wait. Do not infer answers from repository code.
Record `READY` only with cited source facts, evidence references, no open
questions, no inaccessible sources and no unverified assumptions.

Before planning, freeze a per-change verification matrix in
`requirements.json`. Stable acceptance-criterion IDs and required evidence
types must map to reusable repository or integration gate IDs. Every owning
repository requires a repository mapping and every requirement requires an
integration mapping. Do not add change-specific requirement IDs to reusable
repository quality configuration.

Start and plan:

```text
python .github/scripts/program_orchestrator.py start --change-id <id> --request "<request>" --requested-by <identity> --risk-tier <tier>
python .github/scripts/program_orchestrator.py plan --change-id <id> --repositories <comma-separated-seeds> --requirements <requirements.json>
```

The first plan enters `AWAITING_PLAN_REVIEW`. Record independent requirements,
architecture, testing, security or adversarial review evidence with
`review-plan`. High-risk plans require two distinct passing reviewers and
review types; critical plans require three. `CHANGES_REQUIRED` forces a new
plan revision and invalidates all previous passes. Stop at
`AWAITING_PLAN_APPROVAL` only after all cycles pass. Do not implement until
independent, externally auditable, non-placeholder plan evidence has been
recorded with `approve-plan`; conversational approval is not evidence.

Read [program-manifest.md](references/program-manifest.md) when configuring or changing the repository graph.

## Prepare safely

Run `inventory` and dry-run `prepare-workspaces` first. Existing repositories must be clean and have the configured remote. Use `--allow-clone` only when credentials and repository scope are approved. Use `--execute` only after Human Gate 1.

Never switch the user's current branch, overwrite a dirty worktree, reset a repository, or silently substitute another remote.

## Execute and verify

Process the plan's `execution_waves` in order and bound parallelism by `maximum_parallel_repositories`. A repository may run concurrently only with repositories in the same wave.

Use the `supervise-agent-execution` skill and run
`.github/scripts/agent_supervisor.py` for the adaptive implementation phase.
The program orchestrator remains the only program-state writer; do not replace
the supervisor with conversational claims that a worker or test completed.

For every validation-scope repository:

1. resolve its repository extension packet;
2. use `use-repository-extensions` to apply selected local instructions, skills
   and agent roles;
3. operate its repository-scoped SDLC;
4. commit changes and refresh the packet at the exact HEAD;
5. run resolved stack and risk gates selected by the approved verification matrix;
6. bind evidence to both the HEAD and `repository_extension_digest`;
7. record the result through `record-repository-result`.

After any repaired repository changes, rerun its gates and every affected downstream and cross-repository gate. Stop after the configured remediation limit.

Do not edit a validation-only repository. If it needs implementation, stop,
replan with that repository as a seed, and obtain new Human Gate 1 approval.
Record integration evidence only when its commit vector exactly equals the
checked-out repository heads and every cross-repository gate reports `PASS`.
The integration gate set and its requirement, criterion, and evidence mappings
must exactly match the frozen verification matrix; unplanned or omitted gates
are rejected.
Use `run_integration_gates.py --record` to execute the configured program-level
commands and record its original generated evidence. Do not replace it with a
hand-written PASS payload. Record failed and inconclusive attempts and stop when
the configured remediation budget is exhausted.
Stop at `BLOCKED_SPEC` when a normative requirement or required GUI baseline
remains unresolved.

## Close the approved plan

After integration, use `close-plan` with evidence produced by distinct
independent-verification and adversarial-review actors. The closure must prove
every frozen requirement, implementation repository, acceptance criterion and
required evidence type. Missing, stale, extra, inconclusive or unresolved
coverage blocks the run. A PASS closure cannot contain deviations.

Do not prepare PRs until the state is `PLAN_CLOSED`. If any checked-out HEAD
changes after closure, rerun affected repository gates, integration and plan
closure.

## Prepare PRs

Use `prepare-pr-set` only after plan closure passes. Delegate external PR creation to the PR coordinator. Record each PR only if its head equals the tested commit vector.

Stop at `AWAITING_PR_APPROVAL`. The agent cannot approve, merge, or fabricate approval evidence. Advance only with externally obtained evidence for required checks and independent approvals on every exact PR head.

Before handoff, run `verify` and report the exact state, plan digest, commit vector, repository results, PRs, evidence locations, failures and remaining human action.
