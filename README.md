<p align="center">
  <img src="docs/assets/banner.svg" alt="GTS AI SDLC — one AI software-development lifecycle, composed for every GTS system. A 3-tier composition: gts-orchestrator routes each request to the right system; the p7 and t7 orchestrators run the pipeline; eight single-purpose pipeline roles plus a per-system read-only knowledge agent do the work; all draw on 22 common plus system skills, with two read-only cross-system peers — gts-issue-analyst and gts-delivery — alongside. The pipeline runs Plan, Architect, human Gate, RED tests, Develop, Review, Build and PR, then a human-run Deliver." width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-Internal%20DBAG-blue.svg" alt="License: Internal DBAG">
  <img src="https://img.shields.io/badge/composition-3--tier-7c5cff.svg" alt="3-tier composition">
  <img src="https://img.shields.io/badge/agents-24-ff7a59.svg" alt="24 agents">
  <img src="https://img.shields.io/badge/systems-P7%20%C2%B7%20T7-1f9e89.svg" alt="Systems: P7 and T7">
  <img src="https://img.shields.io/badge/skills-34-7c5cff.svg" alt="34 skills">
  <img src="https://img.shields.io/badge/surface-VS%20Code%20Copilot-1f9e89.svg" alt="VS Code Copilot Agent mode">
</p>

<p align="center">
  <b>A VS Code-based agentic SDLC</b> — specialist AI agents that run the full development lifecycle across <b>P7</b> and <b>T7</b>.
</p>

<p align="center">
  <a href="https://pages.github.deutsche-boerse.de/dev/gts.ai.sdlc/explorer/"><img src="docs/assets/btn-explorer.svg" alt="Interactive Agent Explorer" width="30%"></a>
  &nbsp;
  <a href="https://pages.github.deutsche-boerse.de/dev/gts.ai.sdlc/explorer/#setup"><img src="docs/assets/btn-setup.svg" alt="VS Code Set Up Guide" width="30%"></a>
  &nbsp;
  <a href="https://pages.github.deutsche-boerse.de/dev/gts.ai.sdlc/explorer/#evals"><img src="docs/assets/btn-evals.svg" alt="Harness Evals" width="30%"></a>
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
  <img src="docs/assets/where-when.svg" alt="Where and when you use GTS AI SDLC — six ways in from VS Code Copilot (Agent mode): describe the work and let gts-orchestrator route it; target a system with /p7-orchestrator or /t7-orchestrator; run one phase on demand such as a planner, reviewer, tester or spec-author; ask a read-only knowledge query with /t7-sdlc-knowledge or /p7-sdlc-knowledge; diagnose an issue with /gts-issue-analyst — a red build, a Sonar finding, a security alert, a GitHub issue or a SIR — for a read-only root-cause verdict; or deliver a merged change with /gts-delivery, which proposes the gts-deliver command and watches the Integration build. Auto-discovered the moment the repo is open." width="100%">
</p>

Open the repo in VS Code and the whole team is already there — Copilot auto-discovers every
`.github/agents/*.agent.md`, so you run the **whole lifecycle** or call a **single phase** with zero setup.
The six ways in are shown above; you never need to know which orchestrator owns your change.

> **One writer, always gated.** Only the **developer** edits code — every other agent coordinates or reads.
> Nothing reaches a PR until the tester, reviewer and builder gates pass, and a single human gate confirms
> the plan before any code is written.

<p align="center"><img src="docs/assets/divider.svg" alt="" width="100%"></p>

## Architecture at a glance

The framework is a **3-tier composition model**: a generic router on top, one orchestrator per system in
the middle, and single-purpose pipeline agents at the bottom — each system now with its own read-only
knowledge agent — all drawing on shared **skills**. Alongside them sit two read-only cross-system peers:
**`gts-issue-analyst`**, which runs root-cause analysis on engineering issues and feeds fixes back into the
pipeline, and **`gts-delivery`**, which proposes the terminal delivery of a merged change into an integration baseline.

