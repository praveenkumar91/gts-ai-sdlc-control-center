---
name: requirement-conformance
description: "Use when: reviewing a code change to verify it implements the requirement set out in its Jira ticket (Epic / Issue / SIR) for T7 or P7 — i.e. 'does this change actually do what the ticket requires?'. Recovers the ticket's testable intent, links it to the code change, and produces a conformance matrix + verdict. Applies to both systems; complements code-quality review and the STT/ACT human tests."
systems: [all]
tools: [codereviewer_lens/assess_conformance]
---

# Requirement-Conformance Skill — *does the change implement what the ticket requires?*

Code review checks that a change is **well-built** (correctness, security, style). This skill checks that it is the **right change** — that it delivers the requirement stated in its Jira ticket. It is the third, orthogonal review lens:

- **code quality/security/intent-vs-plan** — is the code good, and does it match the *dispatched plan*? *(the `common/code-review` discipline via `code-review-lens`; lens's `review_semantics` uses the task/plan/PR body as the intent)*
- **requirement conformance** — does it do what the *Jira ticket* asked? *(this skill — the ticket's own obligations. The `codereviewer_lens` engine does **not** read the ticket for you, but once you have recovered the obligations it can produce an advisory obligation→change matrix via `assess_conformance` — see §4b.)*
- **STT / ACT test-tasks** — does it pass human system/acceptance test? *(downstream; corroborate, don't duplicate)*

> Follow the **`jira`** skill for all issue-type, workflow, field and link conventions. Never invent fields, states or links — read them from the ticket. Read-only: this skill never mutates Jira.
>
> **Prerequisite (already satisfied by both reviewers):** read-only Jira grant — `devops_jira/get_issue`, `get_issue_comments`, `get_issue_links`, `search_issues`.

---

## 1. Where the requirement actually lives (grounded field map)

There is **no single "Acceptance Criteria" field.** Intent is spread across fields, and *which* field carries it depends on the ticket type. Assemble from all that are present:

| Field | What it carries | Seen in |
|---|---|---|
| **`Description`** | The problem + expected behaviour. **P7 often embeds a GitHub permalink to the exact line** (`…/blob/<sha>/<path>#Lxx`) | P7-2955 (`Pricer.cxx#L111` vola→vega) |
| **`Analysis Summary`** | Root cause + the **testable spec** — often an *Expected-vs-Result table* (defects) or a per-component ***Changes Required*** list (features) | T7-573162 (Expected/Result), T7-568436 (per-component RDS/GUI/RDA/TES changes) |
| **`Test Instructions`** | The verification recipe. Sometimes specific, sometimes generic ("Test that the behavior fulfills the requirement") — if generic, **derive concrete checks** from the Description | P7-2955 ("non-zero dvoladspot"), P7-2924 (generic) |
| **`Solution Description`** | What the author claims was done (and cross-refs to other tickets/PRs) | P7-2955 ("Fixed according to spec"), T7-568436 (lists the 4 implementing SIRs) |
| **`Peer Review Notes`** | The **code-review / PR link(s)** — free-text Jira wiki-links, **often several PRs** | P7-2924 (`…/gts.p7.pricingengine/pull/1276`, `/1285`, `/1297`) |
| **`Labels`** | The **spec reference** — `DFS…`, `SRQ…`, `PIS…` (bridge to `/analyze` / `t7-spec`) | P7-2955 `DFS10115`; P7-2924 `PIS10015` |
| `Classification` / `Risk Assessment` | Severity → how strict the gate should be | `Serious Error` vs `Noncritical Error` |
| `System Test Status` / `Acceptance Test Status` | Human-test outcome to corroborate against | `OK`, `OK with limitations`, `pending` |

---

## 2. Recover the intent (build the obligation checklist)

1. **Resolve the ticket's place in the hierarchy** (`get_issue` + `get_issue_links`):
   - **SIR** → its parent **Issue** via the `is implemented by` / `IssueImpl <IssueKey>` convention → **Epic** (usually named after a spec, e.g. `DFS12200 …`) → **DFS/SRQ**. Hand any DFS/SRQ to `t7-spec` / `/analyze` for spec-level coverage.
   - **Issue** (feature) → it is typically implemented by **several `IssueImpl` SIRs**, one per component (T7-568436 → RDS + RDA + GUI + TES SIRs). The Issue's requirement = the union; conformance spans all implementing SIRs.
2. **Extract obligations by ticket type:**
   - **Defect SIR** → Description (expected vs actual) + `Analysis Summary` Expected/Result rows (each failing row = an obligation to fix).
   - **Feature Issue** → `Analysis Summary` *Changes Required* — **each component bullet is an obligation** (name the component + the concrete change, e.g. "RDS: add `includeTESReversals`, default False").
   - **Epic** → `Description` bullets + the referenced DFS.
   - **Stub ticket** (Description is just the spec title, e.g. `SRQ151007 - Infrastructure Enhancements` or `DFS150520 - XETRA Midpoint Enhancements`) → the requirement lives in the referenced **DFS/SRQ** (hand to `t7-spec` / `/analyze`) and/or the **implementing SIRs**; if neither is retrievable → `INTENT_UNVERIFIABLE`.
   - **Non-implementation ticket** (estimation/feasibility — "provide an estimation…", or a config-only DCCR) → **no code deliverable**; return **N/A**, do not manufacture obligations.
   - **Open/undecided requirement** (contains `TBC` / `TBD` / "to be confirmed", e.g. "send NaN or the previous price?") → mark that obligation `OPEN` — a change cannot *conform* to an undecided requirement.
3. **Flag requirements that aren't inline text.** Authoritative content is sometimes a **non-inline attachment** — a formula/screenshot **image** (e.g. P7-2955's PNG), or an attached **PDF / XML / doc** ("described in detail in the attached document"). Mark those `needs-attachment/human` — **never guess the content**.
4. **Emit a checklist:** `{id, obligation, source-field, component, checkability ∈ {pinpoint | semantic | manual}}`.

---

## 3. Recover the code change (tolerant, ordered — the link is unstructured)

The Jira **development panel / structured remote links are effectively unused** (`get_remote_issue_links` is empty in practice). Recover the change in this order and stop at the first that yields the code:

1. **Structured remote link** (`get_remote_issue_links`) — try, but expect empty.
2. **`Peer Review Notes`** — parse `github.deutsche-boerse.de/.../pull/<n>` URLs (bare, or Jira wiki-links `[title|url]`). **Often multiple PRs per ticket** — collect them all. The field sometimes just says "see PR" / "See github PR" with **no URL** → fall through to the next rungs. *(Primary for P7.)*
3. **Embedded permalink(s) in `Description`** — `…/blob/<sha>/<path>#Lxx` gives a precise code anchor.
4. **Implementing SIRs** — for an Issue, aggregate the code of each `is implemented by` / `IssueImpl` SIR.
5. **Branch / PR title** by the issue-key convention (`<KEY>-…`, per the `jira`/`github` skills).
6. **Fallback — the pipeline's working-tree diff.** In the in-pipeline (pre-PR) gate the change *is* the developer's local diff, read with `read`/`search`. **This is the reliable path and the only one for T7** (baseline/CMQA delivery — T7 tickets have no GitHub PR).

> **Mode:** in-pipeline (default) → review the local diff, no GitHub fetch. User-invoked on a merged ticket → the recovered PR(s) may be fetched for context (needs a `github` grant; T7 reviewer has one). If no code is recoverable at all → `INTENT_UNVERIFIABLE`. **Never fabricate a link.**

---

## 4. Map obligations → change (conformance)

For each obligation, decide a status **with file:line evidence**:

| Checkability | How to decide |
|---|---|
| **pinpoint** (names a file/line/attribute) | Near-deterministic: did the change touch exactly that and make the stated change? (P7-2955: `Pricer.cxx`~L111 `vola`→`vega`; P7-3229: `MdhSender.cxx` swap `and`→`or`; T7-568436: does RDS actually add `includeTESReversals`?). Allow for language operator spellings (C++ `and`/`or` ≡ `&&`/`||`). |
| **semantic** (prose obligation) | Judge whether the diff implements it; cite the file:line that does |
| **manual / needs-attachment** | Defer to STT/ACT + human; record as unverified-here |

Status ∈ **`COVERED` / `PARTIAL` / `MISSING` / `CONTRADICTED` / `OPEN`** (`OPEN` = the requirement itself is undecided, e.g. a `TBC`). Also (reverse): a change touching areas tied to **no** obligation is *undeclared scope* → a `[SUGGESTION]`/NIT, not a block.

### 4a. RDS/RDA obligations (T7 only) — verify against the live reference data

When an obligation names an **RDS/RDA** attribute, enum, or entity (e.g. T7-568436 *"RDS: add `includeTESReversals`, default False"*), checking the **code** alone is not enough — also confirm the declared value against the **real reference data** via the **`t7-refdata`** skill. Do the three-way, baseline-aware check:

1. **Spec obligation** — the value set the ticket / DFS / DTS declares (`t7-spec` for the spec).
2. **RDS documentation model** — does the model define the attribute/enum for the **target baseline**?
3. **Live reference data** — is the value present in `rdb` on the stated environment?

Classify `match` / `model-gap` / `data-absent` / `extra-in-data`. **The live database is corroboration, not the gate:** a value in spec + model but not yet in the live data is `data-absent` = *pending deployment* (the change is simply not deployed on that environment yet) — report it, but it is **not** a `MISSING`/gap. A genuine `model-gap` (spec value absent from the RDS model for the target baseline) **is** a gap. If the baselines cannot be aligned, mark the obligation `INTENT_UNVERIFIABLE`.

> **Prerequisite:** the reviewer / knowledge endpoint carries the **`t7-refdata`** skill (`t7dbcopy` read grant). This sub-check is **T7-only** — P7 has no RDS.

### 4b. Corroborate the mapping with the lens (advisory)

Once the obligation checklist and the recovered diff are in hand, corroborate the mapping with the `codereviewer_lens` engine: call `assess_conformance(diff_text, requirement_text=<the assembled obligations>)` — or `requirement_url=<ticket/spec URL>` when the source is fetchable. It runs the same concern + synthesis pipeline the reviewer uses and returns an **advisory** obligation→change matrix; it **never posts and never gates by itself** (the response is flagged `advisory`). Use it as a second opinion — it can surface an obligation you scored `COVERED` that the engine judges unmet, or vice-versa. Reconcile against your own reading: **your Jira-grounded verdict is authoritative**; the lens result corroborates it. If the lens is unavailable, proceed with the manual mapping — this step is corroboration, not a prerequisite.

---

## 5. Test-conformance (corroborate the human tests — don't duplicate)

- Does the change include tests exercising the ticket's `Test Instructions`? A stated Test Instruction with **no** corresponding test is a gap even if the code looks right.
- Cross-check the **STT / ACT** test-task status and `System/Acceptance Test Status`. A green code-conformance with a failing/absent system test is not "done".

---

## 6. System variance (T7 vs P7) — grounded

| Aspect | **T7** | **P7** |
|---|---|---|
| Code delivery | Baseline / CMQA — **no GitHub PR**; review the pipeline diff or the `IssueImpl` SIRs | GitHub PRs, usually listed in `Peer Review Notes` (may be several) |
| Requirement form | `Analysis Summary` tables / per-component *Changes Required*; validate against DFS/SRQ via **`t7-spec`** | `Description` + `Solution Description`; spec via `DFS…` label (no local spec corpus) |
| Verification | STT/ACT test-tasks + per-env `Installation states` | STT/ACT test-tasks + per-env `Installation states` |

---

## 7. Verdict → reviewer status

| Conformance verdict | Meaning | Maps to reviewer status |
|---|---|---|
| **`CONFORMS`** | Every text-checkable obligation `COVERED`; Test Instructions have coverage; nothing `CONTRADICTED` | does not block (feed into APPROVE) |
| **`GAPS_FOUND`** | ≥1 `MISSING` / `PARTIAL` / `CONTRADICTED`, or a stated Test Instruction with no test | **`CHANGES_REQUIRED`** (T7) / **REQUEST CHANGES `[REQUIRED]`** (P7) |
| **`INTENT_UNVERIFIABLE`** | Requirement is attachment-only, undecided (`TBC`), a stub with no retrievable spec, or no code is recoverable | **`NEEDS_CONTEXT`** — escalate to the human; **never silently APPROVE, never hard-block** |
| **`N/A`** | Non-implementation ticket (estimation/feasibility, config-only DCCR) — nothing to conform | Note it and skip the gate |

Scale strictness by `Classification` / `Risk Assessment` — a `Serious Error` warrants a harder gate than a `Noncritical Error`.

---

## 8. Output — append this to the review

```markdown
### Requirement Conformance
**Ticket:** <KEY> (<type>)  ·  **Intent sources:** <Description, Analysis Summary, Test Instructions, DFS/SRQ label>
**Code recovered via:** <pipeline diff | Peer Review Notes PR(s) | permalink | IssueImpl SIRs>

| # | Obligation (source field) | Component | Check | Change evidence | Status |
|---|---|---|---|---|---|
| O1 | <obligation> | <comp> | pinpoint/semantic/manual | <file:line or —> | COVERED/PARTIAL/MISSING/CONTRADICTED |
| T1 | Test Instruction: <…> | — | test | <test file or —> | COVERED/MISSING-TEST |

**Conformance verdict:** CONFORMS | GAPS_FOUND | INTENT_UNVERIFIABLE
<one line per gap: what is missing/partial/contradicted and where>
```

---

## 9. Anti-patterns

- **Don't rely on structured remote links** — they are empty in practice; parse `Peer Review Notes` / the diff.
- **Don't assume a GitHub PR exists** — T7 has none; operate on the pipeline diff.
- **Don't treat a ticket as one PR** — it may map to several PRs or several `IssueImpl` SIRs; aggregate.
- **Don't parse formula/screenshot images as text** — flag `needs-vision/human`.
- **Don't duplicate STT/ACT** — corroborate their status; this gate is a *pre-human* filter.
- **Don't fabricate a code link or an obligation** — unrecoverable ⇒ `INTENT_UNVERIFIABLE`, escalate.
- **Don't hard-block on `INTENT_UNVERIFIABLE`** — a non-textual/undecided requirement is not a failed change.
- **Don't manufacture obligations** for a stub ticket (spec-title only) or an estimation/feasibility ticket — resolve via the spec/child SIRs, or return `INTENT_UNVERIFIABLE` / `N/A`.
