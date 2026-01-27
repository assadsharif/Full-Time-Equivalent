---
name: git-mcp
description: Git repository operations using the Git MCP server. Use when Claude needs to perform version control operations including viewing status, diffs, commit history, creating commits, managing branches, or analyzing repository changes. Triggers on requests involving git operations, version control, commit history, branch management, or repository analysis within the project.
---

# Git MCP

Git repository operations using the @modelcontextprotocol/server-git MCP server.

## Overview

Perform git operations within the project repository. All operations are scoped to the configured repository path for security.

## Core Capabilities

### 1. Repository Status
```
"Show git status"
"What files have I modified?"
```
→ Use `git_status` to see working tree status

### 2. View Changes
```
"Show me the diff for my changes"
"What changed in the last commit?"
```
→ Use `git_diff` for changes between commits/working tree

### 3. Commit History
```
"Show the last 10 commits"
"When was this file last changed?"
```
→ Use `git_log` for commit history

### 4. Branch Management
```
"List all branches"
"Create a new branch called feature/auth"
```
→ Use `git_branch` and `git_checkout` for branch operations

### 5. Code Analysis
```
"Who last modified this line?"
"Show blame for authentication.py"
```
→ Use `git_blame` to see authorship

## Workflow Decision Tree

```
Git operation request
│
├─ Check status? → git_status
├─ View changes? → git_diff
├─ See history? → git_log
├─ Branch operation? → git_branch / git_checkout
├─ Commit changes? → git_add → git_commit
└─ Blame/authorship? → git_blame
```

## Common Patterns

### Pattern 1: Review Changes Before Commit
```
1. Check status → git_status
2. View diffs → git_diff
3. Review changes
4. Stage files → git_add
5. Create commit → git_commit
```

### Pattern 2: Analyze Feature History
```
1. View commits → git_log --grep="feature"
2. Show specific commit → git_show <hash>
3. Analyze changes → git_diff <hash>^..<hash>
```

### Pattern 3: Track File Changes
```
1. View file history → git_log -- <file>
2. Show blame → git_blame <file>
3. Analyze specific change → git_show <hash>:<file>
```

## Integration with Spec-Driven Development

**Track spec changes:**
```
git_log -- specs/authentication/spec.md
```

**Link commits to features:**
```
git_log --grep="auth"
```

**Analyze implementation:**
```
git_diff main..feature/auth
```

## Best Practices

### ✅ DO
- Check status before commits
- Review diffs before staging
- Write clear commit messages
- Use feature branches
- Track file history for context

### ❌ DON'T
- Commit without reviewing changes
- Use git commands that modify history (rebase, reset --hard) without caution
- Skip commit messages
- Work directly on main branch for features

## Reference

For detailed documentation:
- [Git MCP README](../../mcp/git/README.md)
- [MCP Installation Summary](../../mcp/INSTALLATION_SUMMARY.md)
