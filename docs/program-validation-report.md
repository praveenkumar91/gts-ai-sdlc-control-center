# Program orchestration validation report

**Run date:** 2026-08-19

**Branch:** `change/agent-first-sdlc-orchestration`

**Fresh ZIP base:** `55b9a92`

**Command:** `python -m unittest discover -s .github/scripts/tests -p test_*.py -v`

These are executable control-plane tests using real temporary Git repositories/filesystem artifacts and the
standard-library policy kernel. They validate scheduling, state transitions, evidence integrity and gates.
They do **not** certify any Deutsche Börse/Eurex production application, business algorithm, target repository,
CI system, MCP connection or deployment environment. Those require a real approved change and its own evidence.

| ID | Scenario | Scale / negative control | Expected control behaviour | Result |
|---:|---|---|---|---|
| 01 | Repository catalog validation | 100 registered repositories | Load every unique descriptor within the configured catalog limit | PASS |
| 02 | Dependency graph for a small cross-repo change | 3 implementation repositories; one producer, two consumers | Accept the DAG and preserve producer-before-consumer dependencies | PASS |
| 03 | Parallel wave selection and recording | 8 independent implementation repositories; concurrency limit 4; four concurrent result writes | Schedule at most four without resource collision and preserve every state transition under the run lock | PASS |
| 04 | Maximum configured estate | 100 active implementation repositories | Validate the graph without loading all source into one model context | PASS |
| 05 | Active-scope limit | 61 active repositories against a configured limit of 60 | Reject before execution with the exact configured-limit error | PASS |
| 06 | Cyclic dependency | Requirements node depends on final gate | Reject the graph as cyclic | PASS |
| 07 | Missing lifecycle stage | `INTEGRATE` removed | Reject a graph that does not represent all thirteen stages | PASS |
| 08 | Bounded failure loop | Node budget 2; two recorded failures | First failure returns to pending; second becomes terminal `FAIL` | PASS |
| 09 | Agent self-approval | Gate approver is `agent` | Reject automation identity at Human Gate 1 | PASS |
| 10 | Stale approval | Approval digest differs from current graph digest | Reject the approval | PASS |
| 11 | Scope expansion after Gate 1 | Revision adds a repository | Clear every node result and approval; require planning/review/Gate 1 again | PASS |
| 12 | Evidence tampering | Recorded evidence file changed afterward | Fail integrity verification on SHA-256 mismatch | PASS |
| 13 | Complete lifecycle | 3 repositories, all thirteen stages, Gate 1 and Gate 2 | Finish only when every required node and both human gates pass | PASS |
| 14 | VS Code pre-tool policy | Force-push and direct protected-branch push | Deny force-push; require human approval for protected push | PASS |
| 15 | Multi-root workspace generation | 3 active repositories in a 100-repository catalog | Include control centre plus only the three active worktrees; show subagents inline | PASS |

Additional validation:

| Check | Observed result |
|---|---|
| Policy/configuration validation | PASS |
| Custom-agent discovery validation | 32 unique agents; all explicit agent references resolve |
| Agent Skill discovery validation | 36 unique skills; folder/name contracts pass |
| New `program-graph` skill portability validation | PASS with the skill-creator validator |
| Hook configuration validation | 1 hook file; all 8 current VS Code lifecycle events valid |
| JSON schema/config parsing | 4 schemas plus program/catalog/workspace/settings files valid |
| High-risk review segregation | Graph registration rejects fewer than two independent plan-review evidence types |
| Parallel state integrity | Four separate policy-kernel processes recorded one wave without a lost update |
| Retry evidence history | Tampering with evidence from an earlier failed attempt is detected |

## Required real-environment acceptance before production use

Run a controlled pilot against representative, non-production repositories before adopting this as a release
control. The pilot must independently verify:

1. corporate GitHub/SSH authentication and repository descriptor accuracy;
2. Jira, Confluence, P7/T7 specification and codebase MCP permissions;
3. VS Code discovery of the custom agents, Agent Skills and Preview hooks under enterprise policy;
4. one real single-repository change, one three-repository change and one eight-repository change;
5. representative C++, Python, Node/Vite and TypeScript build/test commands;
6. GUI browser/accessibility/visual evidence against an approved design or current-screen baseline;
7. draft PR creation, CODEOWNERS/CI/branch protection and the Human Gate 2 approval path;
8. recovery from unavailable dependencies, flaky tests, stale specs, dirty worktrees and scope expansion.

Until those environment-specific checks pass, the deterministic control plane is validated but the complete
corporate production path remains `INCONCLUSIVE` rather than implicitly certified.
