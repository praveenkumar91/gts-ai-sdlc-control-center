---
name: github
description: "Generic GitHub operations skill. Use when: creating pull requests, reviewing PRs, managing branches, writing commit messages, checking CI status, or performing any GitHub workflow operations."
systems: [all]
---

# GitHub Skill

Provides standard GitHub operations reusable across all GTS systems. For system-specific commit conventions (e.g., P7 layer scopes), use the system-specific github skill overlay.

## Commit Message Format

Follow Conventional Commits:
```
{type}({scope}): {short description}

{optional body}

{optional footer: BREAKING CHANGE, Closes #issue}
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `ci`

## Branch Naming

```
{type}/{jira-ticket}-{short-description}
```
Examples: `feat/P7-123-add-dividend-view`, `fix/T7-456-order-routing-null`

## Pull Request

### Title
Match the primary commit message: `{type}({scope}): {description}`

### Description Template
```markdown
## Summary
{What does this PR do?}

## Changes
- {file/component}: {what changed}

## Testing
- [ ] Unit tests pass
- [ ] Manual verification performed
- [ ] No regressions introduced

## Linked Issues
Closes #{issue-number}
```

### Review Checklist
- All CI checks pass before requesting review
- At least 1 approver required before merge
- Squash merge preferred for feature branches
- Delete branch after merge

## Conventions
- Never force-push to `main` or `develop`
- Draft PRs for work-in-progress
- Add `[WIP]` prefix to draft PR titles
