---
name: gts-build-graph
description: "Read-only build-dependency knowledge for the GTS baseline (EUREX/T7, P7 and other GTS projects). Answers deterministic graph questions with the real build tooling: which components depend on X (reverse dependencies), the correct build order (topological sort), what a component requires (forward dependencies), and the blast radius of a change (what must rebuild). Wraps the project-generic `bquery` engine over `baseline.xml` + `module-info.xml`, documents the Buildfw v1 (module-info.xml) vs v2 (dependencies.txt/cmake) models, and a fallback that parses the dependency files directly when `bquery` is not runnable. KNOWLEDGE, NOT BUILD EXECUTION — it computes/queries the graph and never compiles, never runs a build, never mutates a baseline. Use when scoping a change's impact, resolving build order, or answering 'what depends on this component'."
systems: [all]
user-invocable: false
---

# GTS Build Graph — dependency & build-order queries

Answer **deterministic** build/dependency questions about a GTS baseline using the **real GTS build
tooling**, instead of eyeballing one component manifest at a time. This skill *computes or queries* the
dependency graph; it does **not** build anything — running the build is Jenkins' / the builder's job and
is out of scope.

It answers four questions:

| Question | Meaning |
|---|---|
| **What depends on X?** | **reverse** dependencies — every component that requires X (directly or transitively) |
| **What is the build order?** | a **topological** ordering of a baseline (or a subset) — dependencies before dependents |
| **What does X require?** | **forward** dependencies — everything X needs to build |
| **What does my change impact?** | the **blast radius** — the forward closure of *dependents* that must **rebuild** when X changes |

> **Read-only, always.** Never run a build (`pbuild*`), never mutate the build-number DB (`loaddb`/`calc`),
> never edit `baseline.xml` / `module-info.xml` / `dependencies.txt`. Only the query subcommands below.

---

## 0. The build framework and where the graph lives

GTS baseline components are built by the framework in **`dev/gts.build`**. Two dependency models coexist:

| | **Buildfw v1** — *current default* | **Buildfw v2** — *opt-in* |
|---|---|---|
| Dependency granularity | **component** level | **file** level |
| Declared in | **`module-info.xml`** (+ `pom.xml` for Java/Maven) | **`dependencies.txt`** |
| Engine / build order | **`bquery`** + internal cmake functions | **cmake** manages order and which targets rebuild |
| Activated by | default | `baseline.xml` → `configuration/build/defaults/<buildfw>2</buildfw>` |

So **`bquery` is the v1 engine** and the authoritative answer for the default baseline. For a
**v2-activated** baseline, **cmake owns build order** — see §4. Most components declare **v1**
`module-info.xml`; some also carry a v2 `dependencies.txt` (dual-declared).

**The graph's node set is `baseline.xml`** — the list of `component → tag(version)` for a release
(`<configuration project="EUREX|P7" system="eurex|p7" name="<release>"> … <component name="…"><tag>NNN.NNN.NNN</tag>`).
Obtain the baseline, in order of preference:

1. The **working source area** the engineer already rebased (`baseline.xml` in that directory) — the one
   they will actually build. The CI produces it with `gts-rebase.py -s <system> -r <release> --latest --file=<baseline.xml> --batch --nos3` (the `rebase` tool); you may name that command but need not run it.
2. The **integration repo** (uniform across systems, one folder per release on `master`):
   `github.deutsche-boerse.de/dev/gts.integration.<system>/<release>/baseline.xml`
   (e.g. `gts.integration.eurex/150.006.020/baseline.xml`, `gts.integration.p7/012.003.020/baseline.xml`).
3. The **release repo** at the release git **tag**: `gts.eurex.release` (T7) / `gts.release.p7` (P7), `baseline.xml`.

Fetch it through the **`github`** skill (never a raw ungated call). Always **state which baseline (system +
release) you used** — a dependency answer is only meaningful against a specific baseline.

**Component ↔ repo name.** A component path maps to its git repo by the `gts` prefix with dots:
`common/service/exception` → `gts.common.service.exception`, `eurex/apps/matcher` → `gts.eurex.apps.matcher`.
`bquery` does this via `--github-prefix gts`.

---

## 1. The four modes → real `bquery` subcommands

`bquery` = *"command-line interface to the baseline based integration system"* (installed on dev/build
hosts at `/opt/devenv/bin/bquery`; `bquery` = `bquery3`, the current version). Map each mode to its
subcommand:

| Mode | Command | Returns |
|---|---|---|
| **reverse-deps** ("what depends on X") | `bquery depends -b <baseline.xml> <component> [version]` | components that **require** X |
| **build-order** | `bquery tsort -b <baseline.xml>` | topological order of the baseline (deps first) |
| **forward-deps** ("what X requires") | `bquery requires -b <baseline.xml> <component> [version]` | the recursive tree of what X needs |
| **change-impact / blast radius** | `bquery depends` (dependents) **+** `bquery tsort` to order the rebuild | everything that must rebuild, in build order |

