# Workspace repository discovery contract

The VS Code workspace is the primary repository boundary for multi-repository orchestration. The control centre
does not maintain a parallel repository catalog. This keeps repository identity, code, ownership and build
metadata close to their real sources and removes per-commit catalog maintenance.

## Discovery boundary

The parent enumerates every distinct Git top-level directory inside every VS Code workspace folder. Discovery:

- includes normal clones and worktrees;
- canonicalizes and deduplicates repository roots;
- never searches outside the supplied workspace folders;
- never scans an entire drive or user profile;
- never edits, checks out, fetches, pulls, resets, cleans, builds or tests a repository.

If the workspace exposes more than one path to the same Git root, the canonical root appears once.

## Lightweight runtime snapshot

Before impact analysis, the parent records for every discovered repository:

- canonical root and origin remote when present;
- exact 40-character `HEAD`, current branch, and clean or dirty state;
- root manifests, language and build indicators, CODEOWNERS, and top-level tracked paths;
- local `AGENTS.md`, Copilot instructions, custom agents and skill locations;
- ownership, components, contracts and dependencies evidenced by those files.

This is metadata discovery, not full source analysis. No repository worker or system planner is launched for the
inventory. Deep source reads begin only for repositories that remain plausible impact candidates.

## Incomplete workspace fallback

The workspace is incomplete when no Git repositories are found, a repository explicitly named by the
requirement is absent, a required producer or consumer cannot be located, or the available roots cannot define
the project boundary.

In that case the parent reports the discovered paths and asks once for the smallest useful addition:

1. a parent folder to add to the workspace;
2. a `.code-workspace` file;
3. local repository paths; or
4. Git URLs.

A parent folder is preferred over asking the user to type dozens of repositories. The supplied set is
authoritative for the current change only and is not saved as a custom catalog. Remote-only lists are not cloned
in bulk; provider metadata is inspected first and only plausible impact candidates may be cloned into an
approved workspace location.

## Impact and execution readiness

Every discovered repository is classified as `IMPLEMENTATION`, `VALIDATION_ONLY`, `CONTEXT_ONLY`, or
`NOT_IMPACTED`. Inclusion and exclusion require evidence from requirements, ownership, paths, manifests,
contracts, dependencies or source. The plan records the strongest exclusion reason for every repository that is
not active.

Before Stage 3 completes, each implementation or validation-only repository needs:

- a verified Git root or approved remote and usable location;
- an accountable owner from CODEOWNERS, local evidence, or explicit user confirmation;
- a system route and relevant local customization paths;
- an exact current commit and dirty state.

Missing execution identity is `BLOCKED_SPEC` or `INCONCLUSIVE`; it cannot be replaced with an inferred catalog
entry or broad search outside the workspace.

## Plan-frozen revisions

The independently reviewed plan freezes the canonical path or remote, exact commit and dirty state for every
active repository. A branch name, tag, `HEAD`, `latest`, or abbreviated SHA is not sufficient evidence in the
plan.

Immediately before implementation the parent resolves these values again. Any drift invalidates Human Gate 1
and returns the change to planning and full review. Dirty developer checkouts are never switched, cleaned, reset
or overwritten; implementation uses an isolated worktree or approved clean clone.

## Local expertise

Target repositories do not copy the control centre. When selected, their existing `AGENTS.md`,
`.github/copilot-instructions.md`, `.github/instructions/**`, `.github/agents`, and `.agents/skills` content is
passed to GTS as additive expertise. Local rules may strengthen but never weaken evidence requirements, plan
review or the two human gates.
