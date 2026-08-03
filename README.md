<p align="center">
  <img src="docs/assets/banner.svg" alt="GTS AI SDLC — one AI software-development lifecycle, composed for every GTS system. A 3-tier composition: gts-orchestrator routes each request to the right system; the p7 and t7 orchestrators run the pipeline; eight single-purpose pipeline roles do the work; all draw on 15 common plus system skills. The pipeline runs Plan, Architect, human Gate, RED tests, Develop, Review, Build and PR." width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-Internal%20DBAG-blue.svg" alt="License: Internal DBAG">
  <img src="https://img.shields.io/badge/composition-3--tier-7c5cff.svg" alt="3-tier composition">
  <img src="https://img.shields.io/badge/agents-21-ff7a59.svg" alt="21 agents">
  <img src="https://img.shields.io/badge/systems-P7%20%C2%B7%20T7-1f9e89.svg" alt="Systems: P7 and T7">
  <img src="https://img.shields.io/badge/skills-25-7c5cff.svg" alt="25 skills">
  <img src="https://img.shields.io/badge/surface-VS%20Code%20Copilot-1f9e89.svg" alt="VS Code Copilot Agent mode">
</p>

<p align="center">
  <b>A VS Code-based agentic SDLC</b> — specialist AI agents that run the full development lifecycle across <b>P7</b> and <b>T7</b>.
</p>

<p align="center">
  <a href="https://pages.github.deutsche-boerse.de/dev/gts.ai.sdlc/explorer/">
    <img src="https://img.shields.io/badge/Open%20the%20interactive%20explorer-1f9e89?style=for-the-badge&logo=readthedocs&logoColor=white" alt="Open the interactive SDLC Agent Exploration">
  </a>
</p>

<p align="center">
  ▶ <a href="https://pages.github.deutsche-boerse.de/dev/gts.ai.sdlc/explorer/"><b>GTS AI SDLC · SDLC Agent Exploration</b></a> — click to open in your browser
</p>

<h3 align="center">
  <a href="#where--when-you-use-it">Where &amp; When</a> &nbsp;·&nbsp;
  <a href="#architecture-at-a-glance">Architecture</a> &nbsp;·&nbsp;
  <a href="#the-sdlc-pipeline">The Pipeline</a> &nbsp;·&nbsp;
  <a href="#supported-systems">Systems</a> &nbsp;·&nbsp;
  <a href="#design-principles">Design</a> &nbsp;·&nbsp;
  <a href="#get-started">Get Started</a>
</h3>

<p align="center"><img src="docs/assets/divider.svg" alt="" width="100%"></p>

## Where & when you use it

<p align="center">
  <img src="docs/assets/where-when.svg" alt="Where and when you use GTS AI SDLC — four ways in from VS Code Copilot (Agent mode): describe the work and let gts-orchestrator route it; target a system with /p7-orchestrator or /t7-orchestrator; run one phase on demand such as a planner, reviewer, tester or spec-author; or ask a read-only knowledge query with /t7-sdlc-knowledge. Auto-discovered the moment the repo is open." width="100%">
</p>

Open the repo in VS Code and the whole team is already there — Copilot auto-discovers every
`.github/agents/*.agent.md`, so you run the **whole lifecycle** or call a **single phase** with zero setup.
The four ways in are shown above; you never need to know which orchestrator owns your change.

> **One writer, always gated.** Only the **developer** edits code — every other agent coordinates or reads.
> Nothing reaches a PR until the tester, reviewer and builder gates pass, and a single human gate confirms
> the plan before any code is written.

<p align="center"><img src="docs/assets/divider.svg" alt="" width="100%"></p>

## Architecture at a glance

The framework is a **3-tier composition model**: a generic router on top, one orchestrator per system in
the middle, and single-purpose pipeline agents at the bottom — all drawing on shared **skills**.

<p align="center">
  <img src="docs/assets/architecture.svg" alt="GTS AI SDLC architecture — a 3-tier composition. A developer request passes through gts-prompt-clarifier, then Tier 1 (gts-orchestrator) routes it to the right system; Tier 2 is the p7-orchestrator (linear TDD pipeline) and t7-orchestrator (autonomous Ralph loop); Tier 3 is eight-to-nine single-purpose agents — planner, architect, developer, tester, reviewer, builder, pr-author, spec-author and T7 knowledge — each returning a status code, only the developer writing code; all draw on shared common and system skills." width="100%">
