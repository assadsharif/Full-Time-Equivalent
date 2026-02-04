# Tasks: Monday Morning CEO Briefing

**Input**: Design documents from `/specs/007-ceo-briefing/`
**Prerequisites**: plan.md ✅, spec.md ✅

**Status**: Bronze ✅ DONE | Silver ✅ DONE | Gold ⚠️ IN PROGRESS | Platinum ❌ NOT STARTED

**Completed Work**:
- ✅ Bronze Tier: Data aggregation (`BriefingAggregator`), metrics calculation, Markdown rendering (`TemplateRenderer`)
- ✅ Silver Tier: PDF generation (`generate_pdf`, `generate_pdf_to_file` using fpdf2)
- ✅ Tests: 27 passing tests (aggregation, rendering, PDF, end-to-end pipeline)

**This Document**: Tasks for remaining Gold/Platinum tier features (AI insights, email delivery, scheduling, custom date ranges)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US3, US4, US5)
- Include exact file paths in descriptions

---

## Phase 1: Setup (No additional setup needed)

**Bronze/Silver infrastructure complete**. Existing structure:

```
src/briefing/
├── __init__.py            ✅ Exports BriefingAggregator, TemplateRenderer, generate_pdf
├── aggregator.py          ✅ Data aggregation from /Done (Bronze)
├── models.py              ✅ BriefingData, TaskSummary
├── template_renderer.py   ✅ Jinja2 rendering (Bronze)
└── pdf_generator.py       ✅ PDF generation (Silver)

templates/briefing/
└── executive_summary.md.j2  ✅ Markdown template

tests/briefing/
├── test_briefing.py        ✅ 27 tests passing
└── tests/integration/test_module_integration.py  ✅ 2 briefing pipeline tests
```

---

## Phase 2: Foundational (No blocking prerequisites)

**All foundational work complete**. Bronze/Silver tiers provide full data pipeline and rendering.

**Checkpoint**: Foundation ready - Gold/Platinum features can now be added

---

## Phase 3: User Story 3 - Email Delivery (Priority: P4 - Platinum Tier)

**Goal**: Automatically email CEO briefings every Monday at 7 AM

**Independent Test**: Run `fte briefing --email ceo@company.com` and verify email received with PDF attachment

### Implementation for User Story 3

- [ ] T001 [P] [US3] Create EmailDeliveryService in src/briefing/email_delivery.py
- [ ] T002 [US3] Implement SMTP configuration loading from config/briefing.yaml in src/briefing/email_delivery.py
- [ ] T003 [US3] Add send_briefing_email method with attachment support in src/briefing/email_delivery.py
- [ ] T004 [US3] Create email_body.html.j2 template in templates/briefing/email_body.html.j2
- [ ] T005 [US3] Add --email flag to fte briefing CLI command in src/cli/briefing.py
- [ ] T006 [P] [US3] Add tests for email delivery in tests/briefing/test_email_delivery.py
- [ ] T007 [US3] Update BriefingGenerator to support email delivery in src/briefing/aggregator.py

**Checkpoint**: Email delivery functional - CLI can send briefings via SMTP

---

## Phase 4: User Story 4 - Custom Date Ranges (Priority: P4 - Platinum Tier)

**Goal**: Generate briefings for custom date ranges (monthly, quarterly, custom from/to)

**Independent Test**: Run `fte briefing --month last --format pdf` and verify 31 days of data aggregated

### Implementation for User Story 4

- [ ] T008 [P] [US4] Add date_range_parser module in src/briefing/date_range_parser.py
- [ ] T009 [P] [US4] Implement parse_predefined_range function (--week last/current, --month last, --quarter last) in src/briefing/date_range_parser.py
- [ ] T010 [P] [US4] Implement parse_custom_range function (--from DATE --to DATE) in src/briefing/date_range_parser.py
- [ ] T011 [US4] Add --week, --month, --quarter, --from, --to flags to fte briefing CLI in src/cli/briefing.py
- [ ] T012 [US4] Update BriefingAggregator.aggregate to accept from_date, to_date parameters in src/briefing/aggregator.py
- [ ] T013 [US4] Update report title generation to reflect date range (Weekly/Monthly/Quarterly) in src/briefing/template_renderer.py
- [ ] T014 [P] [US4] Add tests for custom date ranges in tests/briefing/test_date_ranges.py
- [ ] T015 [US4] Add historical comparison logic (vs previous period) in src/briefing/aggregator.py

**Checkpoint**: Custom date ranges working - Can generate weekly, monthly, quarterly briefings

---

