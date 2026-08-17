---
name: security-alert-triage
description: "Use when: investigating a GitHub SECURITY alert — a Dependabot dependency alert (CVE/GHSA), a code-scanning (CodeQL/SAST) alert, or a secret-scanning alert. Covers fetching the alert via the github MCP and adjudicating it authoritatively: for Dependabot, severity + reachability + fix-version / breaking-change; for code-scanning, source→sink data-flow exploitability; for secret-scanning, validity + blast radius + rotation urgency. Read-only — recommends a disposition (fix / dismiss-with-reason / false-positive / rotate), never writes. Agents delegate here and never call the github security tools directly. This is NOT holistic code review (code-review-lens) and NOT a SonarQube finding (sonar-finding-lens)."
systems: [all]
tools: [github/get_dependabot_alert, github/list_dependabot_alerts, github/get_code_scanning_alert, github/list_code_scanning_alerts, github/get_secret_scanning_alert, github/list_secret_scanning_alerts, github/search_code, github/get_file_contents, github/get_repository_tree]
user-invocable: false
---

# Security-Alert Triage — the GitHub security-alert brain

This skill adjudicates a **GitHub security alert** end-to-end and read-only: it fetches the alert via the
`github` MCP, establishes whether it is a **true or false positive** for *this* codebase, and recommends a
**disposition** with a fix or remediation plan. An agent **delegates** here and **never** calls the
`github` security tools directly outside this skill.

## Scope — what this is, and is NOT

Three GitHub security-alert families only:

- **Dependabot** — vulnerable dependency (CVE / GHSA).
- **Code scanning** — CodeQL / SAST findings.
- **Secret scanning** — leaked credentials.

It is **not** holistic code review of a change (`code-review-lens` / `codereviewer_lens`), **not** a
SonarQube finding (`sonar-finding-lens`), and **not** general GitHub browsing (`github`). Those are
separate skills.

## Adjudication playbooks (exact tools + method)

### Dependabot (dependency vulnerability)
1. `github/get_dependabot_alert(owner, repo, alertNumber)` → package, ecosystem, **vulnerable version
   range**, **patched version**, CVSS, CWE, advisory (GHSA), the manifest path, alert state.
2. **Reachability — the decisive true/false-positive signal.** Is the vulnerable package/API actually
   used, and on a reachable path?
   - `github/search_code(q="<import/symbol> repo:owner/repo")` to find usage sites;
   - `github/get_file_contents(...)` on the manifest + call sites to confirm;
   - for a T7 target, delegate grounding to `/t7-sdlc-knowledge` ("where is `<package>` used in
     `<component>`?").
3. **Fix assessment** — the patched version; **direct vs transitive** (transitive needs the parent
   bumped); is the bump **major** (breaking-change risk)?
4. **Disposition** — *fix* (bump to patched) · *dismiss-with-reason* (real but unreachable / dev-only) ·
   *false-positive* (not used) · *escalate*.

### Code scanning (CodeQL / SAST)
1. `github/get_code_scanning_alert(owner, repo, alertNumber)` → rule, severity, **location (file:line)**,
   the **data-flow path** (source → sink), state.
2. **Exploitability** — is the **source** attacker-controlled? is the flow **sanitised** before the
   **sink**? is the sink genuinely reachable? Read the flagged code via `github/get_file_contents`
   (ground the file/line via `/t7-sdlc-knowledge` for T7).
3. **Disposition** — *fix* (with the concrete code change) · *dismiss-with-reason* (infeasible flow) ·
   *false-positive* · *escalate*.

### Secret scanning
1. `github/get_secret_scanning_alert(owner, repo, alertNumber)` → secret type, location, validity signal,
   state.
2. **Validity + blast radius** — is it a **live** credential? where is it used / what does it grant? how
   urgent is rotation?
3. **Disposition** — *rotate-now* (live) · *revoke + purge history* · *false-positive* (test/placeholder)
   · *escalate*. **Never print the secret value** — reference it by type and location only.

## Bulk / repo-wide triage

For "triage all alerts in `owner/repo`" use the matching list tool — `github/list_dependabot_alerts` /
`list_code_scanning_alerts` / `list_secret_scanning_alerts` (filter by `state=open`, severity) — then run
the per-alert playbook and emit a disposition table.

## Disposition vocabulary (shared) — writes are gated

Report one disposition per alert with its evidence:

| Disposition | Meaning | Action (gated behind human approval) |
|---|---|---|
| **fix** | true positive, actionable | hand the fix (bump / code change) to the pipeline |
| **rotate** | live secret | rotate + revoke + purge history |
| **dismiss-with-reason** | real but not exploitable here (unreachable / dev-only / infeasible flow) | recommend a dismissal reason |
| **false-positive** | not applicable to this code | recommend FP dismissal |
| **escalate** | could not be grounded / needs an owner decision | flag the owner |

**Recommend only.** Never mark, dismiss, or comment on an alert, and never file a SIR — those are writes
gated behind human approval (and the `github` connector is read-only by construction).

## Fail-safe (github unreachable)

If the `github` MCP is **unreachable**, do **not** adjudicate from memory: report *"could not analyse —
github security tools unavailable"*, hand back the alert id/reference, and escalate. If only **grounding**
failed (couldn't confirm reachability), never claim a confident *false-positive* — return
**needs-context / escalate**.

## Constraints

- DELEGATE here — never call the `github` security tools directly from an agent body.
- **Read-only**: never dismiss, mark, comment, or file — recommend a disposition only.
- **Never print a secret value** — reference type + location.
- Cite the **alert number**, the **rule / CVE / GHSA**, and the **flagged location** on every disposition.
- This skill is **GitHub security alerts only** — not code review, not Sonar, not general GitHub browsing.
