# SRQ — System Requirement Specification Skill

## Binding Mechanism

Placeholder tokens: `{{FIELD_NAME}}`

## Required Metadata

| Key | Required | Default if Missing |
|-----|----------|--------------------|
| `PROJECT` | Yes | `TODO – input required` |
| `TITLE` | Yes | `TODO – input required` |
| `SUBJECT` | Yes | `TODO – input required` |
| `SRQ_NUMBER` | Yes | `TODO – input required` |
| `VERSION` | Yes | `TODO – input required` |
| `STATUS` | Yes | `Draft` |
| `AUTHOR` | Yes | `TODO – input required` |
| `REVIEWER` | Yes | `TODO – input required` |
| `APPROVER_L1` | Yes | `TODO – input required` |
| `APPROVER_L2` | No | `None` |
| `ABSTRACT` | Yes | `TODO – input required` |
| `KEYWORDS` | Yes | `TODO – input required` |
| `RELEASE` | No | `None` |

## Revision History

Source: the `REVISION_HISTORY` change log in the `<!-- DOCX-METADATA -->` header, which the author mirrors into the body `## Revision History` table. The renderer converts that body table directly into the DOCX.

| Column | Description |
|--------|-------------|
| `date` | `YYYY-MM-DD` |
| `author` | Full name |
| `version` | e.g. `V0.1` |
| `reason` | Short description of changes |

At least one row required.

## Canonical Section Structure

The cover line, the shared Introduction chapter, and the closing Introduction Strategy are defined once in the **Common Section Scaffold** of the author agent. Note that SRQ uses distinct Introduction sub-headings (see the scaffold's SRQ column) and places Introduction Strategy under an Appendix.

```
## <System> - Release <X.X>                   ← cover line (common scaffold)

# Introduction                                ← SRQ sub-blocks:
   ## Summary of Business Motivation
   ## Requirement Summary
   ## Assumptions
   ## Out of Scope                            ← or "Out of Scope and Assumptions"
   ## Open Point                              ← optional
   ## Related Documents
   ## Abbreviations and Important Terms

# Functional Requirement Details              ← a.k.a. "High Level Functional Description(s)"
   ## <Topic>                                 ← repeatable

# High Level Solution Description
   ## <Solution topic>                        ← repeatable

# Dependencies and Open Issues
   ## Dependencies Regarding Other T7 Requirements
   ## Dependencies Regarding Other Systems (Upstream / Downstream)
   ## Open Issues

# Impact Summary
   ## Impact on Components and Downstream Systems
   ## Impact of Requirement on Transaction Load

# Appendix
   ## Introduction Strategy                   ← closing block (common scaffold sub-sections)
       ### Initial Settings
       ### Migration Tools/Conversion
       ### Example Setup for Test
   ## Interface Changes                       ← optional
   ## Enabling New Functionality              ← optional
```

## Repeatable Blocks

**Functional Requirement Details** — describe the business/functional requirements as one or more `## <Topic>` sub-sections. Releases vary between `# Functional Requirement Details` and `# High Level Functional Description(s)`; use whichever fits the source, defaulting to `Functional Requirement Details`.

**High Level Solution Description** — describe the proposed solution per `## <Solution topic>`.

## Validation Rules

- All required metadata keys present; missing → `TODO – input required`
- Cover line `## <System> - Release <X.X>` present
- `# Introduction` present with the SRQ sub-blocks listed above
- `# Functional Requirement Details` (or `High Level Functional Description`) present with at least one topic
- `# High Level Solution Description` present
- `# Dependencies and Open Issues` present with its three sub-sections
- `# Impact Summary` present
- `# Appendix` present containing `## Introduction Strategy` with the three fixed sub-sections
- `Abbreviations and Important Terms`: two-column table (`Term` | `Description`)
- `Open Issues`: content or `None`

## Mapping Rules

Heading levels map to Word styles per the **Common Section Scaffold** table (`#`→Heading 1, `##`→Heading 2, `###`→Heading 3, `####`→Heading 4). Markdown tables → Word tables; Markdown bullet lists → Word bullet lists. YAML metadata keys → template placeholder tokens `{{KEY}}` on the cover page.
