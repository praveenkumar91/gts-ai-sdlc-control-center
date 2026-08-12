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
| **Localise a change (which exact files to touch)** | run the **File Localisation Playbook** (below) — it composes the rows beneath into one ranked, evidence-tagged file set |
| Confirm release baseline | `list_releases` |
| Find where a class is defined | `search_codebase` (class name) → `get_page_chunk` (file) |
| Find all files in a component | `list_files` (component + pattern) |
| Read a specific source file | `page_index_search` (file name) → `get_page_chunk` (section) |
| Find test files for a component | `list_files` (component, pattern=`*Test*` or `*_test*`) |
| Find all callers of a function | `search_codebase` (function name) |
| Verify a class hierarchy | `search_codebase` (base class) → `get_page_chunk` (header) |
| Locate build dependency metadata | `list_files` (component, pattern=`module-info.xml`) → `get_page_chunk` (declared forward deps); for reverse-deps / build order use the `gts-build-graph` skill |

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

## File Localisation Playbook — from requirement/symptom to the exact file set

> **`t7-code`'s highest-value capability.** Planner, developer, tester and reviewer all depend on it — naming the *exact* files a change must touch is the biggest single driver of a correct plan or fix. Optimise for **both** precision (no wrong or fabricated file) **and** recall (no missing coordinated file). Localise to the **fix locus**, not the symptom.

**Input**: a requirement or a bug symptom (+ any symbols, reason codes, log lines, ticket text).
**Output**: a **ranked, evidence-tagged file set** — each file with a role (impl / header / call-site / test / build-config), a tag `[confirmed | likely | candidate | new-planned]`, and the query that proves it.

> **Skill composition:** `t7-code` wraps only the `t7codebase` MCP. Steps that need vocabulary translation, component/owner facts, or change history are performed by the **calling agent** (planner / developer / tester / reviewer), which also loads `t7-spec`, `t7-knowledge-base` and `github`; this playbook tells that agent how to sequence them.

0. **Session setup (once)** — `list_releases` (pin the latest) + `list_projects` (`project=t7, env=eurex`). Every path is relative to this baseline.
1. **Translate business → code vocabulary, and narrow to a component — before any code search.** The symptom is *business* language; the code index is keyword-ranked, so a raw symptom rarely matches real identifiers ("crossed order book butterfly" will not find `CrossingDetector`). Bridge the gap first:
   - **The spec corpus is the Rosetta Stone (primary).** Run the symptom through the semantically-indexed specs via the **`t7-spec` skill** (`vsearch` = semantic; `search` = BM25) — the DFS/DTS/SRQ restate the symptom in **canonical T7 vocabulary** and name the components, messages, and attributes involved. Harvest those canonical nouns + named symbols as your code-search terms. *(Real example: "crossed order book butterfly" → the "Synthetic Matching for Condors and Butterflies" DFS, which says the **uncrossing** procedure prevents **crossed-orderbook** situations from **synthetic matching** — so search code for `uncross`/`crossing`/`synthetic`, not "butterfly". "month/year not set for display source" → a DFS naming the **Contract Manager** + `displayYearSource`.)*
   - **The glossary is the secondary bridge.** Expand abbreviations and map term → module/owner via the **`t7-knowledge-base` skill** (`t7-abbreviations.md`, `t7-modules.md`, `t7-component-map.md`). A cross-team touch is a risk flag.
   Output of this step: the `component` scope **and** a set of code-vocabulary search terms for Step 2. Don't grep the whole tree with business words.
2. **Find where the behaviour is defined — iterate; never single-shot.** Seed the search with the most *concrete identifiers* you have — an exact class / function / enum / reason-code / config-key / **error string / message-type / log token** lifted from the symptom, its logs / stack trace, **and the canonical terms + named components harvested in Step 1**, never a vague business phrase. Then loop until confirmed:
   - `search_codebase(<terms>)` scoped to the component → **read** the top hits (`page_index_search` → `get_page_chunk`).
   - If the hits are only *in the neighbourhood* (right component / family, not the actual locus), **extract the concrete symbols the code you just read uses** and **re-search those**. Repeat.
   - **Exit only when you have read the candidate and confirmed it *decides* the behaviour** (not merely mentions it). Try ≥3 term variants before concluding NOT_FOUND.

   > **Single-shot symptom search is unreliable.** Keyword ranking, plus the gap between *business* vocabulary (the symptom) and *code* vocabulary (the real class / function names), makes a whole-tree or symptom-phrase search land in the wrong place — or only in the right neighbourhood. Bridging that gap by reading a neighbour and re-searching its real symbols is **mandatory**, not optional.
3. **Trace to the root cause, not the symptom** — the file that *emits* a symptom (log line, reason code, exception) is often not the one that must change. Follow the call/data path back to where the behaviour is actually decided, and localise there.
4. **Fan out to every coordinated file** — a real T7 change rarely touches one file:

   | Coordinated file | How to find it |
   |---|---|
   | Header ↔ impl pair (`.hxx` ↔ `.cxx`) | `list_files(component, "<basename>.*")` |
   | **Call sites / usages** of a changed symbol or signature | `search_codebase("<symbol>")` across components. Enumerate **all** when the change alters a public interface, signature, enum, or shared contract; for internal-only changes include the **representative** callers needed to verify the locus, not every passive usage |
   | Subclasses / implementers of a changed interface | `search_codebase("<base class>")` → read the header |
   | **Test file(s)** for the locus | `list_files(component, "*Test*")` · `"*_test*"` · `"test_*"` (GTest / Catch2 / JUnit / pytest) |
   | **Build / config / data** (new file, or changed symbol / dependency / interface / schema) | `list_files(component, "module-info.xml")` (declared deps) + `CMakeLists.txt`, config (`*.xml` / `*.cfg`), and **SQL/schema** (`*.sql`) or generated/model files when the change is non-C++ |

5. **Corroborate with change history (high-signal)** — when the **`github`** skill is available, inspect recent merged PRs/commits on the component: files that *historically change together* with your locus (logical coupling) are strong candidates you would otherwise miss (evidence, not proof). If `github` is unavailable, record `history: skipped`.
6. **Rank, tag, justify** — per file emit `path · role · tag · proving query`. **Every tag requires a *verified* path:**
   - **[confirmed]** = path exists (you read it) **and** it is the fix locus.
   - **[likely]** = path exists **and** is coordinated by a verified rule (header↔impl pair, direct caller, matching test, build/config).
   - **[candidate]** = path **verified to exist**, but its relevance to the fix is uncertain → developer to confirm.
   - **[new-planned]** = file does **not** exist yet; its **parent directory and naming convention are verified** (via `list_files` on analogous files) and its creation is justified by an acceptance criterion.

   **Never tag an unverified or guessed path.** If a path itself cannot be verified, do not list it in the file set — record it as a **discovery / risk item** with the search strategies tried. Prefer a well-reasoned superset over dropping a real file; never invent a path.

> **Illustrative shape** (replace with verified names): requirement "reject an expired-instrument order with reason code X" → (1) KB: order-validation → **OFI** + owning team; (2) `search_codebase("ExpiredInstrument")` → `OrderValidator.cxx` **[confirmed]**; (3) root cause is the validator, not the gateway that logs it; (4) header `OrderValidator.hxx` **[likely]**, caller `OrderGateway.cxx` **[likely]**, test `OrderValidatorTest.cxx` **[confirmed]**; (5) recent OFI PRs also touched `ReasonCodes.hxx` → **[likely]**; (6) emit the ranked set.

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
