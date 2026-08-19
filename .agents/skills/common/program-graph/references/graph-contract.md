# Program graph contract

## Inventory before source

Read `.github/sdlc/program.json`, then every registered `.github/sdlc/repositories.d/*.json` descriptor. A target repository may also provide `.github/sdlc/repository.json`; its local agents, skills, commands, and stronger gates extend the central policy but cannot weaken it.

Classify every catalogued repository as exactly one of:

- `IMPLEMENTATION`: production or test files must change.
- `VALIDATION_ONLY`: no planned change, but its build, contract, consumer, or system test must run.
- `CONTEXT_ONLY`: consulted for ownership, interface, or specification evidence only.
- `NOT_IMPACTED`: excluded with a short evidence-based reason.

Only the first three dispositions enter the active subgraph. Read source only for active repositories, and read only the paths needed by the current node.

## Node types

Use these deterministic node types:

`REQUIREMENTS`, `IMPACT`, `PLAN`, `PLAN_REVIEW`, `HUMAN_GATE_1`, `CHECKOUT`, `IMPLEMENT`, `VERIFY`, `INTEGRATE`, `CLOSURE`, `PR_DRAFT`, `HUMAN_GATE_2`.

Every node declares:

- stable `id`, `type`, and optional `repositoryId`;
- `dependsOn` node IDs;
- one bounded, observable task;
- `attemptBudget` from 1 to the configured maximum;
- required `evidenceTypes`;
- requirement and plan-task IDs it covers.

The graph must be acyclic. Dependencies, repository descriptors, and the final plan determine ready nodes; conversation order does not.

## Scheduling

- Run independent `REQUIREMENTS`, `IMPACT`, and `PLAN_REVIEW` nodes in parallel where the host supports it.
- After Gate 1, prepare one isolated worktree per `IMPLEMENTATION` repository. Never overwrite or branch-switch a dirty user worktree.
- Run independent repository tasks in the same wave. A producer's passing interface/build evidence unlocks its consumers.
- Treat shared databases, generated baselines, deployment targets, and non-isolated GUI environments as exclusive resources and serialize nodes that use them.
- A 60-repository catalog does not imply 60 active workers. Concurrency is the number of ready active nodes, limited by the host and shared-resource locks.

## Scope change

Any new repository, changed obligation, changed public contract, or revised acceptance criterion after Gate 1 creates a new graph revision. Re-run impact analysis and all affected planning/review nodes. The policy kernel clears previous approvals and downstream results; obtain Gate 1 again.

## Repository acquisition

Prefer an existing clean checkout in the open multi-root workspace. Otherwise use the descriptor's approved remote and default branch to clone/fetch, then create an isolated worktree for the change. If the descriptor, credentials, base revision, or repository policy is unavailable, stop with `BLOCKED_SPEC` or `INCONCLUSIVE`; do not guess a remote or branch.
