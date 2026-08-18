---
name: code-review-lens
description: "Use when: performing code review of a T7/P7 change (diff, commit, PR, or snippet). This skill is the single brain for the code-review CONCERNS — correctness, code quality, security (OWASP/CWE), performance, coding-guideline compliance, dependencies, intent-vs-implementation, architecture boundaries, and concurrency — via the codereviewer_lens MCP server. Reviewer agents delegate these concerns here and never call the codereviewer_lens MCP tools directly."
systems: [all]
tools: [codereviewer_lens/review_diff, codereviewer_lens/review_commit, codereviewer_lens/review_pr, codereviewer_lens/review_snippet, codereviewer_lens/review_semantics, codereviewer_lens/validate_intent, codereviewer_lens/check_architecture_rules, codereviewer_lens/analyse_concurrency, codereviewer_lens/trace_impact, codereviewer_lens/query_code_graph, codereviewer_lens/check_compliance, codereviewer_lens/configure_review, codereviewer_lens/get_review_status]
user-invocable: false
---

# Code Review Lens — the review brain

`codereviewer_lens` is a comprehensive, tool-grounded code-review engine: SonarQube, Fortify,
GitHub code/secret scanning, dependency/SCA, a RAG over the C++/Java/Python coding-guideline PDFs,
and deterministic architecture-boundary (`ARCH-###`) + concurrency (`CONC-###`) rules. It is **the
brain for every code-review concern**. A reviewer agent **delegates** these concerns to lens through
this skill; it does **not** re-implement them with its own reasoning, and it **never** calls the
`codereviewer_lens` MCP tools directly outside this skill.

## Language coverage

Review is **not limited to a subset of languages**. Lens's SonarQube findings and its LLM concern
agents span the full project language set enforced by the DBAG quality profiles — **C, C++, Java,
Python, JavaScript, TypeScript, PL/SQL, PHP, HTML, CSS, XML, Shell, YAML** (13). The guideline-RAG
tier carries written prose for C++/Java/Python only; every other language is enforced via SonarQube
(live, at review time) plus the language-agnostic LLM concerns. Pass the diff/files in whatever
language(s) they are — do not restrict the review by language.

## Scope — what this skill does NOT cover

This skill covers **code-review concerns only**. The following review duties are **not** owned by
lens and remain the reviewer's own responsibility (do not expect this skill to produce them):

- the **unit-test discipline gate** (T7: is every changed public method covered by a positive and a
  negative test; are tests non-tautological; do they pass);
- the **holistic PR assessment** ("is this change justified / the right approach / overengineered?");
- **spec-conformance** (T7 DFS/SRQ/SIR via the `t7-spec` skill);
- **system-specific pattern/convention conformance** that lens has no rules for (e.g. P7 frontend
  patterns: Zustand slice signatures, AG Grid `gridCommons`, `useShallow`, Socket.IO flow).

## What each tool reviews

| Concern | Tool | Notes |
|---|---|---|
| Whole change (correctness · quality · security · performance · guideline · dependency) | `review_diff(diff_text, language)` · `review_commit(commit_sha, repo, profile)` · `review_pr(pr_url, profile)` | runs all lens agents; returns one verdict + findings + coverage ledger |
| Design-intent vs implementation | `review_semantics(diff_text, language, repo)` · `validate_intent(...)` | pass the dispatched **task/plan** as the stated intent |
| Component-boundary violations | `check_architecture_rules(diff_text, language, repo)` | deterministic `ARCH-###`; **needs `repo`** |
| Thread-safety / races | `analyse_concurrency(diff_text, language, repo)` | `CONC-###` |
| Cross-component impact (side-effects on dependents) | `trace_impact(...)` · `query_code_graph(...)` | needs `repo` |
| Ad-hoc review of a bare code block (not a diff) | `review_snippet(code, language, profile)` | for a snippet with no unified diff; `check_compliance` is the quick-check shortcut over the same path |
| Ad-hoc quick compliance | `check_compliance(code, language)` | quick-check profile |
| Inspect the effective review profile | `configure_review(profile)` | severity threshold · enabled agents · verdict policy — report what a profile actually runs |
| Re-read a prior result | `get_review_status(review_id)` | — |

