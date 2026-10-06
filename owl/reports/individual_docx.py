"""Deterministic individual-attendance Word builder (parameterized port).

Same visual language as the reference build: cover, how-to-read guide with a
worked example, department color bands, per-employee daily grid(s) plus a
summary table, locked rows, footer with page numbers. Unlike the reference,
month, location, holidays, and columns are parameters, and wide date ranges
are chunked into one grid per calendar month so tables stay readable.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

CYAN = "00B0F0"; ORANGE = "FF6B00"; GREEN = "00C853"; RED = "E53935"
PURPLE = "7C4DFF"; YELLOW = "FFD600"; PINK = "FF4081"; TEAL = "009688"
NAVY = "0D1B4C"; BLUE = "1E88E5"; DEEPO = "F4511E"; WHITE = "FFFFFF"; LGREY = "F2F4F8"
DEPT_COLORS = [CYAN, ORANGE, GREEN, PURPLE, PINK, TEAL, BLUE, DEEPO, RED, YELLOW]
MUTED = "546E7A"

CODE_COLORS = {"L": "0D47A1", "T": "E65100", "H": "4A148C", "IN": "C62828"}


def _shade_cell(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def _shade_para(p, hexcolor):
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hexcolor)
    pPr.append(shd)


def _lock_rows(table, keep_last=False):
    n = len(table.rows)
    for i, row in enumerate(table.rows):
        trPr = row._tr.get_or_add_trPr()
        trPr.append(OxmlElement("w:cantSplit"))
        if keep_last or i < n - 1:
            for c in row.cells:
                for p in c.paragraphs:
                    p.paragraph_format.keep_with_next = True


def _set_cell(cell, text, bold=False, size=8, color=None, align="center"):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT if align == "left" else WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    run = p.add_run(str(text))
    run.bold = bold
    run.font.size = Pt(size)
    run.font.name = "Consolas"
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def _para(doc, text, size=11, bold=False, italic=False, color=None, align="left", space_after=6):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT if align == "left" else WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(space_after)
    run = p.add_run(text)
    run.bold = bold; run.italic = italic
    run.font.size = Pt(size); run.font.name = "Consolas"
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    return p


def _page_numbers(sec, title):
    sec.footer.is_linked_to_previous = False
    p = sec.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"{title}   |   Page ")
    run.font.size = Pt(8); run.font.color.rgb = RGBColor.from_string(MUTED); run.font.name = "Consolas"
    fld = OxmlElement("w:fldSimple"); fld.set(qn("w:instr"), "PAGE")
    rr = OxmlElement("w:r"); tt = OxmlElement("w:t"); tt.text = "1"; rr.append(tt); fld.append(rr)
    p._p.append(fld)


def month_chunks(dates: list[date]) -> list[list[date]]:
    """Split a date list into per-calendar-month chunks."""
    out: list[list[date]] = []
    for d in dates:
        if not out or (d.year, d.month) != (out[-1][-1].year, out[-1][-1].month):
            out.append([])
        out[-1].append(d)
    return out


def chunk_cells(cells: list[dict]) -> list[list[dict]]:
    """Split day cells into per-calendar-month chunks."""
    out: list[list[dict]] = []
    for dc in cells:
        d = dc["date"]
        if not out or (d.year, d.month) != (out[-1][-1]["date"].year, out[-1][-1]["date"].month):
            out.append([])
        out[-1].append(dc)
    return out


def _grid(doc, day_cells: list[dict], header_fill: str) -> None:
    cols = 1 + len(day_cells)
    t = doc.add_table(rows=3, cols=cols)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    _set_cell(t.rows[0].cells[0], "Day", bold=True, size=9, color=WHITE, align="left")
    _shade_cell(t.rows[0].cells[0], NAVY)
    for i, dc in enumerate(day_cells, start=1):
        d = dc["date"]
        _set_cell(t.rows[0].cells[i], f"{d.strftime('%a')} {d.day}", bold=True, size=9, color=WHITE)
        _shade_cell(t.rows[0].cells[i], header_fill)
    _set_cell(t.rows[1].cells[0], "Check-in", bold=True, size=9, color=NAVY, align="left")
    _shade_cell(t.rows[1].cells[0], LGREY)
    _set_cell(t.rows[2].cells[0], "Check-out", bold=True, size=9, color=NAVY, align="left")
    _shade_cell(t.rows[2].cells[0], LGREY)
    for i, dc in enumerate(day_cells, start=1):
        col = CODE_COLORS.get(dc["code"] or "")
        if dc["code"] in ("", None):
            col = None
        _set_cell(t.rows[1].cells[i], dc["ci"], size=9, color=col)
        _set_cell(t.rows[2].cells[i], dc["co"], size=9, color=col)
        if i % 2 == 0:
            _shade_cell(t.rows[1].cells[i], "FAFAFA"); _shade_cell(t.rows[2].cells[i], "FAFAFA")
    n = len(day_cells)
    first_w = 1.0
    rest = min(0.46, max(0.28, 9.6 / max(1, n)))
    widths = [first_w] + [rest] * n
    for r_ in t.rows:
        for i, w in enumerate(widths):
            r_.cells[i].width = Inches(w)
    for i, r_ in enumerate(t.rows):
        r_.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
        r_.height = Inches([0.4, 0.5, 0.5][i])
    _lock_rows(t, keep_last=True)


def _summary(doc, emp: dict, summary: dict) -> None:
    avg = summary["avg_daily_hours_worked"]
    fields = [
        ("Employee ID", str(emp.get("id_no", ""))),
        ("Department", str(emp.get("department", ""))),
        ("Grade Level", str(emp.get("grade_level", ""))),
        ("Rank", str(emp.get("rank", ""))),
        ("Expected workdays", str(summary["expected_workdays"])),
        ("Days present", str(summary["days_present"])),
        ("Days absent", str(summary["days_absent"])),
        ("Days on leave", str(summary["days_on_leave"])),
        ("Days in training", str(summary["days_in_training"])),
        ("Attendance rate", f"{summary['attendance_rate_pct']:.0f}%"),
        ("Days late", str(summary["days_late"])),
        ("Total late minutes", f"{summary['total_minutes_late']:,}"),
        ("Early departures", str(summary["early_departures"])),
        ("Incomplete check-outs", str(summary["incomplete_swipe_days"])),
        ("Total hours worked", f"{summary['total_hours_worked']:.2f}"),
        ("Avg daily hours", "-" if avg is None else f"{avg:.2f}"),
    ]
    rows = (len(fields) + 1) // 2
    t = doc.add_table(rows=rows, cols=4)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i in range(rows):
        left = fields[i]
        right = fields[i + rows] if i + rows < len(fields) else ("", "")
        _set_cell(t.rows[i].cells[0], left[0], bold=True, size=9, color=NAVY, align="left")
        _shade_cell(t.rows[i].cells[0], LGREY)
        _set_cell(t.rows[i].cells[1], left[1], size=9, align="left")
        _set_cell(t.rows[i].cells[2], right[0], bold=True, size=9, color=NAVY, align="left")
        _shade_cell(t.rows[i].cells[2], LGREY)
        _set_cell(t.rows[i].cells[3], right[1], size=9, align="left")
    for r_ in t.rows:
        for i, w in enumerate([2.2, 3.15, 2.2, 3.14]):
            r_.cells[i].width = Inches(w)
    _lock_rows(t)


def build_individual_docx(
    location_label: str,
    period_label: str,
    meta_line: str,
    dept_groups: list[tuple[str, list[dict]]],
    dates: list[date],
    out_path: Path,
) -> Path:
    """Assemble the document. Each emp report: {employee, days, summary}."""
    doc = Document()
    st = doc.styles["Normal"]; st.font.name = "Consolas"; st.font.size = Pt(10)
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width = Inches(11.69); sec.page_height = Inches(8.27)
    sec.top_margin = Inches(0.5); sec.bottom_margin = Inches(0.5)
    sec.left_margin = Inches(0.5); sec.right_margin = Inches(0.5)
    title = f"Individual Attendance Details - {period_label}"
    _page_numbers(sec, title)

    for _ in range(2):
        doc.add_paragraph()
    _para(doc, location_label.upper(), size=16, bold=True, color=CYAN, align="center")
    _para(doc, "INDIVIDUAL ATTENDANCE DETAILS", size=30, bold=True, color=NAVY, align="center", space_after=2)
    _para(doc, period_label.upper(), size=24, bold=True, color=ORANGE, align="center")
    doc.add_paragraph()
    _para(doc, meta_line, size=12, bold=True, color=NAVY, align="center")

    doc.add_page_break()
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(10)
    run = p.add_run("  HOW TO READ THIS TABLE")
    run.bold = True; run.font.size = Pt(20); run.font.name = "Consolas"
    run.font.color.rgb = RGBColor.from_string(WHITE)
    _shade_para(p, PURPLE)
    _para(doc, "Each employee has a daily attendance grid per month plus a summary table.", size=12, bold=True, color=NAVY, space_after=4)
    _para(doc, "Grid rows: Row 1 = day and date. Row 2 = check-in time. Row 3 = check-out time.", size=11)
    _para(doc, "Codes used in the grid:", size=12, bold=True, color=DEEPO, space_after=2)
    for code, meaning in [
        ("(blank)", "absent (no swipe, no leave, no training)"),
        ("L", "approved leave (both rows)"),
        ("T", "training (both rows)"),
        ("H", "public holiday (both rows)"),
        ("IN", "incomplete check-out (check-in captured, short gap)"),
        ("HH:MM", "actual first-swipe (check-in) and last-swipe (check-out) times"),
    ]:
        _para(doc, f"  {code:<9}= {meaning}", size=11)

    for di, (dept, reps) in enumerate(dept_groups):
        accent = DEPT_COLORS[di % len(DEPT_COLORS)]
        doc.add_page_break()
        p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(8)
        run = p.add_run(f"  {dept}   ({len(reps)} employees)")
        run.bold = True; run.font.size = Pt(18); run.font.name = "Consolas"
        run.font.color.rgb = RGBColor.from_string(WHITE)
        _shade_para(p, accent)
        for rep in reps:
            emp = rep["employee"]
            hp = doc.add_paragraph()
            hp.paragraph_format.space_before = Pt(6)
            hp.paragraph_format.space_after = Pt(2)
            hp.paragraph_format.keep_with_next = True
            run = hp.add_run(f"{emp.get('display_name', '')}   (ID: {emp.get('id_no', '')})")
            run.bold = True; run.font.size = Pt(11); run.font.name = "Consolas"
            run.font.color.rgb = RGBColor.from_string(NAVY)
            for chunk in chunk_cells(rep["days"]):
                _grid(doc, chunk, accent)
            sp = doc.add_paragraph()
            sp.paragraph_format.space_after = Pt(0)
            sp.paragraph_format.keep_with_next = True
            _summary(doc, emp, rep["summary"])
            doc.add_paragraph().paragraph_format.space_after = Pt(0)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    return out_path
