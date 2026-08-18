---
name: operate-sdlc-run
description: Operate the repository's durable, evidence-gated SDLC state machine for complex or regulated changes. Use when starting, resuming, advancing, remediating, verifying, blocking, rolling back, or reporting a financial-system delivery run through `.github/scripts/sdlc_engine.py`.
---

# Operate an SDLC run

Use the engine as the sole writer of run state. Never edit `run.json`,
`events.jsonl`, or artifact envelopes manually.

## Start and ingest

Read the repository contract and policies, assign a stable change ID, and
classify risk conservatively. Start the run and snapshot configured sources:

```text
python .github/scripts/sdlc_engine.py start --change-id <id> --request "<request>" --risk-tier <tier>
python .github/scripts/sdlc_engine.py snapshot-sources --change-id <id>
```

Stop on `INCONCLUSIVE`. Do not infer missing normative rules.
The snapshot proves source identity only. It does not prove comprehension.
Require the specification agent to produce the separate `context-pack.json`
and `ingestion-diagnostics.json` before advancing.

## Produce and record evidence

Have the state owner create each required payload as JSON. Record it through:

```text
python .github/scripts/sdlc_engine.py record-artifact --change-id <id> --name <artifact.json> --producer <agent> --decision <PASS|FAIL|INCONCLUSIVE|BLOCKED_SPEC> --input <payload.json>
```

The engine binds the envelope to the current commit and preserves prior
revisions. PASS operational evidence must also satisfy
`.github/sdlc/policies/artifact-contracts.json`; a PASS label with empty or
contradictory content is rejected. Advance only through:

```text
python .github/scripts/sdlc_engine.py advance --change-id <id> --actor <transition-owner>
```

After implementation, commit the code and bind the exact repository `HEAD`
before recording implementation or later evidence:

```text
python .github/scripts/sdlc_engine.py bind-commit --change-id <id> --actor implementation
```

## Handle failures

Report a correctable gate failure through `failure`. The engine increments the
bounded remediation counter, resets post-design evidence, and requires affected
checks to run again.

```text
python .github/scripts/sdlc_engine.py failure --change-id <id> --actor <transition-owner> --reason "<evidence-backed reason>"
```

Use `terminate` for unresolved specification ambiguity, failed mandatory
controls, or irreproducible evidence. Never convert one outcome into another to
obtain a pass.

Production transitions require external human approval evidence enforced by a
protected GitHub environment. An agent must not manufacture that evidence.
Use `rollback` only after a PASS `rollback-execution.json` has been recorded.

## Verify and report

Run these commands before every handoff and final report:

```text
python .github/scripts/sdlc_engine.py verify --change-id <id>
python .github/scripts/sdlc_engine.py status --change-id <id>
```

Report the state, commit, evidence paths, remediation count, failed or missing
controls, residual risk, and external approval still required. A
`PRODUCTION_VALIDATED` state means configured evidence passed; it is not a claim
of mathematical certainty.