<p align="center">
  <img src="docs/assets/architecture.svg" alt="GTS AI SDLC architecture — a left-hand rail marks the tiers. A request flows through gts-prompt-clarifier to Tier 1 (gts-orchestrator, the router), Tier 2 (p7-orchestrator — linear TDD pipeline; t7-orchestrator — autonomous Ralph loop) and Tier 3 (eight pipeline workers: planner, architect, developer — the only code writer — tester, reviewer, builder, pr-author, spec-author), which connect down to the SKILLS block; a narrow read-only rail holds T7/P7 Knowledge, gts-issue-analyst (root-cause) and gts-delivery (propose, human-run). Each agent carries a distinct role icon. Two inventories follow: a SKILLS grid (common + T7/P7) and an MCP SERVERS grid — codereviewer-lens, jenkins-lens, sonarqube-lens, github, devops_jira, confluence, t7codebase, t7spec, t7dbcopy, eurex_refdata and p7spec." width="100%">
</p>

<p align="center"><img src="docs/assets/divider.svg" alt="" width="100%"></p>

## The SDLC pipeline

Each system binds the same lifecycle to its own agents. Every Tier 3 worker ends its turn with a
**status code**, and the orchestrator routes on it — that status contract is what makes the pipeline
autonomous yet gated.

<p align="center">
  <img src="docs/assets/pipeline.svg" alt="The GTS AI SDLC pipeline, eight phases, each one agent that returns a status code: Plan (planner), Architect (architect: APPROVE, REVISE or BLOCK), Human gate (yes, no or revise), RED tests (tester: RED_READY or NOT_APPLICABLE), Develop (developer: DONE — the only code writer), Review (reviewer: APPROVED or CHANGES_REQUIRED via the code-review-lens brain plus requirement conformance), Build (builder: BUILD_PASS or BUILD_FAIL) and PR (pr-author) — then a terminal, cross-system, human-run Deliver step where gts-delivery proposes the gts-deliver command into an integration baseline and watches the Integration build. P7 runs the eight phases as a linear TDD pipeline; T7 as an autonomous Ralph loop." width="100%">
</p>

**Two shapes, one contract.** P7 runs this straight through as a **linear TDD pipeline**; T7 runs it as an
**autonomous Ralph loop** — specs are the source of truth, the plan is disposable, and each iteration
converges one task under tester + builder backpressure.

<p align="center"><img src="docs/assets/divider.svg" alt="" width="100%"></p>

## Supported systems

<p align="center">
  <img src="docs/assets/systems-and-skills.svg" alt="GTS AI SDLC systems and skills — P7 (p7-orchestrator, linear TDD pipeline) with roles planner, architect, developer, tester, reviewer, builder, pr-author and spec-author plus a read-only knowledge agent, and seven system skills p7-code, p7-code-review, p7-debugging, p7-brainstorming, p7-verification, p7-github and p7-spec; T7 (t7-orchestrator, autonomous Ralph loop) with the same roles and knowledge agent, and five system skills t7-code, t7-code-review, t7-spec, t7-knowledge-base and t7-refdata; a shared skill library grouped into review-and-specs, integrations, SDLC discipline and delivery-and-build, plus issue-analysis skills for the read-only gts-issue-analyst and gts-delivery peers. Totals: 24 agents, 34 skills (22 common plus 12 system), 2 systems, 8 pipeline phases." width="100%">
</p>

