# DFS — Detailed Functional Specification Skill

## Binding Mechanism

Placeholder tokens: `{{FIELD_NAME}}`

## Required Metadata

| Key | Required | Default if Missing |
|-----|----------|--------------------|
| `PROJECT` | Yes | `TODO – input required` |
| `TITLE` | Yes | `TODO – input required` |
| `SUBJECT` | Yes | `TODO – input required` |
| `DFS_NUMBER` | Yes | `TODO – input required` |
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

The cover line, the shared Introduction sub-blocks, and the closing Introduction Strategy are defined once in the **Common Section Scaffold** of the author agent. Follow that for the shared parts; this skill defines the functional middle chapters that sit between them.

```
## <System> - Release <X.X>                   ← cover line (common scaffold)

# Introduction                                ← see common scaffold; DFS sub-blocks:
   ## High Level Requirements
   ## Current Situation
   ## Future Situation
   ## Affected Markets
   ## Assumptions
   ## Out of Scope
   ## Open Points                             ← optional
   ## Related Documents and Inputs
   ## Abbreviations and Glossary

# <Functional Topic>                          ← repeatable, free-named functional chapters
   ## / ### subsections for rules, GUI views, use cases

# Introduction of Changes to System Components
   ## Impacted Components

# Data Model and Reference Data               ← a.k.a. "Required Changes to RDS and RDA"
   ## RDS Changes
   ## RDA Changes

# Required Changes to <Component>             ← repeatable, one per affected component:
                                                Matching Engine, TES Manager, T7 GUIs,
                                                ETI / ETI Gateway, OFI / OFI Gateway,
                                                OPM, XML Reports, ...

# Settings                                    ← closing Introduction Strategy (common scaffold);
   ## Initial Settings                          DFS titles this block "Settings"
   ## Migration Tools/Conversion
   ## Example Setup for Test
```

## Repeatable Blocks

**Functional topic chapters** — the functional description is organised as one or more top-level `#` chapters named after the feature (e.g. `# Pre-Trade Risk Limits for Future Spreads`), not as generic "Requirement 3.x" blocks. Each chapter nests `##` / `###` sub-sections for rules, GUI views, and use cases as needed.

**Component change chapters** — author one `# Required Changes to <Component>` chapter per affected T7 component. Common components: Matching Engine, TES Manager, T7 GUIs (Admin / Control / Trader), ETI / ETI Gateway, OFI / OFI Gateway, OPM, XML Reports.

## Validation Rules

- All required metadata keys present; missing → `TODO – input required`
- Cover line `## <System> - Release <X.X>` present
- `# Introduction` present with the DFS sub-blocks listed above
- At least one functional topic chapter present
- `# Introduction of Changes to System Components` present
- `# Data Model and Reference Data` present when reference data is affected, otherwise `Not applicable`
- At least one `# Required Changes to <Component>` chapter when components are impacted
- Closing Introduction Strategy block present with all three sub-sections (`Initial Settings`, `Migration Tools/Conversion`, `Example Setup for Test`)
- `Abbreviations and Glossary`: two-column table (`Term` | `Description`)

## Mapping Rules

Heading levels map to Word styles per the **Common Section Scaffold** table (`#`→Heading 1, `##`→Heading 2, `###`→Heading 3, `####`→Heading 4). Markdown tables → Word tables; Markdown bullet lists → Word bullet lists. YAML metadata keys → template placeholder tokens `{{KEY}}` on the cover page.
