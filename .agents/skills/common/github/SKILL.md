---
name: github
description: "Generic GitHub operations skill. Use when: creating pull requests, reviewing PRs, managing branches, writing commit messages, checking CI status, or performing any GitHub workflow operations."
systems: [all]
---

# GitHub Skill

Provides standard GitHub operations reusable across all GTS systems.

## Commit Message Format

```
{ticket} {Description}
```

Example: `T7-12345 Differentiate on-book vs off-book trade`

- `{ticket}` is the Jira ticket key (e.g. `T7-12345`, `P7-678`).
- `{Description}` is a short imperative summary, capitalised, no trailing period.
- No type prefix, no scope, no conventional-commits format — this applies to all GTS baseline repos (T7, P7, etc.).

> For repositories that are **not** part of a GTS system baseline, conventional commits or another project-specific scheme may apply instead.

## Branch Naming

```
{jira-ticket}_{short_description}
```
Examples: `P7-123_add_dividend_view`, `T7-456_order_routing_null`

## Pull Request

### Title
Match the primary commit message: `{ticket} {Description}`

In the description, summarize what the PR does. If issues are fixed, add respective
`Closes #{issue-number}` clauses.

### Review Checklist
- All CI checks pass before requesting review
- At least 1 approver required before merge
- Squash merge preferred for feature branches
- Delete branch after merge

## Conventions
- Never force-push
- Draft PRs for work-in-progress
- Add `[WIP]` prefix to draft PR titles
