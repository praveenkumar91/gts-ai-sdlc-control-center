# GTS AI SDLC workspace instructions

For every request that may edit code, tests, configuration-as-code, schemas, contracts, or GUI assets, route through `gts-orchestrator` and then `program-orchestrator`. Do not begin implementation in the generic Agent role.

- Show the program orchestrator's thirteen-stage todo and status table before delegating.
- Recover and cite authoritative requirements. If material DFS/FSD/DTS/SRQ/Jira/design/acceptance information is missing or contradictory, ask the user and return `BLOCKED_SPEC`.
- Inventory repository descriptors first and select only the impacted subgraph. A large catalog is not permission to read or change every repository.
- Preserve and use the original P7/T7 agents and all relevant central and repository-local Agent Skills. Local controls may strengthen but never weaken central gates.
- Obtain Human Gate 1 after independent plan review and re-review of every revision. Obtain Human Gate 2 after independent requirement closure and linked draft PR preparation.
- Use bounded one-task Ralph iterations in isolated worktrees. Never hide retries, skip evidence, or claim an unrun check passed.
- Report `PASS`, `FAIL`, `INCONCLUSIVE`, or `BLOCKED_SPEC` truthfully. Never promise perfect correctness.
- Never self-approve, bypass branch protections or CODEOWNERS, merge, deploy, deliver, or change a production/shared baseline without the exact human authorization and repository governance required for that action.

Read-only knowledge, issue analysis, feedback, and delivery-proposal requests may use their existing fast-path agents without starting the program graph.
