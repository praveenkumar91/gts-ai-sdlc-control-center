---
name: sonar-finding-lens
description: "Use when: investigating a SPECIFIC existing SonarQube finding (or a Sonar issue URL / dashboard / hotspot / bulk selection) — adjudicating true-vs-false-positive, understanding a finding end-to-end, or triaging a project's Sonar backlog. Covers the sonarqube-lens MCP server: analyze_finding runs six perspectives and returns a true/false-positive probability plus a verdict and fix plan; parse_sonar_url classifies a pasted Sonar URL/key. This is DISTINCT from code-review-lens (holistic review of a change/diff/PR): use this for a named Sonar finding, not for reviewing new code. Agents delegate here and never call the sonarqube-lens MCP tools directly."
systems: [all]
tools: [sonarqube-lens/analyze_finding, sonarqube-lens/parse_sonar_url]
user-invocable: false
---

# Sonar-Finding Lens — the SonarQube finding-investigation brain

`sonarqube-lens` investigates **a specific, existing SonarQube finding** end-to-end: it collects the
evidence, runs **six perspectives**, adjudicates **true-vs-false-positive with a probability**, and
(read-only) proposes a **verdict + fix plan**. An agent **delegates** finding-investigation to the
lens through this skill and **never** calls the `sonarqube-lens` MCP tools directly outside it.

## Why this is separate from `code-review-lens`

`code-review-lens` (the `codereviewer-lens` engine) reviews **a change** — a diff, commit or PR —
holistically, aggregating SonarQube *among many sources* (Fortify, scanning, guideline RAG, arch/
concurrency rules) into one review verdict. It answers *"is this new code good?"*

`sonar-finding-lens` has a **substantially different objective**: it drills **one already-reported
SonarQube finding** (or a dashboard / bulk selection of them) to answer *"is this Sonar issue a real
problem or a false positive, and if real, how do I fix it?"* — **not tied to a PR or a diff**. Reach
for it when a user asks to *analyse a Sonar issue*, *do false-positive analysis*, or *triage the Sonar
backlog* for a project. It is a finding-investigation tool, not a code-review pass.

## What each tool does

| Need | Tool | Notes |
|---|---|---|
| Analyse a specific finding end-to-end (true/false-positive + verdict + fix plan) | `analyze_finding(url_or_key)` | six perspectives, probability, read-only verdict; accepts an issue URL (`.../issues?open=<key>`), a project dashboard/issues URL, or a raw issue key |
| Classify a pasted Sonar URL/key & extract keys | `parse_sonar_url(url_or_key)` | deterministic, no network — returns the mode `SINGLE` \| `BULK` \| `DASHBOARD` \| `HOTSPOT` \| `QUALITY_PROFILE` \| `SEARCH` + project key + issue keys |

## Choosing the tool (by trigger)

- **"Is this Sonar issue a false positive?" / "analyse finding `<key>`" / a single issue URL** →
  `analyze_finding(url_or_key)`; report its **disposition** (true positive vs false positive) with the
  probability and the six-perspective reasoning.
- **A dashboard / project / bulk selection URL, or you are unsure what the URL points at** → call
  `parse_sonar_url` first to get the **mode** and the extracted keys, then `analyze_finding` on each
  issue key (or the ones the user scoped).
- **Backlog triage** → `parse_sonar_url` to enumerate the keys, then `analyze_finding` per key,
  summarising the true-positive vs false-positive split.

## Reading the lens result

`analyze_finding` returns the collected evidence, the six-perspective analysis, a **true/false-positive
probability**, a proposed **verdict**, and a **fix plan**. Trust the **disposition**, and note that the
false-positive percentage is a **band**, not an exact number (the perspective signal is LLM-assisted).
Always tie the verdict to the **flagged line and the rule** — if the analysed location could not be
grounded against live source, treat the result as **needs escalation**, not a confident false-positive.

## Handling the verdict (writes are gated)

- **False positive** → report it as such with the perspective evidence, and **recommend** the FP-mark;
  do **not** auto-mark it. Marking a finding false-positive in SonarQube or filing a Jira SIR is a
  **write gated behind human approval** — surface the recommendation and let the human confirm.
- **True positive** → report the finding with its **fix plan** so it can be actioned (in-pipeline, feed
  it to the developer; standalone, present it to the user).
- **Ungrounded / stale location** → escalate ("re-scan & close" / "verify location"); never assert a
  confident false positive on an unverified location.

## Fail-safe (lens unavailable)

If the `sonarqube-lens` MCP server is **unreachable**, do **not** hand-adjudicate a finding as a false
positive from memory. Report that the finding **could not be analysed — sonarqube-lens unavailable**
and escalate. A per-provider degradation (e.g. GHE source unavailable for grounding) is reported by the
lens as a lowered confidence / escalation, not an outage.

## Constraints

- DELEGATE here — never call `sonarqube-lens` MCP tools directly from an agent body.
- **Read-only analysis**: never mark a finding false-positive or file a Jira SIR without explicit human
  approval — those writes are gated and out of this skill's scope.
- This skill investigates **existing SonarQube findings** — it is **not** the holistic code review of a
  change (`code-review-lens`) and does not replace the reviewer's own retained duties.
- Cite the **issue key**, the **rule**, and the **flagged line** on every disposition.
