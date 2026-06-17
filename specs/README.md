# specs/

Output location for **formal specification documents** authored during the specification phase (after planning).

- `specs/t7/` — T7 DFS / DTS / SRQ documents produced by the `t7-sdlc-spec-author` agent.
- `specs/p7/` — P7 DFS / DTS / SRQ documents produced by the `p7-sdlc-spec-author` agent.
- `specs/{system}/` — one folder per system, populated by that system's `{system}-sdlc-spec-author` agent.

DFS / DTS / SRQ are a **shared corporate document standard** (common `spec-authoring` skill). Each system's spec-author supplies its own release marker, components, and domain content.

These files carry a `<!-- DOCX-METADATA -->` header and the canonical section structure defined by the common `spec-authoring` skill, and are ready for DOCX conversion via `docx_template_tool.py`.

> Planning artifacts are **not** stored here — the planner produces a lightweight in-conversation plan, not a separate document.

> **Not to be confused with the Ralph loop's `specs/`.** The autonomous build loop (driven by the `t7-orchestrator` agent) uses its own behavioural `specs/` — flat `NN-kebab-case.md` files that are the loop's source of truth (WHAT, not HOW). Those live in the **target system's working tree** (e.g. the T7 codebase), **not** in this framework repo, and carry no DOCX metadata. The formal DFS/DTS/SRQ documents described here are a separate, governance-grade artifact.
