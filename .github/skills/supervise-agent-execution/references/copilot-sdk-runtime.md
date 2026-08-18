# Copilot SDK autonomous runtime

Use `worker.mode=copilot-sdk` to run the implementation phase without keeping
an IDE chat open.

## Provision once

```text
python -m pip install -r .github/sdlc/requirements-copilot-runtime.txt
python .github/scripts/agent_supervisor.py validate --adoption
```

Authenticate the SDK using the signed-in Copilot user or an approved
`COPILOT_GITHUB_TOKEN`. Never put credentials in repository configuration or
run artifacts.

## Execution model

The supervisor creates an isolated repository lease and passes its immutable
prompt plus the digest-bound repository-extension packet to
`copilot_runtime.py`. The adapter:

1. resolves every selected GTS/local agent and skill and validates it against
   its recorded SHA-256;
2. registers the profiles with their exact frontmatter names and binds their
   selected skill directories;
3. starts a durable SDK session scoped to change, repository and attempt;
4. asks the parent model to maintain an adaptive task graph and delegate ready
   work to registered specialists;
5. captures the SDK event stream, a continuously rendered task board and
   subagent outputs;
6. returns `PASS` only after real final-state implementation, build, test and
   independent-review subagent executions return valid `PASS` contracts with
   concrete evidence.

The minimum roles are assurance coverage, not a fixed pipeline. The parent may
create more tasks, use other specialists, revisit implementation, or repeat
validation. If implementation runs again, later build, test and review evidence
is required.

`copilot-runtime-events.jsonl` is the raw lifecycle trace.
`RUNTIME_TASK_BOARD.md` shows the current parent intent and the state of every
observed specialist call while the lease runs.
`copilot-runtime-result.json` binds the trace, agent names, outputs, starting
commit, task board, skill bindings, prompt and extension packet. The supervisor
then independently inspects the diff, commits it and runs deterministic
repository and integration gates.

SDK success never approves a PR or release. Missing SDK, authentication,
specialists, events, structured result contracts, outputs, tooling or
authoritative context is
`INCONCLUSIVE` and stops the run.
