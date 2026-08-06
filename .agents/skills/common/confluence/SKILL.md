---
name: confluence
description: "Generic Confluence documentation skill. Use when: creating or updating Confluence pages, writing ADRs (Architecture Decision Records), documenting APIs, capturing meeting notes, or creating onboarding guides."
systems: [all]
---

# Confluence Skill

Provides standard Confluence documentation operations reusable across all GTS systems.

## Operations

### Create a Page
- Always specify the parent page and space key
- Use Confluence macro formatting for code blocks, info panels, and status macros
- Add a `Last Updated` date and author at the top of every page

### Architecture Decision Records (ADRs)
Use the standard ADR format:
```
# ADR-{number}: {title}

**Date**: {date}
**Status**: Proposed | Accepted | Deprecated | Superseded

## Context
{What is the issue motivating this decision?}

## Decision
{What is the change we're proposing?}

## Consequences
{What becomes easier or harder as a result?}
```

### API Documentation
- Document all endpoints: method, path, request body, response schema, error codes
- Include a curl example for every endpoint
- Keep in sync with code changes — update Confluence in the same PR/commit

### Meeting Notes
- Title format: `{YYYY-MM-DD} {Meeting Type} — {Topic}`
- Sections: Attendees, Agenda, Decisions, Action Items (owner + due date)

## Conventions
- Space naming: use the system abbreviation (P7, T7, etc.) as the space key prefix
- Page titles: descriptive, searchable, no abbreviations
- Link Jira tickets using the `{jira}` macro

## Handling large responses

When a tool response contains `CONTENT TRUNCATED`, the full content has been
stored temporarily under a `spill_id`. Call `read_large_content` with the
`spill_id` and line range from the hint to retrieve the remainder. Repeat with
updated `start_line`/`end_line` until the full range is consumed, then assemble
all parts before proceeding.

Prefer narrower queries first (fewer fields, smaller `maxResults` / page size, or
a tighter filter) to avoid truncation — use `read_large_content` only when the
full content is genuinely required.
