---
name: github-mcp
description: GitHub operations using the GitHub MCP server. Use when Claude needs to interact with GitHub including managing repositories, issues, pull requests, branches, or workflows. Triggers on requests involving GitHub operations, issue tracking, PR management, repository operations, or GitHub Actions workflows.
---

# GitHub MCP

GitHub operations using the @modelcontextprotocol/server-github MCP server.

## Overview

Interact with GitHub API for repository management, issue tracking, pull requests, and workflow automation. Requires authentication token for full access.

## Core Capabilities

### 1. Repository Operations
```
"List my GitHub repositories"
"Create a new repository called my-project"
"Get details for this repository"
```
→ Use `list_repositories`, `create_repository`, `get_repository`

### 2. Issue Management
```
"Create an issue for the authentication bug"
"List all open issues"
"Close issue #42"
```
→ Use `create_issue`, `list_issues`, `update_issue`, `close_issue`

### 3. Pull Request Workflows
```
"Create a PR from feature/auth to main"
"List all open pull requests"
"Merge PR #15"
```
→ Use `create_pull_request`, `list_pull_requests`, `merge_pull_request`

### 4. Branch Operations
```
"Create a new branch called feature/payments"
"List all branches"
"Delete branch feature/old"
```
→ Use `create_branch`, `list_branches`, `delete_branch`

### 5. File Operations
```
"Get README.md from the main branch"
"Update package.json in the repository"
```
→ Use `get_file_contents`, `create_or_update_file`

### 6. Workflow Management
```
"List all GitHub Actions workflows"
"Trigger the deployment workflow"
"Get status of latest workflow run"
```
→ Use `list_workflows`, `trigger_workflow`, `get_workflow_run`

## Workflow Decision Tree

```
GitHub operation request
│
├─ Repository? → create/list/get repository
├─ Issue? → create/list/update/close issue
├─ Pull Request? → create/list/merge PR
├─ Branch? → create/list/delete branch
├─ File? → get/create/update/delete file
└─ Workflow? → list/trigger/get status
```

## Common Patterns

### Pattern 1: Issue-Driven Development
```
1. Create feature spec
2. Convert tasks to issues → create_issue for each task
3. Track progress via GitHub issues
4. Close issues as tasks complete
```

### Pattern 2: PR Workflow
```
1. Create feature branch → create_branch
2. Implement changes (local)
3. Push to remote (git)
4. Create PR → create_pull_request
5. Merge when ready → merge_pull_request
```

### Pattern 3: Repository Setup
```
1. Create repository → create_repository
2. Initialize with README → create_or_update_file
3. Set up branches → create_branch (develop, staging)
4. Configure workflows (GitHub Actions)
```

### Pattern 4: Convert Tasks to Issues
```
1. Read tasks.md
2. Parse task list
3. For each task:
   - create_issue with task details
   - Link to spec/ADR if applicable
   - Add labels (bug, enhancement, etc.)
```

## Integration with Spec-Driven Development

**Create issues from tasks:**
```
Read specs/authentication/tasks.md
→ Create GitHub issues for each task
→ Link issues to spec
```

**Link PRs to specs:**
```
Create PR with description:
  "Implements authentication spec (specs/authentication/spec.md)"
```

**Track ADR implementation:**
```
Create issue: "Implement ADR-001: Database choice"
→ Link to ADR document
→ Track implementation progress
```

## Authentication

**Required:** GitHub Personal Access Token

**Scopes needed:**
- `repo` - Full repository access
- `workflow` - Update GitHub Actions
- `read:org` - Read organization data

**Already configured for this project**

## Best Practices

### ✅ DO
- Write clear issue titles and descriptions
- Link issues to specs and ADRs
- Use labels for organization
- Reference issues in commit messages (#123)
- Review PRs before merging
- Use branch protection on main

### ❌ DON'T
- Create issues without context
- Merge PRs without review
- Delete main/master branch
- Force push to main
- Skip issue descriptions
- Create duplicate issues

## Common Workflows

### Workflow 1: Feature Development
```
1. Create issue for feature
2. Create feature branch
3. Implement feature (local dev)
4. Push commits
5. Create PR linking to issue
6. Review and merge
7. Close issue
```

### Workflow 2: Bug Tracking
```
1. Create issue with "bug" label
2. Describe steps to reproduce
3. Assign to developer
4. Create fix branch
5. Implement fix
6. Create PR with "fixes #<issue>"
7. Merge and auto-close issue
```

### Workflow 3: Release Management
```
1. List merged PRs since last release
2. Generate changelog
3. Create release branch
4. Create GitHub release
5. Tag version
```

## Reference

For detailed documentation:
- [GitHub MCP README](../../mcp/github/README.md)
- [MCP Installation Summary](../../mcp/INSTALLATION_SUMMARY.md)
- [GitHub API Docs](https://docs.github.com/rest)
