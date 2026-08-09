---
name: document-rendering
description: "Word/DOCX document rendering skill. Use when: a request needs a Word (.docx) deliverable rendered from Markdown an agent has produced or been given; turning a DOCX-METADATA specification, a report, or any Markdown artifact into a co-located .docx; adding a document artifact on demand without replacing the Markdown source. NOT for authoring content — the producing agent (spec-author, analyst, etc.) writes the Markdown; this skill only renders it to Word."
systems: [all]
tools: [read, edit, search, execute, ms-python.python/getPythonEnvironmentInfo, ms-python.python/getPythonExecutableCommand, ms-python.python/installPythonPackage, ms-python.python/configurePythonEnvironment]
---

# Document Rendering — Markdown → Word (.docx)

Reusable capability for turning **Markdown into a Word document** when a request requires a document deliverable. This is a **shared, system-agnostic** capability: any agent that produces a document-worthy Markdown artifact (a formal DFS/DTS/SRQ specification, an analysis report, a summary) can use it to render a `.docx`.

> **Additive, never destructive.** Markdown is always the canonical source artifact. The `.docx` is a rendered **companion** — rendering never deletes, replaces, or overwrites the Markdown, and is only produced when a Word document is actually requested or required.

---

## When to Render

Render a `.docx` when **any** of these is true:

- the user explicitly asks for a **Word document**, a **`.docx`**, or a **document / deliverable** output;
- the invoking agent's workflow requires a Word artifact (e.g. a governance-grade specification that must be delivered as a document);
- an orchestrator or human gate says the artifact must be delivered as a document.

Do **not** render a `.docx` when the user only asked for Markdown, a plan, an inline answer, or code. When in doubt, produce the Markdown and ask whether a Word document is wanted.

---

## The Renderer

Use the bundled, **dependency-free** renderer (standard-library Python only — no `python-docx`, no `pandoc`, so it runs anywhere a Python interpreter is available):

```
.agents/skills/common/document-rendering/tools/docx_template_tool.py
```

### Invocation

```bash
python3 .agents/skills/common/document-rendering/tools/docx_template_tool.py \
  --input <path/to/source>.md \
  --output <path/to/output>.docx
```

- The positional form `docx_template_tool.py <source>.md` also works; `--output` defaults to the `FILE_NAME` stem (from the metadata header) with a `.docx` extension, written next to the source.
- If the environment does not expose `python3`, obtain the interpreter with the `ms-python.python/getPythonExecutableCommand` tool and run the same script with that executable.
- Running the script requires the agent's `execute` tool. An agent that lacks `execute` cannot render — it must only produce the Markdown and report that the DOCX was not rendered.

### What it renders

- Reads an optional `<!-- DOCX-METADATA -->` header and maps `TITLE` / `SUBJECT` / `AUTHOR` / `KEYWORDS` into the Word core document properties.
- Maps Markdown into WordprocessingML: `#`–`####` headings → Word `Heading1`–`Heading4`; Markdown tables → Word tables; bullet and numbered lists → Word lists; paragraphs with inline emphasis/links/code flattened to text; fenced code / `mermaid` blocks → a labelled monospaced block.
- Writes a valid `.docx` (OOXML) package and leaves the Markdown source untouched.
- Markdown with **no** metadata header renders too — the body is converted and default document properties are used.

---

## Output Convention

Write the `.docx` **next to** the Markdown, using the same filename stem:

| Source Markdown | Rendered Word document |
|-----------------|------------------------|
| `specs/t7/DTS141XXX-RDA24-5.md` | `specs/t7/DTS141XXX-RDA24-5.docx` |
| `specs/p7/DFS230XXX-RiskLimit.md` | `specs/p7/DFS230XXX-RiskLimit.docx` |

Both files are kept. The Markdown remains the source of truth; the `.docx` is the rendered deliverable.

---

## Failure Handling

If rendering fails:

- **keep the Markdown file** — it is the completed source artifact;
- report the **exact error** and mark the DOCX as **not produced**;
- never silently claim a Word document exists.

Do not fall back to hand-writing a binary `.docx`, and do not alter the Markdown to work around a render error.

---

## Constraints

- DOCX rendering is **additive** — never remove, replace, or overwrite the Markdown output.
- Do **not** author or edit document content in this skill — render only. Content authoring belongs to the producing agent.
- Do **not** introduce third-party dependencies — the renderer is intentionally standard-library only.
- Preserve terminology and content exactly as written in the Markdown source.
