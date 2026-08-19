# Evidence and gate contract

## Evidence

Every required node records one or more durable files. Evidence must identify:

- command or review method;
- repository and immutable revision;
- timestamp and actor/agent role;
- outcome `PASS`, `FAIL`, `INCONCLUSIVE`, or `BLOCKED_SPEC`;
- requirement IDs and plan-task IDs covered;
- raw output location or a lossless reference to it.

The policy kernel hashes evidence files when recording them and verifies the hashes before completion. A summary in chat, a claimed subagent status, or a PR check badge without retrievable output is not sufficient evidence.

## Human Gate 1

Gate 1 approves the reviewed requirement baseline, repository dispositions, architecture decisions, plan tasks, dependency graph, GUI acceptance approach, and exclusions. The approval must name a human approver and exactly match the current graph digest. Agents cannot approve it.

## Human Gate 2

Gate 2 occurs after implementation, integration, independent closure, and draft PR creation. Present:

- requirement-to-change-to-test traceability;
- repository commits and linked draft PRs;
- test/build/security/GUI evidence;
- failed, skipped, flaky, manual, or environment-blocked checks;
- residual risks and rollout/rollback notes;
- the exact graph digest being approved.

The human may approve, reject, or request revision. Approval never overrides repository protections, required reviewers, CI, segregation of duties, or production change controls.

## GUI changes

Convert prose into observable states and interactions during planning. Require the appropriate evidence for the risk:

- component/unit tests for state and business logic;
- browser automation for flows, validation, accessibility, and console/network errors;
- screenshots or visual-regression baselines for approved viewport/theme combinations;
- real service contracts or controlled fixtures for data-dependent finance screens;
- explicit human visual review when no authoritative screen or design baseline exists.

If exact visual fidelity is required but no design, current screen, or approved baseline exists, return `BLOCKED_SPEC`. Do not invent the target appearance.
