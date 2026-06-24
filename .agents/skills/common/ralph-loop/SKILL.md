---
name: ralph-loop
description: "Autonomous 'Ralph' build-loop methodology for SDLC orchestration. Use when: running a system's development loop (specs → plan → build), coordinating one-task-per-iteration autonomous implementation gated by test/build backpressure, managing the durable specs / disposable plan / operational-memory artifacts, or keeping a long-running loop within context limits. This is the canonical, system-agnostic loop protocol that each system orchestrator binds to its own pipeline agents."
systems: [all]
tools: [read, edit, search]
---

# Ralph Build Loop — Canonical Protocol

Reusable definition of the **autonomous "Ralph" build loop** used by GTS system orchestrators (T7, P7, and future systems). The loop converges on a set of behavioural specs through many small, isolated iterations — **one task per iteration, fresh context each time** — each gated by backpressure (tests + build).

> **This skill is the single source of truth for the methodology.** A system orchestrator **binds** this protocol by mapping each generic loop role below to one of its concrete `{system}-sdlc-*` subagents. When the methodology changes, change it **here** and keep each orchestrator's binding in sync. Authoring a behavioural spec or a plan is delegated to the system's planner; this skill defines *how the loop is structured*, not the system's domain content.

---

## The Three Artifacts (the heart of the loop)

These live in the **target codebase working tree** (the repo being built), not in the framework repo.

| Artifact | Role | Lifetime | Owner |
|---|---|---|---|
| `loop-specs/` | **Source of truth** — behavioural requirement specs, one file per topic of concern (WHAT, not HOW), flat `NN-kebab-case.md` | Durable | Authored in SPECS mode |
| `IMPLEMENTATION_PLAN.md` | **Disposable shared state** — prioritized bullet list of open tasks from gap analysis (specs vs code) | Disposable / regenerable | Written in PLAN mode, updated each BUILD iteration |
| `AGENTS.md` | **Operational memory** — build/test/lint commands (backpressure) + operational learnings only (no status, no progress) | Durable, kept brief | Updated when a build/run learning is discovered |

> `loop-specs/` is deliberately named differently from any formal `specs/<system>/` governance directory (DFS/DTS/SRQ), so the two artifact types stay structurally distinct — different directories, not just a naming convention — even if a single checkout ever holds both.

---

## Loop Principles

- **One task per iteration, fresh context** — each BUILD iteration dispatches a fresh chain of subagents for a *single* task, then resets. Never batch many tasks into one context.
- **Don't assume not implemented** — always search the codebase before building. The biggest failure mode is rebuilding what already exists.
- **Don't assume unspecified** — the authoritative requirements often already exist (e.g. a formal spec corpus). Consult it before authoring new behavioural specs or treating a requirement as undefined.
- **Backpressure gates every task** — tests (Tester) and compile (Builder) must pass before a task is committed. A task is not "done" until backpressure is green.
- **The plan is disposable** — if `IMPLEMENTATION_PLAN.md` is stale, wrong, or cluttered, regenerate it (re-run PLAN mode) rather than fighting it.
- **Let the loop converge** — after the single human gate, run autonomously. Trust eventual consistency through iteration; only stop for a hard blocker.
- **State lives in files, not memory** — the three artifacts ARE the loop's state. Re-derive what is left to do by re-reading them each iteration, never from accumulated conversation history.
- **Markdown over JSON; brevity wins** — keep the plan and `AGENTS.md` terse.

---

## Three Modes

A loop run is in exactly one mode. Default task work runs **PLAN → gate → BUILD**.

### Mode: SPECS — maintain the source of truth
Run only when specs are missing/stale or the user asks to define requirements.
- Distil behavioural specs from the authoritative formal corpus — **do not invent requirements**; cite the source document IDs.
- One file per **topic of concern** under `loop-specs/` (must pass the "one sentence without 'and'" test — if you need "and", split it).
- Capture **acceptance criteria as observable outcomes** (WHAT to verify), never implementation detail (no algorithms, class names, or file paths).
- Output: created/updated `loop-specs/*.md`. No implementation.

### Mode: PLAN — gap analysis → IMPLEMENTATION_PLAN.md
- Study `loop-specs/` + the authoritative formal corpus + the current codebase. Do a gap analysis (required behaviour vs code).
- **Don't assume anything is unimplemented; confirm with a code search first.** Treat the formal corpus as the authoritative statement of required behaviour where `loop-specs/` are silent.
- Produce/refresh `IMPLEMENTATION_PLAN.md` as a prioritized bullet list of the tasks still required — each with acceptance criteria, source spec IDs, verified file paths, and required tests. Plan only — implement nothing.
- An **architecture review** of the plan (component boundaries, ownership, build dependencies) should pass before the gate: APPROVED → gate; NEEDS REVISION → back to the planner (bounded); BLOCKED → escalate.
- The plan is **disposable**: regenerate it any time it goes stale rather than editing around it.

