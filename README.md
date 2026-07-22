# gts.ai.sdlc

Developer reference for the GTS AI SDLC framework — agent and skill definitions for automating software development workflows across GTS systems.

---

## Overview

This repository defines a **3-tier composition model** for AI-assisted software development:

```
Tier 1: Generic Orchestrator  (.github/agents/gts-orchestrator.agent.md)
         ↓ routes by system
Tier 2: System Orchestrator   (.github/agents/{system}-orchestrator.agent.md)
         ↓ coordinates pipeline
Tier 3: Pipeline Agents       (.github/agents/{system}-sdlc-{role}.agent.md)
         ↓ use skills
        Common Skills          (.agents/skills/common/)
        System Skills          (.agents/skills/systems/{system}/)
```

- **Tier 1 (Generic Orchestrator)** — Knows all registered systems. Routes the user's request to the correct system orchestrator. Never implements anything itself.
- **Tier 2 (System Orchestrator)** — Knows the SDLC pipeline for one system (Plan → Gate → Develop → Review → PR). Coordinates Tier 3 agents. Never implements anything itself.
- **Tier 3 (Pipeline Agents)** — Specialised workers: planner, developer, reviewer, tester, builder, pr-author. Each does exactly one job and reports a status code back to the orchestrator.

Skills are reusable knowledge modules loaded by agents — not agents themselves.

---

## Repository Structure

