---
name: gts-delivery
description: "Delivery mechanics for gts-deliver — the common, project-generic tool that delivers a merged, reviewed change into an integration release baseline (EUREX/T7, P7, and other GTS projects). Covers the real gts-deliver CLI (project / release / sirno / branches / tag), the project registry that maps a project to its Jira project + release repo + Integration Jenkins job, the read-only preview commands the agent MAY run, the governance gates that can stop a delivery, tag- and branch-suggestion rules, error remedies, and post-delivery build monitoring. PROPOSE + READ-ONLY: never executes a real delivery, never creates or pushes tags, never mutates a baseline. Use when a change is ready to deliver, or to monitor the delivery's Integration build."
systems: [all]
user-invocable: false
---

# gts-delivery — gts-deliver mechanics & pre-delivery readiness

`gts-deliver` is the integration-delivery tool from the **common** integration toolkit
(`dev-confidential/gts.common.int.toolkit`), checked out on build/dev hosts at
**`/sw/contint/toolkit/bin/gts-deliver`**. It takes a **reviewed component tag** and **delivers it
into a target release baseline**: it validates inputs and permissions, validates SIR/Jira governance,
**creates annotated git tags** from the selected branch, **updates the target release baseline and
reconciliation releases**, and **writes delivery records and sends delivery mail**.

**It is project-generic.** The `--project` (a.k.a. `--system`) value selects the project context and
its release-configuration source from the toolkit's registry (`etc/project_info.xml`). The same tool,
the same flags and the same gates serve **every** GTS integration project — only the project string,
the Jira project, the release repo and the Integration Jenkins job differ.

**Hard boundary (repeated everywhere for a reason):** delivery **mutates shared state** (tags,
baseline, reconciliation repos, mail). This skill is **propose + read-only**. The agent runs only the
**read-only preview** commands listed below and **PROPOSES** the real `gts-deliver` command for a
human to run. After `gts-deliver`, **Jenkins owns the Integration build** — see §6.

---

## 0. Project registry (`etc/project_info.xml`) — the per-project parameters

`gts.ai.sdlc` targets **T7** and **P7**; both deliver with `gts-deliver`. Resolve the project's
parameters from the registry — never hardcode from memory.

| gts.ai.sdlc system | `--project` / `<system>` | Jira project(s) | Release / relmgmt repo | Integration Jenkins job |
|---|---|---|---|---|
| **T7** | `eurex` | `T7` (also `GROBI`, `FGW`) | `gts.eurex.release` / `gts.eurex.relmgmt` | `INT-EUREX-<release>` |
| **P7** | `p7` | `P7` | `gts.release.p7` (release **and** relmgmt) | `INT-P7-<release>` |

