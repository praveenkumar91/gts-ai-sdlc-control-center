---
name: code-review
description: "Use when: performing a code review of a change in any GTS system (T7, P7). Defines the system-agnostic review DISCIPLINE — process, holistic assessment, false-positive avoidance, the canonical severity→verdict mapping, scope-to-change, the coverage ledger, and the output skeleton. Code-review CONCERNS themselves (correctness, quality, security, performance, guideline, dependency, intent, architecture) are produced by the `code-review-lens` skill; this skill is how a reviewer orchestrates lens and forms the final verdict. System skills (`p7-code-review`, `t7-code-review`) extend this base with their own rules and retained gates."
systems: [all]
---

# Code Review — shared discipline

This is the common review discipline for every GTS system. The **code-review concerns**
(correctness, code quality, security, performance, coding-guideline compliance, dependencies,
intent-vs-implementation, architecture boundaries/concurrency) are the domain of the
**`code-review-lens`** skill — the review brain. **This skill defines how a reviewer *orchestrates*
lens and turns its result into a verdict**, plus the judgment lens does not make (holistic
assessment) and the system-specific gates each system retains (tests, spec-conformance, patterns).

System skills extend this base:
- `systems/p7/p7-code-review` (`extends: skills/common/code-review`) — P7 rules + retained P7 gates.
- `systems/t7/t7-code-review` (`extends: skills/common/code-review`) — T7 rules + retained T7 gates.

## Review process

1. **Gather context.** Identify the changed files / diff, the primary language(s), and the `repo`.
   Keep any commit SHA or PR URL. Read enough surrounding code to understand the change (not just the
   hunks).
2. **Independent assessment first (anti-anchoring).** Before reading the author's narrative (PR body,
   linked issue), form your own view of what the change does and what could be wrong. Reading the
   narrative first anchors judgment and hides real problems.
3. **Delegate the code-review concerns to `code-review-lens`.** Do not hand-roll them. Pass the
   dispatched **task + plan + acceptance criteria** (pre-PR) or the PR body (user-invoked) as the
   stated intent for `review_semantics`.
4. **Run the system's retained gates** (defined in the system skill) — e.g. unit-test discipline,
   spec-conformance, system-specific pattern conformance. Lens does **not** own these.
5. **Holistic assessment (your judgment — lens does not do this).** Is the change justified? Is it the
   right approach at the right layer? Overengineered? Net-positive against its maintenance cost and
   blast radius?
6. **Translate** lens's `verdict` + `findings` + `coverage_gaps` — combined with your retained-gate
   and holistic findings — into the system's verdict + the output below.

## False-positive avoidance

- Verify a concern against the full context before reporting it; confirm it isn't already handled by
  a caller/callee/wrapper.
- Skip theoretical concerns with negligible real-world probability ("could happen" ≠ "will happen").
- Trust the codebase's established conventions; if a pattern is consistent with the repo, assume it is
  intentional. Never assert something "doesn't exist / is deprecated" from training data — verify.
- Don't re-raise anything a linter/compiler/CI will catch.

## Multi-model review (when supported)

When the environment can launch sub-agents with different models, run the review in parallel across
2–3 distinct model families for diverse perspectives, then synthesise: deduplicate, **elevate**
findings that ≥2 models agree on, and keep unique high-confidence findings. Model-selection rules:
pick only models listed as available; prefer the highest-capability tier per family; never pick
"mini/fast/cheap" for review; do not reuse the model already running the primary review; avoid
known-unreliable models (e.g. `gpt-5.4` — sub-agent timeouts), preferring a `-codex` / highest-version
non-blocked variant. If a sub-agent stalls >10 min, proceed with the results you have and note which
models contributed. Also launch any **area-specific review agents** in `.github/agents` whose
description matches the change, in parallel, and integrate their findings — they are add-ons, not
replacements.

## Canonical severity → verdict (F4)

One ordered ladder maps to a verdict. Each system keeps its own verdict words as **aliases**.

```
Severity (worst surviving finding wins):
  must-fix    (blocking)   ← lens critical/high · ❌ error · [REQUIRED] · BLOCKER
  should-fix  (advisory+)  ← lens medium · ⚠️ warning · WARNING
  nit         (optional)   ← lens low/info · 💡 suggestion · [SUGGESTION] · NIT

Verdict:
  any must-fix           ⇒ Changes Required   (P7: REQUEST CHANGES · T7: CHANGES_REQUIRED)
  else any should-fix    ⇒ Needs Human/Comment (P7: COMMENT · T7: APPROVED_WITH_COMMENTS)
  else                   ⇒ Approve             (P7: APPROVE · T7: APPROVED)
```

- **The lens `verdict` is authoritative for code-review concerns** (lens applies its own
  severity/confidence gating). Do not raise a lens `pass` to a block, or hide a lens `block`, on a
  code-review concern. A **retained gate** (failed tests, spec violation) may independently lower the
  verdict.
- A system may tighten the mapping (e.g. T7 hot-path/boundary findings block at `should-fix`).

## Scope to change (F5)

- Tag each finding **Introduced** (caused by this change) or **Pre-existing** (already in a touched
  file). Lens already excludes findings on untouched files.
- **Pre-existing** issues are at most advisory follow-ups — they must **not** drive Changes Required.

## Coverage & Limitations (F1) — an honest verdict

Every review states what was **not** checked. Surface lens `coverage_gaps[]` verbatim in a Coverage &
Limitations block. **A gap in a risk-relevant area means the review is not a clean approval** —
escalate to human rather than approve. Benign notes (e.g. "no dependency manifest changed") do not
move the verdict.

## Confidence & corroboration (F2)

Lens tags each finding's `source` (`guideline`/`tool`/provider) and `rule_id`. Report them. Trust
lens's internal confidence gating for code-review concerns; do not manufacture a block from your own
opinion on a concern lens owns. Your **retained gates** are where your own judgment blocks.

## Fail-safe

If `code-review-lens` reports the lens server is **unreachable** (not a per-provider degradation),
**do not approve** — return the system's changes-required / needs-context verdict with the reason and
escalate. No brain ⇒ no certification.

## Output skeleton

Each system defines its exact output; every review includes at least:

> **AI-generated-content disclosure.** When posting review content to GitHub under a user's
> credentials (not a dedicated bot/app account), include a concise visible note (e.g. a `> [!NOTE]`
> alert) that the content was AI/Copilot-generated — unless the user explicitly asks to omit it.

```markdown
### Verdict: <system verdict word>
### Lens verdict: PASS | WARN | BLOCK
### Holistic Assessment — Motivation / Approach
### Findings   (each: file:line · severity · Source: lens <rule_id> | <retained gate> · Issue · Fix · Scope: Introduced|Pre-existing)
### Retained gates   (system-specific: tests / spec / patterns)
### Coverage & Limitations   (lens coverage_gaps; "none reported" if empty)
### What Looks Good
```

## Verdict-consistency rules

- The verdict must reflect the most severe surviving finding (lens or retained-gate).
- When genuinely uncertain, escalate to human review rather than approve — a false approval is worse
  than an unnecessary escalation.
- Separate code correctness from approach completeness: correct code that takes an insufficient
  approach still warrants a non-approval on the holistic axis.
