# Implementation Plan: CEO Briefing System

**Branch**: `007-ceo-briefing` | **Date**: 2026-01-28 | **Spec**: [specs/007-ceo-briefing/spec.md](./spec.md)

## Summary

Build automated weekly CEO briefing system that aggregates completed tasks from `/Done` folder, generates executive summary reports using Jinja2 templates, creates PDF/Markdown outputs, and delivers via email. Provides high-level visibility into AI Employee activities without manual reporting.

**Key Approach**: Scheduled Python script (cron/PM2), data aggregation from Markdown files, Jinja2 template rendering, PDF generation (wkhtmltopdf), email delivery via MCP Gmail server.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Jinja2>=3.1.0, pdfkit>=1.0.0, python-dateutil>=2.8.0, pandas>=2.0.0
**Storage**: Obsidian vault (read-only), generated reports in `/Briefings`
**Testing**: pytest>=7.4.0, Jinja2 template tests
**Target Platform**: Linux/macOS (wkhtmltopdf available)
**Project Type**: Single project (reporting module)
**Performance Goals**: <30s briefing generation, <1MB PDF size
**Constraints**: ADDITIVE ONLY, read-only access to vault, privacy-preserving (no external analytics)
**Scale/Scope**: Aggregate 50+ tasks/week, generate 10-page report

## Constitution Check

✅ **Section 2 (Source of Truth)**: Reads data from vault (source of truth)
✅ **Section 3 (Local-First)**: Report generation is local, email via approved MCP
✅ **Section 6-7 (HITL)**: Email delivery requires approval
✅ **Section 8 (Auditability)**: Briefing generation logged

## Project Structure

```text
src/briefing/
├── __init__.py
├── aggregator.py        # Data aggregation from /Done
├── template_renderer.py # Jinja2 rendering
├── pdf_generator.py     # PDF generation
└── models.py            # Briefing data models

templates/briefing/
├── executive_summary.md.j2
├── detailed_report.html.j2
└── email_body.html.j2

config/briefing.yaml     # Briefing configuration

tests/briefing/
├── test_aggregator.py
├── test_template_renderer.py
└── test_briefing_integration.py
```

## Implementation Roadmap

### Bronze Tier (Week 1): Data Aggregation & Templates
- Implement `BriefingAggregator` to parse `/Done` files
- Create Jinja2 templates (summary, detailed report)
- Basic Markdown report generation
- Unit tests

### Silver Tier (Week 2): PDF & Email Delivery
- Implement PDF generation (wkhtmltopdf)
- Email delivery integration (Gmail MCP)
- Schedule automation (cron/PM2)
- CLI integration (`fte briefing generate`)

### Gold Tier (Week 3): Advanced Analytics
- Add charts/graphs (matplotlib)
- Task completion trends
- Time tracking analytics
- Interactive HTML reports

## Success Metrics

- [ ] Weekly briefings auto-generated
- [ ] PDF reports <1MB, <10 pages
- [ ] Email delivery via HITL-approved MCP
- [ ] Zero manual intervention required

---

**Next Steps**: Run `/sp.tasks` to generate actionable task breakdown.