</p>

<p align="center"><img src="docs/assets/divider.svg" alt="" width="100%"></p>

## The SDLC pipeline

Each system binds the same lifecycle to its own agents. Every Tier 3 worker ends its turn with a
**status code**, and the orchestrator routes on it — that status contract is what makes the pipeline
autonomous yet gated.

<p align="center">
  <img src="docs/assets/pipeline.svg" alt="The GTS AI SDLC pipeline, eight phases, each one agent that returns a status code: Plan (planner), Architect (architect: APPROVE, REVISE or BLOCK), Human gate (yes, no or revise), RED tests (tester: RED_READY or NOT_APPLICABLE), Develop (developer: DONE — the only code writer), Review (reviewer: APPROVED or CHANGES_REQUIRED via the code-review-lens brain plus requirement conformance), Build (builder: BUILD_PASS or BUILD_FAIL) and PR (pr-author). P7 runs it as a linear TDD pipeline; T7 as an autonomous Ralph loop." width="100%">
</p>

**Two shapes, one contract.** P7 runs this straight through as a **linear TDD pipeline**; T7 runs it as an
**autonomous Ralph loop** — specs are the source of truth, the plan is disposable, and each iteration
converges one task under tester + builder backpressure.

<p align="center"><img src="docs/assets/divider.svg" alt="" width="100%"></p>

## Supported systems

<p align="center">
  <img src="docs/assets/systems-and-skills.svg" alt="GTS AI SDLC systems and skills — P7 (p7-orchestrator, linear TDD pipeline) with roles planner, architect, developer, tester, reviewer, builder, pr-author and spec-author, and system skills p7-code, p7-code-review, p7-debugging, p7-brainstorming, p7-verification and p7-github; T7 (t7-orchestrator, autonomous Ralph loop) with the same roles plus a read-only knowledge agent, and system skills t7-code, t7-code-review, t7-spec and t7-knowledge-base; a shared skill library grouped into review-and-specs, integrations and SDLC discipline. Totals: 21 agents, 25 skills, 2 systems, 8 pipeline phases." width="100%">
</p>

> **T7 adds a knowledge agent.** `t7-sdlc-knowledge` answers read-only "where / who owns / what changed"
> questions directly — no plan, gate or build cycle.
>
> **Specs are on-demand.** `{system}-sdlc-spec-author` runs *after* planning to produce formal
> **DFS / DTS / SRQ** under `specs/{system}/` — separate from the lightweight plan the planner writes, and
> reusing the shared `spec-authoring` skill so every system follows the same corporate standard.

<p align="center"><img src="docs/assets/divider.svg" alt="" width="100%"></p>

## Design principles

<p align="center">
  <img src="docs/assets/design-principles.svg" alt="Eight GTS AI SDLC design principles, each enforced in the agent definitions: 1 one job per agent (single responsibility); 2 one writer, many gates (only the developer writes code, gated by tester, reviewer and builder after a human gate); 3 retrieve, don't inline (paths and specs fetched live through skills); 4 evidence-grounded work (evidence localisation, discriminating RED tests, cited reviews); 5 classify first, verify fit (NOT_APPLICABLE for non-behavioural changes); 6 skill-first tool access (skills are transport); 7 vendor-neutral, composable skills (compose, don't duplicate); 8 untrusted content is data (OWASP LLM01)." width="100%">
</p>

Not marketing lines — each of these is enforced in the agent and skill definitions themselves, not left to
the model's discretion.

---

## Get started

The framework needs no build step — it *is* the agent and skill definitions. To use it:

1. **Open this repo in VS Code** with GitHub Copilot (Agent mode). Every `.github/agents/*.agent.md` is
   auto-discovered as a callable subagent.
2. **Describe your task in Copilot Chat.** Start broad and let routing take over, or target a system:

   ```
   /gts-orchestrator   Fix the SMP Type-B reason code on cancel in T7
   /p7-orchestrator    Add a validation rule to the pricing-engine request handler
   /t7-sdlc-knowledge  Who owns the Matcher, and where does the order lifecycle live?
   /p7-sdlc-reviewer   Review the diff on this branch
   ```

3. **Confirm the plan at the human gate**, then let the pipeline run its RED → GREEN → review → build →
   PR loop to a reviewed, evidence-linked change.

---

## License

Internal to Deutsche Börse AG — see [`LICENSE.md`](LICENSE.md).
