# gts.ai.sdlc

Developer reference for the GTS AI SDLC framework — agent and skill definitions for automating software development workflows across GTS systems.

---

## Overview

This repository defines a **3-tier composition model** for AI-assisted software development:

```
Tier 1: Generic Orchestrator  (.agents/gts-orchestrator.agent.md)
         ↓ routes by system
Tier 2: System Orchestrator   (.agents/{system}-orchestrator.agent.md)
         ↓ coordinates pipeline
Tier 3: Pipeline Agents       (.agents/{system}-sdlc-{role}.agent.md)
         ↓ use skills
        Common Skills          (.agents/skills/common/)
        System Skills          (.agents/skills/systems/{system}/)
```

- **Tier 1 (Generic Orchestrator)** — Knows all registered systems. Routes the user's request to the correct system subagent. Never implements anything itself.
- **Tier 2 (System Orchestrator)** — Knows the SDLC pipeline for one system (Plan → Gate → Develop → Review → PR). Coordinates Tier 3 agents. Never implements anything itself.
- **Tier 3 (Pipeline Agents)** — Specialised workers: planner, developer, reviewer, tester, builder, pr-author. Each does exactly one job and reports a status code back to the orchestrator.

Skills are reusable knowledge modules loaded by agents — not agents themselves.

---

## Repository Structure

```
gts.ai.sdlc/
├── README.md                                    # This file
│
├── .agents/                                     # VS Code discovers all *.agent.md files here
│   ├── gts-orchestrator.agent.md                # Tier 1: generic routing orchestrator
│   ├── p7-orchestrator.agent.md                 # Tier 2: P7 system orchestrator
│   ├── p7-sdlc-planner.agent.md                 # Tier 3: P7 pipeline agents
│   ├── p7-sdlc-architect.agent.md
│   ├── p7-sdlc-developer.agent.md
│   ├── p7-sdlc-tester.agent.md
│   ├── p7-sdlc-reviewer.agent.md
│   ├── p7-sdlc-builder.agent.md
│   ├── p7-sdlc-pr-author.agent.md
│   ├── t7-orchestrator.agent.md                 # Tier 2: T7 system orchestrator
│   ├── t7-sdlc-planner.agent.md                 # Tier 3: T7 pipeline agents
│   ├── t7-sdlc-developer.agent.md
│   ├── t7-sdlc-reviewer.agent.md
│   ├── t7-sdlc-knowledge.agent.md
│   └── skills/
│       ├── _template/
│       │   └── SKILL.md                         # Template: copy to create any new skill
│       ├── common/                              # Skills reusable across ALL systems
│       │   ├── github/
│       │   ├── github-pr-miner/
│       │   ├── jira/
│       │   ├── confluence/
│       │   ├── teams/
│       │   ├── sdlc-brainstorming/
│       │   ├── sdlc-debugging/
│       │   └── sdlc-verification/
│       └── systems/                             # Skills scoped to one system
│           ├── p7/
│           │   ├── p7-code/
│           │   ├── p7-code-review/
│           │   ├── p7-debugging/
│           │   ├── p7-brainstorming/
│           │   ├── p7-verification/
│           │   └── p7-github/
│           └── t7/
│               ├── t7-code/
│               ├── t7-spec/
│               └── t7-knowledge-base/
│
└── _template/                                   # Copy this to add a new system (not auto-discovered)
    ├── SYSTEM-orchestrator.agent.md             # Template: system orchestrator (Tier 2)
    └── SYSTEM-sdlc-developer.agent.md           # Template: developer pipeline agent (Tier 3)
```

---

## Supported Systems

| System | Orchestrator | Pipeline Agents | System Skills |
|--------|-------------|-----------------|---------------|
| P7 — Pricing & Risk Management | `p7-orchestrator` | planner, architect, developer, tester, reviewer, builder, pr-author | p7-code, p7-code-review, p7-debugging, p7-brainstorming, p7-verification, p7-github |
| T7 — Trading System | `t7-orchestrator` | planner, developer, reviewer, knowledge | t7-code, t7-spec, t7-knowledge-base |

---

## How to Add a New System

**Step 1 — Create the system orchestrator**

Copy `_template/SYSTEM-orchestrator.agent.md` to `.agents/{system}-orchestrator.agent.md`.
Replace every `{SYSTEM}` / `{system}` placeholder.

**Step 2 — Create pipeline agents**

