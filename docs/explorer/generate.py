#!/usr/bin/env python3
"""Generate a self-contained interactive Agent Explorer (docs/explorer/index.html)
from the real agent frontmatter in .github/agents/*.agent.md.

Run:  python3 docs/explorer/generate.py
No dependencies; output is a single static HTML file (works via file:// and GitHub Pages).
"""
import glob, json, os, re, textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
AGENT_DIR = os.path.join(ROOT, ".github", "agents")

BUILTIN_TOOLS = {"read", "edit", "search", "execute", "agent", "todo"}
STATUS_STOP = {"DO", "NOT", "MUST", "ALWAYS", "NEVER", "AND", "OR", "THE", "DFS", "DTS",
               "SRQ", "SIR", "TDD", "MCP", "PR", "RED", "GREEN", "OWASP", "JQL", "JSON",
               "WIP", "URL", "API", "P7", "T7", "GTS", "VET", "QA", "CM", "HTTP", "YAML"}

ROLE_ORDER = {"orchestrator": 0, "planner": 1, "architect": 2, "spec-author": 3, "tester": 4,
              "developer": 5, "reviewer": 6, "builder": 7, "pr-author": 8, "knowledge": 9,
              "analyst": 10, "delivery": 11, "feedback": 12}
PIPELINE = ["Plan", "Architect", "Spec", "Test", "Develop", "Review", "Build", "PR"]
ROLE_PHASE = {"planner": 0, "architect": 1, "spec-author": 2, "tester": 3,
              "developer": 4, "reviewer": 5, "builder": 6, "pr-author": 7}
PHASE_LABEL = {"planner": "planning", "architect": "the architecture-review gate",
               "spec-author": "spec authoring (on demand)", "tester": "the RED/GREEN test phase",
               "developer": "the develop phase", "reviewer": "review", "builder": "the build gate",
               "pr-author": "PR authoring", "knowledge": "knowledge queries"}

SYSTEMS = {
    "p7": {"label": "P7", "name": "Pricing & Risk", "fill": "#E3ECFB", "ink": "#3F6FB5"},
    "t7": {"label": "T7", "name": "Trading System", "fill": "#DBF0EE", "ink": "#2E8E84"},
    "generic": {"label": "Generic", "name": "All systems", "fill": "#ECE7FA", "ink": "#6E5BB8"},
}
GROUP_LABEL = {"generic": "Generic · routing & signal analysis",
               "p7": "P7 · Pricing & Risk Management", "t7": "T7 · Trading System"}
GROUP_ORDER = {"generic": 0, "p7": 1, "t7": 2}

OBJECTIVE = {
    "router": "Send the request to the correct system orchestrator so the right pipeline runs.",
    "clarifier": "Turn an ambiguous request into a precise, enriched instruction before any agent acts.",
    "orchestrator": "Drive the whole SDLC pipeline to a reviewed, shipped change — delegating every phase, coding nothing itself.",
    "planner": "Produce a grounded, evidence-located plan with tasks and acceptance criteria.",
    "architect": "Validate the plan against architecture and gate it — approve, revise or block.",
    "spec-author": "Turn an approved plan into a governance-grade DFS / DTS / SRQ.",
    "tester": "Write a discriminating failing test (RED), then verify GREEN — proving the change.",
    "developer": "Implement the minimal code that turns the failing tests green, following the plan.",
    "reviewer": "Judge the change for correctness, security, patterns and requirement-conformance.",
    "builder": "Compile the affected components in dependency order and report pass or fail.",
    "pr-author": "Package the change into a clean, ticket-linked pull request.",
    "knowledge": "Answer read-only questions about the codebase, specs, ownership and terminology.",
    "analyst": "Diagnose an engineering signal — a red build, a Sonar finding, a security alert, an issue or a SIR — to a grounded root-cause verdict; recommend the next step, never implement.",
    "delivery": "Get a merged, reviewed change safely into an integration baseline — run the readiness gates, propose the exact delivery command for you to run, then watch the integration build.",
    "feedback": "Turn a problem you hit with the agents into a filed ticket — conversation captured, secrets redacted, duplicates checked.",
}

# Real, grounded scenarios threaded through the invocation examples.
# T7 uses actual SIRs from the study corpus; P7 uses realistic pricing-engine tasks.
SCEN = {
    "t7": [
        ("T7-574620", "reject a TradingActionRequest from a SpAProvider user without the QUALIFIED_BACKOFFICE_USER role"),
        ("T7-574466", "exclude volume-only trades from the VWAP settlement-price waterfall"),
        ("T7-502218", "fix the Pope deadlock crash by reverting BatchDelete() to Delete()"),
    ],
    "p7": [
        ("", "reject negative bid-ask spreads in the pricing-engine request handler"),
        ("", "add the missing risk-limit check that lets over-limit quotes through in middleware"),
    ],
    "generic": [
        ("T7-574620", "reject unauthorised TradingActionRequests in T7"),
        ("", "add a validation rule to the P7 pricing engine"),
    ],
}

