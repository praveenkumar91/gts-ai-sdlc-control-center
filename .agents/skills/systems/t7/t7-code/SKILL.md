---
name: t7-code
description: "T7 codebase navigation and code retrieval. Use when: locating source files in T7 components, searching for classes or functions in the T7 codebase, reading large source files by chunk, listing files within a component by pattern, confirming the latest T7 release baseline, understanding component structure and build dependencies. Covers all interactions with the t7codebase MCP tools — agents must always delegate codebase lookups to this skill rather than calling the MCP tools directly."
systems: [t7]
tools: [t7codebase/*]
user-invocable: false
---

# T7 Code — Codebase Navigation & Retrieval

Use this skill whenever you need to locate, read, or explore T7 source code. This skill governs **all** direct interactions with the `t7codebase` MCP tools — agents must always delegate codebase lookups to this skill rather than calling the MCP tools directly.

---

## T7 Codebase MCP Tool Usage

### Tool Selection Guide

| Tool | When to use |
|------|-------------|
| `mcp_t7codebase_list_releases` | Confirm the latest release baseline before any search |
| `mcp_t7codebase_list_projects` | Confirm available projects and environments (standard: `project=t7`, `env=eurex`) |
| `mcp_t7codebase_search_codebase` | Find classes, functions, configuration parameters, or symbols by keyword |
| `mcp_t7codebase_list_files` | Enumerate files within a component using `component` + `pattern` filters |
| `mcp_t7codebase_page_index_search` | Locate pages (sections) within a large source file by keyword |
| `mcp_t7codebase_get_page_chunk` | Read a specific page/chunk of a large source file by page ID |

### Usage Rules

1. **Always call `mcp_t7codebase_list_releases` first** in any session before searching or reading code — pin every result to the confirmed latest release.
2. **Use `mcp_t7codebase_list_projects`** once per session to confirm `project=t7`, `env=eurex` are correct before querying.
3. **Use `mcp_t7codebase_search_codebase`** for symbol or keyword searches. Start with the most specific terms (exact class name, method name, enum value); broaden if no results.
4. **Use `mcp_t7codebase_list_files`** with a `component` path (from the `t7-knowledge-base` skill) and a `pattern` (e.g., `*.cpp`, `*Test*`) to list actual files before referencing them in tasks or reviews.
5. **Use `mcp_t7codebase_page_index_search` + `mcp_t7codebase_get_page_chunk`** to navigate and read large files — never fabricate file content; always retrieve it.
6. **Never reference a file path or class name** that has not been verified through one of the tools above.

### Query Strategy by Task Type

| Task | Recommended tool sequence |
|------|--------------------------|
| Confirm release baseline | `list_releases` |
| Find where a class is defined | `search_codebase` (class name) → `get_page_chunk` (file) |
| Find all files in a component | `list_files` (component + pattern) |
| Read a specific source file | `page_index_search` (file name) → `get_page_chunk` (section) |
| Find test files for a component | `list_files` (component, pattern=`*Test*` or `*_test*`) |
| Find all callers of a function | `search_codebase` (function name) |
| Verify a class hierarchy | `search_codebase` (base class) → `get_page_chunk` (header) |
| Locate build dependency metadata | `list_files` (component, pattern=`component.json`) → `get_page_chunk` |

---

## Standard Session Setup

At the start of any session involving code navigation, run these two calls once:

```
mcp_t7codebase_list_releases()          → pin to latest release
mcp_t7codebase_list_projects()          → confirm project=t7, env=eurex
```

Record the release value and use it as the baseline for all subsequent references.

---

## File Enumeration Pattern

To list files in a component, always supply both `component` (from the `t7-knowledge-base` skill Component Map) and a `pattern`:

```
mcp_t7codebase_list_files(component="<verified-component-path>", pattern="*.cpp")
mcp_t7codebase_list_files(component="<verified-component-path>", pattern="*Test*")
```

Do not pass fabricated component paths — resolve them from the `t7-knowledge-base` skill first.

---

## Large File Navigation Pattern

For source files too large to read in one chunk:

1. `mcp_t7codebase_page_index_search(query="<class or function name>")` → find the page IDs containing the relevant section.
2. `mcp_t7codebase_get_page_chunk(page_id="<id>")` → read that section in full.

Repeat step 2 for adjacent sections as needed to gather complete context before writing or reviewing code.

---

## Search Quality Rules

- Try at least **three distinct search strategies** (e.g., class name → method name → related enum) before concluding a symbol is NOT_FOUND.
- When a search returns too many results, narrow by adding the component name or module scope as an additional term.
- When a search returns nothing, broaden by trying related T7 terminology — consult the `t7-knowledge-base` skill for canonical term variants.
- Always read the **surrounding context** of every match — never act on a single line in isolation.

---

## Constraints

- DO NOT fabricate class names, method signatures, or file paths — verify everything through the tools.
- DO NOT skip `list_releases` at the start of a session — always pin to the confirmed latest release.
- DO NOT call `t7codebase` MCP tools from agent instructions directly — all calls must flow through this skill.
