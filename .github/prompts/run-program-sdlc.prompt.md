---
name: run-program-sdlc
description: Run a complex change across the governed multi-repository program
agent: gts-orchestrator
---

Treat the supplied text as a program-level software change. Assign or require
a stable change ID, identify only directly implicated seed repositories, and
use the `orchestrate-program-change` skill.

Immediately create a visible todo list for intake, sources, requirements,
planning, architecture review, Human Gate 1, repository waves, integration,
Plan Closure and Human Gate 2. After Human Gate 1, replace each active
repository item with the supervisor's exact `visible_work_plan` subtasks and
keep their status current in Chat. Also print the checklist in Chat and refresh
both views after every state transition.

Run the deterministic intake assessment before requirements or planning. If
authoritative Jira/DFS/FSD content cannot be read, a GUI request lacks affected
screens or an approved baseline, or acceptance behavior is incomplete, record
`NEEDS_CLARIFICATION`, ask the user the concrete missing questions, and wait.
Never infer the answers from code.

Read authoritative DFS/FSD and architecture sources. Produce a cited global
plan, stable acceptance-criterion IDs, a complete per-change verification
matrix, dependency impact, repository slices, UI contract where applicable,
integration strategy, migration, rollout and rollback. The matrix must map
every obligation to reusable repository or integration gate IDs. Stop at Human
Gate 1 only after the required independent plan review/revision cycles pass.
Any `CHANGES_REQUIRED` review invalidates earlier passes and requires a new
digest-bound plan.

At Human Gate 1, always present a concise Plan Review Pack before requesting
approval. Include:

- summary of the requested change and risk tier;
- authoritative sources found and what information was extracted;
- implementation, validation and checkout scopes with rationale;
- acceptance criteria and required evidence mapped to repositories;
- assumptions, open questions and known unknowns;
- exact artifacts produced and digests;
- explicit next actions: approve, request re-plan, or adjust requirements.

If the user or a plan reviewer requests re-plan, update requirements and regenerate plan artifacts
instead of stopping at an approval-template-only message.

Never convert chat text such as "approved" into approval evidence. Require the
external independent non-placeholder approval record for the exact plan digest.

After externally verified plan approval, reuse safe existing clones or create
approved isolated worktrees. Resolve every affected repository's optional
extension manifest and apply only its selected instructions, skills and agent
roles. Implement in dependency waves, bind repository evidence to the resolved
extension digest, run repository and cross-repository gates, and perform
bounded remediation. Execute cross-repository commands with
`run_integration_gates.py --record`; do not manufacture or edit a PASS payload.

Drive this phase with `agent_supervisor.py run --change-id <id>`. The
supervisor must use the adopted command in `agent-runtime.json`, a fresh
repository-scoped prompt per attempt, its durable hash-chained journal and the
existing deterministic gate runners. Resume the same change ID after an IDE,
runner or human-gate pause; do not restart completed work.

For `worker.mode=copilot-sdk`, let the supervisor own the complete model-driven
implementation loop. The SDK parent creates and revises its task graph,
dynamically invokes selected GTS/local custom agents, and returns lifecycle
evidence. Show the durable task board and terminal decision in Chat; never
replace missing subagent events with a receipt or narrative claim.

If `worker.mode` is legacy `vscode-chat`, remain in the loop. Read each active leased
task, use the selected GTS/local guidance at its resolved paths,
implement only in its worktree, and run the task's exact `complete-task`
command. This compatibility mode does not prove independent agent execution.
Continue until a human gate or a fail-closed stop. Chat prose is never completion evidence.

Close every approved plan obligation after integration. Prepare linked draft
PRs only after the Plan Closure Gate passes, then stop at Human Gate
2. Never self-approve, bypass required checks, or manufacture evidence.
