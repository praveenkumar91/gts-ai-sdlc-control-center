# GTS AI SDLC workspace instructions

Use `program-orchestrator` as the parent for any code-changing request whose repository scope is unknown or may span multiple repositories. Use `gts-orchestrator`, `p7-orchestrator`, or `t7-orchestrator` directly for clearly single-system work and read-only routes.

- The multi-repository layer is agent-only. Do not run `.github/scripts/policy_kernel.py`, Python control-plane commands, or custom SDLC hooks.
- Keep the seven-stage plan visible in the parent chat before delegating and update it after every question, review cycle, repository wave, and human gate.
- Recover and cite authoritative DFS/FSD/DTS/SRQ/Jira/design/user requirements. If material information is missing or contradictory, ask the smallest focused question and report `BLOCKED_SPEC`.
- Read repository descriptor metadata once, select the impacted subset, and deep-read or checkout only that subset. A large catalog is not permission to open or change every repository.
- Use GTS as the domain router. GTS must reuse the original P7/T7 planners, architects, developers, testers, reviewers, builders, PR authors, and relevant common, system, and repository-local skills.
- Keep Stage 3 blocked unless every active implementation or validation repository has a registered owner, immutable revision and resolvable checkout or approved remote, and every required GTS system plan returns `READY`. Do not substitute parent-authored assumptions or broad workspace searches for missing repository evidence.
- Review the complete cross-repository plan independently. A corrected plan receives a new revision and a complete re-review; do not repeat approved reviews without an actual change.
- Obtain Human Gate 1 only on an existing, readable plan artifact backed by ready system plans and registered repository identities. Obtain Human Gate 2 after independent closure and draft PR preparation, before approval, merge, release, deployment, or delivery.
- Never display a plan, evidence or PR path that was not actually created. Label an unpersisted dry-run result as a chat revision, not as a file.
- Execute one bounded task per affected repository in dependency-ready waves. Preserve dirty user worktrees and use isolated checkouts or worktrees for implementation.
- Show commands and evidence actually produced. An unrun, missing, stale, flaky, or inaccessible mandatory check is `INCONCLUSIVE`, never an implied pass.
- Report `PASS`, `FAIL`, `INCONCLUSIVE`, or `BLOCKED_SPEC` truthfully. No finite workflow guarantees defect-free software.
- Never self-approve or bypass CODEOWNERS, CI, branch protection, security controls, or repository governance.

Read-only knowledge, issue analysis, feedback, and delivery-proposal requests keep their existing fast routes and do not start multi-repository orchestration.
