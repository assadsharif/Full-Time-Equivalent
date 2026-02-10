"""
CEO Briefing System (spec 007).

Aggregates completed tasks from /Done, renders executive-summary
reports via Jinja2, and writes Markdown output to /Briefings.
"""

from .models import TaskSummary, BriefingData
from .aggregator import BriefingAggregator
from .template_renderer import TemplateRenderer
from .pdf_generator import generate_pdf, generate_pdf_to_file
from .email_delivery import EmailDeliveryService, SMTPConfig

__all__ = [
    "TaskSummary",
    "BriefingData",
    "BriefingAggregator",
    "TemplateRenderer",
    "generate_pdf",
    "generate_pdf_to_file",
    "EmailDeliveryService",
    "SMTPConfig",
]
