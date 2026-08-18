---
name: coordinate-pr-set
description: Prepare, create, record, monitor, and verify a linked set of GitHub draft pull requests for one multi-repository change. Use after the Plan Closure Gate passes and before human PR approval, ordered merge, or release coordination.
---

# Coordinate a PR set

Read the program run, `plan.json`, `commit-vector.json` and `pr-set.json`. Refuse PR work unless the program state is `PR_SET_READY` or `AWAITING_PR_APPROVAL`.

## Create drafts

For every implementation-scope repository:

1. verify the worktree is clean;
2. verify its HEAD equals the tested `head_sha`;
3. push only the named change branch;
4. create a draft PR against the configured default branch;
5. include the change ID, plan digest, commit-vector digest, related PRs, evidence, rollout and rollback;
6. record the PR number, URL and exact head SHA through `program_orchestrator.py record-pr`.

Never force push, approve, mark ready, merge, change protection, dismiss a review or bypass a required check without explicit authority.

Read [pr-set-evidence.md](references/pr-set-evidence.md) before preparing Human Gate 2.

## Wait for Human Gate 2

Require every PR to have required status checks and independent CODEOWNER approvals for the exact recorded head. A new commit invalidates the affected approval and integration evidence.

The program-level approver must be independent from the requester. Obtain approval evidence from GitHub or another protected, auditable authority; never infer approval from a comment, draft status or the agent’s own review.

Report the complete PR matrix, blockers and required merge order. Merge only through configured branch protection or merge queue after program state is `PR_APPROVED`.
