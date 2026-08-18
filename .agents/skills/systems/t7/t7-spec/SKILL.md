---
name: t7-spec
description: "T7 Trading System specification and domain knowledge. Use when: reading, writing, or referencing T7 functional specifications, interface documents, or ETI/FIX LF/EOBI protocol specs; understanding order lifecycle states; identifying instrument types; naming reference documents (DFS/SRQ/MFG/MTD/DTS); searching the T7 spec corpus via MCP tools; answering questions about T7 SUMMIT work products, document review/sign-off/final phases, naming and versioning conventions, and where to find or access the supporting artifacts."
systems: [t7]
tools: [t7spec/*]
---

# T7 Spec — Functional Specification & Domain Knowledge

Use this skill when working with T7 functional specifications, interface definitions, protocol documentation, or any domain-level design questions about the T7 Trading System. This skill also governs all direct interactions with the T7 spec corpus via the `t7spec` MCP tools — **agents must always delegate spec lookups to this skill rather than calling the MCP tools directly**.

---

## T7 Spec MCP Tool Usage

### Tool Selection Guide

| Tool | When to use | Typical latency |
|------|-------------|-----------------|
| `mcp_t7spec_grep` | Exact term, DFS/SRQ/SIR number, or abbreviation — fastest, 100% recall | ~170ms |
| `mcp_t7spec_search` | Known keywords, ranked results needed | ~1-2s |
| `mcp_t7spec_vsearch` | Natural-language question; vocabulary may differ from spec terminology | ~3-5s |
| `mcp_t7spec_query` | Best-quality hybrid search with re-ranking, for complex or vague requirements | ~3-6s |
| `mcp_t7spec_get` | Read a full spec document by path or docid | — |
| `mcp_t7spec_multi_get` | Read several related spec files at once using a glob pattern | — |
| `mcp_t7spec_status` | Check availability and index status of the spec server | — |

### Usage Rules

1. **Always start with `mcp_t7spec_grep`** for any DFS/SRQ/SIR number or exact abbreviation — it is the fastest tool with 100% recall for exact terms.
2. **Follow up with `mcp_t7spec_query`** for the conceptual area if the grep yields no relevant documents — it provides the best-quality hybrid results for vague or natural-language queries.
3. **Use `mcp_t7spec_vsearch`** when the query vocabulary may not match the spec terminology (e.g., "order expiry" vs. "order cancellation on session end").
4. **Read full spec sections** with `mcp_t7spec_get` before drafting tasks or making implementation decisions — do not rely on snippet summaries alone.
5. **Use `mcp_t7spec_multi_get`** to load several related spec files (e.g., all DTS files for a component) in one call using a glob pattern.
6. **Record all spec document IDs** consulted so the plan or implementation can cross-reference them.

### Query Strategy by Task Type

| Task | Recommended query sequence |
|------|---------------------------|
| Find spec for a feature by Jira/DFS number | `mcp_t7spec_grep` (number) → `mcp_t7spec_get` (doc) |
| Understand a business rule or workflow | `mcp_t7spec_query` (concept) → `mcp_t7spec_get` (section) |
| Find all specs for a component | `mcp_t7spec_grep` (component name) → `mcp_t7spec_multi_get` (glob) |
| Verify implementation against spec | `mcp_t7spec_grep` (class or field name) → `mcp_t7spec_get` (doc) |
| Explore unfamiliar feature area | `mcp_t7spec_vsearch` (plain language) → `mcp_t7spec_query` (refined) → `mcp_t7spec_get` |

---

## T7 Document Types

T7 specifications use the following document type prefixes. Document IDs take the form `{doctype}{XXXXX}-{description}-v{version}-{status}`. Incomplete list of document types:

| Prefix | Type | Example |
|--------|------|---------|
| **DFS** | Detailed Functional Specification | `dfs10070-smp-enhancement` |
| **SRQ** | System Requirements | `srq6052-security-concept-t7-release-6-final` |
| **MFG** | Market Functional Guide | `mfg141002-t7-functional-reference-version-1-r14-1-2-0-final` |
| **MTD** | Manual / Technical Document | `mtd141015-fix-lf-manual-r14-1-2-0-final` |
| **SRA** | System Requirements Analysis | `sra40x10-high-level-functional-differences-cash-market-t7` |
| **DTS** | Design / Technical Specification | `dts151xxx-rda-24-5-reference-data-propagation-concept` |
| **SIR** | System Incident Report | — |
| **BRA** | Business Requirements Analysis | — |

---

## SUMMIT Work Product Process

T7 work products (WPs) follow a structured review cycle administered by the Project Management Office (PMO), sometimes called SUMMIT. Work products include specification documents, internal readiness documents, and also non-document artifacts like database schemas.

### Phases

Work products go through the following phases in order:

| Phase | Description |
|-------|-------------|
| **Review** | Just created; to be reviewed by colleagues with detailed understanding of the content |
| **Sign-Off** | Sign-off by senior executives responsible for the relevant area |
| **Final** | Document is published and can be used by T7 users |

### File Naming and Version Scheme

Document ID scheme:
```
<type prefix><release number><document number> - <title>_R<release number with dots>_<document version>_<status>
```
Example: `DTS141096 - File Transfer Configuration_R14.1_2.3_Final`

Version number conventions:

| Phase | Version |
|-------|---------|
| Review | 1.0 |
| Sign-Off | 1.1 |
| Final | 2.0 |

The minor version digit increments for each iteration within a phase (e.g. Sign-Off may start at 1.5 after 4 review iterations). Version numbers restart at 1.0 for each new release.

All created versions have to be listed in the history section of each document, even if no changes were made (like "xy version created (no changes)" in reason column). Review
phase can be skipped if there are no changes (then Sign-Off has version 1.0).

### Accessing Work Product Artifacts

- **Alfresco** (official): `https://alfresco.deutsche-boerse.de/alfresco/XDM/n/myalfresco` — no MCP available
- **SharePoint**: Theoretically accessible via SharePoint MCP (may be unreliable). Sample R14.1 path: `T7 Releases > T7_R14_1 > 05 WPs R14.1 > Work Products > DTS141096 File Transfer Config Guide`
- **t7spec MCP tools**: May provide access to published documents — check with `mcp_t7spec_grep` or `mcp_t7spec_get`
- **If unavailable**: Ask the user to supply the document/artifact directly

### References

- SUMMIT manual (v2.1): [SharePoint](https://deutscheboerse.sharepoint.com/sites/ps0051/Shared%20Documents/Forms/AllItems.aspx?id=%2Fsites%2Fps0051%2FShared%20Documents%2F07%20Sol%2D3%2F99%20Summit%2FDBG%20Summit%20Manual%5Fv2%2E1%5Ffinal%2Epdf&parent=%2Fsites%2Fps0051%2FShared%20Documents%2F07%20Sol%2D3%2F99%20Summit) — local copy in `t7-spec/assets/DBG Summit Manual_v2.1_final.pdf`
- SUMMIT Work Products Workflow: local copy in `t7-spec/assets/SUMMIT Work Products Workflow.pdf`

