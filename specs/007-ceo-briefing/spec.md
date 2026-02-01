# Monday Morning CEO Briefing Specification (P5)

**Feature Name**: Monday Morning CEO Briefing (Weekly Executive Summary)
**Priority**: P5 (Gold Tier, High-Value Feature)
**Status**: Draft
**Created**: 2026-01-28
**Last Updated**: 2026-01-28
**Owner**: AI Employee Hackathon Team
**Stakeholders**: Executive Leadership, Operations Team

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Context and Background](#context-and-background)
3. [User Stories](#user-stories)
4. [Functional Requirements](#functional-requirements)
5. [Non-Functional Requirements](#non-functional-requirements)
6. [Technical Architecture](#technical-architecture)
7. [Briefing Template Design](#briefing-template-design)
8. [Data Aggregation](#data-aggregation)
9. [Security Considerations](#security-considerations)
10. [Constitutional Compliance](#constitutional-compliance)
11. [Implementation Phases](#implementation-phases)
12. [Success Metrics](#success-metrics)
13. [Open Questions](#open-questions)
14. [Appendix](#appendix)

---

## Executive Summary

### Problem Statement

Executives need a **high-level summary** of the AI Employee's weekly activities to:

- **Understand productivity** (tasks completed, response times, bottlenecks)
- **Identify trends** (increasing volume, recurring issues, priority shifts)
- **Make decisions** (resource allocation, process improvements, risk mitigation)
- **Maintain oversight** without manually reviewing hundreds of task files

Current state: Manual review of `/Done` folder (100+ Markdown files) to understand weekly performance.

### Proposed Solution

Develop a **Monday Morning CEO Briefing Generator** that:

1. **Aggregates data** from `/Done` folder (completed tasks from past week)
2. **Calculates metrics** (tasks completed, avg response time, priority distribution)
3. **Identifies insights** (top clients, common patterns, anomalies)
4. **Generates report** in Markdown and optionally PDF format
5. **Delivers via CLI** (`fte briefing`) or scheduled via cron (Monday 7 AM)
6. **Stores briefings** in `/Briefings/<YYYY-MM-DD>_Weekly_Briefing.md`

### Key Benefits

| Benefit | Impact |
|---------|--------|
| **Executive Visibility** | Weekly summaries keep leadership informed |
| **Data-Driven Decisions** | Metrics enable resource allocation optimization |
| **Trend Identification** | Early detection of volume spikes, bottlenecks |
| **Time Savings** | Automated report generation vs manual review |
| **Accountability** | AI Employee performance tracked and documented |

### Scope

**In Scope:**
- Data aggregation from `/Done` folder (past 7 days)
- Metrics calculation (tasks completed, response times, priority distribution)
- Insight generation (top clients, common patterns, anomalies)
- Markdown report generation using templates
- PDF export (optional, via pandoc or weasyprint)
- CLI integration (`fte briefing --week last --format pdf`)
- Scheduled generation (cron job: Monday 7 AM)
- Email delivery (optional, via SMTP)

**Out of Scope:**
- Real-time dashboards (Grafana/Kibana) - deferred to P8
- Interactive visualizations (charts, graphs) - deferred to P7
- Multi-team briefings (separate reports per department) - deferred to P9
- Predictive analytics (forecasting future workload) - deferred to P10
- Natural language generation (AI-written summaries) - Claude can do this

**Dependencies:**
- ✅ P2: Logging Infrastructure (query service for aggregation)
- ✅ P3: CLI Integration (briefing commands)
- ✅ P6: Orchestrator (task completion data in `/Done`)

---

## Context and Background

### Architecture Context

The CEO Briefing sits at the top of the reporting stack:

```
┌─────────────────────────────────────────────────────────────────┐
│  External Sources (Gmail, WhatsApp, Files)                      │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Perception Layer (Watchers)                                     │
│  Ingest tasks                                                    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Memory Layer (Obsidian Vault)                                   │
│  /Needs_Action → /In_Progress → /Done                           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Orchestrator & Scheduler                                        │
│  Process tasks autonomously                                      │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  MONDAY MORNING CEO BRIEFING  ◄── THIS SPEC                     │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  1. Data Aggregation                                    │    │
│  │     - Scan /Done folder (past 7 days)                  │    │
│  │     - Parse YAML frontmatter from all task files       │    │
│  │     - Extract: source, priority, timestamps, status    │    │
│  │                                                         │    │
│  │  2. Metrics Calculation                                 │    │
│  │     - Total tasks completed                             │    │
│  │     - Avg response time (created → completed)          │    │
│  │     - Priority distribution (high, medium, low)        │    │
│  │     - Source distribution (gmail, whatsapp, files)     │    │
│  │                                                         │    │
│  │  3. Insight Generation                                  │    │
│  │     - Top 5 clients by task volume                     │    │
│  │     - Common patterns (frequent subjects, actions)     │    │
│  │     - Anomalies (unusually long response times)        │    │
│  │     - Week-over-week trends (+/- % change)             │    │
│  │                                                         │    │
│  │  4. Report Generation                                   │    │
│  │     - Render Markdown using Jinja2 templates           │    │
│  │     - Optionally convert to PDF (pandoc/weasyprint)    │    │
│  │     - Store in /Briefings/<date>_Weekly_Briefing.md    │    │
│  │                                                         │    │
│  │  5. Delivery                                            │    │
│  │     - CLI: fte briefing --week last --format pdf       │    │
│  │     - Email: Send to executives via SMTP               │    │
│  │     - Scheduled: Cron job Monday 7 AM                  │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Executives / Leadership                                         │
│  Review weekly summaries, make decisions                         │
└─────────────────────────────────────────────────────────────────┘
```

**CEO Briefing Responsibilities:**
1. **Data Aggregation**: Collect all completed tasks from `/Done` folder
2. **Metrics Calculation**: Compute KPIs (tasks, response times, priorities)
3. **Insight Generation**: Identify patterns, trends, anomalies
4. **Report Formatting**: Render Markdown/PDF using templates
5. **Delivery**: CLI output, email, or file storage

### Constitutional Principles

| Section | Requirement | CEO Briefing Compliance |
|---------|-------------|------------------------|
| **Section 2: Source of Truth** | Obsidian vault is authoritative | ✅ Reads from `/Done` folder (vault) |
| **Section 3: Privacy First** | No PII in reports | ✅ Anonymize email addresses in reports |
| **Section 8: Auditability** | All actions logged | ✅ Briefing generation logged via P2 |

### Hackathon Tier Alignment

| Tier | CEO Briefing Requirements | Estimated Time |
|------|--------------------------|----------------|
| **Bronze** | Not required | 0 hours |
| **Silver** | Not required | 0 hours |
| **Gold** | Basic briefing (Markdown, CLI) | 4-6 hours |
| **Platinum** | Advanced features (PDF, email, charts) | 6-8 hours |

---

## User Stories

### US1: Generate Weekly Briefing (Gold Tier)

**As an** executive
**I want** a weekly summary of the AI Employee's activities
**So that** I can understand productivity and make informed decisions

**Acceptance Criteria:**
- [ ] Briefing aggregates data from past 7 days (Monday-Sunday)
- [ ] Briefing includes: total tasks, avg response time, priority distribution
- [ ] Briefing identifies top 5 clients by task volume
- [ ] Briefing highlights anomalies (unusually long response times)
- [ ] Briefing generated via CLI: `fte briefing`
- [ ] Briefing saved to `/Briefings/<date>_Weekly_Briefing.md`
- [ ] Briefing generation logged via P2 logging infrastructure

**Example Output:**

```markdown
# Monday Morning CEO Briefing
## Week of January 22-28, 2026

---

### Executive Summary

The AI Employee processed **47 tasks** this week, maintaining an average response time of **2.3 hours**. High-priority tasks were handled efficiently (avg 1.2 hours), while low-priority items took longer (avg 4.5 hours). Gmail remains the primary task source (68%), followed by WhatsApp (22%) and file system monitoring (10%).

**Key Highlights:**
- ✅ All urgent deadlines met (100% on-time completion)
- ⚠️ Response time increased 15% vs previous week (volume spike)
- 🔍 Client A generated 12 tasks (26% of total) - potential automation opportunity

---

### Metrics Dashboard

| Metric | This Week | Last Week | Change |
|--------|-----------|-----------|--------|
| **Total Tasks** | 47 | 41 | +15% ↑ |
| **Avg Response Time** | 2.3 hours | 2.0 hours | +15% ↑ |
| **High Priority Tasks** | 18 (38%) | 15 (37%) | +3% ↑ |
| **Tasks from Gmail** | 32 (68%) | 28 (68%) | 0% → |
| **Approval Requests** | 12 | 10 | +20% ↑ |
| **Human Interventions** | 3 | 2 | +50% ↑ |

---

### Task Breakdown by Priority

| Priority | Count | % | Avg Response Time |
|----------|-------|---|-------------------|
| High | 18 | 38% | 1.2 hours |
| Medium | 22 | 47% | 2.8 hours |
| Low | 7 | 15% | 4.5 hours |

---

### Task Breakdown by Source

| Source | Count | % | Avg Response Time |
|--------|-------|---|-------------------|
| Gmail | 32 | 68% | 2.1 hours |
| WhatsApp | 10 | 22% | 2.8 hours |
| File System | 5 | 10% | 2.0 hours |

---

### Top 5 Clients by Task Volume

| Rank | Client | Tasks | % of Total |
|------|--------|-------|------------|
| 1 | Client A (client.a@example.com) | 12 | 26% |
| 2 | Client B (client.b@example.com) | 8 | 17% |
| 3 | Client C (client.c@example.com) | 6 | 13% |
| 4 | Internal (team@company.com) | 5 | 11% |
| 5 | Client D (client.d@example.com) | 4 | 9% |

---

### Insights & Recommendations

#### 1. Volume Spike from Client A
Client A generated 12 tasks this week (26% of total), up from 7 last week (+71%). This represents a significant increase.

**Recommendation:** Schedule call with Client A to understand needs. Consider dedicated account manager or proactive outreach.

#### 2. Response Time Increase
Average response time increased 15% (2.0h → 2.3h) despite only 15% more tasks. This suggests processing inefficiency or complexity increase.

**Recommendation:** Review task complexity. Consider optimizing Claude prompts or adding automation for common patterns.

#### 3. High Approval Request Rate
12 approval requests this week (26% of tasks) required human review. This is above historical average (18%).

**Recommendation:** Audit approval triggers. Determine if threshold adjustments could reduce human intervention while maintaining safety.

---

### Anomalies & Alerts

| Date | Task ID | Issue | Details |
|------|---------|-------|---------|
| Jan 25 | gmail_client_2026-01-25T14-00-00 | Long response time | 8.2 hours (3.5x avg) - Claude timeout, required retry |
| Jan 27 | whatsapp_1234567890_2026-01-27T10-00-00 | Human intervention | Task escalated to operator after 3 failed retries |
| Jan 28 | file_Contract_v5_2026-01-28T09-00-00 | Approval timeout | Approval request pending > 24h, moved to /Needs_Human_Review |

---

### Week-over-Week Trends

```
Task Volume Trend (Past 4 Weeks):
Week of Jan 1-7:   35 tasks
Week of Jan 8-14:  38 tasks (+9%)
Week of Jan 15-21: 41 tasks (+8%)
Week of Jan 22-28: 47 tasks (+15%)

→ Consistent upward trend, suggesting growing adoption
```

---

### Operational Health

| Indicator | Status | Notes |
|-----------|--------|-------|
| **Uptime** | ✅ 99.8% | 2 minutes downtime (system restart) |
| **Error Rate** | ✅ 4% | 2 tasks failed permanently (network errors) |
| **Approval Rate** | ⚠️ 26% | Above target (18%) - review thresholds |
| **SLA Compliance** | ✅ 100% | All urgent deadlines met |

---

### Upcoming Week Preview

**High-Priority Items (Deadlines < 3 days):**
- Board meeting prep (due Jan 30)
- Q4 financial report review (due Jan 31)
- Contract renewal for Client B (due Feb 1)

**Recommended Focus Areas:**
1. Reduce approval request rate (target: 18%)
2. Optimize response time for medium-priority tasks
3. Proactive outreach to Client A (high volume)

---

**Generated:** 2026-01-29T07:00:00Z
**Period:** Jan 22-28, 2026 (7 days)
**Data Source:** /Done folder (47 tasks)
**Tool:** FTE Monday Morning CEO Briefing v1.0
```

**Test Cases:**
1. **TC1.1**: Generate briefing for past week → verify 7 days of data aggregated
2. **TC1.2**: Briefing includes all required sections (summary, metrics, insights)
3. **TC1.3**: Briefing saved to `/Briefings/<date>_Weekly_Briefing.md`
4. **TC1.4**: No PII exposed (email addresses anonymized where needed)
5. **TC1.5**: Briefing generation logged via P2 infrastructure

---

### US2: PDF Export (Platinum Tier)

**As an** executive
**I want** briefings exported as PDF
**So that** I can print or share them with stakeholders

**Acceptance Criteria:**
- [ ] Briefing can be exported to PDF via `fte briefing --format pdf`
- [ ] PDF includes company branding (logo, colors, fonts)
- [ ] PDF is well-formatted (page breaks, headers, footers)
- [ ] PDF saved to `/Briefings/<date>_Weekly_Briefing.pdf`
- [ ] PDF generation uses pandoc or weasyprint

**Example:**

```bash
# Generate PDF briefing
fte briefing --week last --format pdf

# Output:
# ✅ Briefing generated: /Briefings/2026-01-29_Weekly_Briefing.pdf
# 📄 Size: 245 KB
# 📊 Pages: 4
```

**Test Cases:**
1. **TC2.1**: Generate PDF briefing → verify PDF created
2. **TC2.2**: PDF includes company logo and branding
3. **TC2.3**: PDF page breaks at logical sections
4. **TC2.4**: PDF is readable (fonts, spacing, margins correct)
5. **TC2.5**: PDF file size reasonable (< 1MB)

---

### US3: Email Delivery (Platinum Tier)

**As an** executive
**I want** briefings automatically emailed every Monday
**So that** I receive them without manual retrieval

**Acceptance Criteria:**
- [ ] Briefing can be emailed via `fte briefing --email ceo@company.com`
- [ ] Email includes briefing as attachment (PDF or Markdown)
- [ ] Email subject: "Monday Morning CEO Briefing - Week of [Date]"
- [ ] Email sent via SMTP (configurable server, credentials)
- [ ] Scheduled email delivery (cron job: Monday 7 AM)

**Example Cron Job:**

```bash
# /etc/cron.d/fte-briefing

# Send CEO briefing every Monday at 7:00 AM
0 7 * * 1 /usr/bin/fte briefing --week last --format pdf --email ceo@company.com
```

**Email Template:**

```
From: AI Employee <fte@company.com>
To: CEO <ceo@company.com>
Subject: Monday Morning CEO Briefing - Week of January 22-28, 2026

Hello,

Attached is your weekly AI Employee performance summary for the week of January 22-28, 2026.

Key highlights:
- 47 tasks completed (+15% vs last week)
- 2.3 hour avg response time
- 100% SLA compliance (all urgent deadlines met)

Please review the full briefing for insights and recommendations.

Best regards,
AI Employee (FTE v1.0)

---
Attachment: 2026-01-29_Weekly_Briefing.pdf (245 KB)
```

**Test Cases:**
1. **TC3.1**: Send briefing email → verify email received by recipient
2. **TC3.2**: Email attachment is PDF (correct format)
3. **TC3.3**: Email subject line correct (includes date range)
4. **TC3.4**: Cron job executes Monday 7 AM → email sent automatically
5. **TC3.5**: SMTP authentication successful (no credential errors)

---

### US4: Custom Date Ranges (Platinum Tier)

**As an** executive
**I want** to generate briefings for custom date ranges
**So that** I can analyze specific time periods (monthly, quarterly)

**Acceptance Criteria:**
- [ ] Support custom date ranges: `fte briefing --from 2026-01-01 --to 2026-01-31`
- [ ] Support predefined ranges: `--week last`, `--week current`, `--month last`, `--quarter last`
- [ ] Briefing adapts title and content based on date range
- [ ] Historical comparison available (vs previous period)

**Example:**

```bash
# Generate monthly briefing
fte briefing --month last --format pdf

# Output:
# ✅ Monthly Briefing generated: /Briefings/2026-01-31_Monthly_Briefing.pdf
# 📊 Period: January 1-31, 2026 (31 days)
# 📈 Total tasks: 187 (+23% vs December)
```

**Test Cases:**
1. **TC4.1**: Generate briefing for last month → verify 31 days of data
2. **TC4.2**: Generate briefing for Q4 2025 → verify 92 days of data
3. **TC4.3**: Generate briefing for custom range (Jan 15-25) → verify 11 days
4. **TC4.4**: Briefing title reflects date range ("Monthly Briefing", "Quarterly Briefing")
5. **TC4.5**: Historical comparison included (vs previous period)

---

### US5: Insight Generation with Claude (Platinum Tier)

**As an** executive
**I want** AI-generated insights and recommendations in briefings
**So that** I get actionable intelligence, not just raw metrics

**Acceptance Criteria:**
- [ ] Briefing includes "Insights & Recommendations" section
- [ ] Claude analyzes task data and generates 3-5 insights
- [ ] Insights are actionable (specific recommendations included)
- [ ] Insights identify patterns (volume spikes, bottlenecks, anomalies)
- [ ] Insights reference specific data points (task IDs, clients, dates)

**Example Insights:**

```markdown
### Insights & Recommendations (AI-Generated)

#### 1. Client A Volume Spike (+71% WoW)
**Pattern Detected:** Client A task volume increased from 7 to 12 tasks (+71%).
  This is the highest weekly volume from any single client this month.

**Recommendation:** Proactive outreach to Client A. Schedule quarterly business
  review to understand needs and explore expansion opportunities. Consider
  dedicated account management if volume sustains.

**Confidence:** High (based on 4 weeks historical data)

#### 2. Approval Bottleneck (26% approval rate)
**Pattern Detected:** 12 of 47 tasks (26%) required human approval, up from
  historical average of 18%. This is adding 3-4 hours of human time per week.

**Recommendation:** Audit approval triggers. Common patterns observed:
  - Payment actions > $1,000 (8 tasks)
  - External email sending (3 tasks)
  - File deletions (1 task)

  Consider raising payment threshold to $5,000 or implementing tiered approvals.

**Confidence:** Medium (limited historical data)

#### 3. Response Time Degradation (+15% WoW)
**Pattern Detected:** Avg response time increased from 2.0h to 2.3h despite
  only 15% volume increase. This suggests processing inefficiency.

**Root Cause Analysis:**
  - 2 tasks experienced Claude timeouts (8+ hour response time)
  - 3 tasks required multiple retries (network errors)
  - Complex tasks (contract review) took 2x longer than email responses

**Recommendation:**
  1. Optimize Claude prompts for complex tasks (contract review templates)
  2. Increase Claude timeout from 10min to 15min for document-heavy tasks
  3. Implement pre-processing for large attachments (OCR, summarization)

**Confidence:** High (clear correlation between task complexity and response time)
```

**Test Cases:**
1. **TC5.1**: Briefing includes "Insights & Recommendations" section
2. **TC5.2**: 3-5 insights generated automatically
3. **TC5.3**: Insights reference specific data (task IDs, clients, percentages)
4. **TC5.4**: Insights include actionable recommendations
5. **TC5.5**: Insight confidence levels indicated (High, Medium, Low)

---

## Functional Requirements

### FR1: Data Aggregation Functions

| ID | Requirement | Priority |
|----|-------------|----------|
| FR1.1 | Scan `/Done` folder for tasks in date range | P3 (Gold) |
| FR1.2 | Parse YAML frontmatter from all task files | P3 (Gold) |
| FR1.3 | Extract fields: source, priority, timestamps, status | P3 (Gold) |
| FR1.4 | Store aggregated data in memory (dataframe) | P3 (Gold) |
| FR1.5 | Handle malformed YAML gracefully (skip, log error) | P3 (Gold) |

### FR2: Metrics Calculation Functions

| ID | Requirement | Priority |
|----|-------------|----------|
| FR2.1 | Calculate total tasks completed | P3 (Gold) |
| FR2.2 | Calculate avg response time (created → completed) | P3 (Gold) |
| FR2.3 | Calculate priority distribution (high, medium, low) | P3 (Gold) |
| FR2.4 | Calculate source distribution (gmail, whatsapp, files) | P3 (Gold) |
| FR2.5 | Calculate week-over-week trends (% change) | P4 (Platinum) |
| FR2.6 | Identify top 5 clients by task volume | P3 (Gold) |

### FR3: Insight Generation Functions

| ID | Requirement | Priority |
|----|-------------|----------|
| FR3.1 | Identify anomalies (unusually long response times) | P3 (Gold) |
| FR3.2 | Detect patterns (recurring clients, subjects) | P3 (Gold) |
| FR3.3 | Generate AI insights using Claude (optional) | P4 (Platinum) |
| FR3.4 | Provide actionable recommendations | P4 (Platinum) |

### FR4: Report Generation Functions

| ID | Requirement | Priority |
|----|-------------|----------|
| FR4.1 | Render Markdown report using Jinja2 template | P3 (Gold) |
| FR4.2 | Save Markdown to `/Briefings/<date>_Weekly_Briefing.md` | P3 (Gold) |
| FR4.3 | Convert Markdown to PDF (pandoc or weasyprint) | P4 (Platinum) |
| FR4.4 | Apply company branding (logo, colors, fonts) | P4 (Platinum) |

### FR5: Delivery Functions

| ID | Requirement | Priority |
|----|-------------|----------|
| FR5.1 | CLI command: `fte briefing` (default: last week) | P3 (Gold) |
| FR5.2 | Support custom date ranges (`--from`, `--to`) | P4 (Platinum) |
| FR5.3 | Support predefined ranges (`--week last`, `--month last`) | P4 (Platinum) |
| FR5.4 | Email delivery via SMTP (`--email <recipient>`) | P4 (Platinum) |
| FR5.5 | Scheduled generation (cron job: Monday 7 AM) | P4 (Platinum) |

---

## Non-Functional Requirements

### NFR1: Performance

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR1.1 | Briefing generation time | < 10s | Time from CLI invocation → file written |
| NFR1.2 | PDF conversion time | < 5s | Time from Markdown → PDF |
| NFR1.3 | Email delivery time | < 3s | Time from SMTP send → delivery confirmation |
| NFR1.4 | Memory footprint | < 100MB | RSS memory during generation |

### NFR2: Reliability

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR2.1 | Data accuracy | 100% | All task data correctly aggregated |
| NFR2.2 | Calculation correctness | 100% | Metrics match manual verification |
| NFR2.3 | Generation success rate | 99% | Successful generations / total attempts |

### NFR3: Usability

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR3.1 | CLI simplicity | Single command | `fte briefing` (no args required) |
| NFR3.2 | Report readability | Executive-friendly | Non-technical language, clear visuals |
| NFR3.3 | Delivery latency | Same day | Briefing delivered by 7 AM Monday |

---

## Technical Architecture

### Component Design

```python
# src/briefing/briefing_generator.py

from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict
import pandas as pd
from jinja2 import Template

from src.logging import get_logger

logger = get_logger(__name__)


class BriefingGenerator:
    """
    Generate Monday Morning CEO Briefing.

    Responsibilities:
    - Aggregate data from /Done folder
    - Calculate metrics
    - Generate insights
    - Render Markdown/PDF report
    """

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.done_folder = vault_path / "Done"
        self.briefings_folder = vault_path / "Briefings"
        self.briefings_folder.mkdir(exist_ok=True)

    def generate(
        self,
        from_date: datetime,
        to_date: datetime,
        format: str = "markdown"
    ) -> Path:
        """
        Generate briefing for date range.

        Args:
            from_date: Start date (inclusive)
            to_date: End date (inclusive)
            format: Output format ("markdown" or "pdf")

        Returns:
            Path to generated briefing file
        """
        logger.info(
            f"Generating briefing for {from_date.date()} to {to_date.date()}",
            context={'format': format}
        )

        # Step 1: Aggregate data
        tasks = self._aggregate_tasks(from_date, to_date)
        logger.info(f"Aggregated {len(tasks)} tasks")

        # Step 2: Calculate metrics
        metrics = self._calculate_metrics(tasks)
        logger.info(f"Calculated metrics: {metrics['total_tasks']} tasks")

        # Step 3: Generate insights
        insights = self._generate_insights(tasks, metrics)
        logger.info(f"Generated {len(insights)} insights")

        # Step 4: Render report
        briefing_data = {
            'from_date': from_date,
            'to_date': to_date,
            'generated_at': datetime.now(timezone.utc),
            'metrics': metrics,
            'insights': insights,
            'tasks': tasks  # For detailed analysis
        }

        markdown_path = self._render_markdown(briefing_data)
        logger.info(f"Markdown briefing: {markdown_path}")

        if format == "pdf":
            pdf_path = self._convert_to_pdf(markdown_path)
            logger.info(f"PDF briefing: {pdf_path}")
            return pdf_path

        return markdown_path

    def _aggregate_tasks(
        self,
        from_date: datetime,
        to_date: datetime
    ) -> List[Dict]:
        """
        Aggregate tasks from /Done folder in date range.

        Args:
            from_date: Start date
            to_date: End date

        Returns:
            List of task dictionaries
        """
        tasks = []

        for task_file in self.done_folder.glob("*.md"):
            try:
                # Parse YAML frontmatter
                metadata = self._parse_yaml_frontmatter(task_file)

                # Check if task completed in date range
                completed_at = datetime.fromisoformat(metadata.get('completed_at'))

                if from_date <= completed_at <= to_date:
                    tasks.append({
                        'filename': task_file.name,
                        'task_id': metadata.get('task_id'),
                        'source': metadata.get('source'),
                        'priority': metadata.get('priority'),
                        'from': metadata.get('from'),
                        'subject': metadata.get('subject'),
                        'created_at': datetime.fromisoformat(metadata.get('created_at')),
                        'completed_at': completed_at,
                        'status': metadata.get('status'),
                        'response_time_hours': self._calculate_response_time(metadata)
                    })

            except Exception as e:
                logger.warning(f"Failed to parse task: {task_file.name} - {e}")
                continue

        return tasks

    def _calculate_metrics(self, tasks: List[Dict]) -> Dict:
        """
        Calculate metrics from task data.

        Args:
            tasks: List of task dictionaries

        Returns:
            Metrics dictionary
        """
        df = pd.DataFrame(tasks)

        if df.empty:
            return {'total_tasks': 0}

        metrics = {
            'total_tasks': len(df),
            'avg_response_time_hours': df['response_time_hours'].mean(),
            'median_response_time_hours': df['response_time_hours'].median(),

            # Priority distribution
            'priority_distribution': df['priority'].value_counts().to_dict(),

            # Source distribution
            'source_distribution': df['source'].value_counts().to_dict(),

            # Top 5 clients by volume
            'top_clients': df['from'].value_counts().head(5).to_dict(),

            # Anomalies (response time > 2x avg)
            'anomalies': df[
                df['response_time_hours'] > 2 * df['response_time_hours'].mean()
            ].to_dict('records')
        }

        return metrics

    def _generate_insights(
        self,
        tasks: List[Dict],
        metrics: Dict
    ) -> List[Dict]:
        """
        Generate insights from task data and metrics.

        Args:
            tasks: List of task dictionaries
            metrics: Metrics dictionary

        Returns:
            List of insight dictionaries
        """
        insights = []

        # Insight 1: Volume trends
        if metrics['total_tasks'] > 0:
            # Compare to previous week (placeholder - would query historical data)
            insights.append({
                'title': 'Task Volume',
                'description': f"Processed {metrics['total_tasks']} tasks this week.",
                'recommendation': "Monitor for sustained growth."
            })

        # Insight 2: Top client
        if metrics.get('top_clients'):
            top_client = list(metrics['top_clients'].items())[0]
            insights.append({
                'title': f"Top Client: {top_client[0]}",
                'description': f"{top_client[1]} tasks ({top_client[1]/metrics['total_tasks']*100:.0f}%)",
                'recommendation': "Consider proactive outreach or dedicated support."
            })

        # Insight 3: Anomalies
        if metrics.get('anomalies'):
            insights.append({
                'title': "Response Time Anomalies",
                'description': f"{len(metrics['anomalies'])} tasks took >2x avg response time.",
                'recommendation': "Review for process improvements or resource constraints."
            })

        return insights

    def _render_markdown(self, briefing_data: Dict) -> Path:
        """
        Render Markdown briefing using Jinja2 template.

        Args:
            briefing_data: Briefing data dictionary

        Returns:
            Path to generated Markdown file
        """
        template_path = Path(__file__).parent / "templates" / "briefing_template.md.j2"
        template = Template(template_path.read_text())

        markdown_content = template.render(**briefing_data)

        # Save to /Briefings
        filename = f"{briefing_data['to_date'].date()}_Weekly_Briefing.md"
        output_path = self.briefings_folder / filename

        output_path.write_text(markdown_content, encoding='utf-8')

        return output_path

    def _convert_to_pdf(self, markdown_path: Path) -> Path:
        """
        Convert Markdown to PDF using pandoc.

        Args:
            markdown_path: Path to Markdown file

        Returns:
            Path to generated PDF file
        """
        import subprocess

        pdf_path = markdown_path.with_suffix('.pdf')

        cmd = [
            'pandoc',
            str(markdown_path),
            '-o', str(pdf_path),
            '--pdf-engine=weasyprint',
            '--template=briefing_template.tex',  # Custom LaTeX template
            '--variable=company_name:Company Inc',
            '--variable=logo:company_logo.png'
        ]

        subprocess.run(cmd, check=True)

        return pdf_path

    def _calculate_response_time(self, metadata: Dict) -> float:
        """
        Calculate response time in hours.

        Args:
            metadata: Task metadata dictionary

        Returns:
            Response time in hours
        """
        created_at = datetime.fromisoformat(metadata.get('created_at'))
        completed_at = datetime.fromisoformat(metadata.get('completed_at'))

        delta = completed_at - created_at
        return delta.total_seconds() / 3600  # Convert to hours

    def _parse_yaml_frontmatter(self, file_path: Path) -> Dict:
        """Parse YAML frontmatter from Markdown file."""
        import yaml

        content = file_path.read_text(encoding='utf-8')

        # Extract YAML frontmatter between --- markers
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                yaml_content = parts[1]
                return yaml.safe_load(yaml_content)

        return {}


# CLI Integration

def cli_briefing(args):
    """
    CLI command: fte briefing

    Args:
        args: CLI arguments (--week, --format, --email, etc.)
    """
    from src.briefing.briefing_generator import BriefingGenerator

    vault_path = Path(os.getenv('VAULT_PATH', '/path/to/AI_Employee_Vault'))
    generator = BriefingGenerator(vault_path)

    # Parse date range
    if args.week == 'last':
        # Last Monday-Sunday
        today = datetime.now(timezone.utc)
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        from_date = last_monday.replace(hour=0, minute=0, second=0)
        to_date = last_sunday.replace(hour=23, minute=59, second=59)

    # Generate briefing
    output_path = generator.generate(from_date, to_date, format=args.format)

    print(f"✅ Briefing generated: {output_path}")

    # Email delivery (optional)
    if args.email:
        send_email(args.email, output_path)
        print(f"📧 Briefing emailed to: {args.email}")
```

---

## Briefing Template Design

### Jinja2 Template Structure

```jinja2
{# src/briefing/templates/briefing_template.md.j2 #}

# Monday Morning CEO Briefing
## Week of {{ from_date.strftime('%B %d') }}-{{ to_date.strftime('%d, %Y') }}

---

### Executive Summary

The AI Employee processed **{{ metrics.total_tasks }} tasks** this week, maintaining an average response time of **{{ "%.1f"|format(metrics.avg_response_time_hours) }} hours**.

{% if metrics.priority_distribution.get('high') %}
High-priority tasks were handled efficiently (avg {{ "%.1f"|format(metrics.avg_response_time_high) }} hours).
{% endif %}

**Key Highlights:**
{% for insight in insights %}
- {{ insight.title }}: {{ insight.description }}
{% endfor %}

---

### Metrics Dashboard

| Metric | This Week | Last Week | Change |
|--------|-----------|-----------|--------|
| **Total Tasks** | {{ metrics.total_tasks }} | {{ metrics.last_week_tasks }} | {{ metrics.tasks_change }}% |
| **Avg Response Time** | {{ "%.1f"|format(metrics.avg_response_time_hours) }} hours | {{ "%.1f"|format(metrics.last_week_response_time) }} hours | {{ metrics.response_time_change }}% |

---

### Task Breakdown by Priority

| Priority | Count | % | Avg Response Time |
|----------|-------|---|-------------------|
{% for priority, count in metrics.priority_distribution.items() %}
| {{ priority.title() }} | {{ count }} | {{ "%.0f"|format(count/metrics.total_tasks*100) }}% | {{ "%.1f"|format(metrics.avg_response_time_by_priority[priority]) }} hours |
{% endfor %}

---

### Top 5 Clients by Task Volume

| Rank | Client | Tasks | % of Total |
|------|--------|-------|------------|
{% for client, count in metrics.top_clients.items() %}
| {{ loop.index }} | {{ client }} | {{ count }} | {{ "%.0f"|format(count/metrics.total_tasks*100) }}% |
{% endfor %}

---

### Insights & Recommendations

{% for insight in insights %}
#### {{ loop.index }}. {{ insight.title }}
{{ insight.description }}

**Recommendation:** {{ insight.recommendation }}

{% endfor %}

---

**Generated:** {{ generated_at.isoformat() }}
**Period:** {{ from_date.strftime('%b %d') }}-{{ to_date.strftime('%d, %Y') }} ({{ (to_date - from_date).days + 1 }} days)
**Data Source:** /Done folder ({{ metrics.total_tasks }} tasks)
**Tool:** FTE Monday Morning CEO Briefing v1.0
```

---

## Data Aggregation

### Task File Parsing

```python
def parse_task_file(file_path: Path) -> Dict:
    """
    Parse task Markdown file and extract metadata.

    Expected YAML frontmatter:
    ---
    source: gmail
    task_id: gmail_ceo_2026-01-28T10-00-00
    from: ceo@company.com
    subject: "Board meeting prep"
    priority: high
    created_at: 2026-01-28T10:00:00Z
    started_at: 2026-01-28T10:05:00Z
    completed_at: 2026-01-28T11:30:00Z
    status: success
    ---

    Args:
        file_path: Path to task Markdown file

    Returns:
        Task metadata dictionary
    """
    import yaml

    content = file_path.read_text(encoding='utf-8')

    # Extract YAML frontmatter
    if not content.startswith('---'):
        raise ValueError(f"Invalid task file format: {file_path}")

    parts = content.split('---', 2)
    if len(parts) < 3:
        raise ValueError(f"Malformed YAML frontmatter: {file_path}")

    yaml_content = parts[1]
    metadata = yaml.safe_load(yaml_content)

    # Validate required fields
    required_fields = ['source', 'task_id', 'created_at', 'completed_at']
    for field in required_fields:
        if field not in metadata:
            raise ValueError(f"Missing required field: {field}")

    return metadata
```

---

## Security Considerations

### SEC1: PII Anonymization

**Risk:** Email addresses, phone numbers exposed in briefings

**Mitigation:**
1. Anonymize email addresses in reports (e.g., "c***@example.com")
2. Aggregate data (counts, percentages) instead of individual records
3. No PII in briefing titles or filenames

**Example:**

```python
def anonymize_email(email: str) -> str:
    """Anonymize email address for reports."""
    local, domain = email.split('@')

    # Show first character, mask rest
    anonymized_local = local[0] + '*' * (len(local) - 1)

    return f"{anonymized_local}@{domain}"

# Example:
# ceo@company.com → c**@company.com
# john.doe@example.com → j*******@example.com
```

---

## Constitutional Compliance

| Constitutional Section | Requirement | CEO Briefing Compliance |
|------------------------|-------------|------------------------|
| **Section 2: Source of Truth** | Obsidian vault is authoritative | ✅ Reads from `/Done` folder only |
| **Section 3: Privacy First** | No PII in logs or reports | ✅ Email anonymization implemented |
| **Section 8: Auditability** | All actions logged | ✅ P2 logging for briefing generation |

---

## Implementation Phases

### Phase 1: Data Aggregation (Gold Tier) - 2-3 hours

**Deliverables:**
- [ ] `src/briefing/briefing_generator.py` (BriefingGenerator class)
- [ ] Task file parsing (YAML frontmatter)
- [ ] Date range filtering
- [ ] Pandas DataFrame aggregation

**Acceptance Test:**
```python
# Test: Aggregate tasks from last week
tasks = generator._aggregate_tasks(last_monday, last_sunday)
assert len(tasks) == 47
assert tasks[0]['source'] == 'gmail'
```

### Phase 2: Metrics Calculation (Gold Tier) - 1-2 hours

**Deliverables:**
- [ ] Total tasks calculation
- [ ] Avg response time calculation
- [ ] Priority distribution
- [ ] Source distribution
- [ ] Top 5 clients

**Acceptance Test:**
```python
# Test: Calculate metrics
metrics = generator._calculate_metrics(tasks)
assert metrics['total_tasks'] == 47
assert metrics['avg_response_time_hours'] == 2.3
assert 'high' in metrics['priority_distribution']
```

### Phase 3: Markdown Rendering (Gold Tier) - 2-3 hours

**Deliverables:**
- [ ] Jinja2 template (`briefing_template.md.j2`)
- [ ] Template rendering
- [ ] Markdown output to `/Briefings`
- [ ] CLI integration (`fte briefing`)

**Acceptance Test:**
```bash
# Test: Generate Markdown briefing
fte briefing

# Verify output
ls Briefings/
# Expected: 2026-01-29_Weekly_Briefing.md

cat Briefings/2026-01-29_Weekly_Briefing.md | head -20
# Expected: Markdown report with metrics
```

### Phase 4: PDF Export (Platinum Tier) - 1-2 hours

**Deliverables:**
- [ ] Pandoc integration
- [ ] PDF conversion
- [ ] Company branding (logo, colors)
- [ ] CLI integration (`--format pdf`)

**Acceptance Test:**
```bash
# Test: Generate PDF briefing
fte briefing --format pdf

# Verify output
ls Briefings/
# Expected: 2026-01-29_Weekly_Briefing.pdf

file Briefings/2026-01-29_Weekly_Briefing.pdf
# Expected: PDF document, version 1.7
```

### Phase 5: Email Delivery (Platinum Tier) - 1-2 hours

**Deliverables:**
- [ ] SMTP integration
- [ ] Email template
- [ ] Attachment handling
- [ ] CLI integration (`--email <recipient>`)
- [ ] Cron job configuration

**Acceptance Test:**
```bash
# Test: Send briefing via email
fte briefing --email ceo@company.com

# Verify email received
# (Manual verification required)
```

---

## Success Metrics

### Gold Tier (Basic Briefing)

- [ ] Briefing aggregates data from `/Done` folder (past 7 days)
- [ ] Briefing includes all required metrics (tasks, response time, priorities)
- [ ] Briefing identifies top 5 clients correctly
- [ ] Briefing saved to `/Briefings` folder in Markdown format
- [ ] CLI command `fte briefing` works without errors

### Platinum Tier (Advanced Features)

- [ ] PDF export functional (pandoc conversion)
- [ ] Email delivery operational (SMTP sending)
- [ ] Scheduled generation (cron job Monday 7 AM)
- [ ] Custom date ranges supported (`--month last`, `--quarter last`)
- [ ] AI-generated insights included (using Claude)

---

## Open Questions

1. **Historical Data Storage:**
   - Should we store historical metrics in a database for trend analysis?
   - **Recommendation:** Start with file-based (past briefings), migrate to SQLite if needed.

2. **Chart/Graph Generation:**
   - Should briefings include visual charts (bar charts, line graphs)?
   - **Recommendation:** Defer to Platinum tier, use matplotlib or Chart.js.

3. **Multi-Recipient Email:**
   - Should briefings support multiple recipients (CC, BCC)?
   - **Recommendation:** Yes, support comma-separated email list.

4. **Briefing Customization:**
   - Should executives be able to customize briefing sections?
   - **Recommendation:** Yes, support configuration file (`briefing_config.yaml`).

5. **Real-Time Alerts:**
   - Should briefing system send alerts for critical issues (e.g., high error rate)?
   - **Recommendation:** Yes, implement alert thresholds in configuration.

---

## Appendix

### A1: Configuration Schema

```yaml
# config/briefing.yaml

schedule:
  enabled: true
  day: monday  # Day of week
  time: "07:00"  # 24-hour format
  timezone: UTC

format:
  default: markdown  # or pdf
  markdown_template: templates/briefing_template.md.j2
  pdf_template: templates/briefing_template.tex

recipients:
  - ceo@company.com
  - coo@company.com

smtp:
  server: smtp.company.com
  port: 587
  username: fte@company.com
  password: ${SMTP_PASSWORD}  # Environment variable
  from: "AI Employee <fte@company.com>"

branding:
  company_name: "Company Inc"
  logo: assets/company_logo.png
  primary_color: "#0066CC"
  secondary_color: "#FF6600"

metrics:
  include:
    - total_tasks
    - avg_response_time
    - priority_distribution
    - source_distribution
    - top_clients
    - anomalies
  exclude: []

insights:
  enabled: true
  use_claude: true  # AI-generated insights
  min_insights: 3
  max_insights: 5

anonymization:
  enabled: true
  anonymize_emails: true
  anonymize_phone_numbers: true
```

### A2: CLI Commands Reference

```bash
# Generate briefing for last week (default)
fte briefing

# Generate briefing for last month
fte briefing --month last

# Generate briefing for custom date range
fte briefing --from 2026-01-01 --to 2026-01-31

# Generate PDF briefing
fte briefing --format pdf

# Email briefing to recipient
fte briefing --email ceo@company.com

# Email PDF briefing
fte briefing --format pdf --email ceo@company.com

# Generate briefing for current week (Monday-today)
fte briefing --week current

# Test briefing generation (dry run, no file written)
fte briefing --dry-run

# View briefing configuration
fte briefing --show-config

# List all historical briefings
fte briefing --list
```

---

## Change Log

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-01-28 | v1.0 | AI Employee Team | Initial specification |

---

**Next Steps:**
1. Review spec with executive stakeholders
2. Generate implementation plan using `/sp.plan`
3. Generate task breakdown using `/sp.tasks`
4. Begin Gold Tier implementation (data aggregation, Markdown rendering)

---

*This specification is part of the Personal AI Employee Hackathon 0 project. For related specs, see:*
- *[P2: Logging Infrastructure](../002-logging-infrastructure/spec.md)*
- *[P3: CLI Integration Roadmap](../003-cli-integration-roadmap/spec.md)*
- *[P5: Watcher Scripts](../005-watcher-scripts/spec.md)*
- *[P6: Orchestrator & Scheduler](../006-orchestrator-scheduler/spec.md)*
