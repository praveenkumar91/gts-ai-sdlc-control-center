# gts.ai.sdlc

Developer reference for the GTS AI SDLC framework — agent and skill definitions for automating software development workflows across GTS systems.

---

## Overview

This repository defines a **3-tier composition model** for AI-assisted software development:

```
Tier 1: Generic Orchestrator  (agents/orchestrator/)
         ↓ routes by system
Tier 2: System Subagent       (subagents/{system}/agent.md)
         ↓ coordinates pipeline
Tier 3: Pipeline Agents       (subagents/{system}/agents/*.agent.md)
         ↓ use skills
        Common Skills          (skills/common/)
        System Skills          (skills/systems/{system}/)
```

- **Tier 1 (Generic Orchestrator)** — Knows all registered systems. Routes the user's request to the correct system subagent. Never implements anything itself.
- **Tier 2 (System Subagent)** — Knows the SDLC pipeline for one system (Plan → Gate → Develop → Review → PR). Coordinates Tier 3 agents. Never implements anything itself.
- **Tier 3 (Pipeline Agents)** — Specialised workers: planner, developer, reviewer, tester, builder, pr-author. Each does exactly one job and reports a status code back to the orchestrator.

Skills are reusable knowledge modules loaded by agents — not agents themselves.

---

## Repository Structure

```
gts.ai.sdlc/
├── registry.json                        # Master manifest: systems, subagents, pipeline agents, skills
├── README.md                            # This file
│
├── agents/
│   └── orchestrator/
│       └── agent.md                     # Tier 1: generic routing orchestrator (gts-orchestrator)
│
├── subagents/
│   ├── _template/                       # Copy this to add a new system
│   │   ├── agent.md                     # Template: system subagent (Tier 2)
│   │   └── agents/
│   │       └── sdlc-developer.agent.md  # Template: system developer pipeline agent (Tier 3)
│   ├── p7/
│   │   ├── agent.md                     # P7 system subagent (p7-orchestrator)
│   │   └── agents/                      # P7 pipeline agents (planner, developer, reviewer, …)
│   └── t7/
│       ├── agent.md                     # T7 system subagent (t7-orchestrator)
│       └── agents/                      # T7 pipeline agents (planner, developer, reviewer)
│
└── skills/
    ├── _template/
    │   └── SKILL.md                     # Template: copy to create any new skill
    ├── common/                          # Skills reusable across ALL systems (systems: [all])
    │   ├── github/                      # GitHub PR, branch, commit operations
    │   ├── jira/                        # Jira ticket creation, status updates, linking
    │   ├── confluence/                  # Confluence page creation, ADRs, API docs
    │   ├── teams/                       # Microsoft Teams notifications and message formatting
    │   ├── sdlc-brainstorming/          # Generic feature exploration and requirements gathering
    │   ├── sdlc-debugging/              # Generic systematic debugging workflow
    │   └── sdlc-verification/          # Generic pre-completion verification checklist
    └── systems/                         # Skills scoped to one system (systems: [systemname])
        ├── p7/
        │   ├── p7-code/                 # P7 coding conventions across all 4 layers
        │   ├── p7-debugging/            # P7-specific debugging patterns
        │   ├── p7-brainstorming/        # P7 feature exploration (overrides common)
        │   ├── p7-verification/         # P7 pre-completion verification (overrides common)
        │   └── p7-github/              # P7 commit scope conventions (overrides common)
        └── t7/
            ├── t7-code/                 # T7 coding conventions across all 4 layers
            └── t7-spec/                 # T7 functional specs, FIX protocol, order lifecycle
```

---

## Supported Systems

| System | Subagent | Pipeline Agents | System Skills |
|--------|----------|-----------------|---------------|
| P7 — Pricing & Risk Management | `subagents/p7/agent.md` | planner, architect, developer, tester, reviewer, builder, pr-author | p7-code, p7-debugging, p7-brainstorming, p7-verification, p7-github |
| T7 — Trading System | `subagents/t7/agent.md` | planner, developer, reviewer | t7-code, t7-spec |

---

## How to Add a New System

**Step 1 — Create the system subagent**
```
cp -r subagents/_template subagents/{system}
```
Edit `subagents/{system}/agent.md` — replace every `{system}` / `{SYSTEM}` placeholder.

**Step 2 — Create pipeline agents**

Edit `subagents/{system}/agents/sdlc-developer.agent.md` — fill in layer paths, build commands, coding standards.
Add additional agents (`sdlc-planner.agent.md`, `sdlc-reviewer.agent.md`, etc.) as the system matures.

**Step 3 — Create system skills**
```
mkdir -p skills/systems/{system}/{system}-code
cp skills/_template/SKILL.md skills/systems/{system}/{system}-code/SKILL.md
```
Fill in layer table, naming conventions, build commands, testing patterns.

**Step 4 — Register in `registry.json`**
```json
"{system}": {
  "name": "{Full System Name}",
  "subagent": "subagents/{system}/agent.md",
  "pipeline_agents": [
    "subagents/{system}/agents/sdlc-developer.agent.md"
  ],
  "skills": [
    "skills/systems/{system}/{system}-code"
  ]
}
```

**Step 5 — Add to the generic orchestrator**

In `agents/orchestrator/agent.md`, add `{system}-orchestrator` to the `agents:` frontmatter list and add a routing rule in the **Routing Rules** section.

---

## Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| System folder names | lowercase, no separators | `p7`, `t7`, `cue` |
| Subagent `name` field | `{system}-orchestrator` | `t7-orchestrator` |
| Pipeline agent file names | `sdlc-{role}.agent.md` | `sdlc-developer.agent.md` |
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
│  gts-orchestrator  (Tier 1)     │  agents/orchestrator/agent.md
│  "Which system?"                │
│  Routes to system subagent      │
└───────────┬─────────────────────┘
            │  delegates to
            ▼
┌─────────────────────────────────┐
│  {system}-orchestrator (Tier 2) │  subagents/{system}/agent.md
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
    │   Common Skills    │  skills/common/  (github, jira, confluence, …)
    │   System Skills    │  skills/systems/{system}/  ({system}-code, …)
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
