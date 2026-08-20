---
name: run-program-sdlc
description: "Start the visible governed SDLC for a feature, bug fix, refactor, GUI change, migration, or multi-repository integration."
agent: program-orchestrator
argument-hint: "Describe the change and provide requirement/ticket/design references"
---

Run the agent-only multi-repository SDLC for this request. Begin with exactly the seven todo items from the `multi-repo-orchestration` skill and show the same status table in this chat. Resolve authoritative requirements, discover every Git repository inside all VS Code workspace folders, ask for a parent folder, `.code-workspace` file, local paths, or Git URLs only when that workspace is incomplete, and select impact from a lightweight runtime inventory. Deep-read only plausible candidates, freeze exact selected commits in the reviewed plan, obtain one GTS planning response per affected system, independently review and re-review real plan revisions, stop at Human Gate 1, execute approved repository tasks through GTS in bounded dependency waves, independently verify requirement closure, prepare linked draft PRs, and stop at Human Gate 2. Do not run Python control-plane scripts, hooks, graph schemas, or create a central repository catalog.

User request: ${input:request:Describe the feature, fix, refactor, migration, or GUI change}

Known requirement or ticket sources: ${input:sources:DFS/FSD/DTS/SRQ/Jira/Confluence/design paths or links, or say unknown}
