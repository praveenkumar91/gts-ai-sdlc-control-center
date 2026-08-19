---
name: run-program-sdlc
description: "Start the visible governed SDLC for a feature, bug fix, refactor, GUI change, migration, or multi-repository integration."
agent: program-orchestrator
argument-hint: "Describe the change and provide requirement/ticket/design references"
---

Run the complete visible program SDLC for this request. Begin with the thirteen-stage todo and status table. Resolve authoritative requirements, ask for missing material information, select the impacted repository subgraph, independently review and re-review the plan, stop at Human Gate 1, execute approved tasks in bounded dependency waves, independently verify requirement closure, prepare linked draft PRs, and stop at Human Gate 2.

User request: ${input:request:Describe the feature, fix, refactor, migration, or GUI change}

Known requirement or ticket sources: ${input:sources:DFS/FSD/DTS/SRQ/Jira/Confluence/design paths or links, or say unknown}
