---
name: spec-authoring
description: "Specification document authoring skill. Use when: authoring or generating a formal specification Markdown document (DFS, DTS, SRQ) AFTER the planning phase; structuring DOCX-ready content with a complete metadata header; mapping gathered content into the canonical section model for a given document type; preparing Markdown for conversion via docx_template_tool.py. NOT for planning — the planner produces a lightweight plan artifact, not these documents."
systems: [all]
tools: [read, edit, search]
---

# Spec Authoring — Formal Specification Documents (DFS / DTS / SRQ)

Reusable knowledge for authoring **formal specification documents** that are immediately ready for DOCX conversion. **DFS / DTS / SRQ are a shared corporate document standard** used across GTS systems (T7, P7, and future systems); this skill owns the **document metadata contract**, the **filename convention**, the **revision-history model**, the **common section scaffold**, and the **diagram rules**. The per-type section structure lives in the reference files under [`references/`](references/).

> **System-agnostic** — the cover line and component/chapter examples are illustrative (T7 names are shown as examples). Each system's spec-author agent supplies its own release marker, affected components, and domain content via its system skills.

> **Scope boundary** — This skill is for the **specification phase that runs AFTER planning**. The planner produces a single lightweight planning artifact with no separate documents and no DOCX metadata. This skill produces the separate, governance-grade DFS / DTS / SRQ files that feed the document generator.

---

## Document Types

| Type | Description | Reference file |
|------|-------------|----------------|
| `DFS` | Detailed Functional Specification | [`references/DFS.md`](references/DFS.md) |
| `DTS` | Detailed Technical Specification | [`references/DTS.md`](references/DTS.md) |
| `SRQ` | System Requirement Specification | [`references/SRQ.md`](references/SRQ.md) |

**Always read the reference file for the chosen type in full before authoring.** Each reference is the authoritative source of truth for that type's required metadata, canonical section structure, repeatable blocks, validation rules, and mapping rules.

---

## Authoring Workflow

1. **Identify the document type** (`DFS` / `DTS` / `SRQ`) from the request or context.
2. **Read the matching reference file** in [`references/`](references/) before doing anything else. Do not proceed until it has been read.
3. **Collect and validate the metadata header** (see below). If any required key is missing or blank, stop and ask the user — do not author the body with missing required metadata. Use `TODO – input required` only where the reference's *Default if Missing* column allows it.
4. **Gather content** from real sources (user input, Jira, Confluence, Teams, SharePoint, the system codebase/specs). Never invent content — insert `TODO – input required` and flag the gap where information cannot be found.
5. **Author the body** using the Common Section Scaffold below for the shared chapters and the reference file for the type-specific middle chapters.
6. **Save the file** using the `FILE_NAME` value as the exact filename, in the location the invoking agent specifies.
7. **Report a completeness summary** — filled vs. `TODO` metadata keys, fully authored vs. gapped sections, approximate word count, and the saved path.

---

## Document Metadata Header

Every generated file **must begin** with a `<!-- DOCX-METADATA ... -->` block. The required keys differ per type — the reference file's *Required Metadata* table is authoritative. Common keys across all types:

| Key | Required | Notes |
|-----|----------|-------|
| `DOC_TYPE` | Yes | `DFS` / `DTS` / `SRQ` |
| `PROJECT` | Yes | e.g. `T7 Release 14.1` |
| `TITLE` | Yes | Short document title |
| `SUBJECT` | Yes | One-line subject summary |
| `VERSION` | Yes | e.g. `V0.1` |
| `STATUS` | Yes | `Draft` / `Review` / `Final` (default `Draft`) |
| `AUTHOR` | Yes | Full name(s) |
| `REVIEWER` | Yes | Full name(s) or `TODO – input required` |
| `APPROVER_L1` | Yes | Full name or `TODO – input required` |
| `APPROVER_L2` | No | Optional second approver (`None` if absent) |
| `ABSTRACT` | Yes | 2–5 sentence summary |
| `KEYWORDS` | Yes | Comma-separated keywords |
| `REV_DATE` | Yes | Date of this revision, `YYYY-MM-DD` |
| `REV_AUTHOR` | Yes | Author of this revision |
| `REV_VERSION` | Yes | Same as `VERSION` |
| `REV_REASON` | Yes | Short description of changes |
| `REVISION_HISTORY` | Yes | Full multi-row change log table — see Revision History Model |
| `FILE_NAME` | Yes | See Filename Convention |

Type-specific keys: `DFS_NUMBER` (DFS), `SRQ_NUMBER` (SRQ), `RELEASE` (DFS/SRQ, optional). DTS carries no document-number key.

### Header format in the output file

```markdown
<!-- DOCX-METADATA
DOC_TYPE: DTS
PROJECT: T7 Release 14.1
TITLE: My Specification Title
SUBJECT: Brief subject line
VERSION: V0.2
STATUS: Draft
AUTHOR: Jane Smith
REVIEWER: TODO – input required
APPROVER_L1: TODO – input required
ABSTRACT: This document describes ...
KEYWORDS: T7, RDC, 24/5
REV_DATE: 2026-05-05
REV_AUTHOR: Jane Smith
REV_VERSION: V0.2
REV_REASON: Added section 3.2
REVISION_HISTORY:
| Date | Author | Version | Reason |
|------|--------|---------|--------|
| 2026-05-05 | Jane Smith | V0.2 | Added section 3.2 |
| 2026-05-01 | Jane Smith | V0.1 | Initial draft |
FILE_NAME: DTS141XXX-MyTitle.md
-->
```

---

## Filename Convention