### Plan Gate — the single human confirmation (HARD-GATE)
Do **not** start the BUILD loop until the user has explicitly confirmed the plan. Present a short plan summary and wait for **yes / no / revise**. Do not auto-proceed even if the plan looks complete — this is the one human gate; the loop runs autonomously after it.

### Mode: BUILD — the autonomous loop
After the gate, iterate until `IMPLEMENTATION_PLAN.md` has no open tasks (or a max-iteration / blocker stop). **Each iteration handles exactly one task with a fresh subagent chain**, then resets context for the next.

Per-iteration sequence (generic roles in **bold** — each orchestrator binds these to its own subagents):

1. **Orient** — read `loop-specs/` + `IMPLEMENTATION_PLAN.md` (delegate any codebase/spec/ownership facts to the **Knowledge** role).
2. **Select** — pick the single most important open task from `IMPLEMENTATION_PLAN.md`.
3. **Investigate** — *don't assume not implemented*: confirm via the **Knowledge** role what already exists before changing anything.
4. **RED** — the **Tester** writes failing tests for the task's acceptance criteria and confirms they fail (no production code). Capture the failing test paths.
5. **GREEN** — the **Developer** implements the minimal code to make the failing tests pass, following the plan + architecture notes.
6. **Verify (backpressure)** — the **Tester** runs the tests; formerly-failing tests must pass with no regressions. Failure → back to Developer (bounded retries).
7. **Review (backpressure)** — the **Reviewer** checks correctness, security, performance, patterns. Changes required → back to Developer → re-verify → re-review (bounded).
8. **Build (backpressure)** — the **Builder** builds the affected components in dependency order. Build failure → back to Developer → re-verify → re-review → rebuild (bounded). Timeout → surface to the user.
9. **Record** — the Developer updates `IMPLEMENTATION_PLAN.md` (mark the task done; note discoveries / new tasks / bugs found) and, only if an operational build/run learning emerged, appends a brief note to `AGENTS.md`.
10. **Commit** — one task = one commit.
11. **Loop** — drop the task's context and start the next iteration fresh from step 1.

### Stop conditions
- `IMPLEMENTATION_PLAN.md` has no open tasks → exit loop, proceed to PR.
- A task returns **BLOCKED** that re-dispatch can't resolve → escalate to the user (don't spin).
- Backpressure fails repeatedly past the retry budget on the same task → escalate; consider regenerating the plan.

> **Autonomy boundary**: inside the loop, do NOT re-gate every task — that defeats the loop. Only pause for a genuine blocker or repeated backpressure failure.

---

## Context Hygiene & Scaling (keeping a long loop within limits)

A long loop's risk is **not** the fixed system prompt — it is the **growing conversation history**. If the coordinator carries every iteration's full subagent output, the fixed protocol at the top competes with an ever-growing transcript at the bottom, and the loop starts skipping gates or losing retry limits. Keep the loop bounded:

- **Externalise state to the three files.** `loop-specs/`, `IMPLEMENTATION_PLAN.md` and `AGENTS.md` are the durable memory. The coordinator re-derives "what's left" by re-reading them each iteration (via a read-capable agent), not from memory.
- **Keep the coordinator's own context terse.** After each iteration, retain only a one-line tally — `task · RED✓ GREEN✓ Verify✓ Review✓ Build✓ · commit <hash>`. Discard verbose subagent transcripts; the files hold anything durable.
- **Fresh context per task.** Each iteration dispatches a fresh subagent chain for a single task; subagents return a concise status + the changed artifacts, not full transcripts.
- **Ideal harness shape (if supported).** Spawn a **fresh coordinator invocation per iteration**, reading loop state from the three files at start and writing results back at end. This makes coordinator context **O(1)** regardless of iteration count and is the most robust realisation of "fresh context each time". Where the harness cannot reset the coordinator mid-run, the terse-tally + externalised-state discipline above is the fallback that keeps history bounded.

---

## Binding This Protocol in a System Orchestrator

Each system orchestrator implements this loop by:

1. **Mapping roles → subagents** — bind **Tester / Developer / Reviewer / Builder / Knowledge / Planner / Architect** to that system's `{system}-sdlc-*` agents.
2. **Keeping the binding in sync with this skill** — the orchestrator's loop section is the system-specific *binding*; this skill is the canonical *methodology*. Change methodology here first.
3. **Honouring the artifacts and modes** exactly as defined above (`loop-specs/`, `IMPLEMENTATION_PLAN.md`, `AGENTS.md`; SPECS / PLAN / BUILD; the single HARD-GATE).
4. **Applying the context-hygiene rules** so the loop scales to many iterations.

> Coordinator-only orchestrators (no file-read capability) cannot load this skill at runtime; they carry an operational copy of the per-iteration sequence inline and treat this skill as the canonical reference to stay aligned with. Read-capable pipeline agents may consult this skill directly.