## Choosing the tool + profile (by trigger)

- **In-pipeline, pre-PR** (the orchestrator hands you changed files; no PR exists):
  - If a **commit SHA** exists, prefer **`review_commit(sha, repo, profile="quick-check")`** — passing
    `repo` lets lens resolve the SonarQube project key and GitHub scanning.
  - Otherwise **`review_diff(diff_text, language)`** on the working-tree diff. Note: `review_diff`
    takes **no `repo`**, so SonarQube/GitHub scanning will degrade and appear in the coverage ledger.
  - Add **`check_architecture_rules(diff, language, repo)`** — and `analyse_concurrency(...)` for
    threading-sensitive C++ — when the change crosses component boundaries or shared state.
  - Pass the dispatched **task + plan + acceptance criteria** as intent to `review_semantics`.
  - **Do not** post to GitHub in this mode — return a status only.
- **User-invoked on a PR** ("review this PR `<url>`"): **`review_pr(url)`** (a `full-audit` profile).
- **Profiles** (lens `config/profiles/*.yaml`): `quick-check` in the tight loop, `full-audit` at the
  PR boundary / when a human asks. Pass via the `profile` argument of `review_commit` / `review_pr`.

## Reading the lens result

Every review tool returns a JSON object with:

- `verdict`: `pass` | `warn` | `block`
- `findings[]`: each has `id`, `severity` (`info`…`critical`), `title`, `file`, `line_range`,
  `source` (`guideline` | `tool` | provider), `rule_id`, `suggested_fix`
- `coverage_gaps[]`: checks that could **not** run (e.g. "SonarQube: no project key") — the honest
  "what was not verified" ledger
- `notes[]`: benign/expected skips (e.g. "no dependency manifest changed") + a data-sovereignty
  containment note

## Turning the lens result into your verdict

1. **The lens `verdict` is authoritative for code-review concerns** (lens applies its own
   severity/confidence gating internally). Map it into your agent's verdict vocabulary:
   `block` → *changes required*, `warn` → *needs human / comment*, `pass` → *approve* — subject to
   your **retained** duties (tests, holistic assessment, spec, system patterns), which may still
   lower the verdict but must never raise it above what lens returned for a code-review concern.
2. **Surface `coverage_gaps[]`** in a "Coverage & Limitations" block. A gap in a risk-relevant area
   means the result is **not** a clean approval — say so explicitly.
3. **Cite `rule_id` and `source`** on every finding you report.
4. **Do not hide a `block`, and do not invent a `block`** for a code-review concern — that is lens's
   domain. You may block on your **retained** duties independently.

## Fail-safe (lens unavailable)

If the `codereviewer_lens` MCP server is **unreachable** (as opposed to a per-provider degradation,
which lens reports as a coverage gap and still returns a verdict), you **must not** return an
approval. Return your agent's *changes-required / needs-context* verdict with the reason
*"code review could not be completed — codereviewer_lens unavailable"* and escalate. **No brain ⇒ no
certification.**

## Constraints

- DELEGATE here — never call `codereviewer_lens` MCP tools directly from an agent body.
- ALWAYS pass `repo` to `review_commit` and the focused tools (`check_architecture_rules`,
  `analyse_concurrency`, `trace_impact`, `query_code_graph`) so repo-scoped rules and the SonarQube
  project key resolve.
- This skill is **code-review concerns only** — do not use it for the unit-test discipline gate,
  holistic PR assessment, spec-conformance, or system-specific pattern conformance.
- In-pipeline (pre-PR) mode: return a **status only**; never post to GitHub.