Copy `_template/SYSTEM-sdlc-developer.agent.md` to `.agents/{system}-sdlc-developer.agent.md`.
Fill in layer paths, build commands, coding standards.
Add additional agents (`.agents/{system}-sdlc-planner.agent.md`, `.agents/{system}-sdlc-reviewer.agent.md`, etc.) as the system matures.

**Step 3 — Create system skills**
```
mkdir .agents/skills/systems/{system}/{system}-code
cp .agents/skills/_template/SKILL.md .agents/skills/systems/{system}/{system}-code/SKILL.md
```
Fill in layer table, naming conventions, build commands, testing patterns.

**Step 4 — Add to the generic orchestrator**

In `.agents/gts-orchestrator.agent.md`, add `{system}-orchestrator` to the `agents:` frontmatter list and add a routing rule in the **Routing Rules** section.

---

## Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| System folder names | lowercase, no separators | `p7`, `t7`, `cue` |
| Subagent `name` field | `{system}-orchestrator` | `t7-orchestrator` |
| Pipeline agent file names | `{system}-sdlc-{role}.agent.md` | `t7-sdlc-developer.agent.md` |
| Pipeline agent `name` field | `{system}-sdlc-{role}` | `t7-sdlc-developer` |
| Skill folder names | `{system}-{topic}` (system) or plain noun (common) | `t7-code`, `github` |
| Skill `name` field | matches folder name | `t7-code`, `github` |
| Common skill `systems` field | `[all]` | `systems: [all]` |
| System skill `systems` field | `[{system}]` | `systems: [t7]` |
| System override skill `extends` | `common/{skill-name}` | `extends: common/github` |

---

## Composition Model

```
User request
    │
    ▼
┌─────────────────────────────────┐
│  gts-orchestrator  (Tier 1)     │  .agents/gts-orchestrator.agent.md
│  "Which system?"                │
│  Routes to system orchestrator  │
└───────────┬─────────────────────┘
            │  delegates to
            ▼
┌─────────────────────────────────┐
│  {system}-orchestrator (Tier 2) │  .agents/{system}-orchestrator.agent.md
│  Plan → Gate → Develop →        │
│  Review → PR                    │
└──┬──────────┬────────────┬──────┘
   │          │            │
   ▼          ▼            ▼
planner   developer    reviewer      (Tier 3 pipeline agents)
   │          │            │
   └──────────┴────────────┘
              │ load
    ┌─────────┴──────────┐
    │   Common Skills    │  .agents/skills/common/  (github, jira, confluence, …)
    │   System Skills    │  .agents/skills/systems/{system}/  ({system}-code, …)
    └────────────────────┘
```

Every Tier 2 and Tier 3 agent is a **coordinator or worker only** — no agent reads files or writes code outside its designated role. The developer agent is the only agent that writes code.

---

## Common Skills

| Skill | Path | Use When |
|-------|------|----------|
| `github` | `skills/common/github/` | Creating PRs, writing commit messages, branch management, review checklists |
| `jira` | `skills/common/jira/` | Linking Jira tickets, updating status, referencing tickets in commits/PRs |
| `confluence` | `skills/common/confluence/` | Writing ADRs, API docs, meeting notes, onboarding guides |
| `teams` | `skills/common/teams/` | Sending Teams notifications, formatting pipeline status messages |
| `sdlc-brainstorming` | `skills/common/sdlc-brainstorming/` | Exploring requirements, clarifying scope before planning begins |
| `sdlc-debugging` | `skills/common/sdlc-debugging/` | Systematic diagnosis of bugs before any fix is attempted |
| `sdlc-verification` | `skills/common/sdlc-verification/` | Pre-completion checklist before declaring DONE |

---

## Open Questions / Future Work

| Question | Recommended Answer |
|----------|--------------------|
| **Should system skills be able to override common skills?** | Yes — use the `extends` frontmatter field. The system skill adds rules on top; the common skill is the base. Already in use with `p7-github` overriding `common/github`. |
| **How should the orchestrator handle a system not yet in `registry.json`?** | Ask the user which system they are working on, then prompt them to follow the "How to Add a New System" steps above. Do not guess or hallucinate a subagent. |
| **When should a new pipeline agent role be added vs reusing developer?** | Add a dedicated agent when the role has distinct constraints (e.g. tester must not edit production code, builder must only run build commands). Roles that only differ by scope can share the developer agent with task-specific instructions in the plan. |
| **How are skills versioned when a common skill changes?** | System skills that `extend` a common skill inherit changes automatically. System skills that duplicate common content must be updated manually. Avoid duplication — prefer `extends` and additive overrides. |