```
gts.ai.sdlc/
├── README.md                                        # Repo overview, tier model, onboarding guide
├── CODEOWNERS                                        # PR Review by @gts-ai-developer
│
├── .github/
│   └── agents/                                      # VS Code Copilot auto-discovers *.agent.md here
│       │
│       │  # ── Tier 1: Generic Orchestrator ──
│       ├── gts-orchestrator.agent.md                # Routes user requests → correct system orchestrator
│       │
│       │  # ── Tier 2: System Orchestrators ──
│       ├── p7-orchestrator.agent.md                 # P7 system orchestrator
│       ├── t7-orchestrator.agent.md                 # T7 system orchestrator
│       │
│       │  # ── Tier 3: P7 Pipeline Agents ──
│       ├── p7-sdlc-planner.agent.md
│       ├── p7-sdlc-architect.agent.md
│       ├── p7-sdlc-developer.agent.md
│       ├── p7-sdlc-tester.agent.md
│       ├── p7-sdlc-reviewer.agent.md
│       ├── p7-sdlc-builder.agent.md
│       ├── p7-sdlc-pr-author.agent.md
│       ├── p7-sdlc-spec-author.agent.md             # On-demand DFS/DTS/SRQ authoring (post-planning)
│       │
│       │  # ── Tier 3: T7 Pipeline Agents ──
│       ├── t7-sdlc-planner.agent.md
│       ├── t7-sdlc-architect.agent.md
│       ├── t7-sdlc-developer.agent.md
│       ├── t7-sdlc-tester.agent.md
│       ├── t7-sdlc-reviewer.agent.md
│       ├── t7-sdlc-builder.agent.md
│       ├── t7-sdlc-pr-author.agent.md
│       ├── t7-sdlc-knowledge.agent.md
│       └── t7-sdlc-spec-author.agent.md             # On-demand DFS/DTS/SRQ authoring (post-planning)
│
├── .agents/
│   └── skills/                                      # Vendor-neutral skills (VS Code + Codex + CLI)
│       │
│       ├── _template/
│       │   └── SKILL.md                             # Template: copy to create any new skill
│       │
│       ├── common/                                  # Skills reusable across ALL systems
│       │   ├── github/
│       │   │   └── SKILL.md
│       │   ├── github-pr-miner/
│       │   │   └── SKILL.md
│       │   ├── jira/
│       │   │   └── SKILL.md
│       │   ├── confluence/
│       │   │   └── SKILL.md
│       │   ├── teams/
│       │   │   └── SKILL.md
│       │   ├── sdlc-brainstorming/
│       │   │   └── SKILL.md
│       │   ├── sdlc-debugging/
│       │   │   └── SKILL.md
│       │   ├── sdlc-verification/
│       │   │   └── SKILL.md
│       │   ├── ralph-loop/                         # Canonical autonomous build-loop protocol (artifacts, modes, backpressure)
│       │   │   └── SKILL.md
│       │   │
│       │   ├── spec-authoring/                     # Authors DFS/DTS/SRQ (DOCX-ready) after planning
│       │   │   ├── SKILL.md
│       │   │   └── references/
│       │   │       ├── DFS.md                       # Detailed Functional Specification model
│       │   │       ├── DTS.md                       # Detailed Technical Specification model
│       │   │       └── SRQ.md                       # System Requirement Specification model
│       │   │
│       │   └── coding-guidelines/
│       │       ├── SKILL.md
│       │       └── references/
│       │           ├── C++_Coding_Guidelines_v1.4.md
│       │           ├── Java_Coding_Guidelines_v1.4.md
│       │           └── Python_Coding_Guidelines_v1.4.md
│       │
│       └── systems/
│           │
│           ├── p7/                                  # P7 system skills
│           │   ├── p7-code/
│           │   │   └── SKILL.md
│           │   ├── p7-code-review/
│           │   │   └── SKILL.md
│           │   ├── p7-debugging/
│           │   │   └── SKILL.md
│           │   ├── p7-brainstorming/
│           │   │   └── SKILL.md
│           │   ├── p7-verification/
│           │   │   └── SKILL.md
│           │   └── p7-github/
│           │       └── SKILL.md
│           │
│           └── t7/                                  # T7 system skills
│               ├── t7-code/
│               │   └── SKILL.md
│               ├── t7-spec/
│               │   └── SKILL.md
│               └── t7-knowledge-base/
│                   ├── SKILL.md
│                   ├── assets/
│                   │   ├── output-template.md
│                   │   └── output-template copy.md
│                   └── references/
│                       ├── t7-applications.md       # T7 application inventory
│                       ├── t7-abbreviations.md      # T7 domain glossary & search-term guidance
│                       ├── t7-component-map.md      # T7 component dependency map
│                       ├── t7-component-owners.md   # T7 component ownership directory
│                       ├── t7-interfaces.md         # T7 interface definitions
│                       ├── t7-modules.md            # T7 module catalog
│                       └── t7-regulatory-glossary.md  # Regulatory abbreviations (DBG context)
│
└── _template/                                       # Bootstrapping templates (NOT auto-discovered)
    ├── SYSTEM-orchestrator.agent.md                 # Template: system orchestrator (Tier 2)
    ├── SYSTEM-sdlc-developer.agent.md               # Template: developer pipeline agent (Tier 3)
    └── SYSTEM-sdlc-spec-author.agent.md             # Template: on-demand DFS/DTS/SRQ spec-author (Tier 3)
```

---

## Supported Systems

| System | Orchestrator | Pipeline Agents | System Skills |
|--------|-------------|-----------------|---------------|
| P7 — Pricing & Risk Management | `p7-orchestrator` | planner, architect, developer, tester, reviewer, builder, pr-author, spec-author | p7-code, p7-code-review, p7-debugging, p7-brainstorming, p7-verification, p7-github |
| T7 — Trading System | `t7-orchestrator` | planner, architect, developer, tester, reviewer, builder, pr-author, knowledge, spec-author | t7-code, t7-spec, t7-knowledge-base |

> The **spec-author** agent (`{system}-sdlc-spec-author`) runs **on-demand after planning** to produce formal DFS/DTS/SRQ documents under `specs/{system}/`, using the common `spec-authoring` skill. It is separate from the planner: the planner produces a lightweight plan, the spec-author produces DOCX-ready specification files. DFS/DTS/SRQ are a shared corporate standard, so every system reuses the same common skill.

---

## How to Add a New System

**Step 1 — Create the system orchestrator**

Copy `_template/SYSTEM-orchestrator.agent.md` to `.github/agents/{system}-orchestrator.agent.md`.
Replace every `{SYSTEM}` / `{system}` placeholder.

**Step 2 — Create pipeline agents**

