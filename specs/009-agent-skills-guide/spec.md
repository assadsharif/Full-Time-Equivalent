# Agent Skills Guide Specification (P2)

**Feature Name**: Agent Skills Development Framework
**Priority**: P2 (Bronze Tier, Foundational)
**Status**: Draft
**Created**: 2026-01-28
**Last Updated**: 2026-01-28
**Owner**: AI Employee Hackathon Team
**Stakeholders**: All Developers, Claude Code

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [What Are Agent Skills](#what-are-agent-skills)
3. [Skill Anatomy](#skill-anatomy)
4. [Creating Your First Skill](#creating-your-first-skill)
5. [Skill Lifecycle](#skill-lifecycle)
6. [Skill Categories](#skill-categories)
7. [Best Practices](#best-practices)
8. [Advanced Patterns](#advanced-patterns)
9. [Testing and Validation](#testing-and-validation)
10. [Skill Registry](#skill-registry)
11. [Constitutional Compliance](#constitutional-compliance)
12. [Examples](#examples)
13. [Appendix](#appendix)

---

## Executive Summary

### Problem Statement

The hackathon requires **"All AI functionality should be implemented as Agent Skills"**, but:

- **No clear definition** of what an "Agent Skill" is
- **No templates** or examples to follow
- **No guidelines** for skill structure, naming, or organization
- **No testing framework** for validating skills
- **Inconsistent quality** when developers create skills independently

Without a standardized approach:
- Skills are not reusable across projects
- Claude cannot discover or invoke skills reliably
- Quality and safety vary widely
- Documentation is incomplete or missing
- Skills conflict or duplicate functionality

### Proposed Solution

Create a **Agent Skills Development Framework** that defines:

1. **Standard structure** for Agent Skills (commands/skills/ directory)
2. **Skill anatomy** (metadata, instructions, examples, validation)
3. **Naming conventions** (skill-name.skill.md)
4. **Lifecycle management** (create, test, deploy, update)
5. **Quality guidelines** (constitutional compliance, security, performance)
6. **Discovery mechanism** (skill registry, Claude scans commands/)
7. **Testing framework** (skill validation, integration tests)

### Key Benefits

| Benefit | Impact |
|---------|--------|
| **Standardization** | All skills follow same structure, easy to understand |
| **Reusability** | Skills portable across projects |
| **Discoverability** | Claude can find and invoke skills automatically |
| **Quality Assurance** | Built-in validation and testing |
| **Documentation** | Self-documenting skills (metadata + examples) |
| **Safety** | Constitutional compliance checks in every skill |

### Scope

**In Scope:**
- Skill structure definition (Markdown format)
- Skill metadata standards (YAML frontmatter)
- Skill naming conventions
- Skill categories (task, query, config, diagnostic, etc.)
- Skill lifecycle (create, test, deploy)
- Skill registry (CLI: `fte skill list`)
- Skill validation (syntax, completeness, safety)
- Example skills (simple to complex)

**Out of Scope:**
- Custom skill languages (use Markdown only)
- Dynamic skill loading (runtime compilation)
- Skill marketplace (public sharing)
- Skill versioning system (use Git for now)
- Skill monetization or licensing

**Dependencies:**
- ✅ Claude Code installed
- ✅ CLI integration (P3)
- ⏳ Skill executor in Claude Code

---

## What Are Agent Skills

### Definition

An **Agent Skill** is a reusable, self-contained unit of AI functionality that:

1. **Encodes expert knowledge** (how to perform a specific task)
2. **Provides clear instructions** (for Claude Code to execute)
3. **Includes examples** (for few-shot learning)
4. **Has metadata** (for discovery and categorization)
5. **Is independently testable** (validation criteria included)

**Analogy:** Skills are like "recipes" for Claude Code. Just as a recipe tells a chef how to make a dish, a skill tells Claude how to perform a task.

### Why Skills Matter

**Without Skills:**
```
User: "Commit my code changes"
Claude: "I'll commit your changes..." [guesses what to do, inconsistent]
```

**With Skills:**
```
User: "Commit my code changes"
Claude: [Invokes /sp.git.commit_pr skill]
Claude: [Follows skill instructions: run git status, analyze changes,
         draft commit message following repo conventions, commit with
         Co-Authored-By tag, run git status to verify]
Result: Consistent, high-quality commits every time
```

### Skill vs. Function vs. Prompt

| Concept | Purpose | Format | Reusability |
|---------|---------|--------|-------------|
| **Function** | Execute code | Python, JS, etc. | Low (language-specific) |
| **Prompt** | One-time instruction | Natural language | Low (context-specific) |
| **Agent Skill** | Reusable AI workflow | Markdown | High (portable, discoverable) |

**Example:**

```markdown
# Function (Python)
def commit_changes(message: str):
    subprocess.run(['git', 'add', '.'])
    subprocess.run(['git', 'commit', '-m', message])

# Prompt (Natural Language)
"Please commit my changes with message 'Fix bug'"

# Agent Skill (Markdown)
---
name: sp.git.commit_pr
description: Commit code changes following repo conventions
triggers: [commit, git commit, commit changes]
---

[Detailed instructions for Claude, including:
 - How to analyze changes
 - How to draft commit message
 - How to follow repo conventions
 - How to verify success]
```

---

## Skill Anatomy

### Skill File Structure

Every skill is a **Markdown file** with:

1. **YAML Frontmatter** (metadata)
2. **Overview Section** (what the skill does)
3. **Instructions Section** (step-by-step guidance for Claude)
4. **Examples Section** (few-shot learning examples)
5. **Validation Section** (success criteria)

**File Location:** `commands/skills/<skill-name>.skill.md`

**Naming Convention:** `<namespace>.<category>.<action>.skill.md`

Examples:
- `sp.git.commit_pr.skill.md` - Commit and create PR
- `fte.vault.init.skill.md` - Initialize Obsidian vault
- `fte.briefing.generate.skill.md` - Generate CEO briefing

### YAML Frontmatter (Metadata)

```yaml
---
# === Skill Identity ===
name: sp.git.commit_pr
version: 1.0.0
description: |
  Commit code changes and optionally create a pull request.
  Follows repo conventions, adds Co-Authored-By tag, verifies success.

# === Invocation ===
triggers:
  - commit
  - git commit
  - commit changes
  - create pr
  - commit and pr

command: /sp.git.commit_pr
aliases: [/commit, /git-commit]

# === Categorization ===
category: git
tags: [git, version-control, commit, pr, github]

# === Dependencies ===
requires:
  tools: [git, gh]  # Required CLI tools
  skills: []        # Dependent skills
  env: [GITHUB_TOKEN]  # Required environment variables

# === Context ===
context_needed:
  - current_branch
  - git_status
  - recent_commits

# === Configuration ===
parameters:
  - name: message
    type: string
    required: false
    description: Custom commit message (optional, auto-generated if omitted)

  - name: create_pr
    type: boolean
    required: false
    default: false
    description: Whether to create a pull request after committing

# === Safety ===
safety_level: medium  # low, medium, high
approval_required: false
destructive: false  # Does this skill modify or delete data?

# === Compliance ===
constitutional_compliance:
  - section: 8  # Auditability (all git operations logged)
  - section: 9  # Error recovery (graceful handling of git failures)

# === Metadata ===
author: AI Employee Team
created: 2026-01-28
last_updated: 2026-01-28
---
```

### Overview Section

```markdown
## Overview

This skill handles committing code changes and optionally creating pull requests.
It follows repository conventions, analyzes changes to draft appropriate commit
messages, adds Co-Authored-By tags, and verifies success.

**Use this skill when:**
- You've made code changes and want to commit them
- You want commit messages that follow repo conventions
- You want to create a PR immediately after committing

**Do NOT use this skill when:**
- No changes exist (git status clean)
- You want to amend an existing commit (use /sp.git.amend instead)
- You want to commit only specific files (use /sp.git.commit_partial)
```

### Instructions Section

```markdown
## Instructions for Claude

### Prerequisites
1. Run `git status` to check for changes
2. If no changes exist, inform user and exit
3. If changes exist but are not staged, decide whether to stage them

### Step 1: Analyze Changes
1. Run `git status` to see all files changed
2. Run `git diff` to see detailed changes
3. Categorize changes:
   - New features (files added, major new functionality)
   - Bug fixes (fixing existing issues)
   - Refactoring (code improvements, no behavior change)
   - Documentation (README, comments, docs)
   - Tests (new or updated tests)
   - Other (config, dependencies, etc.)

### Step 2: Draft Commit Message
1. Run `git log --oneline -10` to see recent commit message style
2. Follow the repo's commit message convention:
   - First line: < 50 chars, imperative mood ("Add", not "Added" or "Adds")
   - Blank line
   - Body: Explain "why" not "what" (code shows "what")
   - Reference issue numbers if applicable (#123)
   - Add Co-Authored-By tag at end

3. Example commit message:
   ```
   Add CEO briefing generation feature

   Implements weekly executive summary with metrics, insights, and PDF export.
   Addresses requirement for leadership visibility into AI Employee activities.

   Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
   ```

### Step 3: Stage and Commit
1. Stage relevant files: `git add <files>`
   - If user provided specific files, stage only those
   - Otherwise, stage all modified files: `git add -u`
   - Be cautious with `git add .` (can add unwanted files)

2. Commit with message: `git commit -m "$(cat <<'EOF'\n<message>\nEOF\n)"`
   - Use heredoc for multi-line messages
   - Always include Co-Authored-By tag

3. Run `git status` to verify commit succeeded

### Step 4: Create PR (Optional)
If `create_pr` parameter is true:
1. Push branch to remote: `git push -u origin <branch>`
2. Create PR using gh CLI: `gh pr create --title "<title>" --body "<body>"`
3. Output PR URL for user

### Step 5: Verify and Report
1. Run `git log -1` to show the new commit
2. Report success to user:
   - Commit SHA
   - Commit message
   - Files changed
   - PR URL (if created)

### Error Handling
- **No changes:** Inform user, do not create empty commit
- **Staged and unstaged changes mixed:** Ask user which to include
- **Commit fails:** Show error, suggest fixes (e.g., pre-commit hook failure)
- **Push fails:** Show error, suggest fixes (e.g., remote branch diverged)
```

### Examples Section

```markdown
## Examples

### Example 1: Simple Commit

**User Input:**
```
User: "Commit my changes"
```

**Skill Execution:**
```bash
# Claude runs:
$ git status
# On branch feature/briefing
# Changes not staged for commit:
#   modified: src/briefing/generator.py
#   modified: README.md

$ git diff
# ... (shows changes)

$ git add src/briefing/generator.py README.md

$ git commit -m "$(cat <<'EOF'
Add briefing generation feature

Implements CEO briefing with metrics and PDF export.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
# [feature/briefing abc1234] Add briefing generation feature
#  2 files changed, 150 insertions(+), 5 deletions(-)

$ git status
# On branch feature/briefing
# nothing to commit, working tree clean
```

**Output:**
```
✅ Changes committed successfully

Commit: abc1234
Message: "Add briefing generation feature"
Files changed: 2 (src/briefing/generator.py, README.md)

Next steps:
- Push to remote: git push
- Create PR: /sp.git.create_pr
```

### Example 2: Commit and Create PR

**User Input:**
```
User: "Commit and create a PR"
```

**Skill Execution:**
```bash
# Claude runs:
$ git add -u
$ git commit -m "..."
$ git push -u origin feature/briefing
$ gh pr create --title "Add CEO briefing feature" --body "..."
```

**Output:**
```
✅ Changes committed and PR created

Commit: abc1234
PR: https://github.com/company/repo/pull/42

PR Title: "Add CEO briefing feature"
PR Body:
## Summary
- Implements weekly CEO briefing
- Metrics: tasks, response time, priorities
- PDF export via pandoc

## Test Plan
- [x] Generate weekly briefing
- [x] Export to PDF
- [ ] Email delivery (manual test needed)

🤖 Generated with Claude Code
```

### Example 3: Error Handling (No Changes)

**User Input:**
```
User: "Commit my changes"
```

**Skill Execution:**
```bash
$ git status
# On branch main
# nothing to commit, working tree clean
```

**Output:**
```
ℹ️ No changes to commit

Your working tree is clean. There are no uncommitted changes.

If you expected changes:
- Check if you saved your files
- Run `git status` to verify
- Use `git diff` to see if any changes exist
```
```

### Validation Section

```markdown
## Validation Criteria

### Success Criteria
- [ ] Git status checked before committing
- [ ] Commit message follows repo conventions (< 50 char first line, imperative mood)
- [ ] Co-Authored-By tag included in commit message
- [ ] Git status checked after committing (verify success)
- [ ] If PR created, PR URL returned to user
- [ ] All git operations logged (P2 logging infrastructure)

### Failure Conditions
- [ ] Empty commit attempted (no changes)
- [ ] Commit message > 72 chars in first line
- [ ] Missing Co-Authored-By tag
- [ ] Git operation failed (non-zero exit code)
- [ ] Unhandled error (exception not caught)

### Safety Checks
- [ ] No sensitive data in commit message (API keys, passwords)
- [ ] No `git commit --amend` used (unless explicitly requested)
- [ ] No `git push --force` used (unless explicitly requested)
- [ ] Pre-commit hooks executed (not skipped with --no-verify)
```

---

## Creating Your First Skill

### Step 1: Choose a Task

Pick a task that:
- Is **repeatable** (you do it multiple times)
- Has **clear steps** (can be documented)
- Requires **AI reasoning** (not just a simple script)

**Good First Skills:**
- Initialize a project structure
- Generate a report from data
- Analyze code quality
- Send a formatted email

**Avoid for First Skill:**
- Complex multi-step workflows
- Tasks requiring external APIs (OAuth, webhooks)
- Tasks with many edge cases

### Step 2: Document the Steps

Write down how you currently perform the task manually:

```
Task: Initialize Obsidian vault

Manual Steps:
1. Create directory: mkdir AI_Employee_Vault
2. Create subfolders: Inbox, Needs_Action, In_Progress, Done, etc.
3. Create Dashboard.md file
4. Create Company_Handbook.md file
5. Create .gitignore file
6. Initialize Git: git init
7. Make initial commit
8. Open in Obsidian
```

### Step 3: Create Skill File

Create `commands/skills/fte.vault.init.skill.md`:

```markdown
---
name: fte.vault.init
version: 1.0.0
description: Initialize Obsidian vault structure for AI Employee
triggers: [init vault, initialize vault, create vault]
command: /fte.vault.init
category: vault
tags: [obsidian, vault, initialization]
safety_level: low
---

## Overview
Initializes a standardized Obsidian vault structure for the AI Employee system.

## Instructions for Claude

### Step 1: Check if vault already exists
1. Check if target directory exists
2. If exists and contains files, warn user and exit
3. If empty, proceed

### Step 2: Create folder structure
Run the following commands:
```bash
mkdir -p AI_Employee_Vault/{Inbox,Needs_Action,In_Progress,Done,Approvals,Briefings,Attachments,Templates}
```

### Step 3: Create Dashboard.md
Create file with template content (see templates/)

### Step 4: Create Company_Handbook.md
Create file with template content (see templates/)

### Step 5: Initialize Git
```bash
cd AI_Employee_Vault
git init
echo ".obsidian/workspace.json" > .gitignore
git add .
git commit -m "Initial commit: Initialize AI Employee vault"
```

### Step 6: Verify and report
List created folders and files, inform user of success.

## Examples
[See example executions above]

## Validation
- [ ] All 8 folders created
- [ ] Dashboard.md exists and is valid Markdown
- [ ] Company_Handbook.md exists
- [ ] Git repository initialized
- [ ] .gitignore configured
```

### Step 4: Test the Skill

```bash
# Test skill invocation
fte skill test fte.vault.init

# Or manually test with Claude
claude code --skill /fte.vault.init
```

### Step 5: Deploy the Skill

```bash
# Add to Git
git add commands/skills/fte.vault.init.skill.md
git commit -m "Add vault initialization skill"

# Skill is now discoverable by Claude
fte skill list
# Output: fte.vault.init - Initialize Obsidian vault structure
```

---

## Skill Lifecycle

### 1. Create

```bash
# Generate skill scaffold
fte skill create fte.vault.init --category vault

# This creates:
# commands/skills/fte.vault.init.skill.md (with template)
```

### 2. Edit

```bash
# Open skill in editor
fte skill edit fte.vault.init

# Or manually edit
vim commands/skills/fte.vault.init.skill.md
```

### 3. Validate

```bash
# Validate skill syntax and completeness
fte skill validate fte.vault.init

# Output:
# ✅ Skill valid: fte.vault.init
#    - Metadata complete
#    - Instructions clear
#    - Examples provided
#    - Validation criteria defined
```

### 4. Test

```bash
# Test skill in dry-run mode
fte skill test fte.vault.init --dry-run

# Test skill with real execution
fte skill test fte.vault.init

# Run integration tests
pytest tests/skills/test_vault_init.py
```

### 5. Deploy

```bash
# Commit skill to Git
git add commands/skills/fte.vault.init.skill.md
git commit -m "Add vault initialization skill"

# Skill is now available in CLI
fte skill list
```

### 6. Update

```bash
# Edit skill
fte skill edit fte.vault.init

# Update version in YAML frontmatter
version: 1.1.0

# Commit changes
git add commands/skills/fte.vault.init.skill.md
git commit -m "Update vault init skill: add error handling"
```

### 7. Deprecate/Remove

```bash
# Mark skill as deprecated
fte skill deprecate fte.vault.init --reason "Replaced by fte.vault.init.v2"

# Remove skill
fte skill remove fte.vault.init
```

---

## Skill Categories

### Task Skills

Execute specific tasks (e.g., commit code, generate report)

**Examples:**
- `sp.git.commit_pr` - Commit and create PR
- `fte.briefing.generate` - Generate CEO briefing
- `fte.vault.init` - Initialize vault

### Query Skills

Retrieve information (e.g., search code, find files)

**Examples:**
- `fte.vault.search` - Search vault for tasks
- `sp.git.find_commit` - Find commit by message
- `fte.logs.query` - Query P2 logging infrastructure

### Config Skills

Manage configuration (e.g., set thresholds, update settings)

**Examples:**
- `fte.config.set` - Set configuration value
- `fte.config.show` - Show current configuration
- `fte.approval.threshold` - Update approval thresholds

### Diagnostic Skills

Diagnose issues (e.g., check health, analyze errors)

**Examples:**
- `fte.health.check` - Check system health
- `fte.watcher.diagnose` - Diagnose watcher issues
- `fte.logs.analyze_errors` - Analyze error patterns

### Workflow Skills

Multi-step workflows (e.g., plan → tasks → implement)

**Examples:**
- `sp.plan` - Execute planning workflow
- `sp.tasks` - Generate task breakdown
- `sp.implement` - Execute implementation tasks

---

## Best Practices

### DO: Write Clear Instructions

**Good:**
```markdown
## Instructions
1. Run `git status` to check for uncommitted changes
2. If changes exist, stage them with `git add -u`
3. Draft commit message following repo conventions
4. Commit with Co-Authored-By tag
5. Verify success with `git log -1`
```

**Bad:**
```markdown
## Instructions
Commit the changes.
```

### DO: Provide Examples

**Good:**
```markdown
## Examples

### Example 1: Simple commit
User: "Commit my changes"
[Shows full execution flow]

### Example 2: Commit with custom message
User: "Commit with message 'Fix bug #123'"
[Shows custom message handling]

### Example 3: Error handling
User: "Commit my changes" (but no changes exist)
[Shows graceful error handling]
```

**Bad:**
```markdown
## Examples
See usage above.
```

### DO: Include Validation Criteria

**Good:**
```markdown
## Validation
- [ ] Git status checked before and after
- [ ] Commit message < 50 chars (first line)
- [ ] Co-Authored-By tag present
- [ ] No sensitive data in commit message
- [ ] All errors caught and reported
```

**Bad:**
```markdown
## Validation
Should work correctly.
```

### DO: Handle Errors Gracefully

**Good:**
```markdown
### Error Handling
- **No changes:** Inform user "No changes to commit"
- **Commit fails:** Show git error, suggest fixes
- **Push fails:** Show error, explain likely causes
```

**Bad:**
```markdown
### Error Handling
If error, show error.
```

### DON'T: Make Skills Too Generic

**Bad:**
```markdown
name: do_task
description: Do any task the user asks
```

This is too broad. Skills should be specific and focused.

### DON'T: Hardcode Values

**Bad:**
```markdown
## Instructions
1. Commit with message "Updated code"
```

**Good:**
```markdown
## Instructions
1. Analyze changes and draft appropriate commit message
2. Follow repo conventions (see git log for examples)
```

### DON'T: Skip Safety Checks

**Bad:**
```markdown
## Instructions
1. Delete all files in /tmp
```

**Good:**
```markdown
## Instructions
1. Check if /tmp contains important files
2. Ask user for confirmation before deletion
3. Delete with safety checks (avoid /* wildcards)
4. Log all deletions for audit trail
```

---

## Advanced Patterns

### Pattern 1: Skill Composition

Skills can invoke other skills:

```markdown
---
name: sp.full_workflow
description: Execute complete feature workflow (spec → plan → tasks → implement)
requires:
  skills: [sp.specify, sp.plan, sp.tasks, sp.implement]
---

## Instructions
1. Invoke /sp.specify to create feature spec
2. Wait for user approval of spec
3. Invoke /sp.plan to generate implementation plan
4. Wait for user approval of plan
5. Invoke /sp.tasks to generate task breakdown
6. Invoke /sp.implement to execute tasks
7. Report completion
```

### Pattern 2: Parameterized Skills

Skills can accept parameters:

```markdown
---
name: fte.briefing.generate
parameters:
  - name: period
    type: string
    default: week
    options: [week, month, quarter]

  - name: format
    type: string
    default: markdown
    options: [markdown, pdf]

  - name: email
    type: string
    required: false
---

## Instructions
1. Parse parameters (period, format, email)
2. Aggregate data for specified period
3. Generate briefing in specified format
4. If email provided, send briefing via SMTP
```

### Pattern 3: Conditional Execution

Skills can branch based on conditions:

```markdown
## Instructions

### Step 1: Check if approval required
1. Analyze action risk level
2. Check approval thresholds in Company_Handbook.md

### Step 2: Branch based on approval requirement
**If approval required:**
- Generate approval request in /Approvals
- Wait for human approval
- Proceed only if approved

**If approval not required:**
- Execute action immediately
- Log action for audit trail
```

### Pattern 4: Error Recovery

Skills can retry and recover:

```markdown
## Instructions

### Step 3: Execute with retry logic
1. Attempt API call
2. If fails with network error:
   - Wait 1 second
   - Retry (max 3 attempts)
   - If all retries fail, escalate to human

3. If fails with authentication error:
   - Do NOT retry (permanent error)
   - Alert user to check credentials
```

---

## Testing and Validation

### Validation Levels

#### Level 1: Syntax Validation

```bash
# Check YAML frontmatter valid
fte skill validate fte.vault.init --level syntax

# Checks:
# - YAML parses correctly
# - Required fields present (name, description, category)
# - No duplicate skill names
```

#### Level 2: Completeness Validation

```bash
# Check skill has all required sections
fte skill validate fte.vault.init --level complete

# Checks:
# - Overview section exists
# - Instructions section exists
# - Examples section exists (at least 2 examples)
# - Validation section exists
```

#### Level 3: Quality Validation

```bash
# Check skill meets quality standards
fte skill validate fte.vault.init --level quality

# Checks:
# - Instructions are clear (> 10 steps)
# - Examples include user input and output
# - Error handling documented
# - Safety checks included
```

#### Level 4: Integration Testing

```bash
# Execute skill in test environment
fte skill test fte.vault.init

# Runs skill and checks:
# - Skill executes without errors
# - Expected outputs generated
# - Validation criteria met
```

### Test Framework

```python
# tests/skills/test_vault_init.py

import pytest
from src.skills import SkillRunner

def test_vault_init_creates_folders():
    """Test that vault init skill creates all required folders."""
    runner = SkillRunner()

    result = runner.run_skill(
        skill_name="fte.vault.init",
        parameters={"path": "/tmp/test_vault"}
    )

    assert result.success
    assert result.vault_path.exists()
    assert (result.vault_path / "Inbox").exists()
    assert (result.vault_path / "Needs_Action").exists()
    assert (result.vault_path / "Done").exists()

def test_vault_init_fails_if_exists():
    """Test that vault init fails gracefully if vault already exists."""
    runner = SkillRunner()

    # Create vault
    result1 = runner.run_skill(
        skill_name="fte.vault.init",
        parameters={"path": "/tmp/test_vault"}
    )
    assert result1.success

    # Try to create again
    result2 = runner.run_skill(
        skill_name="fte.vault.init",
        parameters={"path": "/tmp/test_vault"}
    )
    assert not result2.success
    assert "already exists" in result2.error_message
```

---

## Skill Registry

### Discovery

Claude Code automatically discovers skills by scanning:
- `commands/skills/` directory
- `.specify/commands/` directory (if exists)
- Project-specific `commands/` directory

### CLI Commands

```bash
# List all available skills
fte skill list

# Output:
# Available Skills (15):
#
# Git Skills:
#   /sp.git.commit_pr    - Commit and create PR
#   /sp.git.create_pr    - Create pull request
#
# Vault Skills:
#   /fte.vault.init      - Initialize Obsidian vault
#   /fte.vault.search    - Search vault for tasks
#
# Briefing Skills:
#   /fte.briefing.generate - Generate CEO briefing

# Show skill details
fte skill show fte.vault.init

# Output:
# Skill: fte.vault.init
# Version: 1.0.0
# Description: Initialize Obsidian vault structure
# Category: vault
# Safety Level: low
#
# Triggers: [init vault, initialize vault, create vault]
# Command: /fte.vault.init
#
# Parameters: None
#
# Requires:
#   - Tools: [mkdir, git]
#   - Environment: []
#
# Examples: 3
# Validation Criteria: 5

# Search skills by tag
fte skill search --tag git

# Output:
# Skills tagged 'git' (3):
#   /sp.git.commit_pr
#   /sp.git.create_pr
#   /sp.git.find_commit
```

---

## Constitutional Compliance

### Compliance Checklist

Every skill MUST verify constitutional compliance:

```yaml
---
constitutional_compliance:
  - section: 2  # Source of Truth (reads from vault)
  - section: 4  # Frozen Control Plane (no modifications to src/control_plane/)
  - section: 5  # HITL for dangerous actions
  - section: 8  # Auditability (all actions logged)
  - section: 9  # Error recovery (graceful degradation)
---
```

### Safety Levels

| Level | Description | Approval Required | Examples |
|-------|-------------|-------------------|----------|
| **Low** | Read-only, no side effects | No | Search, query, analyze |
| **Medium** | Writes data, non-destructive | No | Create files, update config |
| **High** | Destructive or risky | Yes | Delete files, send email, payment |

### Dangerous Action Detection

Skills that perform dangerous actions MUST:

1. **Declare safety level:**
   ```yaml
   safety_level: high
   approval_required: true
   destructive: true
   ```

2. **Check approval before execution:**
   ```markdown
   ## Instructions
   ### Step 1: Check approval
   1. Look for approval file in /Approvals/<task-id>.yaml
   2. Verify approval_status = approved
   3. If not approved, STOP and wait for human

   ### Step 2: Execute (only if approved)
   [Proceed with action]
   ```

3. **Log all actions:**
   ```markdown
   ### Step 3: Log action
   1. Log via P2 logging infrastructure
   2. Include: action type, parameters, outcome
   3. Store audit trail in /Done folder
   ```

---

## Examples

### Example 1: Simple Task Skill

```markdown
---
name: fte.vault.status
version: 1.0.0
description: Show vault status (task counts, system health)
triggers: [vault status, check vault, vault info]
command: /fte.vault.status
category: vault
safety_level: low
---

## Overview
Displays a summary of the vault: task counts in each folder, recent activity, system health.

## Instructions for Claude

### Step 1: Count tasks in each folder
```bash
ls -1 Inbox | wc -l
ls -1 Needs_Action | wc -l
ls -1 In_Progress | wc -l
ls -1 Done | wc -l
```

### Step 2: Get recent activity
```bash
ls -lt Done | head -5
```

### Step 3: Format and display
Output:
```
📊 Vault Status

Tasks:
  📥 Inbox: 3
  ⚡ Needs_Action: 5
  🔄 In_Progress: 2
  ✅ Done (total): 247

Recent Activity:
  - gmail_client_2026-01-28T10-15-00 (completed 5m ago)
  - whatsapp_1234_2026-01-28T10-00-00 (completed 20m ago)
  ...
```

## Examples
[User input and expected output]

## Validation
- [ ] Task counts accurate
- [ ] Recent activity shows last 5 tasks
- [ ] Output formatted clearly
```

### Example 2: Workflow Skill (Multi-Step)

```markdown
---
name: sp.plan
version: 1.0.0
description: Execute implementation planning workflow
requires:
  skills: []
  tools: [git]
  files: [spec.md]
---

## Overview
Generates an implementation plan from a feature specification.

## Instructions for Claude

### Phase 0: Setup
1. Run `.specify/scripts/bash/setup-plan.sh --json`
2. Parse JSON output (FEATURE_SPEC, IMPL_PLAN, SPECS_DIR, BRANCH)

### Phase 1: Load Context
1. Read FEATURE_SPEC file
2. Read `.specify/memory/constitution.md`
3. Load IMPL_PLAN template

### Phase 2: Fill Technical Context
1. Extract technologies from spec
2. Identify dependencies
3. Mark unknowns as "NEEDS CLARIFICATION"

### Phase 3: Constitution Check
1. For each constitutional section, verify compliance
2. Flag violations (ERROR if unjustified)

### Phase 4: Research (if needed)
1. For each "NEEDS CLARIFICATION", create research task
2. Generate research.md with findings

### Phase 5: Design Artifacts
1. Generate data-model.md
2. Generate API contracts in /contracts/
3. Generate quickstart.md

### Step 6: Report
Output plan path and summary

## Examples
[See sp.plan execution examples]

## Validation
- [ ] plan.md generated
- [ ] All NEEDS CLARIFICATION resolved
- [ ] Constitution check passed
- [ ] Design artifacts created
```

### Example 3: Parameterized Skill

```markdown
---
name: fte.briefing.generate
version: 1.0.0
description: Generate CEO briefing for specified period
parameters:
  - name: period
    type: string
    default: week
    options: [week, month, quarter]
  - name: format
    type: string
    default: markdown
    options: [markdown, pdf]
---

## Instructions

### Step 1: Parse parameters
1. Get period parameter (default: week)
2. Get format parameter (default: markdown)
3. Calculate date range based on period

### Step 2: Aggregate data
1. Scan /Done folder for tasks in date range
2. Parse YAML frontmatter from each task
3. Calculate metrics

### Step 3: Generate briefing
1. Render Markdown using Jinja2 template
2. If format=pdf, convert to PDF

### Step 4: Report
Output briefing file path

## Examples

### Example 1: Weekly briefing (default)
```
User: /fte.briefing.generate
Output: /Briefings/2026-01-29_Weekly_Briefing.md
```

### Example 2: Monthly PDF briefing
```
User: /fte.briefing.generate --period month --format pdf
Output: /Briefings/2026-01-31_Monthly_Briefing.pdf
```
```

---

## Appendix

### A1: Skill Template

```markdown
---
name: <namespace>.<category>.<action>
version: 1.0.0
description: |
  Brief description of what the skill does.
  One or two sentences max.

triggers:
  - trigger phrase 1
  - trigger phrase 2

command: /<skill-name>
category: <category>
tags: [tag1, tag2, tag3]

requires:
  tools: []
  skills: []
  env: []

parameters: []

safety_level: low  # low, medium, high
approval_required: false
destructive: false

constitutional_compliance:
  - section: 2
  - section: 8

author: Your Name
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
---

## Overview

What does this skill do? When should it be used?

## Instructions for Claude

### Step 1: [First step]
Detailed instructions...

### Step 2: [Second step]
Detailed instructions...

### Error Handling
- **Error type 1:** How to handle
- **Error type 2:** How to handle

## Examples

### Example 1: [Title]
**User Input:**
```
User: "..."
```

**Skill Execution:**
```bash
# Commands executed
```

**Output:**
```
[Expected output]
```

### Example 2: [Title]
[Another example]

## Validation Criteria

### Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2

### Safety Checks
- [ ] Check 1
- [ ] Check 2
```

### A2: CLI Commands Reference

```bash
# Create new skill
fte skill create <name> --category <category>

# Edit skill
fte skill edit <name>

# Validate skill
fte skill validate <name>

# Test skill
fte skill test <name>

# List all skills
fte skill list

# Search skills
fte skill search --tag <tag>
fte skill search --category <category>

# Show skill details
fte skill show <name>

# Deprecate skill
fte skill deprecate <name> --reason "<reason>"

# Remove skill
fte skill remove <name>

# Export skill (for sharing)
fte skill export <name> --output <file.md>

# Import skill
fte skill import <file.md>
```

---

## Change Log

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-01-28 | v1.0 | AI Employee Team | Initial specification |

---

**Next Steps:**
1. Create your first skill using the template
2. Validate skill with `fte skill validate`
3. Test skill with `fte skill test`
4. Deploy skill to `commands/skills/` directory
5. Use skill with Claude Code: `/your-skill-name`

---

*This specification is part of the Personal AI Employee Hackathon 0 project. All AI functionality should be implemented as Agent Skills following this guide.*
