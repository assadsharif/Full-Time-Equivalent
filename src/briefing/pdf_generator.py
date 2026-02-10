"""
PDF Generator for CEO Briefing reports (spec 007 — Silver Tier).

Converts a ``BriefingData`` payload into a single-page (or multi-page)
PDF executive summary using fpdf2.  Output is written to disk or
returned as raw bytes for testing.
"""

from pathlib import Path

from fpdf import FPDF

from .models import BriefingData

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

_PAGE_W = 210  # A4 mm
_MARGIN = 15
_TITLE_H = 12
_SECTION_GAP = 6
_ROW_H = 7
_HEADER_BG = (41, 65, 122)  # dark navy
_HEADER_FG = (255, 255, 255)
_ALT_ROW_BG = (240, 243, 250)
_PRIORITY_COLOURS = {
    "urgent": (220, 53, 69),
    "high": (253, 126, 4),
    "medium": (40, 167, 69),
    "low": (108, 117, 125),
    "normal": (108, 117, 125),
}


class _BriefingPDF(FPDF):
    """FPDF subclass that stamps a consistent header on every page."""

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*_HEADER_FG)
        self.set_fill_color(*_HEADER_BG)
        self.cell(
            _PAGE_W - 2 * _MARGIN,
            8,
            "AI Employee - Executive Briefing",
            new_x="LMARGIN",
            new_y="NEXT",
            fill=True,
            align="C",
        )
        self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(128)
        self.cell(0, 5, f"Page {self.page_no()}", align="C")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_pdf(data: BriefingData) -> bytes:
    """Render *data* as a PDF and return the raw PDF bytes."""
    pdf = _build(data)
    return bytes(pdf.output())


def generate_pdf_to_file(data: BriefingData, output_path: Path) -> Path:
    """Render *data* as a PDF and write it to *output_path*.

    Parent directories are created if they do not exist.
    Returns the resolved output path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = _build(data)
    pdf.output(str(output_path))
    return output_path.resolve()


# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------


def _build(data: BriefingData) -> _BriefingPDF:
    pdf = _BriefingPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    _title_block(pdf, data)
    _summary_stats(pdf, data)
    _priority_breakdown(pdf, data)
    _top_senders(pdf, data)
    _task_table(pdf, data)

    return pdf


def _title_block(pdf: _BriefingPDF, data: BriefingData) -> None:
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(41, 65, 122)
    pdf.cell(
        0,
        _TITLE_H,
        "Weekly Executive Briefing",
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(80)
    period = f"{data.period_start.strftime('%Y-%m-%d')}  to  {data.period_end.strftime('%Y-%m-%d')}"
    pdf.cell(0, 5, period, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(
        0,
        5,
        f"Generated: {data.generated_at.strftime('%Y-%m-%d %H:%M')}",
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )
    pdf.ln(_SECTION_GAP)


def _summary_stats(pdf: _BriefingPDF, data: BriefingData) -> None:
    _section_header(pdf, "Summary")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0)
    pdf.cell(
        0,
        _ROW_H,
        f"Total tasks completed: {data.total_tasks}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        _ROW_H,
        f"Average persistence iterations: {data.avg_iterations:.1f}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(_SECTION_GAP)


def _priority_breakdown(pdf: _BriefingPDF, data: BriefingData) -> None:
    if not data.by_priority:
        return
    _section_header(pdf, "Completion by Priority")
    col_w = (_PAGE_W - 2 * _MARGIN) / 2
    # header row
    pdf.set_fill_color(*_HEADER_BG)
    pdf.set_text_color(*_HEADER_FG)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(
        col_w, _ROW_H, "Priority", new_x="RIGHT", new_y="TOP", fill=True, align="C"
    )
    pdf.cell(
        col_w, _ROW_H, "Count", new_x="LMARGIN", new_y="NEXT", fill=True, align="C"
    )
    # data rows
    pdf.set_text_color(0)
    pdf.set_font("Helvetica", "", 9)
    for i, (pri, count) in enumerate(sorted(data.by_priority.items())):
        if i % 2 == 1:
            pdf.set_fill_color(*_ALT_ROW_BG)
        else:
            pdf.set_fill_color(255)
        pdf.cell(
            col_w,
            _ROW_H,
            pri.capitalize(),
            new_x="RIGHT",
            new_y="TOP",
            fill=True,
            align="L",
        )
        pdf.cell(
            col_w,
            _ROW_H,
            str(count),
            new_x="LMARGIN",
            new_y="NEXT",
            fill=True,
            align="C",
        )
    pdf.ln(_SECTION_GAP)


def _top_senders(pdf: _BriefingPDF, data: BriefingData) -> None:
    if not data.top_senders:
        return
    _section_header(pdf, "Top Senders")
    col_w = (_PAGE_W - 2 * _MARGIN) / 2
    pdf.set_fill_color(*_HEADER_BG)
    pdf.set_text_color(*_HEADER_FG)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(col_w, _ROW_H, "Sender", new_x="RIGHT", new_y="TOP", fill=True, align="C")
    pdf.cell(
        col_w, _ROW_H, "Tasks", new_x="LMARGIN", new_y="NEXT", fill=True, align="C"
    )
    pdf.set_text_color(0)
    pdf.set_font("Helvetica", "", 9)
    for i, (sender, count) in enumerate(data.top_senders):
        if i % 2 == 1:
            pdf.set_fill_color(*_ALT_ROW_BG)
        else:
            pdf.set_fill_color(255)
        pdf.cell(
            col_w, _ROW_H, sender, new_x="RIGHT", new_y="TOP", fill=True, align="L"
        )
        pdf.cell(
            col_w,
            _ROW_H,
            str(count),
            new_x="LMARGIN",
            new_y="NEXT",
            fill=True,
            align="C",
        )
    pdf.ln(_SECTION_GAP)


def _task_table(pdf: _BriefingPDF, data: BriefingData) -> None:
    if not data.tasks:
        return
    _section_header(pdf, "Task Details")

    cols = ("Task", "Priority", "Sender")
    widths = [100, 35, 45]  # mm, should sum ≈ PAGE_W - 2*MARGIN

    # header
    pdf.set_fill_color(*_HEADER_BG)
    pdf.set_text_color(*_HEADER_FG)
    pdf.set_font("Helvetica", "B", 8)
    for col, w in zip(cols, widths):
        pdf.cell(w, _ROW_H, col, new_x="RIGHT", new_y="TOP", fill=True, align="C")
    pdf.ln(_ROW_H)

    # rows
    pdf.set_text_color(0)
    pdf.set_font("Helvetica", "", 8)
    for i, task in enumerate(data.tasks):
        if i % 2 == 1:
            pdf.set_fill_color(*_ALT_ROW_BG)
        else:
            pdf.set_fill_color(255)
        # truncate long names
        name = task.name[:38] + "..." if len(task.name) > 38 else task.name
        pdf.cell(
            widths[0], _ROW_H, name, new_x="RIGHT", new_y="TOP", fill=True, align="L"
        )
        pdf.cell(
            widths[1],
            _ROW_H,
            task.priority.capitalize(),
            new_x="RIGHT",
            new_y="TOP",
            fill=True,
            align="C",
        )
        pdf.cell(
            widths[2],
            _ROW_H,
            task.sender,
            new_x="LMARGIN",
            new_y="NEXT",
            fill=True,
            align="L",
        )


def _section_header(pdf: _BriefingPDF, title: str) -> None:
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(41, 65, 122)
    pdf.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(41, 65, 122)
    pdf.line(_MARGIN, pdf.get_y(), _PAGE_W - _MARGIN, pdf.get_y())
    pdf.ln(3)