> The tool also serves `prisma` and the `grobi-*` family (out of `gts.ai.sdlc`'s scope). The guide's
> example is the T7 case (`--project eurex --sirno T7-…`); the P7 case is `--project p7 --sirno P7-…`.
> **Release numbering differs per project** (e.g. EUREX `151.002.010`, P7 `0XX.00Y.ZZZ`) — read it, don't assume.

**"Ready to deliver" differs by project delivery model:**
- **P7** is GitHub-PR-based → "ready" means the fix is in a **merged, reviewed PR**.
- **EUREX/T7** uses the baseline/CMQA model (often **no PR**) → "ready" means the fix is committed on the
  intended branch and the **SIR is in a deliverable state**.

---

## The delivery record — how branch, tag and baseline connect

`gts-deliver` binds the three into a `delivery.xml` (real structure from `etc/example_delivery.xml`):

```xml
<configuration project='EUREX' name='001.001.000'>   <!-- name = this delivery set -->
  <deliveries><delivery>
    <components>
      <component name='common/intmsg/model/messaging' ctype='Core'>
        <tag branch='trunk'>002.002.273</tag>        <!-- TAG 002.002.273 created FROM branch 'trunk' -->
        <releases>
          <deliver>001.001.000</deliver>             <!-- target release baseline -->
          <deliver>002.000.000</deliver>             <!-- reconciliation baseline(s) -->
        </releases>
      </component>
    </components>
    <sirs><sir>227227</sir></sirs>                    <!-- SIR(s) fixed -->
  </delivery></deliveries>
</configuration>
```

The chain, end to end:
1. **Branch** (component repo, e.g. `trunk` or `branches/GTS001_maintenance`) — where the reviewed change
   lives; supplied by `--branches`. `HEAD` is remapped to `master` before clone.
2. **Tag** (e.g. `002.002.273`) — an **annotated git tag `gts-deliver` creates *from* that branch** and
   pushes to the component repo; it is the component **version**. Stored as `<tag branch='…'>TAG</tag>`.
3. **Baseline** — each release has a `baseline.xml` (in the release repo, branch `<prefix><release>`) that
   maps **component → delivered tag**; `gts-deliver` **updates baseline.xml** to pin the new tag
   (`Baseline.get_tag(component)` reads it back).
4. **Release(s)** — `<releases><deliver>` lists the **target** baseline plus every **reconciliation**
   baseline the same tag is propagated into.

Never conflate: the **tag** (component version, e.g. `002.002.273`) is **independent of** the
**release/baseline** number (e.g. `151.002.010`) — one baseline pins many component tags. The **branch**
is only the tag's *source*; the baseline pins the **tag**, not the branch.

**Why reconciliation matters.** The target baseline is often *not* the only one that needs the fix. A
delivery's `<releases><deliver>` list — and the container itself (e.g. a baseline named
*“141.007.077 … (Reconciles to 141.007.091)”*) — propagates the **same component tag** into
**reconciliation baselines**, typically **lower → higher** within a release line. If a fix is delivered
to the target baseline **only**, the un-reconciled parallel/higher baseline still pins the **old tag**,
so the bug **regresses** the moment that baseline is built or deployed. Reconciliation is what keeps a
fix present across the whole release line — treat the reconciliation target(s) as **part of the
delivery**, never an afterthought, and never add `--noreconcile` without an explicit reason. **Mechanism:**
delivery **fast-forward-merges** the change from `dev` into the parallel **rel org** (immutable forked
copies of the dev repos), so each target/reconciliation baseline gets the **exact, dev-tested** code;
`gts-deliver` verifies FF-mergeability against the previously-delivered tag and the release repo (the check
`--noFFCheck` disables). The **one** documented skip is a hotfix **already fixed differently in dev** — done
by a **human** `git merge -s ours` + `git revert -m 1` (with a reason) before `gts-deliver`, **never** a blind
`--noreconcile` and **never** the agent's action.

## Upstream / downstream topology (repos & the build)

| Direction | Artifact | Where (`project_info.xml`) |
|---|---|---|
| **Upstream** | Component repo — source **branch**, receives the pushed **tag** | `github.deutsche-boerse.de/dev/gts.<component>` |
| **Downstream** | **Release repo** — each release's `baseline.xml` (component→tag), plus `initial/baseline.xml` & `allowed2DeliverInThisBaseline.txt` | T7 `gts.eurex.release` · P7 `gts.release.p7` (branch `<prefix><release>`) |
| **Downstream** | **Relmgmt / reconciliation repo** — reconciliation targets, release mgmt | T7 `gts.eurex.relmgmt` · P7 `gts.release.p7` (P7 uses one repo for both) |
| **Downstream** | **Integration Jenkins ("dev") build** — reads `baseline.xml`, builds the release | `INT-EUREX-<release>` / `INT-P7-<release>` (instance **gtsci**) |
| Read-only check | Component present in the rel org? | `checkRelRepo.py` |
| Permission | Who may deliver into this release | `allowed2DeliverInThisBaseline.txt` in the release |

Flow: **component-repo branch → (gts-deliver) tag → release-repo `baseline.xml` → `INT-<PROJECT>-<release>`
build on gtsci → reconciliation baselines**. The **"dev build"** a developer sees after delivering **is
that `INT-<PROJECT>-<release>` build on gtsci** — §6 covers finding and reading it.