## Phase 5: User Story 5 - AI Insights Generation (Priority: P4 - Platinum Tier)

**Goal**: Generate actionable AI insights and recommendations using Claude

**Independent Test**: Generate briefing and verify "Insights & Recommendations" section contains 3-5 AI-generated insights with confidence levels

### Implementation for User Story 5

- [ ] T016 [P] [US5] Create InsightGenerator class in src/briefing/insight_generator.py
- [ ] T017 [P] [US5] Implement detect_volume_patterns method in src/briefing/insight_generator.py
- [ ] T018 [P] [US5] Implement detect_response_time_issues method in src/briefing/insight_generator.py
- [ ] T019 [P] [US5] Implement detect_approval_bottlenecks method in src/briefing/insight_generator.py
- [ ] T020 [US5] Add generate_claude_insights method using Claude Code invocation in src/briefing/insight_generator.py
- [ ] T021 [US5] Create insights_prompt.txt template for Claude analysis in templates/briefing/insights_prompt.txt
- [ ] T022 [US5] Update executive_summary.md.j2 to include Insights & Recommendations section in templates/briefing/executive_summary.md.j2
- [ ] T023 [US5] Add --insights flag to fte briefing CLI to enable/disable AI insights in src/cli/briefing.py
- [ ] T024 [US5] Integrate InsightGenerator into BriefingAggregator.aggregate in src/briefing/aggregator.py
- [ ] T025 [P] [US5] Add tests for insight generation in tests/briefing/test_insights.py
- [ ] T026 [US5] Add confidence level calculation for insights in src/briefing/insight_generator.py

**Checkpoint**: AI insights working - Briefings include actionable recommendations with confidence levels

---

## Phase 6: User Story 3 Extended - Scheduled Delivery (Priority: P4 - Platinum Tier)

**Goal**: Automatically send briefings every Monday at 7 AM via cron

**Independent Test**: Configure cron job and verify briefing email received Monday 7 AM UTC

### Implementation for User Story 3 Extended

- [ ] T027 [P] [US3] Create cron job configuration template in config/cron.d/fte-briefing
- [ ] T028 [US3] Add install-cron command to fte CLI in src/cli/briefing.py
- [ ] T029 [US3] Create briefing scheduler script in scripts/briefing_scheduler.py
- [ ] T030 [US3] Add logging for scheduled briefing runs in scripts/briefing_scheduler.py
- [ ] T031 [P] [US3] Add documentation for cron setup in docs/briefing_scheduling.md

**Checkpoint**: Scheduled delivery working - Briefings sent automatically every Monday

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Configuration, documentation, and testing improvements

- [ ] T032 [P] Create config/briefing.yaml configuration file with SMTP settings, recipients, branding
- [ ] T033 [P] Add PII anonymization utilities in src/briefing/anonymize.py (anonymize_email, anonymize_phone)
- [ ] T034 [P] Update executive_summary.md.j2 to use anonymized emails in templates/briefing/executive_summary.md.j2
- [ ] T035 [P] Add --dry-run flag to fte briefing CLI for testing without sending in src/cli/briefing.py
- [ ] T036 [P] Add --list command to show all historical briefings in src/cli/briefing.py
- [ ] T037 [P] Add --show-config command to display current configuration in src/cli/briefing.py
- [ ] T038 [P] Create end-to-end test for full briefing workflow (aggregate → render → PDF → email) in tests/briefing/test_e2e_briefing.py
- [ ] T039 [P] Update README with CEO briefing usage examples in docs/README_BRIEFING.md
- [ ] T040 [P] Add performance tests for briefing generation (<30s target) in tests/performance/test_briefing_performance.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1-2**: Complete ✅
- **Phase 3-6**: User Stories can proceed in parallel (all independent of each other)
  - US3 (Email): No dependencies
  - US4 (Date Ranges): No dependencies
  - US5 (AI Insights): No dependencies
  - US3 Extended (Scheduling): Depends on US3 completion
- **Phase 7**: Can start anytime, runs in parallel with user stories

### User Story Dependencies

- **User Story 3 (Email Delivery)**: Can start immediately - No dependencies
- **User Story 4 (Custom Date Ranges)**: Can start immediately - No dependencies
- **User Story 5 (AI Insights)**: Can start immediately - No dependencies
- **User Story 3 Extended (Scheduling)**: Requires US3 tasks T001-T007 complete

### Within Each User Story

- US3: SMTP config → email service → CLI integration → tests
- US4: Date parser → CLI flags → aggregator updates → tests
- US5: Insight detectors → Claude integration → template updates → tests
- US3 Extended: Cron template → scheduler script → CLI install command

