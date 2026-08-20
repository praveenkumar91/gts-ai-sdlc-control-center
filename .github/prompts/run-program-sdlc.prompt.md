---
name: run-program-sdlc
description: "Start the visible governed SDLC for a feature, bug fix, refactor, GUI change, migration, or multi-repository integration."
agent: program-orchestrator
argument-hint: "Describe the change and provide requirement/ticket/design references"
---

Run the agent-only multi-repository SDLC for this request. Begin with exactly the seven todo items from the `multi-repo-orchestration` skill and show the same status table in this chat. Resolve authoritative requirements, ask the smallest focused question when material information is missing, select only impacted repositories from `.github/gts-repositories.json`, obtain one GTS planning response per affected system, independently review and re-review real plan revisions, stop at Human Gate 1, execute approved repository tasks through GTS in bounded dependency waves, independently verify requirement closure, prepare linked draft PRs, and stop at Human Gate 2. Do not run Python control-plane scripts, hooks, graph schemas, or search for another control-plane catalog.

User request: ${input:request:Describe the feature, fix, refactor, migration, or GUI change}

Known requirement or ticket sources: ${input:sources:DFS/FSD/DTS/SRQ/Jira/Confluence/design paths or links, or say unknown}
