---
name: program-graph
description: "Coordinate a governed software change across one or many repositories as an impact-selected dependency graph with bounded Ralph loops, evidence gates, and two human approvals. Use for code-changing feature, defect, refactor, migration, GUI, or integration work that may span multiple repositories. Do not use for read-only knowledge or diagnosis requests."
---

# Program Graph

Use this skill as the **outer control loop** around the existing system-specific GTS agents and the canonical `ralph-loop` skill. Agents reason about requirements, architecture, and impact. The policy kernel only validates graph state, evidence digests, retry limits, and approvals.

## Non-negotiable invariants

1. Show the full macro plan in chat before delegating anything, and keep its status current.
2. Build an inventory from repository descriptors before reading repository source. Select the impacted subgraph; never load every repository merely because it belongs to the program.
3. Every requirement obligation must cite an authoritative DFS, FSD, DTS, SRQ, Jira, approved design, or user statement. Missing or contradictory material is `BLOCKED_SPEC`; ask the user for the smallest missing decision.
4. Planning is read-only. Review the plan independently and re-review every revision. Human Gate 1 approves a digest of the final plan and graph before any production-code edit.
5. Execute one approved task per isolated repository worktree. Bind P7 and T7 work to their existing orchestrators in Program Worker Mode; use the generic repository worker only when no registered system agent applies.
6. Run ready graph nodes in dependency waves. Parallelize independent read-only analysis and independent repositories; serialize dependent writes and shared integration resources.
7. Each implementation node uses bounded RED -> GREEN -> verify -> review -> build backpressure. Never spin after the declared attempt budget.
8. Reconcile the completed change against every approved obligation and plan task. Missing evidence is `INCONCLUSIVE`, not `PASS`.
9. Create only draft or proposed PRs before Human Gate 2. Never self-approve, merge, deploy, or mutate a shared baseline without the user's explicit action and repository policy.
10. If repository scope, requirements, architecture, or acceptance criteria materially change after Gate 1, revise the graph, invalidate downstream evidence, re-review, and obtain a new Gate 1 approval.

## Operating shape

Read [graph contract](references/graph-contract.md) when planning or scheduling a run. Read [worker contract](references/worker-contract.md) before dispatching an implementation node. Read [evidence contract](references/evidence-contract.md) before recording a result or requesting a gate.

The outer run has thirteen visible stages:

1. Intake and source access
2. Requirement clarification and freeze
3. Repository impact analysis
4. Architecture and execution plan
5. Independent review, revision, and re-review
6. Human Gate 1
7. Isolated checkout/worktree preparation
8. Dependency-wave implementation
9. Per-repository test, security, GUI, and build validation
10. Cross-repository integration validation
11. Independent requirement and plan closure
12. Linked draft PR set
13. Human Gate 2

Stages may contain many graph nodes, but the chat should remain a compact, visible control surface. Durable state belongs under `.github/sdlc/runs/<change-id>/`, not in accumulated conversation history.

## Truthful completion

No finite workflow guarantees defect-free software. Report exactly one overall result:

- `PASS`: every required graph node and both human gates passed with digest-bound evidence.
- `FAIL`: a required check failed after its bounded retries.
- `INCONCLUSIVE`: required evidence could not be produced or verified.
- `BLOCKED_SPEC`: an authoritative requirement or material user decision is missing or contradictory.

Never convert an `INCONCLUSIVE` or `BLOCKED_SPEC` result into a pass by inference.