---

## 1. Command anatomy (the real CLI)

```sh
# T7 (project = eurex, Jira project = T7)
gts-deliver \
    --project eurex \
    --release 151.002.010 \
    --sirno  T7-123456,T7-123457 \
    --branches common/service/exception/branches/GTS001_maintenance \
    common/service/exception/tags/151.002.030

# P7 (project = p7, Jira project = P7) — same tool, same flags
gts-deliver --project p7 --release <P7-release> --sirno P7-123456 \
    --branches <component>/branches/<ref> <component>/tags/<TAG>
```

| Part | Flag(s) | Meaning |
|---|---|---|
| Project / system | `-p` / `-s` / `--project` / `--system` | Selects release config, permission checks, scope-control, reconciliation targets, mail lists (from `project_info.xml`). T7 → `eurex`; P7 → `p7`. |
| Target release | `-r` / `--release` | The exact baseline to update. **Must be OPEN** or delivery stops. Format `XXX.YYY.ZZZ`. This is the **baseline** number — *not* the component tag. |
| SIR(s) | `-n` / `--sirno` | Comma-separated Jira/SIR keys fixed by the delivery. **Must match the project's Jira project** (T7→`T7-…`, P7→`P7-…`). Drives governance: readability, project ownership, state, container compatibility, scope-control. |
| Source branch(es) | `-S` / `--branches` | Comma-separated `component/branches/<ref>` — the branch the delivery tag is created from. |
| Delivery tag(s) | positional `component/tags/TAG` (or `-d` / `--deliveries`) | The component + tag being delivered (the **component version**, distinct from `--release`). |

Read-only / listing modes (safe — §2): `-l`/`--list`, `--dlist`, `--rlist` (+ `-g`/`--listlength`,
`--rlist-filter-reltype OFFICIAL|PRIVATE|BRANCH|all`, `--ignore` prefix, default `777`).

Tag automation: `-a`/`--autotag` (auto-generate the next tag **and deliver**), `--auto-tag-inc`
(increment, default `10`, env `GTS_DELIVER_TAG_INC`).

Other execution flags (part of the **proposed** command, never run by the agent): `--notag` (reuse an
existing tag), `-N`/`--nodelivery` (create tag + build only — **still creates a tag**), `--batch`
(non-interactive), `--testbuild`, `-R`/`--reconcile` / `-e`/`--noreconcile`, `--localbranch`
(BRANCH release type), `--protocol ssh|https`, `--remove-component` (BRANCH/PRIVATE only).

**Never-suggest flags:** `--noSireCheck` (skip SIR/Jira governance) and `--noFFCheck` (skip
fast-forward check) exist only for when the SIR/Jira system is confirmed down, and are an
**authorized human's** decision — never put them in a proposed command or recommend routinely
bypassing governance.

---

## 2. Read-only preview commands the agent MAY run

All read-only with respect to the baseline / release / remote (they never create tags, never push,
never mail). If the toolkit is **not installed** in the current environment, do **not** guess —
describe the command and gather the same evidence from git / Jira reads (delegated to
`t7-sdlc-knowledge`, the cross-system read endpoint) instead.

| Need | Command | Notes |
|---|---|---|
| Existing tags of a component (tag suggestion) | `gts-deliver -p <project> --list <component>` | Lists available tag names. Honour `--ignore` (default `777`). |
| Tags already delivered for a project | `gts-deliver -p <project> --dlist` | Delivered-tags list. |
| A component's current tag across releases | `gts-deliver -p <project> --rlist` | Use `--listlength` to widen. |
| Is the component repo present in the rel org? | `checkRelRepo.py [<component>...]` | **Fully read-only** (repo/branch availability). |
| Scope reconciliation (SIRs↔commits vs container) | `scopeCheck.py [options]` | Lists commits referencing SIRs not in the delivery container, and container SIRs without commits. **Writes a local report file only** — no remote mutation. Optional / heavier check. |
| Will the change **fast-forward-merge** into the rel org (the reconciliation/FF gate)? | `git branch --contains <ancestor-tag>` / `git tag --contains <ancestor-tag>` (from a local clone) | **Read-only.** Delivery FF-merges `dev` → the rel org; a non-FF change means the rel state never existed in `dev` (likely **untested**) and `gts-deliver` stops (unless `--noFFCheck`). |

