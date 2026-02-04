"""
CEO Briefing System (spec 007).

Aggregates completed tasks from /Done, renders executive-summary
reports via Jinja2, and writes Markdown output to /Briefings.
"""

from src.briefing.models import TaskSummary, BriefingData
from src.briefing.aggregator import BriefingAggregator
from src.briefing.template_renderer import TemplateRenderer
from src.briefing.pdf_generator import generate_pdf, generate_pdf_to_file

__all__ = [
    "TaskSummary",
    "BriefingData",
    "BriefingAggregator",
    "TemplateRenderer",
    "generate_pdf",
    "generate_pdf_to_file",
]
