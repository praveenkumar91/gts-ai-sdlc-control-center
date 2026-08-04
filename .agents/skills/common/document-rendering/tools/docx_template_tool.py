#!/usr/bin/env python3
"""Render a DOCX file from a DOCX-METADATA Markdown specification.

This tool intentionally has no third-party dependencies so SDLC agents can use it
from a standard Python installation. It preserves the Markdown source and writes
the Word document to the requested output path.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import zipfile
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Iterable, Sequence


METADATA_RE = re.compile(r"\A<!--\s*DOCX-METADATA\s*\n(.*?)\n-->\s*", re.S)
KEY_RE = re.compile(r"^([A-Z][A-Z0-9_]*):\s*(.*)$")


def parse_metadata(markdown: str) -> tuple[dict[str, str], str]:
    """Return (metadata, markdown_without_metadata_header)."""
    match = METADATA_RE.match(markdown)
    if not match:
        return {}, markdown

    block = match.group(1)
    metadata: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    def flush_current() -> None:
        nonlocal current_key, current_lines
        if current_key is not None:
            metadata[current_key] = "\n".join(current_lines).strip()
        current_key = None
        current_lines = []

    for line in block.splitlines():
        key_match = KEY_RE.match(line)
        if key_match:
            flush_current()
            key, value = key_match.groups()
            if key == "REVISION_HISTORY":
                current_key = key
                current_lines = [value] if value else []
            else:
                metadata[key] = value.strip()
            continue
        if current_key is not None:
            current_lines.append(line)

    flush_current()
    return metadata, markdown[match.end() :]


def parse_revision_table(table_text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in table_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 4:
            continue
        if cells[0].lower() == "date" or set(cells[0]) <= {"-", ":"}:
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        rows.append(cells[:4])
    return rows


def parse_revisions(value: str | None, metadata: dict[str, str]) -> list[list[str]]:
    if value:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = ast.literal_eval(value)
        return [[str(item) for item in row[:4]] for row in parsed]
    return parse_revision_table(metadata.get("REVISION_HISTORY", ""))


def clean_inline(text: str) -> str:
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
    text = re.sub(r"(\*|_)(.*?)\1", r"\2", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text.replace("<br>", "\n").strip()


def w_text(text: str) -> str:
    return f'<w:t xml:space="preserve">{escape(text, quote=False)}</w:t>'


def paragraph(text: str, style: str | None = None, numbering: str | None = None) -> str:
    ppr = ""
    if style:
        ppr += f'<w:pStyle w:val="{style}"/>'
    if numbering:
        num_id = "1" if numbering == "bullet" else "2"
        ppr += f'<w:numPr><w:ilvl w:val="0"/><w:numId w:val="{num_id}"/></w:numPr>'
    ppr_xml = f"<w:pPr>{ppr}</w:pPr>" if ppr else ""
    parts = str(text).split("\n")
    runs = []
    for index, part in enumerate(parts):
        if index:
            runs.append("<w:r><w:br/></w:r>")
        runs.append(f"<w:r>{w_text(part)}</w:r>")
    return f"<w:p>{ppr_xml}{''.join(runs)}</w:p>"


def table(rows: Sequence[Sequence[str]]) -> str:
    if not rows:
        return ""
    trs = []
    for row in rows:
        cells = "".join(
            "<w:tc><w:tcPr><w:tcW w:w=\"0\" w:type=\"auto\"/></w:tcPr>"
            f"{paragraph(clean_inline(cell))}</w:tc>"
            for cell in row
        )
        trs.append(f"<w:tr>{cells}</w:tr>")
    borders = "".join(
        f'<w:{edge} w:val="single" w:sz="4" w:space="0" w:color="D9DEE5"/>'
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV")
    )
    return (
        "<w:tbl><w:tblPr><w:tblStyle w:val=\"TableGrid\"/>"
        "<w:tblW w:w=\"0\" w:type=\"auto\"/><w:tblBorders>"
        f"{borders}</w:tblBorders></w:tblPr>{''.join(trs)}</w:tbl>"
    )


def is_table_separator(cells: Sequence[str]) -> bool:
    return all(bool(cell) and set(cell) <= {"-", ":"} for cell in cells)


def parse_table(lines: Sequence[str], start: int) -> tuple[list[list[str]], int]:
    rows: list[list[str]] = []
    index = start
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            break
        cells = [clean_inline(cell.strip()) for cell in stripped.strip("|").split("|")]
        if not is_table_separator(cells):
            rows.append(cells)
        index += 1
    return rows, index


def flush_paragraph(buffer: list[str], output: list[str]) -> None:
    if buffer:
        output.append(paragraph(clean_inline(" ".join(buffer))))
        buffer.clear()


def markdown_to_word_xml(markdown: str) -> str:
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    output: list[str] = []
    paragraph_buffer: list[str] = []
    in_fence = False
    fence_lang = ""
    fence_lines: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        fence_match = re.match(r"^```(\w*)\s*$", stripped)
        if fence_match:
            flush_paragraph(paragraph_buffer, output)
            if in_fence:
                label = f"Code block ({fence_lang})" if fence_lang else "Code block"
                output.append(paragraph(label, "Heading4"))
                output.append(paragraph("\n".join(fence_lines), "Code"))
                fence_lines = []
                in_fence = False
                fence_lang = ""
            else:
                in_fence = True
                fence_lang = fence_match.group(1)
            index += 1
            continue

        if in_fence:
            fence_lines.append(line)
            index += 1
            continue

        if not stripped:
            flush_paragraph(paragraph_buffer, output)
            index += 1
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", stripped)
        if heading_match:
            flush_paragraph(paragraph_buffer, output)
            level = min(len(heading_match.group(1)), 4)
            output.append(paragraph(clean_inline(heading_match.group(2)), f"Heading{level}"))
            index += 1
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            flush_paragraph(paragraph_buffer, output)
            rows, index = parse_table(lines, index)
            output.append(table(rows))
            continue

        bullet_match = re.match(r"^\s*[-*]\s+(.+)$", line)
        if bullet_match:
            flush_paragraph(paragraph_buffer, output)
            output.append(paragraph(clean_inline(bullet_match.group(1)), numbering="bullet"))
            index += 1
            continue

        number_match = re.match(r"^\s*\d+\.\s+(.+)$", line)
        if number_match:
            flush_paragraph(paragraph_buffer, output)
            output.append(paragraph(clean_inline(number_match.group(1)), numbering="number"))
            index += 1
            continue

        paragraph_buffer.append(stripped)
        index += 1

    flush_paragraph(paragraph_buffer, output)
    return "".join(output)


def document_xml(body_xml: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body_xml}"
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1417" '
        'w:right="1417" w:bottom="1417" w:left="1417" w:header="708" '
        'w:footer="708" w:gutter="0"/></w:sectPr>'
        "</w:body></w:document>"
    )


def content_types_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""


def root_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""


def document_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>
</Relationships>"""


