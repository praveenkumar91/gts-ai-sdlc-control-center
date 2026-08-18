---
name: sdlc-brainstorming
description: "Generic requirement exploration and design brainstorming skill. Use when: a feature request is ambiguous, requirements need clarification, exploring design alternatives, or performing pre-implementation analysis before planning."
argument-hint: "Describe the feature or problem area to explore"
systems: [all]
---

# SDLC Brainstorming Skill

A structured pre-planning exploration protocol to clarify requirements and explore design options before committing to an implementation plan.

## Protocol

### Phase 1 — Clarify Intent
Ask targeted questions to remove ambiguity:
- What problem does this solve for the end user?
- What does success look like? How will we measure it?
- Are there constraints (performance, security, backwards-compatibility)?
- Are there existing patterns in the codebase this should follow?

### Phase 2 — Explore Options
Generate 2-3 distinct design approaches:
- Option A: {minimal/conservative approach}
- Option B: {recommended balanced approach}
- Option C: {comprehensive/ambitious approach}

For each option, evaluate: complexity, risk, effort, maintainability.

### Phase 3 — Identify Risks
- Technical risks (unknown APIs, performance unknowns, integration points)
- Scope risks (unclear acceptance criteria, dependency on other teams)
- Security risks (new endpoints, data exposure, input validation)

### Phase 4 — Recommend
State a clear recommendation with rationale:
> "I recommend Option B because {reason}. The main tradeoff is {tradeoff}."

### Phase 5 — Draft Acceptance Criteria
Produce a draft list of acceptance criteria in Given/When/Then format:
```
Given {context}
When {action}
Then {expected outcome}
```

## Output
Hand off to the planner with: recommended approach + acceptance criteria + identified risks.
