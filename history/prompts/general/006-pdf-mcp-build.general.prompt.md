---
id: 006
title: PDF MCP Server Build
stage: general
date: 2026-02-03
surface: agent
model: claude-opus-4-5-20251101
feature: none
branch: master
user: asad
command: build the next mcp server
labels: ["mcp", "pdf", "fastmcp", "pydantic", "pypdf", "reportlab"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - src/mcp_servers/pdf_mcp.py
  - .mcp.json
tests:
  - Verification via Python importlib (10 tools loaded)
---

## Prompt

build the next mcp server

## Response snapshot

Built `pdf_mcp.py` with 10 tools for comprehensive PDF manipulation:

1. `pdf_generate_extraction_code` - Generate text/table extraction code (pypdf, pdfplumber, pypdfium2)
2. `pdf_generate_creation_code` - Generate PDF creation code (basic, report, invoice, multi_page)
3. `pdf_generate_merge_split_code` - Generate merge/split/extract operations code
4. `pdf_generate_manipulation_code` - Generate page manipulation code (rotate, crop, watermark, resize)
5. `pdf_generate_metadata_code` - Generate metadata get/set code
6. `pdf_generate_form_code` - Generate form handling code (fillable, non_fillable, detect_fields)
7. `pdf_generate_encryption_code` - Generate password protection/decryption code
8. `pdf_generate_ocr_code` - Generate OCR code for scanned PDFs (with optional preprocessing)
9. `pdf_detect_antipatterns` - Detect anti-patterns in PDF processing code
10. `pdf_generate_scaffold` - Generate complete PDF processing project scaffold

Key features:
- Supports multiple libraries: pypdf, pdfplumber, pypdfium2, reportlab
- Code templates for common operations
- Anti-pattern detection for 8 common PDF code issues
- Project scaffold with CLI support

## Outcome

- Impact: Added PDF MCP server enabling AI-assisted PDF manipulation and code generation
- Tests: Verification passed (10 tools loaded)
- Files: 2 files created/modified
- Next prompts: Build remaining MCP servers (pptx, frontend-design, etc.)
- Reflection: Comprehensive coverage of PDF operations from skill documentation

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): Import verification PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A