`depends`/`requires` render a **dependency tree** (transitive); the version is optional when `-b <baseline>`
supplies it. `tsort` **requires** `-b <baseline>`.

**Change-impact recipe:** the set that must rebuild when X changes = X's **dependents** (`bquery depends`);
order that set with `bquery tsort` (or a `tsort` restricted to the impacted subset) so the rebuild runs
dependencies-first. Distinguish **direct** dependents (edge to X) from **transitive** ones in the answer.

> **What actually rebuilds — validated against the CI.** Delivering a component recompiles **that component
> *plus* its dependents** — i.e. exactly `bquery depends <changed>` (+ the component itself). Real example: one
> tag delivered into `150.005.025` (`eurex/common/entitlement`) → `bquery depends` returns **20** dependents,
> and the Integration build (`INT-EUREX-150.005.025 #49`, `bquery pbuild … --use-cache`) reported
> **`Components to build: 21/308`** (the 20 + entitlement). So `bquery depends` **predicts** the compile set —
> it is *not* a loose upper bound. `--use-cache` can only *trim* it (dependents already precompiled at the same
> build number are skipped), so the CI count is **≤** the closure, never more.
>
> **The downstream CMQA/SCM migration does *not* recompile.** `GTS-Migration` (dacci) runs `OneStepMigration.pl`
> + `prebuild.py … push/pushdev`, **redistributing prebuilt artifacts** (e.g. `Processed: 127/308`, cumulative
> for the release) with **zero** `cmake`/`make`. So distinguish **compiled** (INT, per delivery = the dependents
> closure) from **migrated** (CMQA, cumulative prebuild set): compilation happens **once** at the INT build, and
> everything downstream reuses those prebuilds.

---

## 2. `bquery` command anatomy (the real CLI)

```sh
# reverse dependencies of a component in a baseline (what must rebuild if it changes)
GITHUB_USERNAME=<user> GITHUB_TOKEN=<token> \
  bquery depends -b /path/to/baseline.xml common/service/exception

# whole-baseline build order
bquery tsort -b /path/to/baseline.xml

# forward dependency tree of a component
bquery requires -b /path/to/baseline.xml eurex/cilmsg
```

| Option | Meaning |
|---|---|
| `-b FILE` / `--baseline=FILE` | The baseline to analyse. **Required for `tsort`**; `depends`/`requires` default to `./baseline.xml` in the cwd, so always pass `-b` explicitly. |
| `GITHUB_USERNAME` / `GITHUB_TOKEN` (env) or `--username` / `--password` | Source-control access — `bquery` reads each component's `module-info.xml` from its repo. |
| `--github-prefix gts` | Component → repo mapping (`eurex/apps/matcher` → `gts.eurex.apps.matcher`). Also `--github-url`, `--github-org` — all three **default from the baseline's `<build><defaults>`**, so they are usually not needed when `-b <baseline>` is supplied. |
| `-r` / `--refresh-cache`, `--dir-cache=DIR` | Dependency cache (default `/local/<user>/.bquery3`); a cold cache fetches every component's `module-info.xml`, so the first `tsort`/`depends` over a full baseline can be slow. |

**Read-only subcommands only:** `depends`, `requires`, `tsort`. **Never** run `pbuild` / `pbuild-generic`
/ `pbuild-check` / `load-*` / `distcc-*` (these **build**), nor `calc` / `loaddb` (these compute/mutate
build numbers). None of the three query subcommands mutate anything. The Integration build itself
(`INT-EUREX-<release>` / `INT-P7-<release>`, both `BUILDFW Version: 1`) runs `bquery pbuild --command
gts-build-precompiled --use-cache -b baseline.xml` to order **and build** — recognise it in a build log,
but this agent runs only the read-only queries, which interrogate the **same** graph.

> **Gotcha — `bquery help <subcommand>` is broken** (a Python-3 regression, `dict.has_key`, in the toolkit).
> Do **not** rely on it for argument help; the arguments are exactly as documented above.

---

## 3. Output contract

```markdown
## Dependency Answer: <reverse-deps | build-order | forward-deps | change-impact>

### Query
- Target: <component/file>
- Baseline: <system> <release>   (e.g. eurex 150.006.020)
- Mode: reverse-deps | build-order | forward-deps | impact

### Result
| Component | Relationship | Direct / Transitive |
|-----------|--------------|---------------------|
| <component> | requires-X / required-by-X | direct / transitive |

### Build order (if requested / for an impact rebuild)
1. <first to build>
2. …

### Source
- Tool: `bquery <subcommand> <args>`   (or: parsed `module-info.xml` / `dependencies.txt` — fallback)
- Baseline: <system>/<release> from <working area | gts.integration.<sys> | release repo>
- Buildfw: v1 (module-info.xml) | v2 (dependencies.txt / cmake-managed)
```