```
<DOC_TYPE><RELEASE_COMPACT><DOC_NUMBER>-<TITLE>.md
```

| Segment | Description | Example |
|---------|-------------|---------|
| `DOC_TYPE` | Uppercase document type | `DTS`, `DFS`, `SRQ` |
| `RELEASE_COMPACT` | Release number with dot removed | `14.1` → `141` |
| `DOC_NUMBER` | 3-digit sequential number within the release; use `XXX` placeholder until officially assigned | `XXX` |
| `-` | Fixed separator | |
| `TITLE` | Abbreviated topic title, no spaces, hyphens allowed | `RDA24-5`, `MarketSeparation` |
| `.md` | Fixed file extension | |

**Examples:** `DTS141XXX-RDA24-5.md`, `DFS141XXX-CUE-RESTISIN.md`, `SRQ141XXX-24x5Trading.md`.

`FILE_NAME` is mandatory. If the short title is not supplied, ask:

> "What should the short title be for the filename?
> Pattern: `<DOC_TYPE><RELEASE_COMPACT>XXX-<TITLE>.md` — Example: `DTS141XXX-RDA24-5.md`"

---

## Revision History Model

- **`REV_DATE` / `REV_AUTHOR` / `REV_VERSION` / `REV_REASON`** — the **current (latest) revision only**. Fills the cover-page version field in the DOCX.
- **`REVISION_HISTORY`** — the **complete change log**, all revisions including the current one, newest first in the header table. At least one row is required. (Reference files note `docx_template_tool.py` consumes the rows **oldest first** as `--revisions`.)

The body **must include a Revision History section** immediately after the title (before section 1), rendered from `REVISION_HISTORY`:

```markdown
## Revision History

| Date | Author | Version | Reason |
|------|--------|---------|--------|
| 2026-05-01 | Jane Smith | V0.1 | Initial draft |
| 2026-05-05 | Jane Smith | V0.2 | Added section 3.2 |
```

This table is the single source for revision information in both the Markdown and the DOCX.

---

## Common Section Scaffold (All Document Types)

Every DFS, DTS, and SRQ shares the same outer skeleton. The reference file defines only what goes **between** the Introduction and the closing Introduction Strategy.

### Cover line

The body opens with a release marker as a level-2 heading, derived from `PROJECT` / `RELEASE`:

```markdown
## <System> - Release <X.X>      <!-- e.g. ## T7 - Release 14.1  or  ## P7 - Release 2.3 -->
```

### Introduction (`# Introduction`)

Always the first numbered chapter, with a fixed set of `##` sub-sections. Some labels differ by type — the reference file states which variant to use:

| Purpose | DFS / DTS wording | SRQ wording |
|---------|-------------------|-------------|
| Business driver | `## Current Situation` + `## Future Situation` (under `## High Level Requirements`) | `## Summary of Business Motivation` |
| Scope summary | covered by `## High Level Requirements` | `## Requirement Summary` |
| Markets | `## Affected Markets` | *(omit)* |
| Assumptions | `## Assumptions` | `## Assumptions` |
| Exclusions | `## Out of Scope` | `## Out of Scope` *(or `## Out of Scope and Assumptions`)* |
| Open items | `## Open Points` / `## Open Questions` *(optional)* | *(in the Dependencies and Open Issues chapter)* |
| References | `## Related Documents and Inputs` | `## Related Documents` |
| Terminology | `## Abbreviations and Glossary` | `## Abbreviations and Important Terms` |

Rules common to all types:
- `Affected Markets`: a table, or `Not applicable`.
- `Assumptions` / `Out of Scope`: content or `None`.
- The terminology sub-section is a two-column table (`Term` | `Description`).

### Closing — Introduction Strategy

Every document ends with an **Introduction Strategy** block. The wrapper heading differs by type (the reference states it), but the three sub-sections are fixed:
- `## Initial Settings`
- `## Migration Tools/Conversion`
- `## Example Setup for Test`

### Heading-to-style mapping (all types)

| Markdown | Word style |
|----------|------------|
| `# Heading` | `Heading 1` |
| `## Heading` | `Heading 2` |
| `### Heading` | `Heading 3` |
| `#### Heading` | `Heading 4` |
| Markdown tables | Word tables (template default table style) |
| Markdown bullet lists | Word bullet lists |

---

## Diagrams and Visual Content

- **Always use Mermaid** — render diagrams as fenced ` ```mermaid ` blocks.
- **Use default Mermaid colors** — never add `style`, `classDef`, `fill:`, `stroke:`, or `color:` overrides. The only allowed `%%{init: ...}%%` directive is for layout, not color.
- **Diagram consistency** — when a later diagram relates to an earlier one: reuse the same diagram type, preserve existing node names/IDs/shapes/groupings, and only add/extend/highlight. Render a subset as a zoomed/annotated view of the original, never a redesign.

---

## Constraints

- **Do NOT invent content** — only use information from the user, MCP sources, or the workspace.
- **Do NOT author the body** while required metadata keys are missing — ask first.
- **Do NOT alter the canonical section structure** defined by the reference file for the chosen type.
- **Do NOT change terminology** — preserve all system-specific names exactly as they appear.
- **Do NOT use custom Mermaid colors** and **do NOT redesign an existing diagram**.
- One Markdown file per invocation.

---

## Output Format

The output file contains, in order:
1. `<!-- DOCX-METADATA ... -->` block with all metadata
2. `# <TITLE>` H1 heading
3. `## Revision History` table
4. Document body following the canonical section structure
5. All content sourced from real inputs (no hallucinations)