Copy `_template/SYSTEM-sdlc-developer.agent.md` to `.github/agents/{system}-sdlc-developer.agent.md`.
Fill in layer paths, build commands, coding standards.
Add additional agents (`.github/agents/{system}-sdlc-planner.agent.md`, `.github/agents/{system}-sdlc-reviewer.agent.md`, etc.) as the system matures.

**Step 3 — Create system skills**
```
mkdir .agents/skills/systems/{system}/{system}-code
cp .agents/skills/_template/SKILL.md .agents/skills/systems/{system}/{system}-code/SKILL.md
```
Fill in layer table, naming conventions, build commands, testing patterns.

**Step 4 — (Optional) Add the spec-author agent**

If the system produces formal DFS/DTS/SRQ documents, copy `_template/SYSTEM-sdlc-spec-author.agent.md` to `.github/agents/{system}-sdlc-spec-author.agent.md`.
Replace the `{SYSTEM}` / `{system}` placeholders, wire `skills:` to the system's content-grounding skill(s), and set the output folder to `specs/{system}/`.
Register it in the system orchestrator's `agents:` list and add an on-demand **Spec Authoring** phase + partial-run entry (mirror the T7/P7 orchestrators).
The DFS/DTS/SRQ structure, metadata contract, and filename rules are reused from the common `spec-authoring` skill — no per-system spec skill is required.

**Step 5 — Add to the generic orchestrator**

In `.github/agents/gts-orchestrator.agent.md`, add `{system}-orchestrator` to the `agents:` frontmatter list and add a routing rule in the **Routing Rules** section.

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
│  gts-orchestrator  (Tier 1)     │  .github/agents/gts-orchestrator.agent.md
│  "Which system?"                │
│  Routes to system orchestrator  │
└───────────┬─────────────────────┘
            │  delegates to
            ▼
┌─────────────────────────────────┐
│  {system}-orchestrator (Tier 2) │  .github/agents/{system}-orchestrator.agent.md
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
| `github` | `.agents/skills/common/github/` | Creating PRs, writing commit messages, branch management, review checklists |
| `github-pr-miner` | `.agents/skills/common/github-pr-miner/` | Mining PR history, analysing prior changes, extracting patterns from past PRs |
| `jira` | `.agents/skills/common/jira/` | Linking Jira tickets, updating status, referencing tickets in commits/PRs |
| `confluence` | `.agents/skills/common/confluence/` | Writing ADRs, API docs, meeting notes, onboarding guides |
| `teams` | `.agents/skills/common/teams/` | Sending Teams notifications, formatting pipeline status messages |
| `sdlc-brainstorming` | `.agents/skills/common/sdlc-brainstorming/` | Exploring requirements, clarifying scope before planning begins |
| `sdlc-debugging` | `.agents/skills/common/sdlc-debugging/` | Systematic diagnosis of bugs before any fix is attempted |
| `sdlc-verification` | `.agents/skills/common/sdlc-verification/` | Pre-completion checklist before declaring DONE |
| `coding-guidelines` | `.agents/skills/common/coding-guidelines/` | Writing or reviewing C++, Java, or Python code — applies language-level coding standards across all systems |

---

## Open Questions / Future Work

| Question | Recommended Answer |
|----------|--------------------|
| **Should system skills be able to override common skills?** | Yes — use the `extends` frontmatter field. The system skill adds rules on top; the common skill is the base. Already in use with `p7-github` overriding `common/github`. |
| **How should the orchestrator handle a system it doesn't recognise?** | Ask the user which system they are working on, then prompt them to follow the "How to Add a New System" steps above. The generic orchestrator only routes to systems listed in its `agents:` frontmatter — do not guess or hallucinate a system orchestrator. |
| **When should a new pipeline agent role be added vs reusing developer?** | Add a dedicated agent when the role has distinct constraints (e.g. tester must not edit production code, builder must only run build commands). Roles that only differ by scope can share the developer agent with task-specific instructions in the plan. |
| **How are skills versioned when a common skill changes?** | System skills that `extend` a common skill inherit changes automatically. System skills that duplicate common content must be updated manually. Avoid duplication — prefer `extends` and additive overrides. |