Rules: always name the **tool/data** and the **resolved baseline (system + release)**; separate **direct**
from **transitive**; for **impact**, return the **forward closure** of dependents that must rebuild; never
run a build.

---

## 4. Buildfw v1 vs v2 — pick the right authority

- **Detect v2**: the baseline's top-level `<build><defaults>` block carries `<buildfw>2</buildfw>` (that
  block also holds `<toolchain>`, `<vcs>`, `<github-url>` / `<github-org>` / `<github-prefix>`, `<cmakeVersion>`),
  and/or the component has a `dependencies.txt`. When `<buildfw>` is **absent**, the baseline is **v1** (the
  default — confirmed on real EUREX/P7 baselines, which have `<build><defaults>` but no `<buildfw>`).
- **v1** → `bquery` over `module-info.xml` is authoritative for reverse-deps, forward-deps and `tsort`.
- **v2** → the graph is **file-level** and **cmake manages build order and which targets (re)build**. Do
  **not** claim `bquery tsort` as the v2 build order. For v2, report the `dependencies.txt`-level facts you
  can read and state that the authoritative order is produced by cmake from the generated top-level
  `CMakeLists.txt` (via `prepSrcArea.py --buildfw=2 --generatebuildfiles …` then `cmake`). Be explicit about
  which model the answer came from.

---

## 5. Fallback — when `bquery` is not runnable

If the toolkit isn't installed, the environment can't reach the component repos, or the agent has no
`execute`, **do not guess** — reconstruct the same facts by **reading the dependency files**, delegating
retrieval to the **`t7-code`** skill (T7 components, via `t7codebase`) and the **`github`** skill (the
baseline in `gts.integration.*` / the release repo, and any component repo):

- **v1 — `module-info.xml`** declares a component's **forward** dependencies:
  ```xml
  <component>
    <dependencies>
      <dependency name="common/global"><function name="add_prebuilt_module"/></dependency>
      <dependency name="${GTS_BASELINE_SYSTEM}/common/shell"><function name="add_prebuilt_module"/></dependency>
      …
    </dependencies>
  </component>
  ```
  Each `<dependency name="…">` is a component path. **`${GTS_BASELINE_SYSTEM}`** resolves to the baseline's
  `system` (`eurex` / `p7`) — the same manifest serves both systems. Reading one `module-info.xml` gives
  **forward** deps of that component.
- **Reverse deps without `bquery`** require scanning **every** component's `module-info.xml` in the baseline
  for one that names the target — expensive and easy to get incomplete. Say so, prefer `bquery depends`, and
  scope the manual scan (e.g. to a component family) when a full scan isn't feasible.
- **v2 — `dependencies.txt`** is a per-component directive file (source/lib dirs and file-level inputs), not
  a component list; for v2 order, defer to cmake (§4).

State clearly in **Source** that the answer came from parsed files rather than `bquery`.

---

## 6. Cross-system blast radius (why this is a common, not a T7-only, skill)

The graph **spans systems**. **Many** low-level `common/*` and `thirdparty/*` components appear — with the
**same tag** — in **both** the EUREX and P7 baselines (e.g. `common/service/exception` `078.000.140`,
`thirdparty/boost`, the `build` component), and dependency declarations are written **system-parametric**
via `${GTS_BASELINE_SYSTEM}`. Consequences for an impact answer:

- Changing a **shared** component has **cross-system reach** — its dependents (and any reconciliation) can
  span **multiple projects' baselines** (EUREX, P7, …), not just one. Flag this, and report the **union** of
  `bquery depends` run against **each** affected system's baseline.
- A **system-specific** component (`eurex/apps/*`, `p7/*`) affects only its own system's baseline.
- **The `common/` prefix does *not* imply cross-system.** Some `common/*` components exist in only one
  system — e.g. `common/perfmon` is in EUREX but **not** P7 (P7 has a different `common/intmsg/model/perfmon`).
  **Verify** the component is actually present (same tag) in the other baseline before claiming cross-system
  reach; don't infer it from the name.

---

## 7. Anti-patterns

- ❌ Running a build (`bquery pbuild*`, `make`, `cmake --build`) or mutating a baseline / manifest. This skill is **query-only**.
- ❌ Answering without naming the **resolved baseline** (system + release) — deps are baseline-specific.
- ❌ Reading a single `component.json` for `depends_on`/`used_by`. **`component.json` does not exist** in GTS
  components; the real forward-dep file is **`module-info.xml`**, and **reverse** deps (`used_by`) are not in
  any single file — they are **computed** by `bquery depends` across the baseline.
- ❌ Presenting `bquery tsort` as the build order for a **v2** baseline (cmake owns v2 order).
- ❌ Conflating **direct** and **transitive** dependents, or the component **tag** (`NNN.NNN.NNN`) with the **release** number.
