---
id: 007
title: PPTX MCP Server Build
stage: general
date: 2026-02-03
surface: agent
model: claude-opus-4-5-20251101
feature: none
branch: master
user: asad
command: build the next mcp server
labels: ["mcp", "pptx", "powerpoint", "fastmcp", "pydantic", "html2pptx", "ooxml"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - src/mcp_servers/pptx_mcp.py
  - .mcp.json
tests:
  - Verification via Python importlib (10 tools loaded)
---

## Prompt

build the next mcp server

## Response snapshot

Built `pptx_mcp.py` with 10 tools for PowerPoint presentation manipulation:

1. `pptx_generate_extraction_code` - Generate text/XML/metadata extraction code
2. `pptx_generate_creation_code` - Generate presentation creation code (basic, html2pptx, pptxgenjs)
3. `pptx_generate_slide_html` - Generate HTML for slide content with layouts and palettes
4. `pptx_generate_template_code` - Generate template-based workflow code
5. `pptx_generate_edit_code` - Generate OOXML editing code for text/shapes/notes
6. `pptx_generate_color_palette` - Generate color palette recommendations (18 palettes)
7. `pptx_generate_layout` - Generate layout configurations (6 layout types)
8. `pptx_generate_thumbnail_code` - Generate thumbnail/validation code
9. `pptx_detect_antipatterns` - Detect anti-patterns in PPTX/HTML code
10. `pptx_generate_scaffold` - Generate complete PPTX project scaffold

Key features:
- Supports 3 workflows: html2pptx, template-based, OOXML direct editing
- 18 built-in color palettes with mood matching
- 6 slide layout types (title, content, two_column, image_text, quote, section)
- Web-safe font recommendations
- Anti-pattern detection for 7 common issues

## Outcome

- Impact: Added PPTX MCP server enabling AI-assisted PowerPoint creation and editing
- Tests: Verification passed (10 tools loaded)
- Files: 2 files created/modified
- Next prompts: Build remaining MCP servers (frontend-design, vercel, etc.)
- Reflection: Comprehensive coverage from skill documentation including html2pptx and OOXML workflows

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): Import verification PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