def styles_xml() -> str:
    style_defs = [
        ("Normal", "Normal", None, 22, False),
        ("Heading1", "heading 1", "Normal", 32, True),
        ("Heading2", "heading 2", "Normal", 28, True),
        ("Heading3", "heading 3", "Normal", 24, True),
        ("Heading4", "heading 4", "Normal", 22, True),
        ("Code", "Code", "Normal", 18, False),
    ]
    styles = []
    for style_id, name, based_on, size, bold in style_defs:
        based = f'<w:basedOn w:val="{based_on}"/>' if based_on else ""
        b = "<w:b/>" if bold else ""
        mono = '<w:rFonts w:ascii="Courier New" w:hAnsi="Courier New"/>' if style_id == "Code" else ""
        styles.append(
            f'<w:style w:type="paragraph" w:styleId="{style_id}">'
            f'<w:name w:val="{name}"/>{based}'
            f'<w:rPr>{mono}{b}<w:sz w:val="{size}"/></w:rPr></w:style>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        + "".join(styles)
        + "</w:styles>"
    )


def numbering_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:abstractNum w:abstractNumId="1">
    <w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/></w:lvl>
  </w:abstractNum>
  <w:num w:numId="1"><w:abstractNumId w:val="1"/></w:num>
  <w:abstractNum w:abstractNumId="2">
    <w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl>
  </w:abstractNum>
  <w:num w:numId="2"><w:abstractNumId w:val="2"/></w:num>
</w:numbering>"""


def core_props_xml(metadata: dict[str, str]) -> str:
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    title = escape(metadata.get("TITLE", ""), quote=False)
    subject = escape(metadata.get("SUBJECT", ""), quote=False)
    author = escape(metadata.get("AUTHOR", ""), quote=False)
    keywords = escape(metadata.get("KEYWORDS", ""), quote=False)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns:dcmitype="http://purl.org/dc/dcmitype/"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{title}</dc:title>
  <dc:subject>{subject}</dc:subject>
  <dc:creator>{author}</dc:creator>
  <cp:keywords>{keywords}</cp:keywords>
  <dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>
</cp:coreProperties>"""


def app_props_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
  xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>GTS AI SDLC docx_template_tool.py</Application>
</Properties>"""


def render_docx(markdown_path: Path, output_path: Path, revisions_arg: str | None = None) -> None:
    markdown = markdown_path.read_text(encoding="utf-8")
    metadata, body_markdown = parse_metadata(markdown)
    parse_revisions(revisions_arg, metadata)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    body_xml = markdown_to_word_xml(body_markdown)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types_xml())
        docx.writestr("_rels/.rels", root_rels_xml())
        docx.writestr("word/document.xml", document_xml(body_xml))
        docx.writestr("word/_rels/document.xml.rels", document_rels_xml())
        docx.writestr("word/styles.xml", styles_xml())
        docx.writestr("word/numbering.xml", numbering_xml())
        docx.writestr("docProps/core.xml", core_props_xml(metadata))
        docx.writestr("docProps/app.xml", app_props_xml())


def default_output(markdown_path: Path, metadata: dict[str, str]) -> Path:
    file_name = metadata.get("FILE_NAME")
    if file_name:
        return markdown_path.with_name(Path(file_name).with_suffix(".docx").name)
    return markdown_path.with_suffix(".docx")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a DOCX next to a DOCX-METADATA Markdown specification."
    )
    parser.add_argument("markdown", nargs="?", help="Input Markdown file")
    parser.add_argument("--input", dest="input_path", help="Input Markdown file")
    parser.add_argument("--output", help="Output DOCX path; defaults to FILE_NAME stem next to input")
    parser.add_argument(
        "--revisions",
        help="Optional JSON/Python list of [date, author, version, reason] rows; metadata is used by default",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_value = args.input_path or args.markdown
    if not input_value:
        raise SystemExit("error: provide a Markdown file as positional argument or --input")
    markdown_path = Path(input_value).resolve()
    markdown = markdown_path.read_text(encoding="utf-8")
    metadata, _ = parse_metadata(markdown)
    output_path = Path(args.output).resolve() if args.output else default_output(markdown_path, metadata)
    render_docx(markdown_path, output_path, args.revisions)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