Everything else (SIR state, component paths/owners, branches, `CONTRIBUTE.md`, existing git tags) comes
from **read delegations** to `t7-sdlc-knowledge` (Jira + GitHub + code) and the `jira` / `github`
common skills — never by running a mutating command.

---

## 3. Governance gates — what can stop a delivery, and the read-only preview for each

`gts-deliver` runs these checks **internally** when the human executes it; it stops on the first
failure. Reproduce them **read-only** as a readiness report so a NO-GO is caught before the human runs
anything.

| gts-deliver stop-check | Read-only readiness preview |
|---|---|
| Missing / invalid **project** | Confirm the project is a real registry project (`eurex`, `p7`, …). |
| **Release not OPEN** | Confirm the target release is currently OPEN (via `--rlist` / the project's relmgmt). A non-open release is an automatic NO-GO. |
| Missing git identity (`~/.gitconfig`) | Confirm `user.email` is set (read-only). |
| Invalid tag format / **reserved prefix `9`** | Tag must be `XXX.YYY.ZZZ` and must **not** start with `9`. Pure string check. |
| **No permission** to deliver to project-release | Reason about permission; if denied, the remedy is a human running `allow2DeliverIn2Baseline.py` (§5) — the agent never runs it. |
| Invalid / non-readable / mismatched **Jira/SIR** | Via `devops_jira` reads: SIR is readable, in the **project's Jira project** (T7→`T7`, P7→`P7`), in an acceptable state, and linked to a container compatible with the release. |
| **Scope-control violation** (approved SIR required) | Check the SIR is approved / in the delivery container (`scopeCheck.py` corroborates). |
| Branch ref missing / clone fails | Confirm the `--branches` ref exists in the component repo (read-only). |
| Tag create / push fails | Cannot be previewed — belongs to the human's real run. Flag as a residual risk. |

A single failing gate ⇒ **NO-GO**: name the gate and the concrete reason, and emit **no** command.

---

## 4. Tag suggestion — conform to the component's tradition ("suggest a new tag based on existing tags")

**The tag *format* is uniform** across a baseline: `NNN.NNN.NNN` — three **zero-padded 3-digit** segments
(e.g. `000.000.002`, `150.525.000`) — verified across **both** systems and release lines (P7 `012.003.020`,
EUREX `141.007.062` & `150.006.020` — 749 components, **100% `NNN.NNN.NNN`**). **The *numbering convention* is
per-component and varies** — you must **infer it from the component's own existing tags** and **conform** to it.
Real examples from one baseline:

| Component | Recent tags | Convention |
|---|---|---|
| `perfmon/orderbook-viewer` | `110.030.010 → 121.120.000 → 130.140.000 → 150.525.000` | first segment **tracks the release line** (11.0/12.1/13.0/15.0); irregular step |
| `eurex/apps/price-feed-handler` | `000.000.003 → 015.005.000 → 015.005.003` | realigned to the `015.005` line, then **+1** |
| `eurex/apps/cap` | `000.000.001 → 000.000.002` | **independent**, low numbering, **+1** |
| `thirdparty/benchmark` | `000.000.001 → 000.000.003` | **independent**, **+1** |

Procedure:
1. **List the component's existing tags**: `gts-deliver -p <project> --list <component>` (or the repo's git
   tags via `t7-sdlc-knowledge`). This is the **authoritative** signal — most component repos have **no
   `CONTRIBUTE.md`** (verified: 4/4 sampled repos had none), so the **tag history *is* the tradition**.