### Parallel Opportunities

- **Phase 3-5**: All three user stories (US3, US4, US5) can be developed in parallel by different team members
- Within US5: Tasks T016-T019 (insight detectors) can run in parallel
- Polish tasks (T032-T040) can all run in parallel

---

## Parallel Example: User Story 5 (AI Insights)

```bash
# Launch all insight detectors together:
Task T016: "Create InsightGenerator class in src/briefing/insight_generator.py"
Task T017: "Implement detect_volume_patterns in src/briefing/insight_generator.py"
Task T018: "Implement detect_response_time_issues in src/briefing/insight_generator.py"
Task T019: "Implement detect_approval_bottlenecks in src/briefing/insight_generator.py"

# Then integrate:
Task T020: "Add generate_claude_insights method"
Task T024: "Integrate InsightGenerator into BriefingAggregator"
```

---

## Implementation Strategy

### Recommended Order (Sequential)

1. **US4 (Custom Date Ranges)** - Lowest complexity, immediate value
   - Tasks T008-T015 (8 tasks)
   - Enables monthly/quarterly reports

2. **US3 (Email Delivery)** - Medium complexity, high value
   - Tasks T001-T007 (7 tasks)
   - Enables automated delivery

3. **US5 (AI Insights)** - Highest complexity, high value
   - Tasks T016-T026 (11 tasks)
   - Requires Claude integration

4. **US3 Extended (Scheduling)** - Depends on US3
   - Tasks T027-T031 (5 tasks)
   - Completes automation workflow

5. **Polish (Phase 7)** - Final hardening
   - Tasks T032-T040 (9 tasks)
   - Configuration, docs, testing

### Parallel Team Strategy

With 3 developers:

1. Complete existing Bronze/Silver validation together
2. Then split:
   - Developer A: US4 (Date Ranges) → US3 Extended (Scheduling)
   - Developer B: US3 (Email Delivery) → Polish (Config, Docs)
   - Developer C: US5 (AI Insights) → Polish (Testing, Performance)
3. All features integrate via existing BriefingAggregator interface

### MVP Definition

**Current State (Bronze + Silver)** is already MVP:
- ✅ Generate weekly briefings
- ✅ Markdown and PDF output
- ✅ All core metrics included

**Next MVP (Gold)**: Add US4 (Date Ranges)
- Unlocks monthly/quarterly reporting
- Low risk, high value

**Full Gold**: US3 + US4 + US5 + US3 Extended
- Complete automation with AI insights

---

## Notes

- Bronze/Silver implementation used `fpdf2` not `wkhtmltopdf` (simpler, no system deps)
- Email delivery should use standard Python `smtplib` or integrate with existing email MCP if available
- AI insights should invoke Claude via subprocess (similar to orchestrator pattern)
- All date range logic should handle timezone-aware datetimes (UTC)
- PII anonymization MUST be applied before any external delivery (email, PDF)
- Cron job should include error handling and email notifications on failure
- Configuration file (briefing.yaml) should support environment variable substitution for secrets
- Each user story adds independent value - can deploy/demo after any story completes

---

## Test Coverage Goals

- **Unit Tests**: 80%+ coverage for new modules (email_delivery, date_range_parser, insight_generator)
- **Integration Tests**: End-to-end briefing workflow (aggregate → render → PDF → email)
- **Performance Tests**: Briefing generation <30s for 50 tasks
- **Contract Tests**: Email SMTP delivery, Claude API invocation

---

## Success Metrics

- [ ] Custom date ranges functional (--week, --month, --quarter, --from/--to)
- [ ] Email delivery operational via SMTP
- [ ] AI insights generated with 3-5 recommendations per briefing
- [ ] Scheduled generation via cron (Monday 7 AM)
- [ ] Zero manual intervention required for weekly briefings
- [ ] PII anonymization applied to all external outputs
- [ ] All tests passing (unit, integration, e2e)
- [ ] Configuration file documented and tested

---

**Total Tasks**: 40
- User Story 3 (Email): 7 tasks
- User Story 4 (Date Ranges): 8 tasks
- User Story 5 (AI Insights): 11 tasks
- User Story 3 Extended (Scheduling): 5 tasks
- Polish: 9 tasks

**Estimated Effort**:
- US4: 4-6 hours
- US3: 4-6 hours
- US5: 8-10 hours
- US3 Extended: 2-3 hours
- Polish: 4-6 hours
- **Total**: 22-31 hours (3-4 days of focused work)
