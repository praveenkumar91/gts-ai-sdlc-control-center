---
name: issue-triage
description: "Use when: analysing a human-filed issue or incident — a GitHub issue from ANY repo (about any T7/P7 component) or a Jira SIR — to reach a root-cause / triage verdict. Fetches the issue, UNWRAPS any embedded signal (a Jenkins build, a Sonar link, a CVE, a stack trace, a PR/commit) for hand-off to the matching engine, resolves the subject from the issue CONTENT (not the repo name) via t7-knowledge, and applies a reproduce → localize → root-cause method; also does trend triage across an issue list/query. Read-only. Extends the generic sdlc-debugging protocol with the tracked-issue specifics. NOT for machine-generated security alerts (security-alert-triage) and NOT holistic code review (code-review-lens)."
systems: [all]
extends: skills/common/sdlc-debugging
---

# Issue Triage — human-filed issues & incidents

Extends **`skills/common/sdlc-debugging`** (Reproduce → Isolate → Hypothesise → Verify) with the specifics
of a **tracked issue** — a GitHub issue (from any repo) or a Jira SIR. Read-only: it produces a root-cause /
triage verdict; it never edits code and never writes to the tracker.

Fetch the issue through the **`github`** and **`jira`** skills (this skill is the *method*; those are the
transport — never call their MCP tools directly outside them).

## Scope — what this is, and is NOT

- **Is:** a human-filed **issue / incident / SIR** — a narrative bug or incident report needing reproduce →
  localize → root cause, plus the **unwrapping** of any signal embedded in it.
- **Is NOT:** a machine-generated **security alert** (`security-alert-triage`), a **SonarQube finding**
  (`sonar-finding-lens`), a **Jenkins build failure** on its own (`build-failure-lens`), or **code review**
  of a change (`code-review-lens`). When an issue *embeds* one of those, route it to that engine (§2).

## Method

### 1 — Fetch
- **GitHub issue** → `github/get_issue(owner, repo, number)` + `github/list_issue_comments`.
- **Jira SIR** → `devops_jira/get_issue(key)` + `get_issue_comments` + `get_issue_links` +
  `get_remote_issue_links` (SIRs cross-reference builds, PRs, Sonar issues and other SIRs).

### 2 — Unwrap embedded signals (route, don't re-analyse)
Scan the title / body / comments / links for the signal the issue is really *about*, and hand it to the
right engine:
- a Jenkins **build** URL / job+# / console log → **`build-failure-lens`**;
- a **SonarQube** link / issue key → **`sonar-finding-lens`**;
- a **Dependabot / CodeQL / secret** alert or a `CVE-…` / `GHSA-…` → **`security-alert-triage`**;
- a **stack trace** / crash dump → diagnose it (`build-failure-lens`'s `diagnose_log`, or the protocol
  below);
- a **PR / commit SHA** → pull the culprit (`github/get_commit` · `github/get_pull_request_diff`).

Fold each engine's result back into the one verdict. **Depth guard:** cap wrapper recursion
(SIR → issue → SIR) and dedupe already-seen signals.

### 3 — Resolve the subject from CONTENT, not the repo name
The repo the issue lives in is at most a weak hint — an issue about a T7 component can sit in *any* repo.
Extract component names, error signatures, terminology, file paths and referenced DFS/SRQ, then delegate to
**`/t7-sdlc-knowledge`**: *"Does this describe a T7 component? Which one, where is its code, who owns it,
which spec governs it?"* — it resolves even abbreviations (e.g. *OFI → Outbound Feed Interface* →
repo / owner / governing DFS / code location). For P7, resolve via `github/search_code` +
`github/get_file_contents`.

### 4 — Root-cause (the sdlc-debugging protocol, grounded)
Apply **Reproduce → Isolate → Hypothesise → Verify** from the base skill, grounded on the resolved target:
- confirm reproducibility and the observed-vs-expected behaviour stated in the issue;
- isolate to the component/unit (via `/t7-sdlc-knowledge`; `github/list_commits` for "what changed");
- rank 2–3 candidate causes and eliminate by observables **before** proposing any fix;
- name the culprit change where one exists (`github/get_pull_request_diff` · `github/get_commit`).

### 5 — Trend triage (an issue list or `?q=…` search)
For an issues **index** or a search URL → `github/search_issues(query)` / `github/list_issues` → a table
across the matching issues (recurring root causes, hot components, open vs resolved) so a *pattern* — not
just one issue — is surfaced.

## Output

A root-cause / triage verdict: **symptom → root cause + quoted evidence → affected component & owner →
impact → recommended action**. A real fix is a **recommendation handed to the SDLC pipeline** — this skill
never implements it. Cite the issue/SIR key, the resolved component, and the culprit commit/PR where known.

## Constraints

- **Read-only** — never edit code, and never comment on / transition / close the issue or SIR; recommend
  only.
- **Skill-first** — fetch via the `github` / `jira` skills; ground via `/t7-sdlc-knowledge`; never call
  those MCP tools directly.
- **Unwrap, don't duplicate** — an embedded build / Sonar / security signal goes to *its* engine; do not
  re-analyse it by hand.
- **Honest ledger** — if the subject or the culprit could not be grounded, say so; never assert a confident
  root cause you could not verify.
