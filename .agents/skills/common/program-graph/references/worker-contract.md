# Repository worker contract

Every implementation dispatch is stateless and complete. Include all of the following in the subagent prompt:

```text
Program-Worker-Mode: true
Change-Id: <stable id>
Graph-Digest: <Gate 1 digest>
Graph-Node: <node id>
Repository-Id: <catalog id>
Repository-Path: <isolated worktree>
Base-Revision: <immutable revision>
Task-Id: <one approved plan task>
Requirement-Ids: <cited obligations>
Acceptance-Criteria: <observable checks>
Architecture-Constraints: <approved decisions>
Required-Evidence: <tests/review/build/security/gui/etc.>
Attempt: <n>/<budget>
Forbidden-Scope: <explicit exclusions>
```

The worker must:

1. verify it is in the named repository and isolated worktree;
2. search before editing and return `ALREADY_SATISFIED` only with code and test evidence;
3. execute exactly one approved task;
4. use RED -> GREEN where behaviour is testable, otherwise name the approved fit check;
5. run the repository's local instructions, skills, tests, review, and build commands in addition to central gates;
6. stop on scope expansion and return `SCOPE_CHANGE` rather than editing another repository or obligation;
7. return a concise result envelope and write detailed evidence to files.

Required result envelope:

```text
Worker-Status: PASS | FAIL | INCONCLUSIVE | BLOCKED_SPEC | SCOPE_CHANGE
Change-Id: <id>
Graph-Digest: <digest>
Graph-Node: <id>
Repository-Id: <id>
Commit: <sha or none>
Changed-Paths: <paths or none>
Evidence: <artifact paths and commands>
Requirement-Coverage: <requirement id -> evidence>
Residual-Risks: <risks or none>
```

P7/T7 workers must use their original planner, tester, developer, reviewer, builder, knowledge, and PR-author agents. Program Worker Mode removes duplicate program gates; it does not bypass the system's technical backpressure.