2. **Infer the convention** from the recent tags: does the leading segment(s) **track the release line**
   (e.g. `150.xxx` or `015.xxx` for R15.0 — the alignment style itself differs per repo) or is it
   **independent**? What is the **increment step** (often `+1`, sometimes `+10`, sometimes a realignment)?
   Keep the **zero-padded 3-digit** width.
3. **Propose the next tag that conforms** to that pattern — do not impose a one-size-fits-all rule.
4. Never propose a tag starting with `9` (reserved) or a `777`-prefixed tag (default-ignored).
5. **`--autotag` / `--auto-tag-inc` default `+10`** on the **last** segment — this **may not match** a
   component that increments `+1` or realigns to the release line. Prefer an **explicit,
   convention-matching** tag; treat `--autotag` as a fallback and **flag** when its `+10` step is unlikely
   to conform.
6. When the convention is **ambiguous** (a release realignment is due, or the history is short), present
   the candidate(s) and **ask** — never silently break the component's tradition.

Never conflate the **component tag** with the **release** number — they are independent.

## 4b. Branch suggestion ("suggest branches to use")

- Read the component repo's real branches and `CONTRIBUTE.md` (via `t7-sdlc-knowledge` / `github`).
- Map the SIR to its branch where the repo convention encodes it (e.g. `branches/SIR<number>`) or use
  the maintenance line the repo prescribes.
- Some repos enforce strict branch rules — honour `CONTRIBUTE.md` and flag violations rather than
  inventing a branch. **Never** propose a branch ref that does not exist.

---

## 5. Error remedies ("suggest how to proceed on errors")

| Symptom | Remedy to suggest (human action) |
|---|---|
| Release not OPEN | Wait for / select the open release, or ask release management. |
| Permission denied | An **authorized** engineer adds you via `allow2DeliverIn2Baseline.py` (it commits+pushes an allow-list entry — **the agent never runs it**), then retry. |
| Invalid / mismatched SIR | Fix the SIR: correct Jira project (must match the delivery project), acceptable state, and container linkage for the target release. |
| Scope-control violation | Get the SIR approved / into the delivery container. |
| Missing `~/.gitconfig` | Set `git config --global user.email` (and name). |
| Branch missing / clone fails | Correct the `--branches` ref to an existing branch. |
| Bad tag format / reserved `9` prefix | Choose a valid `XXX.YYY.ZZZ` tag not starting with `9`. |
| SIR/Jira system down | Only an authorized engineer may use `--noSireCheck` — **the agent must not** suggest it as routine; escalate instead. |

**Private-baseline trial:** before an official delivery, the change can be delivered to a **PRIVATE**
baseline for a live trial (private releases accept any kind of SIR). The agent may **propose** that
trial command for the human to run; it still never executes it.

---

## Special delivery cases (grounded in real deliveries)

- **Component removal.** Removing a component from an **official** baseline is a **CM/integrator** action
  applied across the reconciliation range (real example: *“removed `thirdparty/python-zope-testrunner`
  from all `150.003.XXX` baselines”*) — **not** the dev `gts-deliver --remove-component` flag, which is
  **BRANCH/PRIVATE only**. If asked to remove a component from an official baseline, say so and route to CM.
- **Conversion items.** A delivery can carry a **conversion item** (`<conversions>` in `delivery.xml`) that
  enforces a config/data roll-out (real example: *“add conversion item to enforce roll-out of the CMDB
  version”*). These accompany the component tag — surface them, never invent them.
- **Fixed-in vs installed iteration.** *“Fixed in configuration”* names the **target** baseline; the change
  actually lands in the **current open iteration** of that line (real example: fixed-in `150.003.010`,
  installed in `150.003.031`). Don't equate the target release with a specific iteration number.
- **Streams & promotion.** A baseline is delivered across project-defined **streams** (e.g. BF, STD, Nodal)
  × environments (ACT/SIMU/PROD) via **Deployment Requests** (`T7DEP-…`) — not a fixed BF/STD pair. Delivery
  (gts-deliver) puts the tag in the baseline; promotion across streams/envs is the CM/Deployment-Request flow.
