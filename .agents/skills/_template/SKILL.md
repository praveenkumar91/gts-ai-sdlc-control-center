---
name: {skill-name}                        # kebab-case, unique across all skills (e.g. cue-code, sdlc-retro)
description: "One sentence: what this skill does and WHEN to use it. Start with 'Use when:' — this is what the orchestrator reads to decide which skill to invoke."
systems: [all]                            # [all] for common/ skills reusable across every system
                                          # [systemname] for skills in skills/systems/{system}/ (e.g. [t7], [p7])
                                          # [system1, system2] if relevant to multiple but not all systems
# extends: common/{skill-name}           # OPTIONAL: uncomment if this is a system override of a common skill
                                          # System overrides add system-specific rules on top of the common base
# argument-hint: ""                       # OPTIONAL: hint shown to the user when invoking this skill
---

<!--
  WHERE TO PUT THIS FILE
  =======================
  - skills/common/{skill-name}/SKILL.md  → reusable across ALL systems (github, jira, confluence, etc.)
  - skills/systems/{system}/{skill-name}/SKILL.md  → system-specific knowledge ({system}-code, {system}-spec, etc.)

  WHEN TO USE `extends`
  ======================
  Use `extends` when this file adds system-specific rules on top of an existing common skill.
  Example: a p7-github skill that extends common/github with P7-specific commit scope conventions.
  Without `extends`, this skill stands alone.

  NAMING
  =======
  - Common skills: plain noun or action (github, jira, sdlc-debugging)
  - System skills: prefix with system name ({system}-code, {system}-spec, {system}-debugging)
-->

# {Skill Name}

{One paragraph: what this skill covers and why it exists.}

## Purpose

{Describe the problem this skill solves and the operations it supports.}

## Operations / Protocol

<!-- List the concrete operations this skill defines. Adapt headings to match the skill domain. -->

### {Operation 1}
{Rules, format, examples}

### {Operation 2}
{Rules, format, examples}

## Conventions

<!-- List invariants that must always hold when using this skill. -->
- {Convention 1}
- {Convention 2}

## Usage

<!-- How an orchestrator or developer agent should invoke this skill. -->
Invoke this skill when {condition}. Pass {what context is needed}.

Example invocation context:
> "{Concrete example of what to say to trigger this skill}"
