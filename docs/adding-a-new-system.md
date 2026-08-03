# Adding a new system to GTS AI SDLC

This guide explains how to onboard a new GTS system (e.g. `cue`, `xyz`) into the framework by
creating its orchestrator, pipeline agents and skills, then registering it with the generic
orchestrator. It is the companion to the [main README](../README.md) — read the
**Architecture at a glance** section there first.

> **Reuse, don't reinvent.** Everything below is a *copy-and-fill* operation from the templates in
> [`_template/`](../_template/) and [`.agents/skills/_template/`](../.agents/skills/_template/). A new
> system should look like P7 and T7 — same tiers, same status contract, same skill-first tool access.

---

## Step 1 — Create the system orchestrator (Tier 2)

Copy [`_template/SYSTEM-orchestrator.agent.md`](../_template/SYSTEM-orchestrator.agent.md) to
`.github/agents/{system}-orchestrator.agent.md` and replace every `{SYSTEM}` / `{system}` placeholder.

- Keep the **coordinator-only** rule intact — the orchestrator never reads, searches or edits code; it
  only delegates to Tier 3 agents.
- Keep **Step 0: Clarify** so the orchestrator routes the raw request through `/gts-prompt-clarifier`
  before the pipeline starts.
- Decide the pipeline shape: a **linear TDD pipeline** (like P7: Plan → Architect → gate → RED →
  Develop → Verify → Review → Build → PR) or an **autonomous Ralph loop** (like T7, via the
  `ralph-loop` common skill). Bind each generic phase to a concrete `{system}` agent.

## Step 2 — Create the pipeline agents (Tier 3)

Copy [`_template/SYSTEM-sdlc-developer.agent.md`](../_template/SYSTEM-sdlc-developer.agent.md) to
`.github/agents/{system}-sdlc-developer.agent.md` and fill in the layer paths, build commands and
coding standards. Add the remaining roles as the system matures — `{system}-sdlc-planner`,
`-architect`, `-tester`, `-reviewer`, `-builder`, `-pr-author` (and `-knowledge` if the system needs a
read-only query endpoint like T7).

- Each agent does **exactly one job** and ends every response with a **status code** the orchestrator
  routes on (`DONE`, `RED_READY`, `GREEN_PASS`, `NOT_APPLICABLE`, `CHANGES_REQUIRED`, `BUILD_FAIL`, …).
- Only the **developer** may write code. Testers write only test files; reviewers/builders are
  read-only or run-only.

## Step 3 — Create system skills

```bash
mkdir -p .agents/skills/systems/{system}/{system}-code
cp .agents/skills/_template/SKILL.md .agents/skills/systems/{system}/{system}-code/SKILL.md
```

Fill in the layer table, naming conventions, build commands and testing patterns. Add more skills
(`{system}-code-review`, `{system}-debugging`, a knowledge base, …) as needed.

- Set `systems: [{system}]` in each system-skill's frontmatter.
- To adapt a common skill rather than duplicate it, use `extends: common/{skill-name}` and add rules on
  top (as `p7-github` does over `common/github`).
- **Skill-first tool access:** raw MCP namespaces belong in a skill's transport, never called by name
  from an agent body.

## Step 4 — (Optional) Add the spec-author agent

If the system produces formal **DFS / DTS / SRQ** documents, copy
[`_template/SYSTEM-sdlc-spec-author.agent.md`](../_template/SYSTEM-sdlc-spec-author.agent.md) to
`.github/agents/{system}-sdlc-spec-author.agent.md`:

- Replace the `{SYSTEM}` / `{system}` placeholders and wire `skills:` to the system's
  content-grounding skill(s).
- Set the output folder to `specs/{system}/`.
- Register it in the system orchestrator's `agents:` list and add an on-demand **Spec Authoring** phase
  (mirror the T7/P7 orchestrators).

The DFS/DTS/SRQ structure, metadata contract and filename rules are reused from the common
`spec-authoring` skill — no per-system spec skill is required.

## Step 5 — Register with the generic orchestrator (Tier 1)

In [`.github/agents/gts-orchestrator.agent.md`](../.github/agents/gts-orchestrator.agent.md):

1. Add `{system}-orchestrator` to the `agents:` frontmatter list.
2. Add a routing rule in the **Routing Rules** section so the generic orchestrator can hand off to the
   new system.

The generic orchestrator only routes to systems listed in its `agents:` frontmatter — it never guesses
or hallucinates a system orchestrator.

---

## Naming conventions

| Item | Convention | Example |
|------|-----------|---------|
| System folder names | lowercase, no separators | `p7`, `t7`, `cue` |
| Orchestrator `name` field | `{system}-orchestrator` | `t7-orchestrator` |
| Pipeline agent file names | `{system}-sdlc-{role}.agent.md` | `t7-sdlc-developer.agent.md` |
| Pipeline agent `name` field | `{system}-sdlc-{role}` | `t7-sdlc-developer` |
| Skill folder names | `{system}-{topic}` (system) or plain noun (common) | `t7-code`, `github` |
| Skill `name` field | matches folder name | `t7-code`, `github` |
| Common skill `systems` field | `[all]` | `systems: [all]` |
| System skill `systems` field | `[{system}]` | `systems: [t7]` |
| System override skill `extends` | `common/{skill-name}` | `extends: common/github` |

---

## Design decisions (FAQ)

| Question | Answer |
|----------|--------|
| **Should system skills override common skills?** | Yes — use the `extends` frontmatter field. The system skill adds rules on top; the common skill is the base. Already in use with `p7-github` extending `common/github`. |
| **How should the orchestrator handle a system it doesn't recognise?** | Ask the user which system they are working on, then follow the steps above. The generic orchestrator only routes to systems in its `agents:` frontmatter — never guess or hallucinate a system orchestrator. |
| **When should a new pipeline role be added vs reusing the developer?** | Add a dedicated agent when the role has distinct constraints (a tester must not edit production code, a builder must only run build commands). Roles that differ only by scope can share the developer agent with task-specific instructions in the plan. |
| **How are skills versioned when a common skill changes?** | System skills that `extend` a common skill inherit changes automatically. System skills that duplicate common content must be updated manually — prefer `extends` and additive overrides over duplication. |
| **Linear pipeline or Ralph loop?** | Use a linear TDD pipeline (P7) when work is a bounded feature/fix with a clear plan. Use the autonomous Ralph loop (T7, via the `ralph-loop` skill) when converging a codebase onto a body of behavioural specs through many small, gated iterations. |
