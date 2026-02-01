# Security

## Secret Scanning with detect-secrets

This project uses [detect-secrets](https://github.com/Yelp/detect-secrets) to prevent secrets from being committed to the repository.

### Initial Scan Results

**Total files scanned:** 14 files with potential secrets detected

**Summary:**
- Most findings are in documentation/example files (`.claude/`, skill references, `.env.example`)
- These are intentional example credentials and passwords used for documentation
- No actual secrets were found in production code

**Files with findings:**
- `.claude/agents/`: Example passwords in agent documentation
- `.claude/skills/`: Example credentials in skill references
- `.env.example` and `.env.local.example`: Template environment files (not actual secrets)

### Automated CI Scanning

The GitHub Actions workflow (`.github/workflows/detect-secrets.yml`) runs on:
- Every push to `master`, `main`, or `develop` branches
- Every pull request to these branches
- Manual workflow dispatch

**What it does:**
1. Scans the entire codebase for secrets
2. Compares against the baseline (`.secrets.baseline`)
3. Fails the build if new secrets are detected
4. For PRs: Scans only changed files
5. Uploads scan results as artifacts

### Local Development

#### Setup

```bash
# Install detect-secrets in virtual environment
pip install detect-secrets==1.5.0

# Or use the project's venv
.venv/bin/pip install detect-secrets
```

#### Scanning Before Commit

```bash
# Scan all files
detect-secrets scan

# Scan specific files
detect-secrets scan src/new_module.py

# Scan and update baseline
detect-secrets scan > .secrets.baseline

# Scan only changed files (useful for pre-commit)
git diff --name-only --cached | xargs detect-secrets scan
```

#### Reviewing Findings

```bash
# Interactive audit of baseline
detect-secrets audit .secrets.baseline

# Generate report
detect-secrets audit .secrets.baseline --report

# Get JSON report for analysis
detect-secrets audit .secrets.baseline --report --json
```

**During interactive audit:**
- `y` - Mark as real secret (will fail CI)
- `n` - Mark as false positive (will be ignored)
- `s` - Skip (leave unverified)
- `q` - Quit

#### Excluding False Positives

**In code (inline pragma):**
```python
password = "example123"  # pragma: allowlist secret
```

**In baseline (during audit):**
- Mark finding as `false_positive` during interactive audit
- Or edit `.secrets.baseline` and set `"is_verified": false`

**Exclude files/patterns (in CI workflow):**
```bash
detect-secrets scan --exclude-files '\.env\.example$' --exclude-files 'test_.*\.py$'
```

### Pre-commit Hook (Optional)

To automatically scan before every commit:

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
        exclude: \.env\.example$
EOF

# Install the hook
pre-commit install
```

### Common Patterns Detected

The following patterns are automatically detected:

1. **API Keys & Tokens**
   - AWS keys (AKIA...)
   - GitHub tokens (ghp_...)
   - OpenAI keys (sk-...)
   - Stripe keys (sk_live_...)

2. **Authentication**
   - Basic auth (user:password@host)
   - JWT tokens
   - Private keys (RSA, SSH)

3. **High Entropy Strings**
   - Base64 encoded secrets
   - Hex encoded secrets

4. **Service-Specific**
   - Discord bot tokens
   - Slack tokens
   - Telegram bot tokens
   - SendGrid keys
   - Mailchimp keys

### Best Practices

1. **Never commit real secrets** - Use environment variables or secret management services
2. **Use `.env.example`** - Provide templates with placeholder values
3. **Review baseline regularly** - Audit findings periodically
4. **Mark false positives** - Help improve accuracy
5. **Scan before pushing** - Catch secrets before they reach GitHub

### Constitutional Compliance

This secret scanning aligns with **Section 3 (Security and Privacy)**:
- Secrets detection prevents credential leakage
- Automated CI scanning ensures continuous compliance
- Local-first approach: secrets never leave the development machine

### Troubleshooting

#### CI fails with "New secrets detected"

1. Run local audit: `detect-secrets audit .secrets.baseline`
2. Review each finding and mark as real or false positive
3. If real secret: Remove it and update baseline
4. If false positive: Mark as such in audit, commit updated baseline

#### Too many false positives

1. Add inline pragmas: `# pragma: allowlist secret`
2. Exclude files: Update `.secrets.baseline` with exclude patterns
3. Adjust entropy limits: Use `--base64-limit` and `--hex-limit` flags

#### Baseline out of sync

```bash
# Regenerate baseline from scratch
detect-secrets scan > .secrets.baseline

# Review and mark all findings
detect-secrets audit .secrets.baseline

# Commit updated baseline
git add .secrets.baseline
git commit -m "chore: update secrets baseline"
```

---

## Reporting Security Issues

If you discover a security vulnerability, please email security@example.com with:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

**Do not** open public GitHub issues for security vulnerabilities.
