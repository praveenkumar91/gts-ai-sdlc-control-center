---
name: github-pr-miner
description: "Mine pull request history to discover recurring reviewer feedback and update a repository's code-review skill file with evidence-backed rules. Use when: refreshing code-review rules from historical PR data, bootstrapping review rules for a new repository, or keeping review standards in sync with actual review practice."
argument-hint: "Repository path and the skill file to update (e.g. org/repo and skills/code-review/SKILL.md)"
systems: [all]
---

# GitHub PR Review Rules Miner

Use this skill to refresh code-review rules for any repository from its historical PR feedback.

## Scope

- Repository: `{REPOSITORY}` (e.g. `org/repo` on your GitHub host)
- Pull request states: **all** (`open`, `closed`, `merged`)
- Sources: PR metadata, review comments, review bodies, and PR conversation comments
- Target skill file: `{SKILL_FILE_PATH}` (e.g. `.github/skills/code-review/SKILL.md`)

## Required Workflow

1. Fetch all PRs with `state=all` and paginate until empty.
2. Fetch all review comments (`/pulls/comments`) and all issue comments (`/issues/comments`), filtering issue comments to PR numbers.
3. Fetch top-level reviews (`/pulls/{number}/reviews`) for each PR.
4. Build a reviewer-only corpus: remove bot users and comments from the PR author on their own PR.
5. Cluster recurring reviewer concerns and keep only actionable rules that appear repeatedly.
6. Produce repository-specific rules (not generic style advice), with evidence PR numbers.
7. Update `{SKILL_FILE_PATH}` by integrating mined rules into **already existing categories** whenever possible.
8. Create a **new category only if no existing category fits** the rule.
9. Avoid duplicate or near-duplicate rules; improve/merge existing wording instead of appending parallel bullets.

## Multi-Model Mining and Aggregation

When the environment supports launching sub-agents with different models, run the mining pass in parallel across multiple model families, then synthesize one final result. If sub-agents are not available, run a single-model pass.

1. Inspect available models and select 2–3 models from distinct families (max 3 total).
2. Model-selection policy:
   - Pick only explicitly available models.
   - Prefer standard/premium over mini/fast/cheap variants.
   - Avoid reusing the same model as the primary runner.
3. Spawn sub-agents in parallel. Each sub-agent must run the full mining workflow and produce:
   - Recurring reviewer-rule candidates.
   - Proposed placement into existing `{SKILL_FILE_PATH}` categories.
   - Evidence PR numbers for each rule.
4. Aggregate sub-agent outputs into one consolidated update:
   - Deduplicate overlapping rules.
   - Raise confidence for rules found by multiple models.
   - Keep unique single-model rules only when evidence is strong and recurring.
   - Resolve placement conflicts in favor of existing category fit and repository-specific wording.
5. Timeout handling: if a sub-agent is still running after 10 minutes, continue with completed results and document which models contributed.

## Category Placement Policy

- Treat existing `{SKILL_FILE_PATH}` headings and subheadings as canonical buckets.
- For each mined rule, first map it to the closest existing category.
- If multiple existing categories fit, prefer the one that matches current repository terminology and adjacent rules.
- Add a new category only when a recurring rule cannot be represented clearly in any existing category without forcing awkward placement.

## Rule Quality Bar

- Keep only rules that are recurring and materially useful for review quality.
- Prefer rules tied to `{REPOSITORY}`'s architecture and conventions rather than generic style advice.
- Avoid one-off preferences and purely cosmetic nits unless they recur strongly.
- Every emitted rule must include at least one evidence PR number.
