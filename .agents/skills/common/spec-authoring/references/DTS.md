# DTS — Detailed Technical Specification Skill

## Binding Mechanism

Placeholder tokens: `{{FIELD_NAME}}`

## Required Metadata

| Key | Required | Default if Missing |
|-----|----------|--------------------|
| `PROJECT` | Yes | `TODO – input required` |
| `TITLE` | Yes | `TODO – input required` |
| `SUBJECT` | Yes | `TODO – input required` |
| `VERSION` | Yes | `TODO – input required` |
| `STATUS` | Yes | `Draft` |
| `AUTHOR` | Yes | `TODO – input required` |
| `REVIEWER` | Yes | `TODO – input required` |
| `APPROVER_L1` | Yes | `TODO – input required` |
| `APPROVER_L2` | No | `None` |
| `ABSTRACT` | Yes | `TODO – input required` |
| `KEYWORDS` | Yes | `TODO – input required` |

## Revision History

Source: the `REVISION_HISTORY` change log in the `<!-- DOCX-METADATA -->` header, which the author mirrors into the body `## Revision History` table. The renderer converts that body table directly into the DOCX.

| Column | Description |
|--------|-------------|
| `date` | `YYYY-MM-DD` |
| `author` | Full name |
| `version` | e.g. `V0.1` |
| `reason` | Short description of changes |

At least one row required. Additional rows are appended in ascending date order (oldest first).

## Canonical Section Structure

The cover line, the shared Introduction sub-blocks, and the closing Introduction Strategy are defined once in the **Common Section Scaffold** of the author agent. Follow that for the shared parts; this skill defines the technical middle chapters that sit between them.

```
## <System> - Release <X.X>                   ← cover line (common scaffold)

# Introduction                                ← see common scaffold; DTS sub-blocks:
   ## High Level Requirements
   ## Current Situation
   ## Future Situation
   ## Affected Markets
   ## Assumptions
   ## Open Points                             ← optional
   ## Out of Scope
   ## Related Documents and Inputs
   ## Open Questions                          ← optional
   ## Abbreviations and Glossary

# Detailed Requirement Description            ← a.k.a. "Detailed Solution Description"
   ## <Topic>                                 ← repeatable

# <Technical change chapter>                  ← repeatable; include those that apply:
   # Changes in RDS Model and Application     (## UML Model, ## RDS Application)
   # Changes in the WSS Interface
   # Changes in Architecture
   # Changes in the Core Components           (## Matching Engine, ## Post Processing Engine (PoPE))
   # Changes to other T7 Components
   # Overview of Affected System Components and External Systems
                                              (## Affected T7 System Areas,
                                               ## Affected External Interfaces/Systems)
   # Required Changes to the T7 Components/Area
                                              (## Required Changes to the <Component>)

# Introduction Strategy                       ← closing block (common scaffold)
   ## Initial Settings
   ## Migration Tools/Conversion
   ## Example Setup for Test
```

## Repeatable Blocks

**Detailed Requirement Description** — one `## <Topic>` sub-section per requirement topic; nest `###` for detail. Some releases title this chapter `# Detailed Solution Description` — use whichever the source material uses, otherwise default to `Detailed Requirement Description`.

**Technical change chapters** — author only the change chapters that apply to the design. Each affected layer gets its own top-level `#` chapter with `##` sub-sections per component or interface.

## Validation Rules

- All required metadata keys present; missing → `TODO – input required`
- Cover line `## <System> - Release <X.X>` present
- `# Introduction` present with the DTS sub-blocks listed above
- `# Detailed Requirement Description` (or `Detailed Solution Description`) present with at least one topic
- At least one technical change chapter present
- Closing `# Introduction Strategy` present with all three sub-sections
- `Affected Markets`: a table or `Not applicable`
- `Abbreviations and Glossary`: two-column table (`Term` | `Description`)

## Mapping Rules

Heading levels map to Word styles per the **Common Section Scaffold** table (`#`→Heading 1, `##`→Heading 2, `###`→Heading 3, `####`→Heading 4). Markdown tables → Word tables; Markdown bullet lists → Word bullet lists. YAML metadata keys → template placeholder tokens `{{KEY}}` on the cover page.