> **Every system has a knowledge agent.** `p7-sdlc-knowledge` and `t7-sdlc-knowledge` answer read-only
> "where / who owns / what changed" questions directly — no plan, gate or build cycle.
>
> **Issues get a read-only analyst.** `gts-issue-analyst` — a cross-system peer of the knowledge agents —
> runs root-cause analysis on a red Jenkins build, a SonarQube finding, a Dependabot/CodeQL/secret alert, a
> GitHub issue or a Jira SIR (selecting jenkins-lens / sonarqube-lens / GitHub), grounds it in the code, and
> hands any fix back to the pipeline. It **diagnoses, never implements**.
>
> **Delivery is proposed, never auto-run.** `gts-delivery` — the other cross-system peer — is the terminal
> **deliver** step after Build and PR: it runs read-only readiness gates and **proposes** the exact
> `gts-deliver` command that ships a merged change into an integration baseline (the human runs it), then
> watches the resulting Integration build. It **proposes, never executes**.
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

<table align="center">
  <tr>
    <td align="center" width="360">
      <a href="https://pages.github.deutsche-boerse.de/dev/gts.ai.sdlc/explorer/">
        <img src="https://img.shields.io/badge/Open%20the%20interactive%20explorer-1f9e89?style=for-the-badge&logo=readthedocs&logoColor=white" alt="Open the interactive explorer">
      </a>
      <br><sub>Browse every agent, skill &amp; guided example in your browser.</sub>
    </td>
    <td align="center" width="360">
      <a href="https://pages.github.deutsche-boerse.de/dev/gts.ai.sdlc/explorer/#setup">
        <img src="https://img.shields.io/badge/Get%20Started%20with%20VS%20Code%20Set%20Up-2b5cb8?style=for-the-badge&logo=visualstudiocode&logoColor=white" alt="Get Started with VS Code Set Up">
      </a>
      <br><sub>Jump straight to the VS Code setup steps.</sub>
    </td>
  </tr>
</table>

The framework needs no build step — it *is* the agent and skill definitions. To use it:

1. **Open this repo in VS Code** with GitHub Copilot (Agent mode). Every `.github/agents/*.agent.md` is
   auto-discovered as a callable subagent.
2. **Describe your task in Copilot Chat.** Start broad and let routing take over, or target a system:

   ```
   /gts-orchestrator   Fix the SMP Type-B reason code on cancel in T7
   /p7-orchestrator    Add a validation rule to the pricing-engine request handler
   /t7-sdlc-knowledge  Who owns the Matcher, and where does the order lifecycle live?
   /gts-delivery       Deliver eurex tag T7-1234 into the 15.0 integration baseline
   /p7-sdlc-reviewer   Review the diff on this branch
   ```

3. **Confirm the plan at the human gate**, then let the pipeline run its RED → GREEN → review → build →
   PR loop to a reviewed, evidence-linked change.

---

## Feedback & bug reports

Hit a bug in an agent, or have an idea? Reporting takes about a minute — and the most useful bug report
carries the **whole conversation**. The full steps and issue forms live in the
**[feedback repo](https://github.deutsche-boerse.de/dev/gts.ai.sdlc-feedback)**.

<p align="center">
  <a href="https://github.deutsche-boerse.de/dev/gts.ai.sdlc-feedback">
    <img src="docs/assets/how-to-report.svg" alt="How to report a bug or send feedback in three steps: 1 Capture the chat — for a bug, export the conversation via the VS Code Command Palette then Chat: Export Chat to get a verbatim transcript file; 2 Open a ticket — run /gts-feedback in the chat, or open a New issue and pick a form, in dev/gts.ai.sdlc-feedback; 3 Attach and submit — attach the exported chat, redact secrets and submit. Only for the AI SDLC tooling; product bugs in T7/P7 code go to Jira/SIRs, not here." width="100%">
  </a>
</p>

<p align="center">
  <a href="https://github.deutsche-boerse.de/dev/gts.ai.sdlc-feedback/issues/new/choose">
    <img src="https://img.shields.io/badge/Report%20a%20bug%20or%20request%20a%20feature-1f9e89?style=for-the-badge&logo=github&logoColor=white" alt="Report a bug or request a feature">
  </a>
</p>

---

## License

Internal to Deutsche Börse AG — see [`LICENSE.md`](LICENSE.md).
