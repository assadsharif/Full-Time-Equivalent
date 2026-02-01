# Implementation Plan: Obsidian Vault Structure

**Branch**: `008-obsidian-vault-structure` | **Date**: 2026-01-28 | **Spec**: [specs/008-obsidian-vault-structure/spec.md](./spec.md)

## Summary

Define and implement the standard Obsidian vault folder structure, file naming conventions, YAML frontmatter schemas, and core template files (Dashboard.md, Company_Handbook.md) that serve as the memory layer for the AI Employee system.

**Key Approach**: File-based specification with initialization scripts, validation tools, and template files. No code implementation - purely structural and documentation.

## Technical Context

**Language/Version**: Markdown, YAML
**Primary Dependencies**: None (static files)
**Storage**: Obsidian vault (file system)
**Testing**: Schema validation scripts (Python)
**Target Platform**: Cross-platform (Markdown files)
**Project Type**: Documentation + structure
**Performance Goals**: N/A (static files)
**Constraints**: Follow Obsidian conventions, human-readable, Git-friendly
**Scale/Scope**: 7 core folders, 20+ template files

## Constitution Check

✅ **Section 2 (Source of Truth)**: Vault IS the source of truth
✅ **Section 4 (File-Driven Control Plane)**: Folder structure defines workflow
✅ **All sections**: Vault structure is foundation for all constitutional compliance

## Project Structure

```text
AI_Employee_Vault/
├── Inbox/              # New tasks from watchers
├── Needs_Action/       # Tasks ready for processing
├── In_Progress/        # Tasks being worked on
├── Done/               # Completed tasks (audit trail)
├── Approvals/          # Pending human approvals
├── Briefings/          # Weekly CEO briefings
├── Attachments/        # Files, images, documents
├── Templates/          # Task templates
├── Dashboard.md        # Human control center
└── Company_Handbook.md # AI context and policies

.vault_schema/
├── frontmatter_schemas/
│   ├── task.yaml
│   ├── approval.yaml
│   └── briefing.yaml
└── validation_scripts/
    └── validate_vault.py
```

## Implementation Roadmap

### Phase 1: Core Structure Definition
- Define folder hierarchy
- Create YAML frontmatter schemas
- Write Dashboard.md template
- Write Company_Handbook.md template

### Phase 2: Initialization Scripts
- Create `init_vault.py` script
- Add validation scripts
- Template file generators
- CLI integration (`fte vault init`)

### Phase 3: Documentation
- Vault structure guide
- File naming conventions
- Frontmatter field definitions
- State flow diagrams

## Success Metrics

- [ ] All 7 core folders defined
- [ ] YAML schemas validate correctly
- [ ] Dashboard.md provides complete visibility
- [ ] Company_Handbook.md includes all AI context

---

**Next Steps**: Run `/sp.tasks` to generate actionable task breakdown.
