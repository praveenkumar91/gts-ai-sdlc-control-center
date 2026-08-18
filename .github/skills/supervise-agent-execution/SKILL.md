---
name: supervise-agent-execution
description: Drive approved multi-repository implementation through durable model-worker loops, deterministic repository and integration gates, bounded remediation, safe resume, and human-gate pauses.
---

# Supervise repository-agent execution

Use this skill after a program plan exists. The deterministic
`.github/scripts/program_orchestrator.py` remains the sole writer of program
state. `.github/scripts/agent_supervisor.py` owns only its separate,
hash-chained execution journal and invokes configured repository workers.

## Before execution

1. Validate `.github/sdlc/agent-runtime.json`. Use `copilot-sdk` for autonomous
   production-like execution, `vscode-chat` only for interactive legacy task
   leases, or `command` for a separately validated worker executable.
2. In `copilot-sdk` mode, install the exact pinned SDK requirement, verify
   authentication, and run `agent_supervisor.py validate --adoption`. Read
   [copilot-sdk-runtime.md](references/copilot-sdk-runtime.md) before enabling
   execution. A missing or mismatched SDK is `INCONCLUSIVE`.
3. Confirm repository and integration quality contracts are adopted. Model
   output never substitutes for deterministic gate evidence.
4. Do not start workers before the program state is `PLAN_APPROVED`.

## Run and resume

```text
python .github/scripts/agent_supervisor.py validate --adoption
python .github/scripts/agent_supervisor.py run --change-id <id> --allow-clone
```

For legacy VS Code Chat mode, read
[vscode-chat-worker.md](references/vscode-chat-worker.md) and keep processing
the active lease until the supervisor reaches a human gate or real stop.

Use `--watch` only in a durable service or CI runner. Use `--max-steps` for a
bounded invocation. A later call with the same change ID resumes from the
durable program and supervisor state; never delete or edit run JSON manually.

The supervisor:

- prepares isolated worktrees after Human Gate 1;
- launches fresh repository-scoped workers in dependency waves;
- passes only the approved requirement slice, extension paths and previous
  deterministic failure evidence;
- gives the Copilot SDK a repository-scoped specialist catalog and requires
  observed subagent start, completion and non-empty result events for the
  selected implementation, build, test and review capabilities;
- lets the parent runtime create, split, retry and reorder tasks dynamically
  while rejecting final-state validation that predates implementation;
- blocks worker pushes and protected-policy changes;
- commits successful worker changes with a controlled identity;
- runs and records repository gates;
- re-invokes workers after real failures within both worker and program budgets;
- runs integration gates for the exact commit vector;
- sends integration failures back to implementation repositories and reruns
  their repository gates;
- stops on ambiguity, unavailable evidence, exhausted attempts, Plan Closure,
  PR creation authority, or either human gate.

## Failure handling

- `FAIL` from a configured gate triggers bounded remediation.
- `INCONCLUSIVE` pauses; fix the missing tool, context or environment before
  using `--retry-inconclusive`.
- `BLOCKED_SPEC` stops for an accountable specification decision.
- Protected-path mutation pauses without committing or testing the change.
- A stale lock may be recovered only after the configured interval with
  `--recover-stale-lock` and after confirming no supervisor process is active.
- A specialist filename, prompt inclusion or receipt is not agent execution.
  Missing SDK lifecycle evidence always pauses as `INCONCLUSIVE`.

## Handoff

At `PAUSED_PLAN_CLOSURE`, obtain distinct independent-verification and
adversarial-review evidence through auditable external identities. The worker
that implemented the change cannot produce either approval. After
`PLAN_CLOSED`, PR creation remains an explicitly authorized external write and
Human Gate 2 remains independent.
