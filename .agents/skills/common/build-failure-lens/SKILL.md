---
name: build-failure-lens
description: "Use when: a Jenkins / CI build has failed or gone UNSTABLE, or you need a job/build status, and you want the root cause, a false-positive scan, or build/job context. Covers Jenkins build-failure analysis and Q&A via the jenkins-lens MCP server — given a build URL, a job + build number, or a pasted console log, it returns the likely root cause, quoted log evidence, a per-substep false-positive verdict, and job/build metadata. Agents delegate build analysis here and never call the jenkins-lens MCP tools directly. This is read-only build analysis — NOT the local compile step (that is the builder's own `execute`) and NOT code review (that is code-review-lens)."
systems: [all]
tools: [jenkins-lens/analyze_build, jenkins-lens/diagnose_log, jenkins-lens/score_build, jenkins-lens/list_jobs, jenkins-lens/job_status, jenkins-lens/build_info, jenkins-lens/ask]
user-invocable: false
---

# Build-Failure Lens — the CI build-failure brain

`jenkins-lens` is a read-only diagnosis engine for **Jenkins / CI builds**. Given a failed or
`UNSTABLE` build it fetches the console log, localises the failing substep, and returns the **likely
root cause** with **quoted log evidence**, a **false-positive scan** (is the red real, or noise?),
and build/job metadata. It is **the brain for CI build-failure analysis** — an agent **delegates**
this concern to the lens through this skill and **never** calls the `jenkins-lens` MCP tools directly
outside this skill.

## Scope — what this skill is, and is NOT

This skill covers **already-run CI/Jenkins builds only** — diagnosis and false-positive triage. The
following are **not** owned by this skill:

- The **local compile** of just-written code — that stays the builder's own `execute` step (run the
  build command, capture the error output). Use this skill when the failure is a **Jenkins/CI** build
  (a build URL, a `job` + `build_number`, or a pasted Jenkins console log), or to explain whether a
  red CI build is a real defect or a false positive.
- **Code review** (correctness / security / quality / guideline) — that is `code-review-lens`
  (`codereviewer-lens`). A compiler/linker error is a build concern; a code smell is a review concern.
- **Any write to Jenkins** — this skill never triggers, retries, cancels, or mutates a build. It is
  strictly read-only diagnosis.

## What each tool does

| Need | Tool | Notes |
|---|---|---|
| Root cause of a failed / UNSTABLE build | `analyze_build(build_url \| job + build_number, jenkins_instance?)` | **primary** — returns cause, severity, quoted log evidence, suggested next step |
| Diagnose a **pasted** console log (no Jenkins access) | `diagnose_log(log)` | when you already hold the console text |
| Is the red **real or a false positive?** | `score_build(log \| build_url \| job + build_number, jenkins_instance?)` | deterministic per-substep table: verdict, false-positive %, certainty, class — run **before** hand-writing a false-positive review |
| Browse jobs / a view + last status | `list_jobs(view?, only_problems?, jenkins_instance?)` | e.g. `view="EUREX-open-official"`, `only_problems=true` |
| One job's health / history / pass-rate | `job_status(job, jenkins_instance?)` | current state, last success/failure, recent history |
| Build metadata (trigger, params, SCM, culprits) | `build_info(job, build_number, jenkins_instance?)` | for *what/who/when*; for *why-it-failed* use `analyze_build` |
| Free-text follow-up on the last analysed build | `ask(question)` | reuses the analyzer session context |

- **`jenkins_instance`** is one of `gtsci` \| `dacci` — pass it when known; omit to let the lens
  resolve it from the build URL / job.
- Prefer **`analyze_build`** with a `build_url` (or `job` + `build_number`) when Jenkins is reachable;
  fall back to **`diagnose_log`** when you only have pasted console text.

## Choosing the tool (by trigger)

- **"Why did this build fail?" / a failed build URL / job + number** → `analyze_build`. Follow with
  `score_build` when you need to state whether the failure is a **true defect** or a **false
  positive / infra flake**.
- **A pasted Jenkins console log** → `diagnose_log` (and `score_build(log=...)` for the FP verdict).
- **"Is this red a real failure?" / triaging noisy substeps** → `score_build` (deterministic, no API
  key) — cite its per-substep verdict and false-positive %.
- **"What's the state of job X / this view?"** → `job_status(job)` or `list_jobs(view)`.
- **"What triggered / changed in this build?"** → `build_info(job, build_number)`.

## Reading the lens result

`analyze_build` / `diagnose_log` return the **root cause**, a **severity**, **quoted log evidence**,
and a **suggested next step**. `score_build` returns a **per-substep table** (`verdict`,
`false-positive %`, `certainty`, `class`). Always:

1. **Report the cause with its quoted log evidence** — never paraphrase away the evidence line.
2. **State the false-positive disposition** from `score_build` (real defect vs false positive / infra
   / flake) — this is the deciding signal, not the raw red/green.
3. **Attribute** the failing substep and, when available from `build_info`, the SCM change / culprit.

## Turning the lens result into your report

- If the cause is a **real code/build defect**, surface it as the actionable failure — cause + the
  exact failing step + the suggested fix direction — so the developer can act.
- If the failure is a **false positive / infra / environment** issue (per `score_build`), say so
  explicitly and do **not** attribute it to the change under test; point at the infra/owner instead.
- Keep the diagnosis **grounded in the lens output** — do not invent a root cause the lens did not
  evidence.

## Fail-safe (lens unavailable)

If the `jenkins-lens` MCP server is **unreachable**, do **not** guess a root cause from memory.
Report that the CI failure **could not be diagnosed — jenkins-lens unavailable**, hand back any raw
console output you already have, and escalate. No diagnosis ⇒ no verdict on whether the red is real.

## Constraints

- DELEGATE here — never call `jenkins-lens` MCP tools directly from an agent body.
- **Read-only**: never trigger, retry, cancel, or otherwise mutate a Jenkins build or job.
- This skill is **CI build-failure diagnosis only** — not the local compile (builder `execute`), not
  code review (`code-review-lens`).
- Cite the lens's quoted **log evidence** and, for a false-positive claim, the `score_build` verdict.
- Do not expose credentials or tokens that appear in a console log.
