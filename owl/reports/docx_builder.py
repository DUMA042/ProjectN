"""Markdown + chart PNGs -> styled Word document (August-report style).

Styling mirrors the reference build (shaded table headers, colored H1/H2,
KPI-style bold figures, embedded charts, page numbers) without copying its
content. Only a small markdown subset is honored: #/##/### headings,
paragraphs, - bullets, **bold** runs, and pipe tables.
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Inches, Pt, RGBColor

ACCENT = RGBColor(0x16, 0x77, 0xFF)
DARK = RGBColor(0x1F, 0x2A, 0x37)
HEADER_FILL = "1677FF"
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def _shade(cell, hexcolor: str) -> None:
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), hexcolor)
    cell._tc.get_or_add_tcPr().append(shading)


def _add_page_numbers(section) -> None:
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run()
    for tag in ("begin", "separate", "end"):
        el = OxmlElement("w:fldChar")
        el.set(qn("w:fldCharType"), tag)
        run._r.append(el)
        if tag == "separate":
            instr = OxmlElement("w:instrText")
            instr.set(qn("xml:space"), "preserve")
            instr.text = "PAGE"
            run._r.append(instr)


def _rich_text(paragraph, text: str, size: int = 11, color=None) -> None:
    """Paragraph text with **bold** runs honored."""
    paragraph.clear()
    for i, chunk in enumerate(BOLD_RE.split(text)):
        if not chunk:
            continue
        run = paragraph.add_run(chunk)
        run.font.size = Pt(size)
        if color is not None:
            run.font.color.rgb = color
        if i % 2 == 1:
            run.bold = True


def _add_toc(doc) -> None:
    """Auto table-of-contents field (Word fills it in on open)."""
    p = doc.add_paragraph()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = 'TOC \\o "1-3" \\h \\z \\u'
    fld_separate = OxmlElement("w:fldChar")
    fld_separate.set(qn("w:fldCharType"), "separate")
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run = p.add_run()
    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_separate)
    run._r.append(fld_end)
    hint = doc.add_paragraph()
    _rich_text(hint, "Right-click the table above and choose Update Field to fill the contents.",
               size=9, color=DARK)


def kpi_box(doc, items: list[tuple[str, str]]) -> None:
    """One-row KPI strip: big bold values with small labels underneath."""
    if not items:
        return
    table = doc.add_table(rows=2, cols=len(items))
    table.style = "Table Grid"
    for j, (label, value) in enumerate(items):
        top = table.cell(0, j)
        top.text = ""
        _rich_text(top.paragraphs[0], value, size=14, color=ACCENT)
        top.paragraphs[0].runs[0].bold = True
        top.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        bottom = table.cell(1, j)
        bottom.text = ""
        _rich_text(bottom.paragraphs[0], label, size=9, color=DARK)
        bottom.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        _shade(top, "EFF4FF")
    doc.add_paragraph()


def build_docx(
    title: str,
    intro: str,
    sections: list[tuple[str, str]],
    chart_paths: list[tuple[str, Path]],
    out_path: Path,
    kpi_boxes: list[list[tuple[str, str]]] | None = None,
) -> Path:
    """Assemble and save the .docx. Returns out_path."""
    from datetime import date as _date

    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    for section in doc.sections:
        section.top_margin = Inches(0.9)
        section.bottom_margin = Inches(0.9)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
    _add_page_numbers(doc.sections[0])

    # Cover block.
    t = doc.add_heading(level=0)
    _rich_text(t, title, size=24, color=ACCENT)
    sub = doc.add_paragraph()
    _rich_text(sub, _date.today().strftime("%B %Y"), size=13, color=DARK)
    if intro.strip():
        p = doc.add_paragraph()
        _rich_text(p, intro.strip(), size=11, color=DARK)
    _add_toc(doc)

    charts_by_index = {i: (cap, p) for i, (cap, p) in enumerate(chart_paths)}
    kpi_by_section = kpi_boxes or []

    def _emit_chart(idx: int) -> None:
        item = charts_by_index.get(idx)
        if not item:
            return
        caption, path = item
        if path.exists():
            doc.add_picture(str(path), width=Inches(6.0))
            cap = doc.add_paragraph()
            _rich_text(cap, f"Figure: {caption}", size=9, color=DARK)

    for si, (heading, markdown) in enumerate(sections):
        h = doc.add_heading(level=1)
        _rich_text(h, heading, size=15, color=ACCENT)
        if si < len(kpi_by_section):
            kpi_box(doc, kpi_by_section[si])
        lines = markdown.splitlines()
        # Strip a leading duplicate of the section title the model may repeat.
        while lines and re.match(r"^#{1,3}\s+", lines[0].strip()):
            cand = re.sub(r"^#{1,3}\s+", "", lines[0]).strip().lower()
            want = heading.strip().lower()
            if cand and (cand == want or want in cand or cand in want):
                lines.pop(0)
            else:
                break
        i = 0
        table_buf: list[list[str]] = []

        def _flush_table() -> None:
            if len(table_buf) < 2:
                table_buf.clear()
                return
            headers, rows = table_buf[0], table_buf[1:]
            table = doc.add_table(rows=1 + len(rows), cols=len(headers))
            table.style = "Light Grid Accent 1"
            for j, hcell in enumerate(headers):
                cell = table.cell(0, j)
                cell.text = ""
                _rich_text(cell.paragraphs[0], hcell.strip(), size=10)
                cell.paragraphs[0].runs[0].bold = True
                cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                _shade(cell, HEADER_FILL)
            for r, row in enumerate(rows, start=1):
                for j in range(len(headers)):
                    cell = table.cell(r, j)
                    cell.text = ""
                    _rich_text(cell.paragraphs[0], row[j].strip() if j < len(row) else "", size=10)
            doc.add_paragraph()
            table_buf.clear()

        while i < len(lines):
            line = lines[i].rstrip()
            if re.match(r"^\s*\|.*\|\s*$", line):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if cells and all(re.match(r"^:?-{2,}:?$", c) for c in cells):
                    i += 1
                    continue  # separator row
                table_buf.append(cells)
            else:
                _flush_table()
                m = re.match(r"^\s*!\[(.*?)\]\(build-chart:(\d+)\)\s*$", line)
                if m:
                    _emit_chart(int(m.group(2)))
                elif line.startswith("### "):
                    h3 = doc.add_heading(level=3)
                    _rich_text(h3, line[4:].strip(), size=12, color=DARK)
                elif line.startswith("## "):
                    h2 = doc.add_heading(level=2)
                    _rich_text(h2, line[3:].strip(), size=13, color=DARK)
                elif line.startswith("- "):
                    p = doc.add_paragraph(style="List Bullet")
                    _rich_text(p, line[2:].strip(), size=11)
                elif line.strip():
                    p = doc.add_paragraph()
                    _rich_text(p, line.strip(), size=11)
            i += 1
        _flush_table()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    return out_path
