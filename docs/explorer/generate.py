#!/usr/bin/env python3
"""Generate a self-contained interactive Agent Explorer (docs/explorer/index.html)
from the real agent frontmatter in .github/agents/*.agent.md.

Run:  python3 docs/explorer/generate.py
No dependencies; output is a single static HTML file (works via file:// and GitHub Pages).
"""
import glob, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
AGENT_DIR = os.path.join(ROOT, ".github", "agents")

BUILTIN_TOOLS = {"read", "edit", "search", "execute", "agent", "todo"}
STATUS_STOP = {"DO", "NOT", "MUST", "ALWAYS", "NEVER", "AND", "OR", "THE", "DFS", "DTS",
               "SRQ", "SIR", "TDD", "MCP", "PR", "RED", "GREEN", "OWASP", "JQL", "JSON",
               "WIP", "URL", "API", "P7", "T7", "GTS", "VET", "QA", "CM", "HTTP", "YAML"}

ROLE_ORDER = {"orchestrator": 0, "planner": 1, "architect": 2, "spec-author": 3, "tester": 4,
              "developer": 5, "reviewer": 6, "builder": 7, "pr-author": 8, "knowledge": 9}
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
GROUP_LABEL = {"generic": "Generic · router & clarifier",
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
HOWTO = [
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
        "key": "ship", "label": "Build & ship",
        "lead": "Compile the affected components in dependency order, then package the change into a clean, ticket-linked pull request with release notes.",
        "handled": ["t7-sdlc-builder", "t7-sdlc-pr-author"],
        "defRoute": "gts-orchestrator → t7-orchestrator → t7-sdlc-builder / t7-sdlc-pr-author",
        "examples": [
            {"pers": "Build engineer", "cat": "Resolve the build order", "route": "gts-orchestrator → t7-orchestrator → t7-sdlc-builder",
             "prompts": ["What's the correct build order for eurex.cilmsg and its dependents, and build them?"]},
            {"pers": "Build engineer", "cat": "Diagnose a broken build", "route": "gts-orchestrator → t7-orchestrator → t7-sdlc-builder",
             "prompts": ["The build fails after the GOLD-linker change (T7-573865). Build it, capture the error, and tell me what broke.", "Build the linker-change set (T7-573865); if it fails, show the first error and the culprit component."]},
            {"pers": "Release manager", "cat": "PR title + summary only", "route": "gts-orchestrator → t7-orchestrator → t7-sdlc-pr-author",
             "prompts": ["Give me a conventional-commit PR title and a one-paragraph summary for the CoMa validation fix (T7-572008)."]},
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
             "ask": "Write the PR for the SpA rejection fix (T7-574620), link the ticket, and use conventional-commit style.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-pr-author"},
            {"pers": "Release manager", "cat": "Generate release notes",
             "ask": "Generate the release notes for everything merged under DFS150510 this iteration.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-pr-author"},
            {"pers": "Developer", "cat": "Turn my branch into a clean PR",
             "ask": "Turn my current branch into a clean PR \u2014 conventional-commit title, summary and test notes.",
             "route": "gts-orchestrator \u2192 t7-orchestrator \u2192 t7-sdlc-pr-author"},
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
    tail = re.split(r"(?i)\buse when:\s*", desc, maxsplit=1)
    tail = tail[1] if len(tail) > 1 else desc
    parts = [p.strip(" .") for p in re.split(r";\s+", tail) if p.strip(" .")]
    if len(parts) < 2:
        parts = [p.strip(" .") for p in re.split(r",\s+", tail) if p.strip(" .")]
    return parts[:6]


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
  .hero{background:linear-gradient(135deg,#5E54C8 0%,#3F6FB5 52%,#2E8E84 100%);color:#fff;padding:34px 24px 30px}
  .hero-in{max-width:1180px;margin:0 auto}
  .hero .eyebrow{font-size:12.5px;font-weight:700;letter-spacing:2.5px;opacity:.85}
  .hero h1{margin:8px 0 6px;font-size:30px;font-weight:800;letter-spacing:-.4px}
  .hero .sub{margin:0;font-size:15px;opacity:.94;max-width:860px}
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
  .layout{display:grid;grid-template-columns:344px 1fr;gap:20px;align-items:start}
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
  .tabs{display:flex;gap:8px;border-bottom:2px solid var(--line);margin:12px 0 22px}
  .tab{padding:11px 22px;font-size:15.5px;font-weight:700;color:#fff;cursor:pointer;border:2px solid #3F6FB5;background:#3F6FB5;border-radius:12px 12px 0 0;margin-bottom:-2px;transition:.14s;position:relative;top:4px}
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
  .hintro b{color:var(--ink)}
  .hintro code{background:#F1F5FA;border:1px solid #E1E8F0;border-radius:5px;padding:1px 6px;font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:12px;color:#3F6FB5}
  .subtabs{display:flex;flex-wrap:wrap;gap:6px;margin:2px 0 20px;border-bottom:2px solid var(--line)}
  .subtab{display:inline-flex;align-items:center;gap:8px;border:2px solid #C4D8F0;background:#DCE8F8;color:#3F6FB5;border-radius:11px 11px 0 0;padding:9px 15px 9px 10px;font-size:13.5px;font-weight:700;cursor:pointer;transition:.14s;position:relative;top:3px;margin-bottom:-2px}
  .subtab:hover:not(.on){background:#CFE0F5;top:1px}
  .subtab .stpn{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:7px;background:#fff;color:#3F6FB5;font-size:12px;font-weight:800}
  .subtab.on{background:#fff;color:var(--ink);top:0;border-bottom-color:#fff;box-shadow:inset 0 3px 0 #3F6FB5,0 -3px 8px rgba(15,23,42,.05)}
  .subtab.on .stpn{background:#E7F0FB;color:#3F6FB5}
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
  .exroute{font-size:11.5px;color:var(--muted);font-family:'SF Mono',ui-monospace,Menlo,monospace;line-height:1.5;word-break:break-word}
  .exroute .rlab{font-family:Inter,sans-serif;font-weight:700;text-transform:uppercase;letter-spacing:.4px;font-size:10px;color:var(--faint);margin-right:6px}
  footer{margin-top:26px;color:var(--muted);font-size:12px;text-align:center}
  @media(max-width:820px){.layout{grid-template-columns:1fr}.list{max-height:none}.detail{position:static}}
</style>
</head>
<body>
<header class="hero"><div class="hero-in">
  <div class="eyebrow">GTS AI SDLC</div>
  <h1>SDLC Agent Exploration</h1>
  <p class="sub">Explore the whole team — pick an agent to see what it does and how to invoke it, or open <b>How to use GTS AI SDLC Agents</b> for the main things you can ask for and how each request is dispatched.</p>
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
  <footer id="foot"></footer>
</main>
<script>
const AGENTS = /*__AGENTS__*/;
const GROUPS = /*__GROUPS__*/;
const SYS = /*__SYS__*/;
const PIPE = /*__PIPE__*/;
const HOWTO = /*__HOWTO__*/;
const PCOL = {"Developer":"#2E8E84","Tester":"#3E9460","Reviewer":"#C2862B","Architect":"#6E5BB8","Release manager":"#3F6FB5","Business analyst":"#C2557A","Product owner":"#B0518F","Ops engineer":"#5B6472","Security engineer":"#C0553B","Build engineer":"#6B7A45","Newcomer":"#8A92A0","Anyone":"#8A92A0"};
let sel = "/*__DEFAULT__*/";
let fTab = "t7", fSkill = null, q = "";
let hStep = HOWTO[0].key;

const $ = s => document.querySelector(s);
const esc = s => (s||"").replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const byName = n => AGENTS.find(a => a.name === n);
function syncTab(){ if(fTab==="howto") return; const a=byName(sel); if(a && a.system!=="generic") fTab=a.system; }
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
  const intro = `<div class="hintro"><b>One entry point, the whole team behind it.</b> In VS Code, open Copilot Chat, pick <code>gts-orchestrator</code> from the agent selector (or type <code>/gts-orchestrator</code>) and describe what you want — paste a Jira SIR, a GitHub issue, a stack trace, a requirement note or a code snippet, and ask for one thing or ten. It clarifies your request, routes it to <b>P7</b> or <b>T7</b>, and delegates each step to the right specialist; you never pick an internal agent yourself. Below, by SDLC stage, are real ways different people invoke it.</div>`;
  const subtabs = `<div class="subtabs">` + HOWTO.map((s,i)=>
    `<button class="subtab ${s.key===hStep?'on':''}" data-h="${esc(s.key)}"><span class="stpn">${i+1}</span>${esc(s.label)}</button>`).join("") + `</div>`;
  const step = HOWTO.find(s=>s.key===hStep) || HOWTO[0];
  const handled = step.handled.map(n=>`<span class="hby" data-go="${esc(n)}">${esc(n)}</span>`).join("");
  const lead = `<div class="hlead"><div class="hleadtxt">${esc(step.lead)}</div>`+
    `<div class="hhandled"><span class="hbylab">Handled by</span>${handled}</div></div>`;
  const boxes = `<div class="exgrid">` + step.examples.map(e=>{
    const pc = PCOL[e.pers] || "#8A92A0";
    const rt = e.route || step.defRoute || "";
    const proms = (e.prompts || [e.ask]).map((p,i)=>
      (i>0?`<div class="oralt">or</div>`:``)+
      `<div class="excmd"><span class="plab">Prompt:</span><span class="sl">/gts-orchestrator</span> ${esc(p)}</div>`).join("");
    return `<div class="exbox">`+
      `<div class="exhead" style="background:${pc}20;color:${pc};border:1px solid ${pc}3A">`+
        `<span class="exhcat">${esc(e.cat)}</span><span class="exhper">${esc(e.pers)}</span></div>`+
      proms+
      (rt?`<div class="exroute"><span class="rlab">Routes</span>${esc(rt)}</div>`:``)+
    `</div>`;
  }).join("") + `</div>`;
  $("#howto").innerHTML = intro + subtabs + lead + boxes;
  $("#howto").querySelectorAll(".subtab").forEach(b=>b.onclick=()=>{ hStep=b.dataset.h; renderHowto(); });
  $("#howto").querySelectorAll("[data-go]").forEach(el=>el.onclick=()=>{ fSkill=null; const t=byName(el.dataset.go); if(t) fTab=t.system; go(el.dataset.go); });
}
function render(){
  const howto = fTab==="howto";
  document.querySelector(".controls").style.display = howto ? "none" : "";
  document.querySelector(".layout").style.display = howto ? "none" : "";
  $("#howto").style.display = howto ? "" : "none";
  if(howto) renderHowto();
  else { renderList(); renderDetail(); }
  document.querySelectorAll("#tabs .tab").forEach(b=>b.classList.toggle("on",b.dataset.v===fTab));
}
function init(){
  legend();
  $("#tabs").innerHTML = [{v:"t7",t:"T7 SDLC Agents"},{v:"p7",t:"P7 SDLC Agents"},{v:"howto",t:"How to use GTS AI SDLC Agents"}]
    .map(o=>`<button class="tab" data-v="${o.v}">${esc(o.t)}</button>`).join("");
  $("#tabs").querySelectorAll(".tab").forEach(b=>b.onclick=()=>{
    fTab=b.dataset.v;
    if(fTab!=="howto"){
      const cur=byName(sel);
      if(!cur || (cur.system!=="generic" && cur.system!==fTab)) sel=fTab+"-orchestrator";
    }
    try{history.replaceState(null,"",fTab==="howto"?"#howto":"#"+sel)}catch(e){}
    render();
  });
  $("#q").oninput = e => { q = e.target.value.trim().toLowerCase(); render(); };
  const fromHash = decodeURIComponent((location.hash || "").replace(/^#/, ""));
  if(fromHash==="howto") fTab="howto";
  else if(fromHash && byName(fromHash)) sel = fromHash;
  syncTab();
  window.addEventListener("hashchange", () => {
    const n = decodeURIComponent(location.hash.replace(/^#/, ""));
    if(n==="howto"){ fTab="howto"; render(); }
    else if(byName(n)){ sel = n; syncTab(); render(); }
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
        .replace("/*__DEFAULT__*/", DEFAULT))

out = os.path.join(HERE, "index.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"wrote {out}  ({len(agents)} agents, {len(html)} bytes)")