- **Feature = multi-component / multi-SIR delivery.** A spec-driven feature (a DFS, e.g. DFS141435) is
  usually implemented as a **set of per-component IssueImpl SIRs** (real example: `T7-568355…568359` across
  GUI/MD/ME/RDA/RDS, under parent Issue `T7-568195`) — each delivers its **own component tag**, typically
  into the **same baseline**. Deliver the set **together**: several positional `component/tags/TAG` args and
  **all** the SIRs in `--sirno`. Don't deliver one component of a feature and forget its siblings. A
  **follow-up SIR** (e.g. `T7-570245` follows `T7-568357`) is its own later delivery.
- **Shared `common/*` & `thirdparty/*` components span systems.** They are shared across projects — e.g. **102**
  components are identical (same tag) in **both** the EUREX and P7 baselines (`common/service/exception=078.000.140`,
  `thirdparty/boost=001.018.010`, the `build` component `002.004.040`, …). Delivering/updating a shared component
  has **cross-system reach**: its reconciliation/impact can span **multiple projects' baselines** (EUREX, P7, …),
  not just one project's release lines. A **system-specific** component (`eurex/apps/*`, p7-specific) affects only
  its own system — weigh this when assessing a delivery's blast radius.

---

## 6. Post-delivery: which Integration ("dev") build, and did it pass?

After the human runs `gts-deliver`, the **Integration ("dev") build** runs for the project's release —
`INT-<PROJECT>-<release>` on the **gtsci** instance (T7 → `INT-EUREX-<release>`, P7 → `INT-P7-<release>`).
This is the **CR** (candidate-release) stage — after the developer's local **AD** build and before the
separate production **GA** build (GA is out of scope).
Delegate all Jenkins reading to the **`build-failure-lens`** skill (never call the `jenkins_lens` MCP
directly); pass `jenkins_instance="gtsci"`:

| Question | build-failure-lens tool |
|---|---|
| Which run belongs to this delivery? | `job_status("INT-<PROJECT>-<release>")` / `list_jobs(view=…)` to list recent runs, then `build_info(job, build_number)` to match the delivered **tag / SIR / component** in the build's SCM change / changelog. |
| Did the build pass or fail? | `job_status` / `analyze_build`. |
| A **technical** (infra/toolchain) failure vs a real build failure? | `score_build` — its per-substep verdict + false-positive class distinguishes infra/flake from a real defect. |
| Which stage failed? | `analyze_build` localises the failing substep with quoted evidence. |
| Free-text follow-up on that build (**ask mode**) | `ask("…")` — reuses the **last-analysed** build's session (e.g. "which SIR/tag is in this build?", "is this stage infra or code?"). Analyse the build **first**; `ask` has no context until one has been analysed. |

**Correlation flow:** resolve the key (project → `INT-<PROJECT>-<release>`, plus the delivered tag/SIR) →
`job_status`/`list_jobs` for candidate runs → `build_info` to confirm the run whose SCM change contains
the tag/SIR → `analyze_build` (stage + evidence) → `score_build` (technical-vs-real) → `ask` for any
follow-up. For a **deep, authoritative** root-cause verdict, hand the identified build to
**`/gts-issue-analyst`**, the read-only signal-analysis peer.

---

## Hard safety rules (verbatim)

- **NEVER** run `gts-deliver` to create tags, deliver, or reconcile — only `--list` / `--dlist` /
  `--rlist` are permitted, and only the real command is **proposed** for the human.
- **NEVER** run `allow2DeliverIn2Baseline.py` — it commits and pushes an allow-list change.
- **NEVER** put `--noSireCheck` or `--noFFCheck` in a proposed command or recommend bypassing governance.
- **NEVER** push tags or mutate any baseline / release / reconciliation repo.
- **ALWAYS** quote the real output of a read-only check as evidence — never fabricate a PASS.
- If a required input (project, component, tag, SIR, release) is missing, **ask** — never guess.