# 'How to use it' guide: the SDLC journey as stages (sub-tabs), each with boxed,
# categorised example asks tagged by user persona. Every example is an actual
# prompt a user would type, and shows how /gts-orchestrator delegates. Grounded
# in real SIRs from the T7 study corpus (crashes, defects, protocol/field fixes,
# performance, security, spec work and ops incidents).
# ---------------------------------------------------------------------------
# Worked examples for "Prompting 101". One per KIND of task, alternating T7 and
# P7, ordered as a lifecycle: analyse -> understand -> plan -> specify ->
# implement -> review -> deliver. Every example is a job the agent suite can
# genuinely do today, grounded in a real SIR, build, commit, PR or spec — no
# aspirational capabilities. Keep each one SHORT: the point is to teach the
# four-block shape, not to ship a 30-line prompt. Aim for GOAL 1-2 lines,
# CONTEXT 4-5 labelled rows, CONSTRAINTS 2-3, DONE LOOKS LIKE 2-3.
# `route` names the specialist only; the renderer prefixes gts-orchestrator.
# `code` is injected raw into innerHTML, so it must contain no <, > or &.
WORKS = [
    {
        "sys": "T7", "tag": "Build failure",
        "title": "Is this night build a real regression, or noise?",
        "route": "gts-issue-analyst",
        "code": """GOAL
  Is this build failure a real regression or CI noise? Name the owner.

CONTEXT
  Build : INT-EUREX-150.005.031-NIGHT-STEST #12 on gtsci, UNSTABLE
  Odd   : ran 2m 54s against a 1h 04m estimate, so it aborted early
  Green : the sibling job on 150.005.030 passed the same night

CONSTRAINTS
  Read-only - no re-run, no Jira write, no PR. Quote the log lines you
  rely on. If they do not settle it, say UNKNOWN.

DONE LOOKS LIKE
  Verdict first, then the failing stage, the quoted evidence, the owning
  component, and one next step.""",
    },
    {
        "sys": "T7", "tag": "Incident",
        "title": "Why did the production roll-over overrun?",
        "route": "gts-issue-analyst",
        "code": """GOAL
  Explain what drove the roll-over duration on this date, and where the
  realistic savings are.

CONTEXT
  Run     : db=prod, mode STANDARD, business date 2026-08-14, all markets
  Impact  : critical path 178 steps / 09:11:54 - too close to market open
  Top two : wait_to_start_rollover 02:14:28,
            get_session_map_file_SX101_EUREX 01:28:08
  Ruled out : the RDS bridge step takes 00:00:54, so the hand-off is fine

CONSTRAINTS
  Read-only - trigger nothing, change no schedule. Tag every step WAIT or
  WORK; do not sell me a wait as an optimisation target.

DONE LOOKS LIKE
  Top five contributors with durations, each tagged WAIT or WORK, then the
  two changes that would actually shorten the run and what each saves.""",
    },
    {
        "sys": "T7", "tag": "Jira SIR",
        "title": "Root cause straight out of a Jira SIR",
        "route": "gts-issue-analyst",
        "code": """GOAL
  Give me symptom, root cause and remediation for this SIR.

CONTEXT
  SIR     : T7-563473 "OPM/GW - Race condition with BrcSubscriptions and
            SessionLogins", Gateway / OPM, baseline 150.005.025
  Symptom : OPM sometimes gets a PerfBrcSubscription before the matching
            SessionLogin, then writes zero into BrcSubscription.SessionID
  Fix     : shipped in commit bcf927d6 of dev/gts.eurex.gateway.common

CONSTRAINTS
  Jira and GitHub read-only - no comment, no transition, no PR. Do not
  restate the ticket: explain why the ordering can invert at all.

DONE LOOKS LIKE
  SYMPTOM, ROOT CAUSE, FIX AS SHIPPED, RESIDUAL RISK - four short
  sections, with anything you could not verify in the code flagged.""",
    },
    {
        "sys": "T7", "tag": "Sonar finding",
        "title": "True or false positive, with a probability",
        "route": "gts-issue-analyst",
        "code": """GOAL
  Adjudicate this Sonar finding as true or false positive, with a
  probability, and propose the fix.

CONTEXT
  Finding : paste the real Sonar issue URL - the agent needs the key
  SIR     : T7-570497 "Analyse sonar issues in gateway team code basis",
            10 pd estimated, components EDC / Gateway / LDS / TFH
  Why     : 10 pd is too much if most of the backlog is noise

CONSTRAINTS
  Read-only on Sonar - mark nothing false-positive, change no severity,
  open no PR. Ground the verdict in the source file, not the rule text.

DONE LOOKS LIKE
  Verdict and probability first, then rule, file:line, why it fires, and
  either the fix as text or the FP justification a human would paste.""",
    },
    {
        "sys": "P7", "tag": "Crash SIR",
        "title": "Root cause of a crash, down to file and function",
        "route": "gts-issue-analyst",
        "code": """GOAL
  Root-cause this crash SIR, down to file and function.

CONTEXT
  SIR      : P7-3742 "PricingEngine crash (std::out_of_range) during vola
             fitting on LEPO instruments with no put partner", High
  Symptom  : the exception escapes a boost::asio worker thread, so the
             process dies instead of skipping the instrument
  My hunch : LEPOs are call-only, so the put id keeps its sentinel value
             and the lookup on it throws

CONSTRAINTS
  Jira and GitHub read-only - no transition, no comment, no PR. Confirm or
  refute my hunch from the source; if I am wrong, say so.

DONE LOOKS LIKE
  The throwing call at file:line, the call chain to it, why the sibling
  accessor does not crash, and the smallest safe fix as a proposal.""",
    },
    {
        "sys": "P7", "tag": "Ask & understand",
        "title": "How does P7 decide a vola surface may be published?",
        "route": "p7-sdlc-knowledge",
        "code": """GOAL
  Explain how P7 decides a fitted vola surface may be published, and
  where that gate is implemented.

CONTEXT
  Specs   : DFS10155 (Implied Volatility), DFS11120 (Black76 fitting),
            INR10010 for the functional picture
  Trigger : SIR P7-3709, a surface send blocked by Bid/Ask violations -
            I want the designed behaviour, not that defect
  I know  : the flow is PricingEngine to middleware to frontend. I do not
            know which layer owns the veto.

CONSTRAINTS
  Read-only question - no plan, no code change, no Jira, no PR. Where the
  spec and the code disagree, say so and quote both.

DONE LOOKS LIKE
  A short prose answer, the spec sections by document and number, the
  file:line implementing the gate, and what an operator sees.""",
    },
    {
        "sys": "T7", "tag": "Code trace",
        "title": "Trace a behaviour through the code to file:line",
        "route": "t7-sdlc-developer",
        "code": """GOAL
  Trace how a broadcast subscription reaches perfmondb.BrcSubscription,
  and show every place SessionID is set on that path.

CONTEXT
  Repo   : dev/gts.eurex.gateway.common
  Anchor : T7-563473 introduced BrcSubscriptionStore(ConnectionID,
           SessionID, BroadcastType, Integer4, bool, Integer1)
  Ask    : can any caller still reach the store with a zero SessionID?

CONSTRAINTS
  Read-only - read the repo, edit nothing, push nothing, open no PR. Real
  paths and line numbers; if you cannot resolve one, say so.

DONE LOOKS LIKE
  The call path with file:line per hop, a table of every call site and the
  SessionID it passes, then a yes/no with the offending site.""",
    },
    {
        "sys": "T7", "tag": "Plan the work",
        "title": "Three related SIRs into one implementation plan",
        "route": "t7-sdlc-planner",
        "code": """GOAL
  Turn these three SIRs into one plan with shared scope and testable
  acceptance criteria.

CONTEXT
  SIRs  : T7-571883 "CPU sets are parsed incorrectly", T7-574087
          (CPUAffinity=NO_VALUE must be a no-op), T7-559167 (harmonise
          CPU pinning, 1024 cores) - all three touch CPU affinity
  Code  : ParseCpuMask and ToNumber in gts.common.intmsg.model.common
  Worry : the 1024-core work silently re-breaks the parser fix

CONSTRAINTS
  Plan only, no product code. This agent CAN write Jira, so: create and
  update nothing - propose the ticket text in chat and I will ask.

DONE LOOKS LIKE
  A task table with affected files, acceptance criteria per SIR, the safe
  implementation order, and an explicit OUT OF SCOPE list.""",
    },
    {
        "sys": "T7", "tag": "Spec section",
        "title": "The DFS section that would have prevented the defect",
        "route": "t7-sdlc-spec-author",
        "code": """GOAL
  Draft the DFS section that would have prevented this defect.

CONTEXT
  SIR    : T7-574149 "Incorrect offsets in eti.xml" - the final padding
           field of the TES Reversal Broadcast carried a wrong offset
  Source : analysis thread issue #321 in dev/T7-Deep-Analysis-Request
  Gap    : the rule for trailing padding is implicit today; it must be
           explicit enough that a generator and a reviewer agree

CONSTRAINTS
  Write to ./demo-out/ only - do not touch the spec repository, open no
  PR, transition no SIR. DFS conventions: metadata header, numbered
  sections, normative "shall". Assumptions become OPEN QUESTIONs.

DONE LOOKS LIKE
  One self-contained DFS section with metadata header, the normative
  offset rule, a worked example, and the OPEN QUESTIONs. Name the file.""",
    },
    {
        "sys": "P7", "tag": "Test-first fix",
        "title": "RED test first, then the fix as a printed diff",
        "route": "p7-orchestrator → tester → developer",
        "code": """GOAL
  Write the test that fails today because of P7-3742 and passes once the
  guard is added, then show the fix as a printed diff.

CONTEXT
  SIR   : P7-3742, PricingEngine crash on LEPOs with no put partner
  Where : anyInstrumentOfExpiryInContinuousTrading in
          app/VolaFittingWaterfall.cxx asks for the call AND the put;
          getSecurityTradingStatus in library/ProductStateManager.cxx
          then does an unconditional .at(id)
  Model : the sibling getSecurityStatus already guards with count(id) == 0

CONSTRAINTS
  RED first - I want the test failing for the right reason before any
  production line changes. PRINT the diff; do not apply, commit or push.

DONE LOOKS LIKE
  The failing test with its assertion and today's failure message, the
  minimal diff, and why the test fails again if the guard is removed.""",
    },
    {
        "sys": "T7", "tag": "Commit review",
        "title": "Does this commit actually finish the SIR?",
        "route": "t7-sdlc-reviewer",
        "code": """GOAL
  Review this commit against the SIR it claims to fix. Is it complete?

CONTEXT
  Commit : bcf927d6 in dev/gts.eurex.gateway.common
           "T7-563473: Pass SessionId and ConnectionID to Perfmon"
  SIR    : T7-563473, OPM/Gateway race on BrcSubscription, baseline
           150.005.025
  Worry  : the new trailing parameters are defaulted, so old call sites
           keep compiling - was any caller missed?

CONSTRAINTS
  GitHub and Jira read-only - post no review, comment or approval. Judge
  the commit as it stands; do not rewrite unrelated code.

DONE LOOKS LIKE
  A completeness verdict, call sites updated versus left on the default,
  findings with file:line, and the review comments as text for me.""",
    },
    {
        "sys": "P7", "tag": "PR review",
        "title": "Can I approve this pull request?",
        "route": "p7-sdlc-reviewer",
        "code": """GOAL
  Review the open PR for P7-3742 and tell me whether I can approve it.

CONTEXT
  PR   : paste the PR URL so we review the same revision
  SIR  : P7-3742, PricingEngine crash on LEPOs with no put partner
  Bar  : it must not silently swallow a genuinely missing instrument -
         a LEPO with no put is expected, a missing call leg is not
  Also : does it add a test that would have caught the crash?

CONSTRAINTS
  GitHub and Jira read-only - post no review or approval, do not merge,
  transition no SIR. Review the diff, not the whole file.

DONE LOOKS LIKE
  APPROVE or REQUEST CHANGES with one sentence of reasoning, blocking
  findings and nits separated with file:line, a yes/no on the test, and
  the review text for me to paste.""",
    },
    {
        "sys": "T7", "tag": "PR text",
        "title": "PR description and changelog, without opening a PR",
        "route": "t7-sdlc-pr-author",
        "code": """GOAL
  Draft the PR title, description and changelog for this change - and do
  not open the PR.

CONTEXT
  Change   : the CPU-mask parsing fix for T7-571883, in
             gts.common.intmsg.model.common
  Range    : parent 681c6b78 to merge b30e3761
  Tests    : CpuMaskEtAllTestSuite - ParseHumanReadableCpuMaskTest,
             ParseHexCpuMaskTest, ToNumberBase10TestRejectInvalidLiterals
  Audience : reviewers new to this defect, plus a release note for ops

CONSTRAINTS
  Create no PR, push no branch, comment on no Jira issue. Print it as
  text. Claim no behaviour the diff does not contain.

DONE LOOKS LIKE
  A ticket-prefixed title, a body covering what changed, why and how it
  was verified, a one-line changelog, and what to review first.""",
    },
    {
        "sys": "P7", "tag": "Delivery gates",
        "title": "Pre-delivery gates, command printed for a human",
        "route": "gts-delivery",
        "code": """GOAL
  Run the read-only pre-delivery gates for this baseline and print the
  gts-deliver command a human would run - do not run it.

CONTEXT
  Target    : P7, project p7, integration baseline 012.003.021
  Container : P7-3642 "hotfix baseline to sync 1.1 fix - 012.003.021"
  In scope  : SIR P7-3742, still at Analysis complete with an open PR -
              I expect that to fail a gate, so call it out
  Builds    : INT-P7-012.003.021 #3 is SUCCESS on gtsci

CONSTRAINTS
  READ-ONLY - do not run gts-deliver, push no tag, modify no baseline,
  trigger no build. A gate you cannot evaluate is UNKNOWN, never PASS.

DONE LOOKS LIKE
  A gate table - gate, PASS / FAIL / UNKNOWN, evidence, blocking - then a
  go / no-go, then the exact command labelled "not executed".""",
    },
]
HOWTO = [
    {
        "key": "prompting", "label": "Prompting 101",
        "lead": "",
        "body": """<div class="wotitle">Constructing a good prompt <span class="wotsub">— in the GTS AI SDLC context</span></div>
<div class="wointro">Treat every request as a <b>work-order</b> for the agents: hand over one goal, the real artifacts, the guardrails, and a clear definition of done. Fill the four blocks and paste it to <code>/gts-orchestrator</code> — the sharper the order, the sharper the result.</div>
<div class="woheading"><span class="wohn">1</span>The shape <span class="wohs">— a reusable work-order</span></div>
<pre class="wocode">━━━━━━━━━━━━━━━━━━━━━  AGENT WORK-ORDER  ━━━━━━━━━━━━━━━━━━━━━

GOAL             one imperative sentence — the single outcome
CONTEXT          the real artifacts — paste links, not descriptions
                 • build / log URL · SIR / Jira · PR / commit / repo
                 • component + branch (+ baseline) · recent change · already tried
CONSTRAINTS      the guardrails — scope · toolchain · read-only · propose, don't push
DONE LOOKS LIKE  acceptance criteria + format — verdict first, then evidence, then next step</pre>""",
        "worksHead": """<div class="woheading"><span class="wohn">2</span>Worked examples <span class="wohs">— one per kind of task, on real T7 and P7 artifacts</span></div>
<div class="wointro">Fourteen complete work-orders, each for a different <b>kind</b> of job the agents can do today, ordered as a lifecycle — analyse, understand, plan, specify, implement, review, deliver. Every one goes to <code>/gts-orchestrator</code>, which routes it to the specialist named beside it. Pick the one closest to your task and swap in your own artifacts.</div>""",
        "works": WORKS,
        "outro": """<div class="woheading"><span class="wohn">3</span>Vague to sharp <span class="wohs">— the same request, rewritten</span></div>
<pre class="wocode">VAGUE   "the night build is broken again, can you have a look?"
        → which job · which build · broken how · and what do you want back?

SHARP   GOAL             Is this build failure a real regression or CI noise?
                         Name the owner.
        CONTEXT          INT-EUREX-150.005.031-NIGHT-STEST #12 UNSTABLE on gtsci ·
                         ran 2m 54s against a 1h 04m estimate ·
                         the sibling job on 150.005.030 passed the same night
        CONSTRAINTS      Read-only. No re-run, no Jira write, no PR. Say UNKNOWN
                         rather than guessing.
        DONE LOOKS LIKE  Verdict first, quoted log evidence, owner, one next step.</pre>
<div class="wointro">Three habits carry most of the weight. <b>One outcome per work-order</b> — if you need a review <i>and</i> a fix, send two. <b>Paste the artifact, not a description of it</b> — a build number, a SIR key, a commit sha, a PR URL; the agents resolve those live. <b>Say what must not happen</b> — an explicit read-only is honoured, and the agents will tell you what they did <i>not</i> do.</div>""",
    },
    {
        "key": "ask", "label": "Ask & understand",
        "lead": "Read-only questions about either codebase, its specs, ownership or terminology. No pipeline, no code changes \u2014 you just get an answer.",
        "handled": ["t7-sdlc-knowledge"],
        "defRoute": "gts-orchestrator → t7-sdlc-knowledge",
        "examples": [
            {"pers": "Developer", "cat": "Trace a message flow",
             "prompts": ["Trace how an OrderRejectNotification is produced and which components emit it (T7-570552)."]},
            {"pers": "Tester", "cat": "Find & run a test suite",
             "prompts": ["Where are the Market Maker Protection tests, what framework do they use, and how do I run just those?"]},
            {"pers": "Newcomer", "cat": "Learn the terminology",
             "prompts": ["Explain PATE, OFI and RDD in T7 and how they relate in the order lifecycle."]},
            {"pers": "Developer", "cat": "Look up configuration",
             "prompts": ["What configuration parameters control the Retransmitter, and where are they defined?", "List every Retransmitter tunable with its default and the file it lives in."]},
            {"pers": "Architect", "cat": "Dependencies & build order",
             "prompts": ["Which components depend on eurex.cilmsg, and what's the build order around it?"]},
            {"pers": "Business analyst", "cat": "Compare spec vs behaviour",
             "prompts": ["What does DFS141415 say about ExecType when an aggressor triggers Vola, and does the code match?"]},
            {"pers": "Release manager", "cat": "Delivery status roll-up",
             "prompts": ["Show the delivery status of everything under the T7_Iteration_3g label, grouped by component."]},
            {"pers": "Developer", "cat": "Find a symbol and its call-sites",
             "prompts": ["Where is Contract::UpdateWithoutProto defined and everywhere it's called?", "Show the definition and all call-sites of Contract::UpdateWithoutProto."]},
            {"pers": "Ops engineer", "cat": "Runbook question",
             "prompts": ["What does the rollover step execute_TIG_broker_maintenance_prepare do, and what are its preconditions?"]},
            {"pers": "Newcomer", "cat": "Find where something lives",
             "ask": "Where is the TradingActionRequest role check enforced, which component owns it, and what's the class hierarchy around it?",
             "route": "gts-orchestrator \u2192 t7-sdlc-knowledge"},
            {"pers": "Developer", "cat": "Understand how it works",
             "ask": "How does the VWAP settlement-price waterfall work today, and which modules feed into it?",
             "route": "gts-orchestrator \u2192 t7-sdlc-knowledge"},
            {"pers": "Business analyst", "cat": "Find the governing spec",
             "ask": "Which spec defines the QUALIFIED_BACKOFFICE_USER authorisation rules? Summarise the relevant section for me.",
             "route": "gts-orchestrator \u2192 t7-sdlc-knowledge"},
            {"pers": "Release manager", "cat": "Query Jira & GitHub together",
             "ask": "List every open SIR tagged DFS150510, and show the merged PRs that reference T7-571121.",
             "route": "gts-orchestrator \u2192 t7-sdlc-knowledge"},
            {"pers": "Developer", "cat": "Look up a protocol field",
             "ask": "Which ETI/FIX field carries BusinessRejectReason, and what valid value signals a pre-trade risk-limit breach?",
             "route": "gts-orchestrator \u2192 t7-sdlc-knowledge"},
            {"pers": "Ops engineer", "cat": "Onboard to a component",
             "ask": "Who owns the FAGSE Fix Gateway, where does its viewdb config live, and how is it built?",
             "route": "gts-orchestrator \u2192 t7-sdlc-knowledge"},
        ],
    },
    {
        "key": "diagnose", "label": "Root Cause Analysis",
        "lead": "NEW — hand over an engineering signal and get a read-only, evidence-grounded root-cause verdict. The gts-issue-analyst picks the authoritative engine (jenkins-lens for red builds, sonarqube-lens for Sonar findings, GitHub for security alerts), grounds it in the real code and specs, and recommends the next step. It diagnoses, never implements — a real fix is handed back to the pipeline. It also unwraps GitHub issues and Jira SIRs. You can call /gts-issue-analyst directly.",
        "handled": ["gts-issue-analyst"],
        "defRoute": "gts-orchestrator → gts-issue-analyst",
        "examples": [
            {"pers": "Build engineer", "cat": "Jenkins — red build: real or false positive?",
             "prompts": ["Is this red EUREX-INT build a real failure or a false positive? <paste the build URL from gtsci.xeops.deutsche-boerse.de>", "The nightly EUREX build went UNSTABLE — root-cause it and tell me whether it's a flake or a real regression."]},
            {"pers": "Developer", "cat": "Jenkins — root-cause a build from its log",
             "prompts": ["The EUREX release build failed in CPack packaging with 'Error 1101: Cannot extract dependency information' — find the root cause and the smallest fix to hand back.", "Console log pasted below — which component broke the build, and why?"]},
            {"pers": "Ops engineer", "cat": "T7 incident — root-cause a production crash",
             "prompts": ["Production incident: Pope crashed with a deadlock (SIR T7-502218) — classify the signal, ground it in the code, and tell me the authoritative next step.", "TFH-XETR went down with a 'double free' (T7-500068) — where's the double-ownership?"]},
            {"pers": "Ops engineer", "cat": "T7 incident — diagnose a performance regression",
             "prompts": ["dbsync suddenly takes ~17 minutes when stream base directories are missing (T7-570749) — root-cause the regression.", "PerfMon flags a latency spike on the Matcher hot path (T7-573438) — is it real, and where does it originate?"]},
            {"pers": "Reviewer", "cat": "Sonar issue — adjudicate a finding",
             "prompts": ["Adjudicate SonarQube cpp:S6147 on gts.eurex.gateway.outboundfi — true or false positive, with the source→sink data-flow.", "Is cpp:S1032 on this file a real bug or noise? Show me the evidence before I touch it."]},
            {"pers": "Ops engineer", "cat": "Sonar issue — triage a backlog",
             "prompts": ["Triage the critical & blocker SonarQube findings on this project and tell me which are real and worth fixing versus safe to mark won't-fix."]},
        ],
    },
    {
        "key": "analyse", "label": "Analyse an issue",
        "lead": "Turn a raw bug, SIR, log or feature request into a grounded plan \u2014 tasks, affected files, acceptance criteria and risks. Stops at the plan for your review. Paste anything: a ticket ID, an issue, a stack trace, or a snippet.",
        "handled": ["t7-sdlc-planner", "p7-sdlc-planner", "t7-sdlc-architect"],
        "defRoute": "gts-orchestrator → t7-orchestrator → t7-sdlc-planner",
        "examples": [
            {"pers": "Developer", "cat": "Analyse a double-free crash",
             "prompts": ["TFH-XETR crashes with 'double free' (T7-500068). Find the double-ownership and plan a fix plus a repro test."]},
            {"pers": "Business analyst", "cat": "Spec-gap analysis",
             "prompts": ["Compare the current ExecType handling against DFS141415 (T7-572936) and plan the change to keep ExecType from the first ATOrderRecord."]},
            {"pers": "Developer", "cat": "Locate where a validation belongs",
             "prompts": ["CoMa fails: 'contract month/year is not set for display source' (T7-572008). Find where the validation should live and plan the move.", "Analyse T7-572008 — should the fix sit in the proto contract or in Contract::UpdateWithoutProto?"]},
            {"pers": "Ops engineer", "cat": "Performance triage",
             "prompts": ["dbsync takes ~17 minutes when stream base directories are missing (T7-570749). Analyse why and plan a fix."]},
            {"pers": "Reviewer", "cat": "Impact analysis before a change",
             "prompts": ["If we change BusinessRejectReason valid values in FIX LF and ETI (T7-571030), what downstream messages and conversions are affected?"]},
            {"pers": "Developer", "cat": "Paste a code snippet — find the bug",
             "prompts": ["Snippet pasted below. It sometimes returns an empty OrderOrigination (T7-570646). Find the bug and plan the fix."]},
            {"pers": "Tester", "cat": "Turn a bug report into a test plan",
             "prompts": ["Web GUI multi-column sort is wrong (T7-573360). Draft a test plan that pins the correct sort order per column."]},
            {"pers": "Developer", "cat": "Analyse a P7 defect", "route": "gts-orchestrator → p7-orchestrator → p7-sdlc-planner",
             "prompts": ["Over-limit quotes pass the risk-limit check in P7 middleware. Analyse why and plan the fix."]},
            {"pers": "Developer", "cat": "Paste a Jira SIR \u2014 analyse a crash",
             "ask": "Here's SIR T7-502218 \u2014 'Pope crashed due to a deadlock.' Analyse the root cause and give me a fix plan with affected files and risks.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-planner"},
            {"pers": "Anyone", "cat": "Paste a GitHub issue \u2014 ask ten things at once",
             "ask": "I'm pasting GitHub issue #482 below. In one go: (1) explain the likely root cause, (2) list the components involved, (3) draft a task-by-task fix plan, (4) call out regression risks, (5) suggest tests to add.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-planner"},
            {"pers": "Developer", "cat": "Paste a stack trace / crash log",
             "ask": "Crash log pasted below \u2014 GatewayODC-EUREX GW.EMERG. Work out what's crashing and where, then plan the smallest safe fix (T7-574470).",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-planner"},
            {"pers": "Tester", "cat": "Reproduce-first triage",
             "ask": "SIR T7-573162 \u2014 'Negate/Not not working in the Market Maker Protection screen.' Tell me how to reproduce it and what the fix scope is.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-planner"},
            {"pers": "Business analyst", "cat": "Scope a feature into acceptance criteria",
             "ask": "Scope T7-574466 \u2014 exclude volume-only trades from the VWAP waterfall. What changes, where, and what are the acceptance criteria?",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-planner \u2192 t7-sdlc-architect"},
            {"pers": "Ops engineer", "cat": "Triage a production incident",
             "ask": "Rollover keeps failing on 'broker_maintenance execute_TIG_broker_maintenance_prepare' (T7-574274). Triage it and recommend the minimal fix.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-planner"},
            {"pers": "Developer", "cat": "Confirm a suspected memory leak",
             "ask": "T7-573762 \u2014 RetransmitPlugin::OnMessage moves raw pointer ownership into unique_ptr fields. Confirm the leak path and plan the fix.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-planner"},
        ],
    },
    {
        "key": "specify", "label": "Write a spec",
        "lead": "Produce a governance-grade specification document \u2014 DFS (functional), DTS (technical) or SRQ (requirements/security) \u2014 with a full metadata header, from an approved plan or a rough note.",
        "handled": ["t7-sdlc-spec-author", "p7-sdlc-spec-author"],
        "defRoute": "gts-orchestrator → t7-orchestrator → t7-sdlc-spec-author",
        "examples": [
            {"pers": "Business analyst", "cat": "Update an existing spec",
             "prompts": ["Update DFS130315 to reflect the shortened EDC report names for RD240/RD245/RD250/RD255 (T7-561998)."]},
            {"pers": "Developer", "cat": "Protocol DTS section",
             "prompts": ["Author the DTS section documenting the new mandatory PartyExecutingTrader in ETI ExtendedDeletionReport (T7-573246)."]},
            {"pers": "Business analyst", "cat": "DFS with acceptance criteria",
             "prompts": ["Write the functional spec for excluding volume-only trades from the VWAP waterfall (T7-574466), with acceptance criteria."]},
            {"pers": "Security engineer", "cat": "SRQ from security findings",
             "prompts": ["Draft an SRQ capturing the Fortify/SONAR remediation scope for this iteration (T7-568112)."]},
            {"pers": "Product owner", "cat": "Feature DFS from a ticket",
             "prompts": ["From ticket T7-570552, author the DFS for the new EDC OrderRejectNotification broadcast.", "Turn T7-570552 into a functional spec with message layout and trigger conditions."]},
            {"pers": "Developer", "cat": "DTS for a migration fix",
             "prompts": ["Write the DTS for the FAGSE viewdb configuration fix (T7-574213), documenting the corrected database names."]},
            {"pers": "Business analyst", "cat": "EnLight requirement",
             "prompts": ["Author the DFS for showing rejected respondent information in the Eurex EnLight request history (T7-521418)."]},
            {"pers": "Developer", "cat": "Interface-change spec",
             "prompts": ["Document the FIX LF / ETI valid-value addition Pretrade_Risk_Limit_Exceeded=10016 as a DTS interface change (T7-571030)."]},
            {"pers": "Product owner", "cat": "Consolidate specs",
             "prompts": ["Consolidate the linked SpA MARS tickets into one DFS Part-1 document with a metadata header."]},
            {"pers": "Business analyst", "cat": "Paste Confluence text",
             "prompts": ["Here's the Confluence draft (pasted). Convert it into a DOCX-ready DFS in our house format."]},
            {"pers": "Business analyst", "cat": "Write a requirements document (DFS)",
             "ask": "Author the DFS for the SpA Cash-Market Risk requirements (T7-571121 / DFS150510) from the approved plan.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-spec-author"},
            {"pers": "Developer", "cat": "Produce a technical spec (DTS)",
             "ask": "Turn the approved VWAP-waterfall plan into a DTS with the full metadata header and interface changes.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-spec-author"},
            {"pers": "Security engineer", "cat": "Draft a security requirements spec (SRQ)",
             "ask": "Draft the SRQ for the QUALIFIED_BACKOFFICE_USER authorisation rule (DFS150506), including the rejection behaviour.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-spec-author"},
            {"pers": "Business analyst", "cat": "Formalise a rough requirement note",
             "ask": "Here's our rough requirement note (pasted below). Turn it into a governance-grade DFS with proper sections and a metadata header.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-spec-author"},
            {"pers": "Product owner", "cat": "Spec an infrastructure change",
             "ask": "Write the SRQ151007 Infrastructure Enhancements spec from the plan and the linked tickets.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-spec-author"},
        ],
    },
    {
        "key": "implement", "label": "Implement a change",
        "lead": "The full pipeline: plan \u2192 architecture gate \u2192 failing tests (RED) \u2192 implement (GREEN) \u2192 review \u2192 build \u2192 PR. A confirmation gate stops it before any code is written.",
        "handled": ["t7-orchestrator", "p7-orchestrator"],
        "defRoute": "gts-orchestrator → t7-orchestrator → full SDLC pipeline",
        "examples": [
            {"pers": "Developer", "cat": "Fix a GUI defect",
             "prompts": ["Fix the Market Maker Protection screen so Negate/Not works (T7-573162), with a regression test."]},
            {"pers": "Developer", "cat": "Fix a sort bug end-to-end",
             "prompts": ["Fix the Web GUI multi-column sort (T7-573360) and add tests pinning the correct order.", "Web GUI sort is wrong on several columns (T7-573360) — implement the fix end-to-end with tests."]},
            {"pers": "Developer", "cat": "Add a protocol valid value",
             "prompts": ["Add ValidValue 108 (Book) to field 865 EventType in SpecialistInstrumentEventNotification (T7-517720)."]},
            {"pers": "Developer", "cat": "Spec-driven behaviour fix",
             "prompts": ["Keep ExecType from the first ATOrderRecord when an aggressor order triggers Vola (T7-572936 / DFS141415)."]},
            {"pers": "Developer", "cat": "Fix a memory leak",
             "prompts": ["Fix the Retransmitter memory leak by transferring ownership into unique_ptr correctly (T7-573762)."]},
            {"pers": "Security engineer", "cat": "Dependency / CVE fix",
             "prompts": ["Fix the dependabot alerts in cpython (T7-570588) and rebuild the affected bundle."]},
            {"pers": "Developer", "cat": "Add a missing check (P7)", "route": "gts-orchestrator → p7-orchestrator → full SDLC pipeline",
             "prompts": ["Add the missing risk-limit check that lets over-limit quotes through in P7 middleware."]},
            {"pers": "Developer", "cat": "Fix a defect end-to-end",
             "ask": "Reject a TradingActionRequest from a SpAProvider user without the QUALIFIED_BACKOFFICE_USER role (T7-574620). Take it all the way to a PR.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 planner \u2192 architect \u2192 tester \u2192 developer \u2192 reviewer \u2192 builder \u2192 pr-author"},
            {"pers": "Anyone", "cat": "Paste a GitHub issue \u2014 'just do it'",
             "ask": "Here's GitHub issue #517 (pasted). Implement it end-to-end \u2014 plan, tests, code, review, build, PR \u2014 and stop at the plan gate for my sign-off.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 full SDLC pipeline"},
            {"pers": "Developer", "cat": "Build a feature",
             "ask": "Exclude volume-only trades from the VWAP settlement-price waterfall (T7-574466).",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 full SDLC loop"},
            {"pers": "Developer", "cat": "Fix a crash with a repro test first",
             "ask": "Fix the TFH-XETR 'double free' crash (T7-500068) \u2014 write a failing test that reproduces it before the fix.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 tester (RED) \u2192 developer (GREEN) \u2192 \u2026"},
            {"pers": "Developer", "cat": "Add a mandatory protocol field",
             "ask": "Add the mandatory PartyExecutingTrader field to the ETI ExtendedDeletionReport (T7-573246).",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 full SDLC pipeline"},
            {"pers": "Developer", "cat": "Add a valid value across ETI + FIX",
             "ask": "Add valid value Pretrade_Risk_Limit_Exceeded=10016 to BusinessRejectReason in FIX LF and ETI (T7-571030).",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 full SDLC pipeline"},
            {"pers": "Developer", "cat": "Move a validation (CoMa defect)",
             "ask": "CoMa fails with 'contract month/year is not set' (T7-572008). Move the validation from the proto contract into Contract::UpdateWithoutProto and ship it.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 full SDLC pipeline"},
            {"pers": "Developer", "cat": "Add a validation rule (P7)",
             "ask": "Reject negative bid-ask spreads in the P7 pricing-engine request handler.",
             "route": "gts-orchestrator \u2192 p7-orchestrator \u2192 full SDLC pipeline"},
        ],
    },
    {
        "key": "review", "label": "Review code",
        "lead": "Judge a change for correctness, security (OWASP), patterns and requirement-conformance \u2014 as a standalone review. Paste a PR link, a diff, or a snippet.",
        "handled": ["p7-sdlc-reviewer", "t7-sdlc-reviewer", "t7-sdlc-architect"],
        "defRoute": "gts-orchestrator → t7-orchestrator → t7-sdlc-reviewer",
        "examples": [
            {"pers": "Reviewer", "cat": "Concurrency / deadlock review",
             "prompts": ["Review the Pope BatchDelete→Delete change for deadlock safety and lock ordering (T7-502218)."]},
            {"pers": "Reviewer", "cat": "Review a commit range",
             "prompts": ["Review commits abc123..def456 on eurex.apps.fagse for the viewdb-name fix (T7-574213)."]},
            {"pers": "Security engineer", "cat": "CVE-fix review",
             "prompts": ["Review the apache-tomcat CVE-2026-34500 remediation (T7-572764) — is the upgrade complete and safe?"]},
            {"pers": "Reviewer", "cat": "Performance-change review",
             "prompts": ["Review the LTO build change (T7-571498) for correctness and any UB it might expose."]},
            {"pers": "Developer", "cat": "Pre-merge checklist",
             "prompts": ["Run a full review checklist on my branch: correctness, tests, style, security and spec-conformance.", "Review everything on my branch and give a merge-readiness verdict with blockers."]},
            {"pers": "Reviewer", "cat": "Backward-compatibility review",
             "prompts": ["Does adding PartyExecutingTrader to ExtendedDeletionReport (T7-573246) break backward compatibility for ETI clients?"]},
            {"pers": "Reviewer", "cat": "Review a SQL / schema change",
             "prompts": ["Review this MySQL schema change to fagsedb session_subnet (T7-574078) for indexing and migration safety."]},
            {"pers": "Architect", "cat": "Cross-component consistency", "route": "gts-orchestrator → t7-orchestrator → t7-sdlc-architect",
             "prompts": ["Review whether the BusinessRejectReason valid-value change (T7-571030) is consistent across FIX LF, ETI and conversions."]},
            {"pers": "Reviewer", "cat": "Review test quality",
             "prompts": ["Review the new VWAP-waterfall tests — do they actually discriminate the volume-only exclusion?"]},
            {"pers": "Reviewer", "cat": "Review a pull request",
             "ask": "Review PR #128 on gts.p7.pricingengine for correctness, security (OWASP) and spec-conformance.",
             "route": "gts-orchestrator \u2192 p7-orchestrator \u2192 p7-sdlc-reviewer  (or /p7-sdlc-reviewer direct)"},
            {"pers": "Developer", "cat": "Review my own diff before pushing",
             "ask": "Here's my diff for the SpA rejection fix (pasted). Review it for edge cases and missing validation before I push.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-reviewer"},
            {"pers": "Security engineer", "cat": "Audit a snippet for OWASP",
             "ask": "Request-handler snippet below \u2014 audit it for OWASP issues: injection, broken authorisation, error-message leakage.",
             "route": "/p7-sdlc-reviewer  (directly callable)"},
            {"pers": "Reviewer", "cat": "Check spec-conformance",
             "ask": "Does this change actually implement DFS150506 correctly? Review it against the spec's rejection rules.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-reviewer"},
            {"pers": "Architect", "cat": "Sanity-check the approach first",
             "ask": "Before I build: is moving pointer ownership to unique_ptr the right fix for the Retransmitter leak, or will it break the plugin contract?",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-architect"},
            {"pers": "Reviewer", "cat": "Triage a SonarQube backlog",
             "ask": "Review the critical/blocker SonarQube findings on this module and tell me which are real and worth fixing (T7-568112).",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-reviewer"},
        ],
    },
    {
        "key": "ship", "label": "Build, ship & deliver",
        "lead": "Compile the affected components in dependency order, package the change into a clean, ticket-linked pull request \u2014 then, once it is merged and reviewed, run the read-only readiness gates and get the exact gts-deliver command to put it into an integration baseline. The delivery agent proposes and monitors; you execute the delivery.",
        "handled": ["t7-sdlc-builder", "t7-sdlc-pr-author", "gts-delivery"],
        "defRoute": "gts-orchestrator → t7-orchestrator → t7-sdlc-builder / t7-sdlc-pr-author",
        "examples": [
            {"pers": "Build engineer", "cat": "Resolve the build order", "route": "gts-orchestrator → t7-orchestrator → t7-sdlc-builder",
             "prompts": ["What's the correct build order for eurex.cilmsg and its dependents, and build them?"]},
            {"pers": "Build engineer", "cat": "Diagnose a broken build", "route": "gts-orchestrator → t7-orchestrator → t7-sdlc-builder",
             "prompts": ["The build fails after the GOLD-linker change (T7-573865). Build it, capture the error, and tell me what broke.", "Build the linker-change set (T7-573865); if it fails, show the first error and the culprit component."]},
            {"pers": "Release manager", "cat": "PR title + summary only", "route": "gts-orchestrator → t7-orchestrator → t7-sdlc-pr-author",
             "prompts": ["Give me a PR title in {ticket} {Description} form and a one-paragraph summary for the CoMa validation fix (T7-572008)."]},
            {"pers": "Developer", "cat": "Compile the Java tests too", "route": "gts-orchestrator → t7-orchestrator → t7-sdlc-builder",
             "prompts": ["Compile the Java test sources too and confirm they build (T7-571832)."]},
            {"pers": "Release manager", "cat": "Changelog across tickets", "route": "gts-orchestrator → t7-orchestrator → t7-sdlc-pr-author",
             "prompts": ["Draft a changelog grouping all FAGSE migration fixes delivered this week by component."]},
            {"pers": "Build engineer", "cat": "Build a single component", "route": "gts-orchestrator → t7-orchestrator → t7-sdlc-builder",
             "prompts": ["Just build eurex.apps.fagse at the current tag and report warnings and errors."]},
            {"pers": "Release manager", "cat": "Open a ticket-linked PR", "route": "gts-orchestrator → t7-orchestrator → t7-sdlc-pr-author",
             "prompts": ["Open the PR for the ETI PartyExecutingTrader change and link T7-573246 plus the DTS."]},
            {"pers": "Developer", "cat": "Rebuild after a rebase", "route": "gts-orchestrator → t7-orchestrator → t7-sdlc-builder",
             "prompts": ["I rebased on master — rebuild the affected components and confirm nothing regressed."]},
            {"pers": "Release manager", "cat": "Review-ready merge summary", "route": "gts-orchestrator → t7-orchestrator → t7-sdlc-pr-author",
             "prompts": ["Summarise everything on this branch into a review-ready merge description with a test matrix."]},
            {"pers": "Build engineer", "cat": "Dependency-aware full build", "route": "gts-orchestrator → t7-orchestrator → t7-sdlc-builder",
             "prompts": ["Build the whole EDC change set (T7-570552) in dependency order and report the first failure."]},
            {"pers": "Developer", "cat": "Verify the build in dependency order",
             "ask": "Build the components affected by the VWAP-waterfall change in dependency order and report pass/fail.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-builder"},
            {"pers": "Developer", "cat": "Quick compile check after an edit",
             "ask": "I changed the ODC server \u2014 just compile the affected components and tell me if anything breaks.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-builder"},
            {"pers": "Release manager", "cat": "Open the pull request",
             "ask": "Write the PR for the SpA rejection fix (T7-574620), link the ticket, and title it in our {ticket} {Description} form.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-pr-author"},
            {"pers": "Release manager", "cat": "Generate release notes",
             "ask": "Generate the release notes for everything merged under DFS150510 this iteration.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-pr-author"},
            {"pers": "Developer", "cat": "Turn my branch into a clean PR",
             "ask": "Turn my current branch into a clean PR \u2014 a {ticket} {Description} title, summary and test notes.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-pr-author"},
            {"pers": "Release manager", "cat": "Pre-delivery readiness check", "route": "gts-orchestrator \u2192 gts-delivery  (or /gts-delivery direct)",
             "prompts": ["Is release 150.005.031 open for delivery, and is T7-563473 governance-clean? Suggest the tag and branch."]},
            {"pers": "Release manager", "cat": "Propose the delivery command", "route": "gts-orchestrator \u2192 gts-delivery",
             "prompts": ["Deliver gts.eurex.gateway.common for T7-563473 into the open T7 integration release \u2014 run the gates and give me the exact gts-deliver command and the tags it will create."]},
            {"pers": "Build engineer", "cat": "Watch the integration build after delivery", "route": "gts-orchestrator \u2192 gts-delivery \u2192 gts-issue-analyst",
             "prompts": ["I ran gts-deliver \u2014 did INT-EUREX pick it up, did it pass, and if not is it infra noise or a real failure?"]},
        ],
    },
]


def unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0]:
        v = v[1:-1]
    # some agent frontmatter stores escaped unicode (e.g. \u2192) as literal text
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), v)


def parse_list(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        v = v[1:-1]
    return [unquote(x) for x in v.split(",") if x.strip()]


def parse_frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    fm_raw, body = m.group(1), m.group(2)
    fm = {}
    for line in fm_raw.splitlines():
        km = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s?(.*)$", line)
        if km:
            fm[km.group(1)] = km.group(2)
    return fm, body


def extract_statuses(body):
    toks = re.findall(r"^\s*(?:\||-)\s*\*\*([A-Z][A-Z0-9_]{2,})\*\*", body, re.M)
    out = []
    for t in toks:
        if t in STATUS_STOP or t in out:
            continue
        out.append(t)
    return out[:10]


def role_info(name):
    """Return (role, role_label, type_note)."""
    if name == "gts-orchestrator":
        return ("orchestrator", "Generic router",
                "Routes each request to the right system orchestrator — implements nothing itself.")
    if name == "gts-prompt-clarifier":
        return ("clarifier", "Prompt clarifier",
                "Runs before the pipeline: resolves ambiguity and enriches the request, then hands to the router.")
    if name.endswith("-orchestrator"):
        return ("orchestrator", "System orchestrator",
                "Coordinates its system's whole SDLC pipeline — delegates every step, writes no code.")
    if name == "gts-issue-analyst":
        return ("analyst", "Issue Analyst",
                "A read-only, cross-system analysis peer of the knowledge agent — diagnoses an engineering signal (a red build, a Sonar finding, a security alert, an issue or a SIR) and hands any fix back to the pipeline. Never writes.")
    if name == "gts-delivery":
        return ("delivery", "Delivery Agent",
                "A cross-system, propose-only peer of the analyst — runs the read-only pre-delivery readiness gates (release open, SIR governance, scope, tag format, branch availability), proposes the exact gts-deliver command and tags for you to run, then monitors the integration build. It never delivers, tags or mutates a baseline itself.")
    if name == "gts-feedback":
        return ("feedback", "Feedback Channel",
                "The way to report the agent suite itself — captures the conversation, redacts secrets, checks for duplicates and hands you a pre-filled New-Issue link for the feedback repo. It prepares the ticket; you submit it. Not for T7 / P7 product defects — those go to Jira.")
    m = re.match(r"^(?:p7|t7)-sdlc-(.+)$", name)
    role = m.group(1) if m else name
    labels = {"pr-author": "PR Author", "spec-author": "Spec Author", "knowledge": "Knowledge"}
    return (role, labels.get(role, role.replace("-", " ").title()), "")


def _ref(sid):
    return f" ({sid})" if sid else ""


def role_examples(system, role):
    """2-3 grounded example instructions for a role, using real scenarios."""
    scen = SCEN.get(system, SCEN["t7"])
    if role in ("orchestrator", "router"):
        return [t[0].upper() + t[1:] + _ref(s) for s, t in scen[:3]]
    if role == "clarifier":
        return ["rebase and rebuild the FAGSE gateway after the viewdb-name fix",
                "run the tests for the SpA rejection change and open a PR"]
    if role == "knowledge":
        return ["Where is the TradingActionRequest role check, and who owns it?",
                "Which spec covers the VWAP settlement-price waterfall?"]
    if role == "analyst":
        return ["Is this red EUREX build a real failure or a false positive? <paste the Jenkins build URL>",
                "Adjudicate SonarQube issue <key> on gts.eurex.gateway.outboundfi — true or false positive, with the data-flow.",
                "This Jira SIR wraps a failed build — unwrap it, find the root cause, and recommend the fix."]
    if role == "delivery":
        return ["Deliver gts.eurex.gateway.common for T7-563473 into the open 150.005 integration release — run the readiness gates and give me the exact command.",
                "Is release 150.005.031 open, is my SIR governance-clean, and what tag and branch should I use?",
                "I ran gts-deliver — did INT-EUREX pick it up, and did the build pass or is it infra noise?"]
    if role == "feedback":
        return ["The T7 planner ignored my acceptance criteria — file this whole conversation as a bug.",
                "Feature request: let the reviewer post its findings straight onto the pull request."]
    if role == "spec-author":
        return ["Author the DFS for the SpA Cash Market Risk requirements (T7-571121 / DFS150510).",
                "Turn the approved plan into a DTS with the full metadata header."]
    verb = {
        "planner":   "Plan{ref}: {task}.",
        "architect": "Review the plan to {task}{ref} — approve, revise or block.",
        "tester":    "Write a failing test proving: {task}{ref}.",
        "developer": "Implement the minimal change so the failing tests pass — {task}{ref}.",
        "reviewer":  "Review the change to {task}{ref} for correctness, security and spec-conformance.",
        "builder":   "Build the components affected by the {task} change in dependency order.",
        "pr-author": "Write the PR for the {task} change{ref} and link the ticket.",
    }.get(role, "{task}{ref}.")
    return [verb.format(task=t, ref=_ref(s)) for s, t in scen[:2]]


def use_when(desc):
    """Turn a description into short 'Use when' bullets.

    Some agents write 'Use when: a; b; c', others a prose 'Use when ...' paragraph —
    handle both, and break a glued-together clause back into sentences so no bullet
    renders as a wall of text.
    """
    tail = re.split(r"(?i)\buse when:?\s+", desc, maxsplit=1)
    tail = tail[1] if len(tail) > 1 else desc
    parts = [p.strip(" .;") for p in re.split(r";\s+", tail) if p.strip(" .;")]
    if len(parts) < 2:
        parts = [p.strip(" .,") for p in re.split(r",\s+", tail) if p.strip(" .,")]
    out = []
    for p in parts:
        chunks = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", p) if len(p) > 160 else [p]
        for c in chunks:
            c = c.strip(" .;,")
            if not c:
                continue
            if len(c) > 220:
                c = textwrap.shorten(c, width=220, placeholder=" \u2026")
            out.append(c)
    return out[:6]


def invoke_of(name, system, role, invocable):
    ex = role_examples(system, role)
    if invocable:
        return {"mode": "command", "note": "", "examples": [f"/{name} {e}" for e in ex]}
    orch = "p7-orchestrator" if system == "p7" else "t7-orchestrator" if system == "t7" else ""
    phase = PHASE_LABEL.get(role, "its phase")
    note = (f"Internal — you don't call it directly. The {orch} dispatches it during {phase}. Typical dispatch:"
            if orch else f"Internal — dispatched during {phase}. Typical dispatch:")
    return {"mode": "internal", "note": note, "examples": ex}


def model_kind(model):
    ml = (model or "").lower()
    if "opus" in ml:
        return ("Opus", "#C2862B")
    if "mini" in ml:
        return ("GPT-5 mini", "#3E9460")
    if "sonnet" in ml:
        return ("Sonnet", "#3F6FB5")
    return (model or "—", "#8A92A0")


# The MCP servers the agents reach their tools through (skill-first access).
# `id` MUST match the tool namespace used in the agents' `tools:` frontmatter —
# the "Used by agents" list is resolved by that id.
# `tools` is the COMPLETE surface each server exposes, not a sample. Refresh it
# from the live servers (VS Code MCP: List Servers, or the lens repos' own tool
# registries) whenever a server ships new tools. The Cortex `read_large_content`
# pagination helper is present on every hosted server and is omitted throughout.
# Verified 2026-08-18.

# The three GitHub connectors expose the same read-only browse surface.
GITHUB_TOOLS = [
    "search_code", "search_issues", "search_pull_requests", "search_repositories", "search_orgs", "search_users",
    "get_file_contents", "read_file_lines", "get_repository", "get_repository_tree", "list_repositories",
    "list_commits", "get_commit", "list_commit_comments",
    "list_pull_requests", "get_pull_request", "get_pull_request_diff", "list_pull_request_files",
    "list_pull_request_comments", "list_pull_request_reviews",
    "list_issues", "get_issue", "list_issue_comments", "list_issue_labels", "list_labels", "get_label",
    "list_branches", "list_tags", "get_tag", "list_releases", "get_latest_release", "get_release_by_tag",
    "list_workflows", "list_workflow_runs", "get_workflow_run", "list_workflow_run_jobs",
    "get_workflow_job_logs", "list_check_runs", "get_combined_status", "wait_for_required_checks",
    "list_dependabot_alerts", "get_dependabot_alert", "list_code_scanning_alerts", "get_code_scanning_alert",
    "list_secret_scanning_alerts", "get_secret_scanning_alert",
    "list_notifications", "get_notification_details", "get_teams", "get_team_members",
    "list_gists", "get_gist", "get_me", "upload_file",
]

MCPS = [
    {"id": "codereviewer_lens", "label": "Code-review brain", "group": "review", "auth": "via Cortex", "repo": "dev/gts.scm.ai.codereviewer-lens",
     "banner": "assets/lens-codereviewer.svg",
     "blurb": "The review engine behind the reviewer agents — SonarQube, Fortify, GitHub code/secret scanning, dependency checks and a RAG over the C++/Java/Python coding-guideline PDFs, combined with deterministic architecture and concurrency rules. It also scores requirement-conformance and answers guideline questions at write time.",
     "tools": ["review_diff", "review_pr", "review_commit", "review_snippet", "review_semantics", "validate_intent",
               "assess_conformance", "check_architecture_rules", "analyse_concurrency", "trace_impact",
               "query_code_graph", "check_compliance", "configure_review", "get_review_status",
               "ask_guideline", "explain_rule", "list_guidelines"]},
    {"id": "jenkins_lens", "label": "Jenkins build analysis", "group": "review", "auth": "via Cortex", "repo": "dev/gts.scm.ai.jenkins-lens",
     "banner": "assets/lens-jenkins.svg",
     "blurb": "Root-cause failing or UNSTABLE Jenkins builds — pull build info, diagnose the console log, localise the failing substep, score the build and separate real regressions from infrastructure noise. Used by gts-issue-analyst and gts-delivery.",
     "tools": ["analyze_build", "diagnose_log", "score_build", "build_info", "job_status", "list_jobs", "ask"]},
    {"id": "sonarqube_lens", "label": "SonarQube finding analysis", "group": "review", "auth": "via Cortex", "repo": "dev/gts.scm.ai.sonarqube-lens",
     "banner": "assets/lens-sonarqube.svg",
     "blurb": "Turn a SonarQube issue or hotspot into a grounded verdict — parse a pasted Sonar URL or key, then adjudicate the finding against the real code from six perspectives with a true-vs-false-positive probability and a fix plan. Used by gts-issue-analyst.",
     "tools": ["analyze_finding", "parse_sonar_url"]},
    {"id": "t7codebase", "label": "T7 Codebase Explorer", "group": "refdata", "auth": "Cortex bearer + AAD group", "repo": "dev/mcp.codebase-explorer",
     "blurb": "Navigate the T7 source across projects, environments and releases — keyword code search, file listing and semantic page-index lookups. This is how the planner and developer localise a change to real files instead of guessing.",
     "tools": ["search_code", "list_files", "list_projects", "list_environments", "list_releases", "page_index_search", "get_page_chunk"]},
    {"id": "t7dbcopy", "label": "T7 RDS Sense · reference data", "group": "refdata", "auth": "DBCopy login", "repo": "dev/cortex-mcp",
     "blurb": "Query the T7 Reference Data System (DBCopy) — the documented RDS semantic model, the physical schema behind it, read-only SQL over the live 'rdb' and Contract-Manager 'comadb' databases, enum resolution, baseline diffs and roll-over run data.",
     "tools": ["search_entities", "list_entities", "get_entity", "get_entity_relations", "get_semantic_model",
               "search_attributes", "get_baseline_stats", "diff_baselines",
               "map_entity_to_tables", "get_table_entity_mapping", "get_mapping_confidence", "describe_table",
               "list_tables", "list_databases", "get_create_table", "get_table_indexes", "get_schema_snapshot",
               "run_query", "query_entity", "count_entity",
               "resolve_enum", "resolve_map_enum", "lookup_enum",
               "get_environments", "get_deployed_version",
               "get_rds_rollover", "get_rollover_history", "get_rollover_runtime", "render_rds_rollover",
               "search_coma_entities", "list_coma_entities", "get_coma_entity", "get_coma_baseline_stats", "list_coma_baselines"]},
    {"id": "eurex_refdata", "label": "Eurex reference data", "group": "refdata", "auth": "API key", "repo": "dev/cortex-mcp",
     "blurb": "Query public Eurex reference data via the GraphQL API — products, contracts, trading hours, settlement prices, holidays, expirations, tick rules, TES and EnLight profiles, vendor codes and deliverable bonds, plus a raw GraphQL escape hatch.",
     "tools": ["query_products", "query_contracts", "query_flexible_contracts", "query_expirations",
               "query_trading_hours", "query_settlement_prices", "query_holidays", "query_tick_rules",
               "query_tes_profiles", "query_vendor_codes", "query_deliverable_bonds",
               "query_enlight", "query_enlight_responders", "query_changelog", "graphql"]},
    {"id": "github", "label": "GitHub Enterprise · default", "group": "code", "auth": "Cortex bearer", "repo": "dev/cortex-mcp",
     "blurb": "The default GitHub connector, read-only: github.deutsche-boerse.de, where both T7 and P7 product source and the gts.* AI-tooling repos live. Code search, files, commits, diffs, pull requests, issues, branches, tags, releases, CI runs and security alerts. It cannot write — agents that publish do so with the git CLI, never through this server.",
     "tools": GITHUB_TOOLS},
    {"id": "github_ghe", "label": "GitHub Enterprise · explicit", "group": "code", "auth": "GitHub PAT (pass-through)", "repo": "dev/cortex-mcp",
     "blurb": "The same internal host as `github`, in its explicit form, with your own GitHub PAT passed through — same tool surface. The knowledge agents use it so a repository question is always answered from the host the repo actually lives on. Read-only.",
     "tools": GITHUB_TOOLS},
    {"id": "github_dbg", "label": "GitHub Cloud · Trading-DEV", "group": "code", "auth": "GitHub PAT (dbg.ghe.com)", "repo": "dev/cortex-mcp",
     "blurb": "The GitHub Cloud host dbg.ghe.com (Trading-DEV org) — cloud org repos and sandbox mirrors, same tool surface as `github`. A separate identity from the internal GHE: use it only when the repository URL is dbg.ghe.com, never as a fallback for an internal repo. Read-only.",
     "tools": GITHUB_TOOLS},
    {"id": "t7spec", "label": "T7 specifications", "group": "spec", "auth": "Cortex bearer", "repo": "dev/cortex-mcp",
     "blurb": "Search and read the T7 specification corpus (DFS / DTS / SRQ / functional and interface manuals) — keyword, semantic and structured queries over hundreds of documents. `status` first tells you how current the index is.",
     "tools": ["search", "vsearch", "grep", "query", "get", "multi_get", "list_files", "status"]},
    {"id": "p7spec", "label": "P7 specifications", "group": "spec", "auth": "Cortex bearer", "repo": "dev/cortex-mcp",
     "blurb": "Search and read the P7 (Pricing & Risk) specification corpus — the same keyword / semantic / structured retrieval as t7spec, for P7 documents.",
     "tools": ["search", "vsearch", "grep", "query", "get", "multi_get", "status"]},
    {"id": "devops_jira", "label": "Jira · SIRs & tickets", "group": "tickets", "auth": "Jira PAT", "repo": "dev/cortex-mcp",
     "blurb": "The full Jira surface across all projects — issues and SIRs, JQL, boards and sprints, attachments, project metadata and Xray test management. Note this is the server's whole capability: agent grants are least-privilege, so most agents get a read-only subset and none holds the delete or batch tools.",
     "tools": ["get_issue", "get_issue_comments", "get_issue_links", "get_remote_issue_links", "get_issue_changelog",
               "get_issue_watchers", "get_issue_worklogs", "get_transitions", "get_issue_types", "get_link_types",
               "search_issues", "run_jql", "get_my_issues", "get_issues_assigned_to", "get_project_issues",
               "get_epic_issues", "search_users", "get_user", "get_user_permissions", "get_myself",
               "create_issue", "batch_create_issues", "update_issue", "transition_issue", "assign_issue",
               "add_comment", "edit_comment", "delete_comment", "delete_issue", "link_issues", "remove_issue_link",
               "create_remote_issue_link", "add_watcher", "remove_watcher", "add_worklog",
               "get_create_meta", "get_edit_meta", "get_fields", "get_field_options", "get_statuses",
               "get_priorities", "get_resolutions", "get_server_info", "list_projects", "get_project",
               "get_project_components", "get_project_versions", "create_version", "update_version",
               "list_boards", "get_board", "get_board_backlog", "get_board_configuration", "get_board_issues",
               "list_sprints", "get_sprint", "get_sprint_issues", "create_sprint", "update_sprint", "add_issues_to_sprint",
               "list_attachments", "attach_file", "download_attachment", "get_attachment_text",
               "start_attachment_text_extraction", "get_attachment_text_extraction", "get_attachment_visual_context",
               "create_test", "create_test_execution", "add_tests_to_test_execution", "add_tests_to_test_plan",
               "import_junit_results", "propose_coverage"]},
    {"id": "confluence", "label": "Confluence", "group": "tickets", "auth": "Confluence PAT", "repo": "dev/cortex-mcp",
     "blurb": "Read Confluence spaces and pages — search content, fetch pages by title or id, walk ancestors and children, read comments, labels, history and attachments, and (where granted) append or update a section. Used by the spec authors to pull source material into a DFS / DTS / SRQ.",
     "tools": ["search_content", "get_page", "get_page_by_title", "get_page_ancestors", "list_page_children",
               "get_page_comments", "get_page_history", "get_page_version", "get_page_labels", "get_page_attachments",
               "get_content_properties", "list_spaces", "get_space", "get_space_content", "get_user", "get_current_user",
               "append_to_page", "update_page_section", "upload_attachment"]},
    {"id": "sharepoint", "label": "SharePoint · spec documents", "group": "tickets", "auth": "Azure AD sign-in", "repo": "dev/cortex-mcp",
     "blurb": "Reach the SharePoint document libraries where the released specification documents live — the spec authors use it to locate the governing DFS / DTS / SRQ for a release before writing a new one. The whole connector is granted, so its exact tool surface is whichever SharePoint connector you enable in Cortex.",
     "tools": ["sharepoint/*"]},
]

# Agentic-harness benchmarking campaigns (results dashboards + artifact repos), newest first.
EVALS = [
    {"key": "aug2026", "label": "August 2026", "title": "Benchmarking · August 2026", "status": "Current campaign",
     "blurb": "The agents work a fresh slate of real T7 / P7 SIRs and tasks, scored against frozen oracles for plan quality, evidence localisation, fix correctness and review.",
     "dashboard": "https://pages.github.deutsche-boerse.de/dev/gts.ai.harness.eval-results/gts.ai.sdlc/runs/views/dashboard.html",
     "artifacts": "https://github.deutsche-boerse.de/dev/gts.ai.harness.eval-results"},
    {"key": "jul2026", "label": "July 2026", "title": "Benchmarking · July 2026", "status": "Previous campaign",
     "blurb": "The first full benchmarking pass — the baseline scorecard that every later run is measured against.",
     "dashboard": "https://pages.github.deutsche-boerse.de/dev/gts.ai.harness.eval-results/gts.ai.sdlc/runs/views/dashboard.html",
     "artifacts": "https://github.deutsche-boerse.de/dev/gts.ai.harness.eval-results"},
]

# Roadmap shown on the "What's Next" tab — in design or in build, deliberately undated.
# `i` is the tracking issue in dev/gts.ai.sdlc, where one exists.
NEXT = [
    {"t": "T7 Component Skill/Context Generator Agent",
     "b": ["Generates T7 component-specific (ME, GMC, OPM, etc.) skills from the docs, specs, repo and any existing reference the user provides.",
           "Generates a T7 component-specific, task-aware context document."]},
    {"t": "GTS Deep Agents",
     "b": ["Agents create their own GCP instances and run tasks independently."]},
    {"t": "T7 SuperAgent",
     "b": ["Forensic, evidence-based, deterministic issue analysis.",
           "Root-cause for time-critical, hard-to-resolve issues.",
           "Built for the toughest cases."]},
    {"t": "Jira STP Agent",
     "b": ["One-click Jira issue to pull request.",
           "Runs automatically in GCP."],
     "d": "Pilot implementation. Standard uses are subject to risk assessment, policy compliance and further review."},
    {"t": "On-demand RCA Agent",
     "b": ["Root-cause analysis at the point of failure \u2014 e.g. build-failure analysis straight from the failing Jenkins build."]},
    {"t": "Smoke Test Agent", "i": 26,
     "b": ["Reads the Jenkins build, its smoke-test stage and the changeset.",
           "Pulls the smoke-test log, spots the known patterns, summarises.",
           "Investigates on its own GCP instance."]},
    {"t": "Unit Test Agent", "i": 23,
     "b": ["Creates and runs unit tests for one component \u2014 Boost.Test, Catch2, GoogleTest.",
           "Writes a test that reproduces a reported defect, or covers a changeset.",
           "Handles CMake enablement and reports failures."]},
    {"t": "Component Skill & Resource Management",
     "b": ["Collect, coordinate and maintain component-specific skills and agentic resources."]},
    {"t": "Assignment Agents",
     "b": ["Issue analysis by assignment in Jira.",
           "GitHub issue analysis.",
           "Pull-request review by assignment."],
     "d": "Pilot implementation. Standard uses are subject to risk assessment, policy compliance and further review."},
    {"t": "Self-Improving Harness",
     "b": ["Integrated and on-demand evals \u2014 score a change as it happens, not only in a campaign.",
           "Builds learning and memory from every run, so lessons carry across sessions.",
           "Feeds scored failures back into the agent or skill that caused them.",
           "A self-improvement and reflection skill \u2014 use when capturing the learnings from a session."]},
    {"t": "T7 Knowledge Graph",
     "b": ["Efficient, recency- and baseline-aware retrieval across the whole T7 knowledge base \u2014 requirement docs, repos, Confluence, SharePoint."]},
    {"t": "Ready-to-use Skills",
     "b": ["Grill-me, interview-mode and brainstorm-together \u2014 skills you invoke directly."]},
    {"t": "Bidirectional Cortex Integration",
     "b": ["Connect both ways with Cortex to run, resume and continue interactions."]},
    {"t": "t7spec / t7codebase MCP Improvements",
     "b": ["Ongoing work on speed, answer quality and tool capability."]},
]

FEEDBACK_REPO = "https://github.deutsche-boerse.de/dev/gts.ai.sdlc-feedback"
SDLC_REPO = "https://github.deutsche-boerse.de/dev/gts.ai.sdlc"
FEEDBACK_NEW_ISSUE = "https://github.deutsche-boerse.de/dev/gts.ai.sdlc-feedback/issues/new/choose"
SDLC_ISSUE_URL = "https://github.deutsche-boerse.de/dev/gts.ai.sdlc/issues/"

agents = []
for path in sorted(glob.glob(os.path.join(AGENT_DIR, "*.agent.md"))):
    text = open(path, encoding="utf-8").read()
    fm, body = parse_frontmatter(text)
    name = fm.get("name", os.path.basename(path).replace(".agent.md", ""))
    tools = parse_list(fm.get("tools", "[]"))
    servers, seen = [], set()
    for t in tools:
        ns = t.split("/")[0]
        if ns in BUILTIN_TOOLS or ns in seen:
            continue
        seen.add(ns)
        servers.append(ns)
    skills = [s.split("/")[-1] for s in parse_list(fm.get("skills", "[]"))]
    skills_common = parse_list(fm.get("skills_common", "[]"))
    delegates = parse_list(fm.get("agents", "[]"))
    system = fm.get("system", "").strip() or ("p7" if name.startswith("p7") else
                                              "t7" if name.startswith("t7") else "generic")
    role, role_label, type_note = role_info(name)
    invocable = unquote(fm.get("user-invocable", "false")).lower() == "true"
    mk_label, mk_ink = model_kind(fm.get("model", ""))
    if role in ("orchestrator", "router"):
        in_group = 0
    elif role == "clarifier":
        in_group = 1
    else:
        in_group = ROLE_ORDER.get(role, 99) + 1
    agents.append({
        "name": name,
        "system": system,
        "group": GROUP_LABEL[system],
        "groupOrder": GROUP_ORDER[system],
        "inGroup": in_group,
        "role": role,
        "roleLabel": role_label,
        "typeNote": type_note,
        "phase": ROLE_PHASE.get(role, -1),
        "description": unquote(fm.get("description", "")),
        "useWhen": use_when(unquote(fm.get("description", ""))),
        "objective": OBJECTIVE.get(role, ""),
        "argHint": unquote(fm.get("argument-hint", "")),
        "userInvocable": invocable,
        "model": unquote(fm.get("model", "")),
        "modelLabel": mk_label,
        "modelInk": mk_ink,
        "skills": skills,
        "skillsCommon": skills_common,
        "servers": servers,
        "delegates": delegates,
        "statuses": extract_statuses(body),
        "invoke": invoke_of(name, system, role, invocable),
    })

agents.sort(key=lambda a: (a["groupOrder"], a["inGroup"], a["name"]))
group_order = []
for a in agents:
    if a["group"] not in group_order:
        group_order.append(a["group"])

DEFAULT = "t7-sdlc-developer"

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GTS AI SDLC · SDLC Agent Exploration</title>
<style>
  :root{
    --ink:#1F2733; --body:#5B6472; --muted:#8A92A0; --faint:#AEB6C0;
    --line:#E4E9EF; --bg:#F4F7FB; --card:#FFFFFF; --hair:#EEF1F5;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);line-height:1.5;
    font-family:Inter,'SF Pro Display',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;}
  a{color:#3F6FB5;text-decoration:none} a:hover{text-decoration:underline}
  .hero{background:linear-gradient(135deg,#5E54C8 0%,#3F6FB5 52%,#2E8E84 100%);color:#fff;padding:15px 24px 16px}
  .hero-in{max-width:1180px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;gap:14px 20px;flex-wrap:wrap}
  .hero .eyebrow{font-size:11px;font-weight:700;letter-spacing:2px;opacity:.85}
  .hero h1{margin:3px 0 0;font-size:21px;font-weight:800;letter-spacing:-.3px}
  .herobtn{display:inline-flex;align-items:center;gap:8px;padding:8px 13px;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.45);color:#fff;text-decoration:none;font-size:12.5px;font-weight:700;font-family:'SF Mono',ui-monospace,Menlo,monospace;white-space:nowrap;transition:background .14s,border-color .14s}
  .herobtn:hover{background:rgba(255,255,255,.25);border-color:rgba(255,255,255,.75)}
  .herobtn svg{flex:0 0 auto;opacity:.9}
  .hbarw{opacity:.75}
  .wrap{max-width:1180px;margin:0 auto;padding:22px 24px 56px}
  .controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:2px 0 18px}
  .search{flex:1 1 240px;min-width:200px;display:flex;align-items:center;gap:8px;
    border:1px solid var(--line);border-radius:0;padding:9px 12px;background:#fff}
  .search input{border:0;outline:0;font-size:14px;width:100%;color:var(--ink);background:transparent}
  .chips{display:flex;flex-wrap:wrap;gap:6px}
  .chip{border:1px solid var(--line);background:#fff;color:var(--body);border-radius:999px;
    padding:6px 13px;font-size:12.5px;font-weight:600;cursor:pointer;transition:.12s}
  .chip:hover{border-color:#c7cfd8}
  .chip.on{background:#1F2733;color:#fff;border-color:#1F2733}
  .legend{display:flex;flex-wrap:wrap;gap:13px;font-size:11.5px;color:var(--muted);margin-left:auto}
  .legend .dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;vertical-align:1px}
  .layout{display:grid;grid-template-columns:288px 1fr;gap:20px;align-items:start}
  .card{background:var(--card);border:1px solid var(--line);border-radius:0;box-shadow:0 1px 3px rgba(15,23,42,.05)}
  .list{padding:12px;max-height:80vh;overflow:auto}
  .group{font-size:11px;font-weight:700;letter-spacing:.8px;color:var(--muted);text-transform:uppercase;margin:14px 8px 8px}
  .group:first-child{margin-top:4px}
  .agent{display:block;width:100%;text-align:left;border:0;background:transparent;border-radius:10px;
    padding:9px 12px 9px 16px;cursor:pointer;position:relative;transition:.1s}
  .agent:hover{background:#F1F5FA}
  .agent.sel{background:#EAF1FA}
  .agent .bar{position:absolute;left:4px;top:10px;bottom:10px;width:4px;border-radius:2px}
  .agent .an{font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:12.5px;font-weight:600}
  .agent .ar{font-size:11.5px;color:var(--muted);margin-top:2px}
  .agent .sb{position:absolute;right:10px;top:11px;font-size:10px;font-weight:800;padding:2px 8px;border-radius:999px}
  .detail{padding:22px 24px;position:sticky;top:16px;min-width:0}
  .dhead{display:flex;align-items:flex-start;gap:12px;flex-wrap:wrap}
  .dname{font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:21px;font-weight:700}
  .badges{display:flex;gap:6px;flex-wrap:wrap;margin-left:auto}
  .b{font-size:11px;font-weight:700;padding:3px 10px;border-radius:999px;white-space:nowrap}
  .b.inv{background:#E8F2EC;color:#3E8C61}
  .b.noinv{background:#F1F3F6;color:#8A92A0}
  .reach{margin-top:7px;font-size:12.5px;color:var(--muted)}
  .drole{font-size:15px;font-weight:700;margin:14px 0 2px}
  .dtype{color:var(--body);font-size:13.5px;margin:2px 0}
  .ddesc{color:var(--body);font-size:13.5px;line-height:1.55;margin:8px 0 0}
  .sect{font-size:11px;font-weight:700;letter-spacing:.8px;color:var(--faint);text-transform:uppercase;margin:20px 0 9px}
  .pchips,.tchips{display:flex;flex-wrap:wrap;gap:7px}
  .pill{font-size:12px;font-weight:600;padding:6px 11px;border-radius:999px;border:1px solid;cursor:default}
  .pill.sk{background:#F0EBFB;border-color:#E0D6F4;color:#5B49A6;cursor:pointer}
  .pill.sk.sys{background:#EAF5F3;border-color:#CFE9E5;color:#2E7D74}
  .pill.sk:hover{filter:brightness(.97);text-decoration:none}
  .pill.srv{background:#fff;border-color:#D9DEE5;color:#46505E;font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:11.5px}
  .pill.st{background:#FBF1DC;border-color:#EFE0C2;color:#9A6A1E;font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:11px}
  .pill.go{cursor:pointer}
  .none{color:var(--muted);font-size:13px;font-style:italic}
  .cmd{background:#1F2733;color:#E9EEF5;border-radius:0;padding:9px 12px;margin:7px 0;
    font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:12px;line-height:1.5;white-space:normal;word-break:break-word}
  .cmd .sl{color:#7DE3D0;font-weight:700}
  .inote{color:var(--body);font-size:13px;margin:2px 0 6px}
  .disp{color:var(--muted);font-size:12.5px;font-style:italic}
  .meta{display:flex;flex-wrap:wrap;gap:22px;margin-top:8px}
  .meta .k{font-size:11px;font-weight:700;letter-spacing:.6px;color:var(--faint);text-transform:uppercase}
  .meta .v{font-size:13.5px;font-weight:600;margin-top:3px;display:flex;align-items:center;gap:7px}
  .mdot{width:9px;height:9px;border-radius:50%}
  .pipe{display:flex;flex-wrap:wrap;gap:5px;align-items:center;margin-top:6px}
  .pstep{display:flex;align-items:center;gap:5px}
  .pnode{width:9px;height:9px;border-radius:50%;background:#DCE1E8}
  .pstep.on .pnode{background:#2E8E84;box-shadow:0 0 0 4px rgba(46,142,132,.15)}
  .pstep .pl{font-size:11px;color:var(--muted)}
  .pstep.on .pl{color:#2E7D74;font-weight:700}
  .parrow{color:#CBD2DA;font-size:11px}
  .xnote{background:#EEF3FA;border:1px solid #DCE6F3;border-radius:0;padding:9px 12px;
    font-size:12.5px;color:var(--body);margin-bottom:14px;display:flex;gap:10px;align-items:center}
  .xnote b{color:var(--ink)}
  .xnote button{margin-left:auto;border:0;background:#1F2733;color:#fff;border-radius:8px;padding:5px 10px;font-size:11.5px;font-weight:600;cursor:pointer}
  .tabs{display:flex;flex-wrap:wrap;gap:6px;border-bottom:2px solid var(--line);margin:12px 0 22px}
  .tab{padding:9px 12px;font-size:13px;font-weight:700;color:#fff;cursor:pointer;border:2px solid #3F6FB5;background:#3F6FB5;border-radius:11px 11px 0 0;margin-bottom:-2px;transition:.14s;position:relative;top:4px}
  .tab:hover:not(.on){background:#4E7AC0;border-color:#4E7AC0;top:2px}
  .tab.on{color:var(--ink);background:#fff;top:0;border-bottom-color:#fff;box-shadow:inset 0 3px 0 #3F6FB5,0 -3px 8px rgba(15,23,42,.05)}
  .uw{font-size:11.5px;font-weight:700;color:var(--body);margin:0 0 3px}
  ol.uwl{margin:2px 0 0;padding-left:20px}
  ol.uwl li{font-size:13px;color:var(--body);line-height:1.5;margin:3px 0}
  .obj{font-size:13.5px;color:var(--body);margin-top:12px}
  .obj b{color:var(--ink)}
  .dsuffix{margin-left:7px;font-weight:600;font-size:14px;color:var(--muted)}
  .howto{margin-top:2px}
  .hintro{background:#fff;border:1px solid var(--line);border-radius:0;padding:15px 18px;font-size:13.5px;color:var(--body);line-height:1.6;margin-bottom:16px;box-shadow:0 1px 3px rgba(15,23,42,.05)}
  .mcpnote{display:block;margin-top:8px;font-size:12.5px;color:var(--muted)}
  .hintro b{color:var(--ink)}
  .hintro code{background:#F1F5FA;border:1px solid #E1E8F0;border-radius:5px;padding:1px 6px;font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:12px;color:#3F6FB5}
  ol.hprin{margin:11px 0 2px;padding-left:22px}
  ol.hprin li{margin:6px 0;font-size:13.5px;color:var(--body);line-height:1.55}
  ol.hprin li b{color:var(--ink)}
  ol.hprin li::marker{color:#3F6FB5;font-weight:800}
  .hprinnote{display:block;margin-top:9px;color:var(--muted);font-size:13px}
  .qm{margin:14px 0 2px;border:1px solid var(--line);background:#F8FAFD;padding:13px 15px}
  .qmhead{font-size:13px;font-weight:800;color:var(--ink);margin-bottom:10px}
  .qmhead span{font-weight:600;color:var(--muted)}
  .qmform{display:flex;flex-wrap:wrap;align-items:stretch;gap:6px}
  .qmres{flex:0 0 auto;display:flex;align-items:center;background:#2F3B4D;color:#fff;padding:8px 12px;font-size:12.5px;font-weight:800;line-height:1.25;max-width:96px}
  .qmterm{flex:1 1 120px;max-width:280px;background:#fff;border:1px solid #DCE6F3;padding:7px 10px;line-height:1.3}
  .qmterm b{display:block;font-size:12.5px;color:var(--ink)}
  .qmterm span{display:block;margin-top:2px;font-size:11px;color:var(--muted)}
  .qmterm.bad{border-color:#F0D9D7;background:#FFFAF9}
  .qmterm.bad b{color:#B3453F}
  .qmop{flex:0 0 auto;align-self:center;font-size:15px;font-weight:800;color:var(--faint)}
  .qmop.minus{color:#B3453F}
  .qmchart{display:block;width:100%;height:auto;margin:13px 0 0}
  .qmzones{display:flex;flex-wrap:wrap;gap:8px;margin-top:9px}
  .qmzone{flex:1 1 250px;background:#fff;border:1px solid var(--line);border-left:3px solid #3E9460;padding:7px 10px}
  .qmzone b{display:block;font-size:12.5px;color:var(--ink)}
  .qmzone span{display:block;margin-top:2px;font-size:11.5px;color:var(--muted)}
  .qmzone.rot{border-left-color:#C98A2E}
  .qmtake{margin-top:10px;padding-top:9px;border-top:1px dashed #D9E2EE;font-size:12.5px;color:var(--body);line-height:1.55}
  .qmtake b{color:var(--ink)}
  .woheading{display:flex;align-items:center;gap:10px;margin:22px 0 2px;font-size:15px;font-weight:800;color:var(--ink)}
  .woheading .wohn{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:8px;background:linear-gradient(135deg,#3F6FB5,#2E8E84);color:#fff;font-size:12.5px;font-weight:800;flex:0 0 auto}
  .woheading .wohs{font-weight:600;color:var(--muted);font-size:13px}
  .wotitle{font-size:19px;font-weight:800;color:var(--ink);letter-spacing:-.2px;margin:4px 0 0;display:flex;align-items:baseline;gap:9px;flex-wrap:wrap}
  .wotitle .wotsub{font-size:13px;font-weight:600;color:var(--muted);letter-spacing:0}
  .wointro{font-size:13.5px;color:var(--body);line-height:1.6;margin:9px 0 2px}
  .wointro code{background:#F1F5FA;border:1px solid #E1E8F0;border-radius:5px;padding:1px 6px;font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:12px;color:#3F6FB5}
  .wocode{margin:9px 0 2px;background:#fff;border:1px solid #DCE6F3;border-radius:8px;padding:13px 15px;overflow-x:auto;font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:11.7px;line-height:1.6;color:#33415A;white-space:pre;box-shadow:0 1px 2px rgba(15,23,42,.04)}
  .wochips{display:flex;flex-wrap:wrap;gap:6px;margin:11px 0 0}
  .wochip{display:inline-flex;align-items:center;gap:6px;border:1px solid #DCE6F3;background:#fff;color:var(--body);border-radius:999px;padding:5px 12px 5px 6px;font-size:12px;font-weight:700;font-family:inherit;cursor:pointer;transition:background .12s,border-color .12s,color .12s}
  .wochip:hover:not(.on){border-color:#B9CBE4;background:#F7FAFE}
  .wochip.on{background:linear-gradient(135deg,#3F6FB5,#2E8E84);border-color:transparent;color:#fff}
  .wochip .wcsys{display:inline-flex;align-items:center;justify-content:center;min-width:25px;height:17px;border-radius:999px;font-size:9.5px;font-weight:800;letter-spacing:.3px}
  .wcsys.sT7{background:#3F6FB5;color:#fff}
  .wcsys.sP7{background:#2E8E84;color:#fff}
  .wochip.on .wcsys{background:rgba(255,255,255,.26);color:#fff}
  .wometa{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin:14px 0 0;font-size:13.5px;font-weight:800;color:var(--ink)}
  .wometa .wmroute{font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:11px;font-weight:600;color:#3F6FB5;background:#F1F5FA;border:1px solid #E1E8F0;border-radius:5px;padding:2px 8px}
  .wometa .wmroute .rlab{font-family:Inter,sans-serif;font-weight:700;text-transform:uppercase;letter-spacing:.4px;font-size:9.5px;color:var(--faint);margin-right:6px}
  .mcplayout{display:grid;grid-template-columns:288px 1fr;gap:20px;align-items:start}
  .mcprepo{font-size:12.5px;font-weight:700;color:#2B5CB8;text-decoration:none;font-family:'SF Mono',ui-monospace,Menlo,monospace;word-break:break-all}
  .mcpban{display:block;margin:12px 0 2px;border:1px solid var(--line);background:#fff;padding:8px 8px 6px;text-decoration:none;transition:border-color .12s,box-shadow .12s}
  .mcpban:hover{border-color:#C6D6EA;box-shadow:0 2px 8px rgba(15,23,42,.07)}
  .mcpban img{display:block;width:100%;height:auto}
  .mcpbanc{display:block;margin-top:6px;font-size:11.5px;color:var(--muted)}
  .mcpban:hover .mcpbanc{color:#2B5CB8}
  ol.nxlist{counter-reset:n;list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
  ol.nxlist > li{position:relative;background:#fff;border:1px solid var(--line);padding:11px 14px 12px 48px;box-shadow:0 1px 3px rgba(15,23,42,.04)}
  ol.nxlist > li::before{counter-increment:n;content:counter(n);position:absolute;left:12px;top:11px;width:25px;height:25px;display:flex;align-items:center;justify-content:center;background:#6E5BB8;color:#fff;font-weight:800;font-size:13px}
  @media(max-width:960px){ol.nxlist{grid-template-columns:repeat(2,minmax(0,1fr))}}
  @media(max-width:640px){ol.nxlist{grid-template-columns:1fr}}
  .nxt{font-size:13px;font-weight:800;color:var(--ink);line-height:1.35;display:flex;align-items:baseline;gap:7px;flex-wrap:wrap}
  .nxi{font-size:10.5px;font-weight:700;color:#6E5BB8;text-decoration:none;background:#F4F1FC;border:1px solid #E2DCF6;padding:1px 5px}
  .nxi:hover{background:#EAE4F9}
  .nxb{margin:6px 0 0;padding-left:15px}
  .nxb li{font-size:12px;color:var(--body);line-height:1.5;margin:2px 0}
  .nxb li::marker{color:#6E5BB8}
  .nxd{display:block;margin-top:8px;padding:5px 8px;background:#FFFBF3;border:1px solid #F0E2C8;border-left:2px solid #C98A2E;font-size:11px;color:#8A6420;line-height:1.45}
  .fbhero{background:linear-gradient(135deg,#2E8E84 0%,#3F6FB5 100%);color:#fff;padding:22px 24px;box-shadow:0 1px 3px rgba(15,23,42,.06)}
  .fbeyebrow{font-size:11px;font-weight:800;letter-spacing:1.6px;text-transform:uppercase;opacity:.9}
  .fbh1{margin-top:7px;font-size:23px;font-weight:800;letter-spacing:-.3px}
  .fbsub{margin-top:7px;font-size:13.5px;line-height:1.6;opacity:.96;max-width:820px}
  .fbbtns{display:flex;flex-wrap:wrap;gap:9px;margin-top:14px}
  .fbbtn{display:inline-block;padding:9px 15px;font-size:13px;font-weight:800;text-decoration:none;border:1px solid transparent}
  .fbbtn.primary{background:#fff;color:#1F6B62}
  .fbbtn.primary:hover{background:#F1F7F6}
  .fbbtn.ghost{border-color:rgba(255,255,255,.55);color:#fff}
  .fbbtn.ghost:hover{background:rgba(255,255,255,.13)}
  .sect2{margin:20px 2px 9px;font-size:11px;font-weight:800;letter-spacing:.8px;text-transform:uppercase;color:#1F6B45;display:flex;align-items:center;gap:9px}
  .sect2::after{content:"";flex:1;height:1px;background:var(--line)}
  .fbways{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
  @media(max-width:760px){.fbways{grid-template-columns:1fr}}
  .fbway{position:relative;background:#fff;border:1px solid var(--line);padding:12px 14px 13px 48px;box-shadow:0 1px 3px rgba(15,23,42,.04)}
  .fbwn{position:absolute;left:12px;top:12px;width:25px;height:25px;display:flex;align-items:center;justify-content:center;background:#2E8E84;color:#fff;font-weight:800;font-size:13px}
  .fbway b{display:block;font-size:13px;color:var(--ink)}
  .fbwd{display:block;margin-top:5px;font-size:12.5px;color:var(--body);line-height:1.55}
  .fbwd b{display:inline}
  .fbway a{color:#2B5CB8;font-weight:700;text-decoration:none}
  .fbway a:hover{text-decoration:underline}
  .fbway code{background:#F1F5FA;border:1px solid #E1E8F0;border-radius:5px;padding:1px 6px;font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:12px;color:#3F6FB5}
  .fbdiag{display:block;background:#fff;border:1px solid var(--line);padding:8px 8px 6px;text-decoration:none;box-shadow:0 1px 3px rgba(15,23,42,.04);transition:border-color .12s,box-shadow .12s}
  .fbdiag:hover{border-color:#C6D6EA;box-shadow:0 2px 8px rgba(15,23,42,.07)}
  .fbdiag img{display:block;width:100%;height:auto}
  .fbdiagc{display:block;margin-top:7px;font-size:12px;color:var(--muted);line-height:1.55}
  .fbdiag:hover .fbdiagc{color:#2B5CB8}
  .fbscope{margin-top:14px;background:#FFFBF3;border:1px solid #F0E2C8;border-left:3px solid #C98A2E;padding:11px 14px;font-size:12.5px;color:var(--body);line-height:1.55}
  .fbscope b{color:var(--ink)}
  .fblinks{display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px;margin-top:14px;padding-top:12px;border-top:1px solid var(--line)}
  .fbll{font-size:11px;font-weight:800;letter-spacing:.8px;text-transform:uppercase;color:var(--muted)}
  .fblinks a{font-size:12.5px;font-weight:700;color:#2B5CB8;text-decoration:none;font-family:'SF Mono',ui-monospace,Menlo,monospace}
  .fblinks a:hover{text-decoration:underline}
  .nxcta{margin-top:16px;background:#fff;border:1px solid var(--line);border-left:3px solid #2E8E84;padding:14px 16px;box-shadow:0 1px 3px rgba(15,23,42,.05)}
  .nxctat{font-size:14.5px;font-weight:800;color:var(--ink)}
  .nxctad{margin-top:5px;font-size:13px;color:var(--body);line-height:1.6}
  .nxways{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px}
  .nxway{flex:1 1 300px;border:1px solid var(--line);background:#FBFCFE;padding:10px 12px}
  .nxway b{display:block;font-size:12.5px;color:var(--ink)}
  .nxway span{display:block;margin-top:4px;font-size:12px;color:var(--muted);line-height:1.55}
  .nxway a{color:#2B5CB8;font-weight:700;text-decoration:none}
  .nxway a:hover{text-decoration:underline}
  .nxway code{background:#F1F5FA;border:1px solid #E1E8F0;border-radius:5px;padding:1px 6px;font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:11.5px;color:#3F6FB5}
  .mcprepo:hover{text-decoration:underline}
  .evcard{position:relative;background:#fff;border:1px solid var(--line);border-radius:16px;padding:24px 26px;box-shadow:0 4px 18px rgba(15,23,42,.07);max-width:780px;overflow:hidden}
  .evstripe{position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,#3F6FB5,#2E8E84)}
  .evcard-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-top:4px}
  .evtitle{font-size:21px;font-weight:800;color:var(--ink);letter-spacing:-.3px}
  .evsub{font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:1.4px;color:#3F6FB5;margin-top:4px}
  .evdesc{font-size:13.5px;color:var(--body);line-height:1.6;margin:15px 0 2px}
  .evbtns{display:grid;grid-template-columns:1fr;gap:12px;margin-top:18px}
  .evbtn{display:flex;align-items:center;gap:14px;padding:15px 18px;border-radius:13px;text-decoration:none;transition:.16s;border:1px solid transparent}
  .evbtn svg{flex:0 0 auto}
  .evbtn-l{flex:1;min-width:0}
  .evbtn-t{display:block;font-size:14px;font-weight:800;line-height:1.2}
  .evbtn-s{display:block;font-size:11.5px;margin-top:3px;font-weight:600;opacity:.92}
  .evbtn-arw{font-size:19px;font-weight:800;transition:transform .16s}
  .evbtn:hover .evbtn-arw{transform:translateX(4px)}
  .evbtn.primary{background:linear-gradient(135deg,#3F6FB5,#2E8E84);color:#fff;box-shadow:0 5px 16px rgba(46,142,132,.3)}
  .evbtn.primary:hover{box-shadow:0 8px 24px rgba(46,142,132,.42);transform:translateY(-1px)}
  .evbtn.primary .evbtn-s{color:#EAF6F3}
  .evbtn.ghost{background:#F6F9FD;color:var(--ink);border-color:#DCE6F3}
  .evbtn.ghost:hover{background:#EEF3FA;border-color:#3F6FB5;transform:translateY(-1px)}
  .evbtn.ghost .evbtn-s{color:var(--muted)}
  @media(min-width:600px){.evbtns{grid-template-columns:1fr 1fr}}
  .evtag{font-size:11px;font-weight:800;padding:4px 11px;border-radius:999px;background:#F1F3F6;color:#8A92A0;text-transform:uppercase;letter-spacing:.5px;white-space:nowrap}
  .evtag.cur{background:#E8F2EC;color:#3E8C61}
  ol.setup{counter-reset:s;list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:10px}
  ol.setup li{position:relative;background:#fff;border:1px solid var(--line);padding:13px 16px 13px 54px;font-size:13.5px;color:var(--body);line-height:1.55;box-shadow:0 1px 3px rgba(15,23,42,.04)}
  ol.setup li b{color:var(--ink)}
  ol.setup li a{color:#2B5CB8;font-weight:700}
  ol.setup li code{background:#F1F5FA;border:1px solid #E1E8F0;padding:1px 6px;font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:12px;color:#2B5CB8}
  ol.setup li::before{counter-increment:s;content:counter(s);position:absolute;left:14px;top:12px;width:28px;height:28px;display:flex;align-items:center;justify-content:center;background:#3F6FB5;color:#fff;font-weight:800;font-size:14px}
  .setsrv{display:block;margin-top:6px;font-size:12.5px;color:var(--muted)}
  .setsrv b{color:var(--ink)}
  .setnote{margin-top:14px;background:#EEF3FA;border:1px solid #DCE6F3;padding:11px 14px;font-size:12.5px;color:var(--body);line-height:1.55}
  .setnote b{color:var(--ink)}
  .setgrp{margin:24px 2px 10px;font-size:11px;font-weight:800;letter-spacing:.8px;text-transform:uppercase;color:#1F6B45;display:flex;align-items:center;gap:9px}
  .setgrp::after{content:"";flex:1;height:1px;background:var(--line)}
  ol.setup li .setd{display:block;margin-top:7px;font-size:12.8px;color:var(--body);line-height:1.55}
  pre.setcode{margin:10px 0 2px;background:#0F1E36;border:1px solid #24344F;border-radius:8px;padding:13px 15px;overflow-x:auto;font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:11.8px;line-height:1.65;color:#CBD8EE;white-space:pre}
  .setcred{margin:9px 0 2px;border:1px solid var(--line);border-radius:8px;overflow:hidden}
  .setcred>div{display:grid;grid-template-columns:132px 1fr;border-top:1px solid var(--line)}
  .setcred>div:first-child{border-top:0}
  .setcred .ck{background:#F6F9FD;padding:10px 13px;font-weight:800;color:var(--ink);font-size:12.5px}
  .setcred .cv{padding:10px 13px;color:var(--body);line-height:1.55;font-size:12.8px}
  .setverify{margin:10px 0 2px;background:#EAF6EF;border:1px solid #C7E7D5;border-radius:8px;padding:11px 14px;font-size:12.8px;color:#2C6B4A;line-height:1.6}
  .setverify b{color:#245C3E}
  ol.setup .excmd{margin-top:6px}
  .trouble{margin-top:18px;border:1px solid #EAD9B6;border-radius:10px;overflow:hidden;background:#fff}
  .trouble .th{background:#FBF3E0;padding:11px 15px;font-weight:800;font-size:13px;color:#8A6D2F;display:flex;align-items:center;gap:8px}
  .troubler{display:grid;grid-template-columns:210px 1fr;border-top:1px solid #F0E6CE;font-size:12.6px}
  .troubler .sym{padding:11px 14px;font-weight:700;color:#7A5E28;background:#FCF9EF}
  .troubler .fix{padding:11px 14px;color:var(--body);line-height:1.6}
  .trouble code{background:#F1F5FA;border:1px solid #E1E8F0;padding:1px 5px;border-radius:4px;font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:11.3px;color:#2B5CB8}
  .subtabs{display:flex;flex-wrap:wrap;gap:7px;margin:2px 0 20px}
  .subtab{display:inline-flex;align-items:center;gap:7px;white-space:nowrap;border:1px solid #C4D8F0;background:#EAF1FB;color:#3F6FB5;border-radius:9px;padding:7px 12px 7px 8px;font-size:12.5px;font-weight:700;cursor:pointer;transition:.14s}
  .subtab:hover:not(.on){background:#DCE8F8}
  .subtab .stpn{display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;border-radius:7px;background:#fff;color:#3F6FB5;font-size:11px;font-weight:800}
  .subtab.on{background:#3F6FB5;color:#fff;border-color:#3F6FB5;box-shadow:0 1px 4px rgba(63,111,181,.28)}
  .subtab.on .stpn{background:#fff;color:#3F6FB5}
  .hlead{display:flex;flex-wrap:wrap;gap:10px 20px;align-items:center;justify-content:space-between;margin:2px 2px 15px}
  .hleadtxt{font-size:14px;color:var(--body);flex:1 1 340px;line-height:1.55}
  .hhandled{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
  .hbylab{font-weight:700;letter-spacing:.5px;text-transform:uppercase;font-size:10px;color:var(--faint);margin-right:2px}
  .hby{font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:11.5px;background:#fff;border:1px solid #D9DEE5;color:#46505E;border-radius:999px;padding:4px 10px;cursor:pointer;transition:.12s}
  .hby:hover{border-color:#3F6FB5;color:#3F6FB5}
  .exgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(318px,1fr));gap:14px}
  .exbox{background:#fff;border:1px solid var(--line);border-radius:0;padding:13px;box-shadow:0 1px 3px rgba(15,23,42,.05);display:flex;flex-direction:column;gap:8px}
  .exhead{display:flex;align-items:center;justify-content:space-between;gap:8px;font-weight:800;font-size:13.5px;letter-spacing:-.1px;border-radius:0;padding:8px 11px}
  .exhcat{line-height:1.3}
  .exhper{font-size:9.5px;font-weight:800;letter-spacing:.6px;text-transform:uppercase;opacity:.85;white-space:nowrap}
  .excmd{background:#fff;border:1px solid #D8E2F1;border-radius:0;padding:9px 11px;font-size:12.5px;line-height:1.55;color:#2B5CB8;font-family:'SF Mono',ui-monospace,Menlo,monospace;word-break:break-word}
  .excmd .plab{font-family:Inter,'SF Pro Display',sans-serif;font-weight:700;color:#9AA1AB;margin-right:7px;text-transform:uppercase;font-size:10px;letter-spacing:.4px}
  .excmd .sl{color:#1F3A6B;font-weight:700;margin-right:5px}
  .oralt{align-self:center;font-size:10px;font-weight:700;color:var(--faint);text-transform:uppercase;letter-spacing:.7px;margin:-1px 0}
  .wo4{border:1px solid #D8E2F1;padding:11px 12px;display:grid;grid-template-columns:auto 1fr;gap:5px 11px;align-items:baseline;background:#FCFDFF;margin-top:-8px;border-top:none}
  .wo4 .w4l{font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:9px;font-weight:800;letter-spacing:.55px;color:#93A0B4;text-align:right;white-space:nowrap}
  .wo4 .w4t{font-size:12.4px;line-height:1.5;color:var(--body)}
  .excmd.w4h{padding:8px 11px}
  .exroute{font-size:11.5px;color:var(--muted);font-family:'SF Mono',ui-monospace,Menlo,monospace;line-height:1.5;word-break:break-word}
  .exroute .rlab{font-family:Inter,sans-serif;font-weight:700;text-transform:uppercase;letter-spacing:.4px;font-size:10px;color:var(--faint);margin-right:6px}
  footer{margin-top:26px;color:var(--muted);font-size:12px;text-align:center}
  @media(max-width:820px){.layout{grid-template-columns:1fr}.list{max-height:none}.detail{position:static}}
</style>
</head>
<body>
<header class="hero"><div class="hero-in">
  <div>
    <div class="eyebrow">GTS AI SDLC</div>
    <h1>SDLC Agent Exploration</h1>
  </div>
  <a class="herobtn" href="__REPO__" target="_blank" rel="noopener" title="Open the repository on GitHub Enterprise">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
    <span>dev/gts.ai.sdlc</span><span class="hbarw">&#8599;</span>
  </a>
</div></header>
<main class="wrap">
  <div class="tabs" id="tabs"></div>
  <div class="controls">
    <label class="search">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#9AA1AB" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3" stroke-linecap="round"/></svg>
      <input id="q" type="search" placeholder="Search agents, roles, skills…" autocomplete="off">
    </label>
    <div class="legend" id="legend"></div>
  </div>
  <div class="layout">
    <aside class="list card" id="list"></aside>
    <section class="detail card" id="detail"></section>
  </div>
  <div class="howto" id="howto" style="display:none"></div>
  <div class="howto" id="setup" style="display:none"></div>
  <div class="howto" id="mcp" style="display:none"></div>
  <div class="howto" id="evals" style="display:none"></div>
  <div class="howto" id="next" style="display:none"></div>
  <div class="howto" id="feedback" style="display:none"></div>
  <footer id="foot"></footer>
</main>
<script>
const AGENTS = /*__AGENTS__*/;
const GROUPS = /*__GROUPS__*/;
const SYS = /*__SYS__*/;
const PIPE = /*__PIPE__*/;
const HOWTO = /*__HOWTO__*/;
const MCPS = /*__MCPS__*/;
const EVALS = /*__EVALS__*/;
const NEXT = /*__NEXT__*/;
const FEEDBACK_NEW_ISSUE = "/*__FEEDBACK__*/";
const FEEDBACK_REPO = "/*__FBREPO__*/";
const SDLC_ISSUE_URL = "/*__ISSUEURL__*/";
const GUIDE = ["howto","setup","mcp","evals","next","feedback"];
const PCOL = {"Developer":"#2E8E84","Tester":"#3E9460","Reviewer":"#C2862B","Architect":"#6E5BB8","Release manager":"#3F6FB5","Business analyst":"#C2557A","Product owner":"#B0518F","Ops engineer":"#5B6472","Security engineer":"#C0553B","Build engineer":"#6B7A45","Newcomer":"#8A92A0","Anyone":"#8A92A0"};
let sel = "/*__DEFAULT__*/";
let fTab = "howto", fSkill = null, q = "";
let hStep = HOWTO[0].key;
let hEx   = 0;
let selMcp = MCPS[0].id;
let eStep = EVALS[0].key;

const $ = s => document.querySelector(s);
const esc = s => (s||"").replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const byName = n => AGENTS.find(a => a.name === n);
function syncTab(){ if(GUIDE.includes(fTab)) return; const a=byName(sel); if(a && a.system!=="generic") fTab=a.system; }
function go(n){ if(byName(n)){ sel=n; syncTab(); try{history.replaceState(null,"","#"+n)}catch(e){} render(); } }

function legend(){
  const s = Object.entries(SYS).map(([k,v]) =>
    `<span><span class="dot" style="background:${v.ink}"></span>${v.label}</span>`).join("");
  $("#legend").innerHTML = s +
    `<span><span class="dot" style="background:#C2862B"></span>Opus</span>` +
    `<span><span class="dot" style="background:#3F6FB5"></span>Sonnet</span>` +
    `<span><span class="dot" style="background:#3E9460"></span>GPT-5 mini</span>`;
}
function chipBar(el, opts, cur, on){
  el.innerHTML = opts.map(o =>
    `<button class="chip ${o.v===cur?'on':''}" data-v="${o.v}">${o.t}</button>`).join("");
  el.querySelectorAll(".chip").forEach(b => b.onclick = () => on(b.dataset.v));
}
function match(a){
  if(a.system!=="generic" && a.system!==fTab) return false;
  if(fSkill && !(a.skills.includes(fSkill) || a.skillsCommon.includes(fSkill))) return false;
  if(q){
    const hay = (a.name+" "+a.roleLabel+" "+a.description+" "+a.skills.join(" ")+" "+
      a.skillsCommon.join(" ")+" "+a.servers.join(" ")).toLowerCase();
    if(!hay.includes(q)) return false;
  }
  return true;
}
function renderList(){
  const shown = AGENTS.filter(match);
  let html = "";
  for(const g of GROUPS){
    const items = shown.filter(a => a.group === g);
    if(!items.length) continue;
    html += `<div class="group">${esc(g)}</div>`;
    for(const a of items){
      const sv = SYS[a.system];
      html += `<button class="agent ${a.name===sel?'sel':''}" data-n="${a.name}">
        <span class="bar" style="background:${sv.ink}"></span>
        <span class="sb" style="background:${sv.fill};color:${sv.ink}">${sv.label}</span>
        <div class="an">${esc(a.name)}</div>
        <div class="ar">${esc(a.roleLabel)} · ${esc(a.modelLabel)}</div>
      </button>`;
    }
  }
  if(!html) html = `<div class="none" style="padding:12px">No agents match.</div>`;
  const el = $("#list"); el.innerHTML = html;
  el.querySelectorAll(".agent").forEach(b => b.onclick = () => go(b.dataset.n));
}
function pipeStrip(active){
  let h = `<div class="pipe">`;
  PIPE.forEach((p,i) => {
    h += `<span class="pstep ${i===active?'on':''}"><span class="pnode"></span><span class="pl">${p}</span></span>`;
    if(i<PIPE.length-1) h += `<span class="parrow">›</span>`;
  });
  return h + `</div>`;
}
function pipe(a){
  if(a.role==="orchestrator")
    return `<div class="dtype">Coordinates every phase below — never runs one itself.</div>` + pipeStrip(-1);
  if(a.phase<0) return "";
  return pipeStrip(a.phase);
}
function invokeBlock(iv){
  if(iv.mode==="command"){
    return iv.examples.map(e=>{
      const sp=e.indexOf(" "), cmd=sp>0?e.slice(0,sp):e, rest=sp>0?e.slice(sp):"";
      return `<div class="cmd"><span class="sl">${esc(cmd)}</span>${esc(rest)}</div>`;
    }).join("");
  }
  return `<div class="inote">${esc(iv.note)}</div>` +
    iv.examples.map(e=>`<div class="disp">↳ “${esc(e)}”</div>`).join("");
}
function renderDetail(){
  const a = byName(sel) || AGENTS[0];
  const sv = SYS[a.system];
  const invBadge = a.userInvocable
    ? `<span class="b inv">call it directly</span>` : `<span class="b noinv">internal</span>`;
  let x = "";
  if(fSkill){
    const users = AGENTS.filter(z => z.skills.includes(fSkill)||z.skillsCommon.includes(fSkill)).length;
    x = `<div class="xnote">Filtering by skill <b>${esc(fSkill)}</b> — used by <b>${users}</b> agents.
         <button id="clr">clear</button></div>`;
  }
  const sysSkills = a.skills.length
    ? `<div class="pchips">`+a.skills.map(s=>`<span class="pill sk sys" data-sk="${esc(s)}">${esc(s)}</span>`).join("")+`</div>`
    : `<span class="none">none</span>`;
  const comSkills = a.skillsCommon.length
    ? `<div class="pchips">`+a.skillsCommon.map(s=>`<span class="pill sk" data-sk="${esc(s)}">${esc(s)}</span>`).join("")+`</div>`
    : `<span class="none">none</span>`;
  const servers = a.servers.length
    ? `<div class="tchips">`+a.servers.map(s=>`<span class="pill srv">${esc(s)}</span>`).join("")+`</div>`
    : `<span class="none">no external tool servers — pure reasoning / built-ins</span>`;
  const statuses = a.statuses.length
    ? `<div class="tchips">`+a.statuses.map(s=>`<span class="pill st">${esc(s)}</span>`).join("")+`</div>`
    : `<span class="none">—</span>`;
  const delegates = a.delegates.length
    ? `<div class="tchips">`+a.delegates.map(s=>`<span class="pill srv go" data-go="${esc(s)}">${esc(s)}</span>`).join("")+`</div>`
    : "";
  const reach = `Reach: <b>${a.skills.length+a.skillsCommon.length}</b> skills · <b>${a.servers.length}</b> tool servers`;
  $("#detail").innerHTML = x + `
    <div class="dhead">
      <div>
        <div class="dname">${esc(a.name)}<span class="dsuffix">Agent</span></div>
        <div class="reach">${reach}</div>
      </div>
      <div class="badges">
        <span class="b" style="background:${sv.fill};color:${sv.ink}">${sv.label} · ${sv.name}</span>
        ${invBadge}
      </div>
    </div>
    <div class="drole">${esc(a.roleLabel)}</div>
    ${a.typeNote?`<div class="dtype">${esc(a.typeNote)}</div>`:""}
    ${pipe(a)}
    <div class="sect">What it does</div>
    ${a.useWhen.length?`<div class="uw">Use when</div><ol class="uwl">${a.useWhen.map(u=>`<li>${esc(u)}</li>`).join("")}</ol>`:`<div class="ddesc">${esc(a.description)}</div>`}
    ${a.objective?`<div class="obj"><b>Objective</b> — ${esc(a.objective)}</div>`:""}
    <div class="sect">Invoke it</div>
    ${invokeBlock(a.invoke)}
    <div class="sect">System skills</div>${sysSkills}
    <div class="sect">Common skills</div>${comSkills}
    <div class="sect">Tool / MCP servers</div>${servers}
    <div class="sect">Status codes it returns</div>${statuses}
    ${delegates?`<div class="sect">Delegates to</div>${delegates}`:""}
    <div class="meta">
      <div><div class="k">Model</div><div class="v"><span class="mdot" style="background:${a.modelInk}"></span>${esc(a.model)}</div></div>
    </div>`;
  const clr = $("#clr"); if(clr) clr.onclick = () => { fSkill=null; render(); };
  $("#detail").querySelectorAll("[data-sk]").forEach(el =>
    el.onclick = () => { fSkill = el.dataset.sk; render(); });
  $("#detail").querySelectorAll("[data-go]").forEach(el =>
    el.onclick = () => { fSkill=null; go(el.dataset.go); });
}
function renderHowto(){
  const intro = `<div class="hintro"><b>The agentic output is only as good as your prompt</b>, so keep three principles in mind:
    <ol class="hprin">
      <li><b>Say exactly what you want</b> — the clearer you describe the goal, the more focused, actionable and goal-oriented the agents' work becomes.</li>
      <li><b>Give links and context</b> — the real Jira SIR, GitHub issue or PR, build log or URL behind your request, so the agents ground their work on the right thing.</li>
      <li><b>Treat the agent as a companion, not a test</b> — rather than quizzing its intelligence, share the background, the constraints and what &ldquo;done&rdquo; looks like, and refine together.</li>
    </ol>
    <div class="qm">
      <div class="qmhead">What actually decides the output <span>— five things add up, one subtracts</span></div>
      <div class="qmform">
        <div class="qmres">Agentic output</div><span class="qmop">=</span>
        <div class="qmterm"><b>Harness</b><span>the agent, its skills &amp; tools</span></div><span class="qmop">+</span>
        <div class="qmterm"><b>Prompt</b><span>your work-order</span></div><span class="qmop">+</span>
        <div class="qmterm"><b>Model</b><span>Opus 4.8 &middot; Sonnet 5 &middot; GPT-5 Sol</span></div><span class="qmop">+</span>
        <div class="qmterm"><b>Effective context</b><span>signal &middot; relevance &middot; evidence</span></div><span class="qmop minus">&minus;</span>
        <div class="qmterm bad"><b>Context rot</b><span>noise &middot; stale &middot; confusion</span></div>
      </div>
      <svg class="qmchart" viewBox="0 0 760 128" role="img" aria-label="Output quality stays high through roughly the first fifth of the context window, then falls away as context rot sets in">
        <rect x="52" y="14" width="132" height="86" fill="#EAF6EF"/>
        <rect x="184" y="14" width="524" height="86" fill="#FBF4E8"/>
        <line x1="52" y1="100" x2="708" y2="100" stroke="#D9E2EE" stroke-width="1"/>
        <line x1="52" y1="14" x2="52" y2="100" stroke="#D9E2EE" stroke-width="1"/>
        <line x1="184" y1="10" x2="184" y2="104" stroke="#C98A2E" stroke-width="1.5" stroke-dasharray="4 3"/>
        <path d="M52 26 L184 29 C 250 42, 300 70, 380 84 C 470 97, 590 101, 708 103" fill="none" stroke="#3F6FB5" stroke-width="2.5" stroke-linecap="round"/>
        <text x="46" y="21" font-size="11" fill="#8A92A0" text-anchor="end">high</text>
        <text x="46" y="102" font-size="11" fill="#8A92A0" text-anchor="end">low</text>
        <text x="118" y="94" font-size="10.5" fill="#3E9460" font-weight="700" text-anchor="middle">intelligent zone</text>
        <text x="450" y="46" font-size="10.5" fill="#C98A2E" font-weight="700" text-anchor="middle">context rotting zone</text>
        <text x="184" y="120" font-size="11" fill="#C98A2E" font-weight="700" text-anchor="middle">20%</text>
        <text x="708" y="120" font-size="11" fill="#8A92A0" text-anchor="end">context window used &rarr;</text>
      </svg>
      <div class="qmzones">
        <div class="qmzone"><b>First ~20% — intelligent zone</b><span>fresh intent &middot; relevant evidence &middot; steady tool use</span></div>
        <div class="qmzone rot"><b>The rest — context rotting</b><span>signal diluted &middot; old context wins &middot; task focus lost</span></div>
      </div>
      <div class="qmtake"><b>Bigger context is not better.</b> Useful context creates intelligence; stale context creates rot. So give one task per chat, paste the artifacts that matter, and start a fresh chat for the next one.</div>
    </div>
    <span class="hprinnote">The stages below are real ways people put the team to work &mdash; examples, not limits. If an agent gets something wrong, say <code>/gts-feedback</code> in the same chat and it prepares the ticket, conversation and all.</span></div>`;
  const subtabs = `<div class="subtabs">` + HOWTO.map((s,i)=>
    `<button class="subtab ${s.key===hStep?'on':''}" data-h="${esc(s.key)}"><span class="stpn">${i}</span>${esc(s.label)}</button>`).join("") + `</div>`;
  const step = HOWTO.find(s=>s.key===hStep) || HOWTO[0];
  const handled = (step.handled||[]).map(n=>`<span class="hby" data-go="${esc(n)}">${esc(n)}</span>`).join("");
  const lead = step.lead ? `<div class="hlead"><div class="hleadtxt">${esc(step.lead)}</div>`+
    ((step.handled&&step.handled.length)?`<div class="hhandled"><span class="hbylab">Handled by</span>${handled}</div>`:``)+`</div>` : ``;
  let boxes = step.body ? step.body : `<div class="exgrid">` + (step.examples||[]).map(e=>{
    const pc = PCOL[e.pers] || "#8A92A0";
    const rt = e.route || step.defRoute || "";
    const proms = e.g
      ? `<div class="excmd w4h"><span class="plab">Prompt:</span><span class="sl">/gts-orchestrator</span></div>`+
        `<div class="wo4">`+[["GOAL",e.g],["CONTEXT",e.c],["CONSTRAINTS",e.k],["DONE",e.d]].map(([l,t])=>
          `<span class="w4l">${l}</span><span class="w4t">${esc(t||"")}</span>`).join("")+`</div>`
      : (e.prompts || [e.ask]).map((p,i)=>
        (i>0?`<div class="oralt">or</div>`:``)+
        `<div class="excmd"><span class="plab">Prompt:</span><span class="sl">/gts-orchestrator</span> ${esc(p)}</div>`).join("");
    return `<div class="exbox">`+
      `<div class="exhead" style="background:${pc}20;color:${pc};border:1px solid ${pc}3A">`+
        `<span class="exhcat">${esc(e.cat)}</span><span class="exhper">${esc(e.pers)}</span></div>`+
      proms+
      (rt?`<div class="exroute"><span class="rlab">Routes</span>${esc(rt)}</div>`:``)+
    `</div>`;
  }).join("") + `</div>`;
  if(step.works && step.works.length){
    const xi = Math.min(Math.max(hEx,0), step.works.length-1);
    const w  = step.works[xi];
    boxes += (step.worksHead||"")
      + `<div class="wochips">` + step.works.map((x,i)=>
          `<button class="wochip ${i===xi?'on':''}" data-x="${i}"><span class="wcsys s${esc(x.sys)}">${esc(x.sys)}</span>${esc(x.tag)}</button>`).join("") + `</div>`
      + `<div class="wometa">${esc(w.title)}<span class="wmroute"><span class="rlab">Routes</span>gts-orchestrator → ${esc(w.route)}</span></div>`
      + `<pre class="wocode">${w.code}</pre>`
      + (step.outro||"");
  }
  $("#howto").innerHTML = intro + subtabs + lead + boxes;
  $("#howto").querySelectorAll(".subtab").forEach(b=>b.onclick=()=>{ hStep=b.dataset.h; hEx=0; renderHowto(); });
  $("#howto").querySelectorAll("[data-x]").forEach(b=>b.onclick=()=>{ hEx=+b.dataset.x; renderHowto(); });
  $("#howto").querySelectorAll("[data-go]").forEach(el=>el.onclick=()=>{ fSkill=null; const t=byName(el.dataset.go); if(t) fTab=(t.system==="generic"?"t7":t.system); go(el.dataset.go); });
}
function renderSetup(){
  const D = "https://cortex-mcp.cash.dev.fra.gcp.dbgservice.com";
  $("#setup").innerHTML = `
    <div class="hintro"><b>A step-by-step setup guide</b> &mdash; from zero to a working <code>/gts-orchestrator</code> chat. You need three things: <b>VS Code</b>, <b>GitHub Copilot</b> in Agent mode, and a <b>Cortex <code>mcp.json</code></b> holding the MCP connectors GTS AI SDLC needs, each with its token (Cortex bearer or PAT). Follow the steps in order.</div>

    <div class="setgrp">Before you start</div>
    <ol class="setup">
      <li>Get <b>VS Code</b> with <b>GitHub Copilot</b>, and switch Copilot Chat to <b>Agent mode</b> (custom agents enabled).
        <span class="setd">New to Copilot or Cortex on a Simplify device? Do the one-time enrolment and install first &mdash; it's fully scripted in the <a href="${D}/tutorial" target="_blank" rel="noopener">Cortex setup tutorial</a> (steps 0&ndash;3).</span>
      </li>
      <li><b>Clone the repo and open the folder</b> &mdash; Copilot auto-discovers all <b>${AGENTS.length}</b> agents in <code>.github/agents/</code> and every skill in <code>.agents/skills/</code>.
        <pre class="setcode">git clone https://github.deutsche-boerse.de/dev/gts.ai.sdlc
code gts.ai.sdlc</pre>
        <span class="setd">To check, open Copilot Chat and look in the agent picker for <code>gts-orchestrator</code>, <code>t7-orchestrator</code> and <code>p7-orchestrator</code>.</span>
      </li>
    </ol>

    <div class="setgrp">Add the Cortex MCP servers</div>
    <ol class="setup" style="counter-reset:s 2">
      <li><b>Get your <code>mcp.json</code> from Cortex.</b> Open the <a href="${D}/" target="_blank" rel="noopener">Cortex dashboard</a>, click <b>+ Manage connectors</b>, select the services you need, then click <b>Copy mcp.json</b>. Every server is Cortex-hosted over HTTP, so there is nothing to install or run locally. Full walkthrough: <a href="${D}/tutorial" target="_blank" rel="noopener">tutorial step 4</a>.</li>
      <li><b>Save the config in VS Code as <code>.vscode/mcp.json</code>.</b> In the repo root, create a folder named <code>.vscode</code>, add a file called <code>mcp.json</code> inside it, paste what you copied from Cortex, and save. VS Code detects the file and lists the servers under <b>MCP: List Servers</b> (reload the window if they don't appear yet). The file you copied already has one block like this for <b>every</b> server you selected &mdash; you don't write them by hand:
        <pre class="setcode">{
  "servers": {
    "t7codebase": {
      "type": "http",
      "url": "${D}/v2/mcp/t7codebase",
      "headers": { "Authorization": "Bearer &#36;{input:cortex-bearer}" }
    }
  },
  "inputs": [
    { "type": "promptString", "id": "cortex-bearer",
      "password": true, "description": "Cortex MCP bearer token" }
  ]
}</pre>
        <span class="setd"><code>&#36;{input:cortex-bearer}</code> makes VS Code prompt you for the token the first time the server starts and keep it in its secret store, so the secret never goes in the file. Servers that share a token reuse the same input id.</span>
      </li>
      <li><b>Keep the servers your platform uses.</b> Together they give the agents their full capability &mdash; code, specs, reference data, tickets and review:
        <span class="setsrv"><b>Code &amp; GitHub</b> &mdash; <code>github</code> (the default: repos, PRs, commits, CI, security alerts); the knowledge agents also use <code>github_ghe</code>, and <code>github_dbg</code> for repos on <code>dbg.ghe.com</code></span>
        <span class="setsrv"><b>Specifications</b> &mdash; <code>t7spec</code> for T7, <code>p7spec</code> for P7</span>
        <span class="setsrv"><b>T7 codebase &amp; reference data</b> &mdash; <code>t7codebase</code>, <code>t7dbcopy</code>, <code>eurex_refdata</code></span>
        <span class="setsrv"><b>Tickets &amp; documents</b> &mdash; <code>devops_jira</code> (Jira &amp; SIRs), <code>confluence</code>, <code>sharepoint</code> (spec authoring)</span>
        <span class="setsrv"><b>Review &amp; analysis</b> &mdash; <code>codereviewer_lens</code>, <code>jenkins_lens</code>, <code>sonarqube_lens</code>: code review, build root-cause and Sonar-finding adjudication</span>
        <span class="setd">Names matter &mdash; a server must be called exactly this in <code>mcp.json</code>, because the agents' tool grants name it. See <a href="#mcp">MCP Servers</a> for what each one does.</span>
      </li>
    </ol>

    <div class="setgrp">Add your tokens</div>
    <ol class="setup" style="counter-reset:s 5">
      <li>The copied <code>mcp.json</code> already wires each server's authentication &mdash; you don't edit headers by hand. The first time a server starts, VS Code prompts for the secret it needs and stores it locally. Two cover most setups:
        <div class="setcred">
          <div><div class="ck">Cortex bearer</div><div class="cv">One shared token for the Cortex knowledge, spec and review services (<code>t7codebase</code>, <code>t7spec</code>, <code>p7spec</code>, the three lenses). Get it from the <a href="${D}/" target="_blank" rel="noopener">Cortex dashboard</a> &rarr; <b>Manage connectors</b>.</div></div>
          <div><div class="ck">Jira PAT</div><div class="cv">Its own Personal Access Token for <code>devops_jira</code>, which Cortex passes through to Jira. Create it at <code>devopsjira.deutsche-boerse.com</code> &rarr; <b>Profile &rarr; Personal Access Tokens &rarr; Create token</b>.</div></div>
        </div>
        <span class="setd">Any other server you keep authenticates on its own &mdash; <code>github_ghe</code>, <code>github_dbg</code>, <code>confluence</code>, <code>t7dbcopy</code> and <code>eurex_refdata</code> each prompt for their own token, which you get from that service.</span>
        <span class="setd"><code>t7codebase</code> (T7 Codebase Explorer) also requires membership of the <b>&ldquo;Derivatives &amp; Cash Trading IT&rdquo;</b> Azure AD group &mdash; a <code>403</code> means ask your lead to add you. Microsoft services (Teams, SharePoint, Outlook) sign in with an Azure AD popup on first use. See the <a href="${D}/tutorial" target="_blank" rel="noopener">Cortex tutorial</a>.</span>
        <span class="setd">Typically that's just the Cortex bearer, plus a Jira PAT if you use Jira. Tokens are entered at the VS Code prompt and stored by VS Code &mdash; never committed to the repo.</span>
      </li>
    </ol>

    <div class="setgrp">Check it works</div>
    <ol class="setup" style="counter-reset:s 6">
      <li><b>Verify the servers.</b> Run <b>MCP: List Servers</b> from the Command Palette; every server you kept should read <b>green / running</b>.
        <div class="setverify"><b>Smoke test</b> &mdash; open Copilot Chat, pick <code>gts-orchestrator</code>, and send one of the prompts below. A grounded answer means agents, skills and servers are all wired correctly.</div>
        <div class="excmd"><span class="sl">/gts-orchestrator</span> What is the current state of T7-573481?</div>
        <div class="excmd"><span class="sl">/gts-orchestrator</span> How many commits have been made to resolve T7-573481, and what are they?</div>
        <div class="excmd"><span class="sl">/gts-orchestrator</span> What is the root cause of failure? Please do a deep-dive analysis of this Jenkins build failure: &lt;paste a build URL from gtsci.xeops.deutsche-boerse.de&gt;</div>
      </li>
      <li><b>Start building.</b> Describe any task to <code>/gts-orchestrator</code> &mdash; a Jira SIR, a stack trace or a requirement &mdash; and it routes the work and drives the pipeline. New here? See <a href="#howto">How to use GTS AI SDLC Agents</a> for real examples.</li>
    </ol>

    <div class="trouble">
      <div class="th"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#B8862F" stroke-width="2" aria-hidden="true"><path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></svg>Troubleshooting &mdash; the most common snags</div>
      <div class="troubler"><div class="sym">A server shows red / disconnected</div><div class="fix">Usually the corporate proxy can't reach Cortex &mdash; common on Remote-SSH / WSL / OTD Linux. Add the host to <code>http.noProxy</code> in the <b>Remote</b> settings (Command Palette &rarr; <b>Preferences: Open Remote Settings (JSON)</b>): <code>"http.noProxy": ["cortex-mcp.cash.dev.fra.gcp.dbgservice.com"]</code>, then reload. Details: <a href="${D}/tutorial" target="_blank" rel="noopener">tutorial step 8</a>.</div></div>
      <div class="troubler"><div class="sym">401 / Unauthorized</div><div class="fix">The bearer or Jira PAT is wrong or expired. Re-copy <code>mcp.json</code> from Cortex (or regenerate the Jira PAT), then <b>MCP: List Servers &rarr; Restart</b>. Prefer a long-lived token so it doesn't rotate out from under you.</div></div>
      <div class="troubler"><div class="sym">The agent doesn't appear</div><div class="fix">Copilot Chat isn't in <b>Agent mode</b>, custom agents are off, or the wrong folder is open. Switch to Agent mode, open the <code>gts.ai.sdlc</code> folder (agents live in <code>.github/agents/</code>), and reload the window.</div></div>
      <div class="troubler"><div class="sym"><code>mcp.json</code> isn't picked up</div><div class="fix">Wrong path &mdash; it must be <code>.vscode/mcp.json</code> at the repo root. Check for JSON syntax errors, save, then run <b>MCP: List Servers</b>.</div></div>
      <div class="troubler"><div class="sym">Agents appear, but skills don't load</div><div class="fix">Skills are a separate switch from agents: check <code>chat.useAgentSkills</code> is enabled in Settings, confirm the folder you opened contains <code>.agents/skills/</code>, then reload the window.</div></div>
    </div>

    <div class="setnote"><b>You configure servers, not agents</b> &mdash; an agent reaches a tool only through a skill that wraps its server, so once the servers are in <code>mcp.json</code>, every agent that needs them just works. Still stuck, or something here is wrong? <a href="#feedback">Tell us on the Feedback tab</a>.</div>`;
}
function renderMcp(){
  const intro = `<div class="hintro"><b>Every capability the agents use — through one gateway.</b> Skills reach their tools only through these MCP servers (skill-first access), all Cortex-hosted over HTTP. Pick a server on the left to see what it does and the <b>complete</b> set of tools it exposes — an agent is granted a least-privilege subset of that, never necessarily all of it. Keep the servers your work needs — see <a href="#setup">Setup</a>. <span class="mcpnote">Every hosted server also carries a <code>read_large_content</code> pagination helper, omitted below. The spec authors additionally use the local VS Code Python extension to render a spec to DOCX — that is not a server you configure.</span></div>`;
  const GRP = {review:"Review & analysis", refdata:"T7 codebase & reference data", code:"Code & GitHub", spec:"Specifications", tickets:"Tickets & documents"};
  let list = "";
  for(const g of Object.keys(GRP)){
    const items = MCPS.filter(m=>m.group===g);
    if(!items.length) continue;
    list += `<div class="group">${esc(GRP[g])}</div>`;
    for(const m of items){
      list += `<button class="agent ${m.id===selMcp?'sel':''}" data-m="${esc(m.id)}">`+
        `<span class="bar" style="background:#3F6FB5"></span>`+
        `<div class="an">${esc(m.id)}</div>`+
        `<div class="ar">${esc(m.label)}</div>`+
      `</button>`;
    }
  }
  const m = MCPS.find(x=>x.id===selMcp) || MCPS[0];
  const tools = m.tools.map(t=>`<span class="pill srv">${esc(t)}</span>`).join("");
  const repo = m.repo ? `<a class="mcprepo" href="https://github.deutsche-boerse.de/${esc(m.repo)}" target="_blank" rel="noopener">${esc(m.repo)} \u2197</a>` : `<span class="none">\u2014</span>`;
  const users = AGENTS.filter(a=>a.servers.includes(m.id)).map(a=>a.name);
  const usedby = users.length ? `<div class="tchips">`+users.map(n=>`<span class="pill srv go" data-go="${esc(n)}">${esc(n)}</span>`).join("")+`</div>` : `<span class="none">reached indirectly through skills</span>`;
  const wild = m.tools.length===1 && m.tools[0].endsWith("/*");
  const count = wild ? "whole connector granted" : `${m.tools.length} tool${m.tools.length===1?"":"s"}`;
  const banner = m.banner
    ? `<a class="mcpban" href="${esc(m.banner)}" target="_blank" rel="noopener" title="Open full size">`+
      `<img src="${esc(m.banner)}" alt="How ${esc(m.label)} works" loading="lazy">`+
      `<span class="mcpbanc">How it works &mdash; from the ${esc(m.repo.split("/").pop())} repo &#8599;</span></a>`
    : ``;
  const detail = `<div class="dhead"><div><div class="dname">${esc(m.id)}</div>`+
      `<div class="reach">${count} · Cortex-hosted over HTTP</div></div>`+
      `<div class="badges"><span class="b" style="background:#EEF3FA;color:#2B5CB8">${esc(m.label)}</span></div></div>`+
    `<div class="sect">What it does</div><div class="ddesc">${esc(m.blurb)}</div>`+ banner +
    `<div class="sect">Tools it provides</div><div class="tchips">${tools}</div>`+
    `<div class="sect">Authentication</div><div class="ddesc">${esc(m.auth)}</div>`+
    `<div class="sect">Repository</div>${repo}`+
    `<div class="sect">Used by agents</div>${usedby}`;
  $("#mcp").innerHTML = intro + `<div class="mcplayout"><aside class="list card">${list}</aside><section class="detail card">${detail}</section></div>`;
  $("#mcp").querySelectorAll("[data-m]").forEach(b=>b.onclick=()=>{ selMcp=b.dataset.m; renderMcp(); });
  $("#mcp").querySelectorAll("[data-go]").forEach(el=>el.onclick=()=>{ fSkill=null; const t=byName(el.dataset.go); if(t){ fTab=(t.system==="generic"?"t7":t.system); go(el.dataset.go); } });
}
function renderEvals(){
  const intro = `<div class="hintro"><b>How good are the agents, really?</b> Each benchmarking campaign runs the agents through the <b>agentic harness eval</b> — real T7 / P7 SIRs and tasks scored against frozen oracles — then publishes the scorecards and every artifact the agents produced.</div>`;
  const subtabs = `<div class="subtabs">` + EVALS.map((e,i)=>
    `<button class="subtab ${e.key===eStep?'on':''}" data-e="${esc(e.key)}"><span class="stpn">${i}</span>${esc(e.label)}</button>`).join("") + `</div>`;
  const ev = EVALS.find(e=>e.key===eStep) || EVALS[0];
  const dash = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><rect x="7" y="10" width="3" height="7"/><rect x="12" y="6" width="3" height="11"/><rect x="17" y="13" width="3" height="4"/></svg>`;
  const box = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><path d="M3.27 6.96 12 12.01l8.73-5.05"/><path d="M12 22.08V12"/></svg>`;
  const card = `<div class="evcard"><div class="evstripe"></div>`+
    `<div class="evcard-head"><div><div class="evtitle">${esc(ev.title)}</div><div class="evsub">Agentic Harness Eval</div></div>`+
      `<span class="evtag ${ev.status==="Current campaign"?"cur":""}">${esc(ev.status)}</span></div>`+
    `<div class="evdesc">${esc(ev.blurb)}</div>`+
    `<div class="evbtns">`+
      `<a class="evbtn primary" href="${esc(ev.dashboard)}" target="_blank" rel="noopener">${dash}<span class="evbtn-l"><span class="evbtn-t">View assessment dashboard</span><span class="evbtn-s">Scorecards, radar &amp; per-run results</span></span><span class="evbtn-arw">→</span></a>`+
      `<a class="evbtn ghost" href="${esc(ev.artifacts)}" target="_blank" rel="noopener">${box}<span class="evbtn-l"><span class="evbtn-t">Browse agent artifacts</span><span class="evbtn-s">Every plan, patch &amp; report produced</span></span><span class="evbtn-arw">→</span></a>`+
    `</div></div>`;
  $("#evals").innerHTML = intro + subtabs + card;
  $("#evals").querySelectorAll("[data-e]").forEach(b=>b.onclick=()=>{ eStep=b.dataset.e; renderEvals(); });
}
function renderNext(){
  const intro = `<div class="hintro"><b>What's coming next.</b> In design or in build, deliberately undated &mdash; the order shifts with what people actually ask for, which is why the box at the bottom matters.`+
    `<span class="mcpnote"><b>Disclaimer:</b> Upcoming agentic implementations are subject to approved usage, the AI governance model and risk assessment. Using agents is a shared responsibility: be aware, comply, self-regulate.</span></div>`;
  const cards = NEXT.map(n =>
    `<li><div class="nxt">${esc(n.t)}`+
    (n.i ? `<a class="nxi" href="${SDLC_ISSUE_URL}${n.i}" target="_blank" rel="noopener">#${n.i} &#8599;</a>` : ``)+
    `</div>`+
    (n.b.length ? `<ul class="nxb">`+n.b.map(x=>`<li>${esc(x)}</li>`).join("")+`</ul>` : ``)+
    (n.d ? `<span class="nxd">${esc(n.d)}</span>` : ``)+
    `</li>`).join("");
  const cta = `<div class="nxcta">`+
    `<div class="nxctat">Tell us what you need next</div>`+
    `<div class="nxctad">This list is shaped by the people using the agents. Missing, wrong, slow, or would save you an hour a week? Ideas, needs, feature requests and bugs all go to the same place.</div>`+
    `<div class="nxways">`+
      `<div class="nxway"><b>From the chat you're already in</b><span>Type <code>/gts-feedback</code> right after the thing that went wrong. It captures the conversation, redacts secrets, checks for duplicates and hands you a ready-to-submit ticket.</span></div>`+
      `<div class="nxway"><b>Straight on the feedback page</b><span><a href="${FEEDBACK_NEW_ISSUE}" target="_blank" rel="noopener">Open a bug report or feature request &#8599;</a> &mdash; pick the form and fill it in.</span></div>`+
    `</div></div>`;
  $("#next").innerHTML = intro + `<ol class="nxlist">${cards}</ol>` + cta;
}
function renderFeedback(){
  const html = `<div class="fbhero">`+
      `<div class="fbeyebrow">Feedback &middot; ideas &middot; bug reports</div>`+
      `<div class="fbh1">Tell us what to build, fix or change</div>`+
      `<div class="fbsub">This page is how you shape the agents. Anything about the <b>AI SDLC tooling itself</b> &mdash; an agent that got it wrong, a capability you need, a rough edge that costs you time &mdash; belongs here.</div>`+
      `<div class="fbbtns">`+
        `<a class="fbbtn primary" href="${FEEDBACK_NEW_ISSUE}" target="_blank" rel="noopener">Report a bug or request a feature &#8599;</a>`+
        `<a class="fbbtn ghost" href="${FEEDBACK_REPO}/issues" target="_blank" rel="noopener">Browse what's already reported &#8599;</a>`+
      `</div></div>`+
    `<div class="sect2">Two ways to send it</div>`+
    `<div class="fbways">`+
      `<div class="fbway"><span class="fbwn">1</span><b>From the chat &mdash; <code>/gts-feedback</code></b>`+
        `<span class="fbwd">Run it in the chat where the problem happened. The agent captures the conversation, redacts secrets, checks for duplicates and hands you a one-click, pre-filled issue link. Fastest, and the report carries real evidence.</span></div>`+
      `<div class="fbway"><span class="fbwn">2</span><b>On the feedback page &mdash; a form</b>`+
        `<span class="fbwd"><a href="${FEEDBACK_NEW_ISSUE}" target="_blank" rel="noopener">Open a New issue</a> and pick <b>Bug report</b> or <b>Feature request</b>. Use this when you already know what you want to say, or you're not in a chat session.</span></div>`+
    `</div>`+
    `<div class="sect2">A bug report is best with the conversation attached</div>`+
    `<a class="fbdiag" href="${FEEDBACK_REPO}" target="_blank" rel="noopener">`+
      `<img src="assets/how-to-report.svg" alt="Three steps: capture the chat with Command Palette then Chat: Export Chat, open a ticket with /gts-feedback or the New issue form, then attach the exported chat, redact secrets and submit." loading="lazy">`+
      `<span class="fbdiagc">In VS Code: <b>Command Palette</b> &rarr; <b>Chat: Export Chat</b>, then drag the file into the issue. Redact tokens and PII first &mdash; the tracker is shared. Full guide in the repo &#8599;</span></a>`+
    `<div class="fbscope"><b>Scope.</b> This tracker is only for the AI SDLC tooling &mdash; the agents, skills and pipeline. Defects in <b>T7 / P7 product code</b> go to Jira / SIRs or the product repos, not here.</div>`+
    `<div class="fblinks"><span class="fbll">Feedback repository</span>`+
      `<a href="${FEEDBACK_REPO}" target="_blank" rel="noopener">dev/gts.ai.sdlc-feedback &#8599;</a>`+
      `<a href="${FEEDBACK_NEW_ISSUE}" target="_blank" rel="noopener">New issue &#8599;</a>`+
      `<a href="${FEEDBACK_REPO}/issues" target="_blank" rel="noopener">All issues &#8599;</a>`+
    `</div>`;
  $("#feedback").innerHTML = html;
}
function render(){
  const guide = GUIDE.includes(fTab);
  document.querySelector(".controls").style.display = guide ? "none" : "";
  document.querySelector(".layout").style.display = guide ? "none" : "";
  GUIDE.forEach(t => $("#"+t).style.display = fTab===t ? "" : "none");
  if(fTab==="howto") renderHowto();
  else if(fTab==="setup") renderSetup();
  else if(fTab==="mcp") renderMcp();
  else if(fTab==="evals") renderEvals();
  else if(fTab==="next") renderNext();
  else if(fTab==="feedback") renderFeedback();
  else { renderList(); renderDetail(); }
  document.querySelectorAll("#tabs .tab").forEach(b=>b.classList.toggle("on",b.dataset.v===fTab));
}
function init(){
  legend();
  $("#tabs").innerHTML = [{v:"howto",t:"How to use GTS AI SDLC Agents"},{v:"setup",t:"VS Code SetUp Steps"},{v:"mcp",t:"MCP Servers"},{v:"t7",t:"T7 SDLC Agents"},{v:"p7",t:"P7 SDLC Agents"},{v:"evals",t:"Harness Evals"},{v:"next",t:"What's Next"},{v:"feedback",t:"Feedback"}]
    .map(o=>`<button class="tab" data-v="${o.v}">${esc(o.t)}</button>`).join("");
  $("#tabs").querySelectorAll(".tab").forEach(b=>b.onclick=()=>{
    fTab=b.dataset.v;
    if(!GUIDE.includes(fTab)){
      const cur=byName(sel);
      if(!cur || (cur.system!=="generic" && cur.system!==fTab)) sel=fTab+"-orchestrator";
    }
    try{history.replaceState(null,"",GUIDE.includes(fTab)?"#"+fTab:"#"+sel)}catch(e){}
    render();
  });
  $("#q").oninput = e => { q = e.target.value.trim().toLowerCase(); render(); };
  const fromHash = decodeURIComponent((location.hash || "").replace(/^#/, ""));
  if(GUIDE.includes(fromHash)) fTab=fromHash;
  else if(fromHash && byName(fromHash)){ sel = fromHash; const a=byName(sel); fTab=(a.system==="generic"?"t7":a.system); }
  syncTab();
  window.addEventListener("hashchange", () => {
    const n = decodeURIComponent(location.hash.replace(/^#/, ""));
    if(GUIDE.includes(n)){ fTab=n; render(); }
    else if(byName(n)){ sel = n; const a=byName(n); fTab=(a.system==="generic"?"t7":a.system); render(); }
  });
  $("#foot").innerHTML = `${AGENTS.length} agents · generated from <code>.github/agents/*.agent.md</code> — ` +
    `regenerate with <code>python3 docs/explorer/generate.py</code>`;
  render();
}
init();
</script>
</body>
</html>
"""

html = (TEMPLATE
        .replace("/*__AGENTS__*/", json.dumps(agents, ensure_ascii=False))
        .replace("/*__GROUPS__*/", json.dumps(group_order, ensure_ascii=False))
        .replace("/*__SYS__*/", json.dumps(SYSTEMS, ensure_ascii=False))
        .replace("/*__PIPE__*/", json.dumps(PIPELINE, ensure_ascii=False))
        .replace("/*__HOWTO__*/", json.dumps(HOWTO, ensure_ascii=False))
        .replace("/*__MCPS__*/", json.dumps(MCPS, ensure_ascii=False))
        .replace("/*__EVALS__*/", json.dumps(EVALS, ensure_ascii=False))
        .replace("/*__NEXT__*/", json.dumps(NEXT, ensure_ascii=False))
        .replace("/*__FEEDBACK__*/", FEEDBACK_NEW_ISSUE)
        .replace("/*__FBREPO__*/", FEEDBACK_REPO)
        .replace("/*__ISSUEURL__*/", SDLC_ISSUE_URL)
        .replace("__REPO__", SDLC_REPO)
        .replace("/*__DEFAULT__*/", DEFAULT))

out = os.path.join(HERE, "index.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"wrote {out}  ({len(agents)} agents, {len(html)} bytes)")
