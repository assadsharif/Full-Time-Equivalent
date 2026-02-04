#!/usr/bin/env python3
"""
Secrets-baseline updater  (spec 004 Polish T049).

Scans the repository for credential-like patterns and writes a baseline
file (.fte/secrets_baseline.json).  CI can diff this file to detect new
secrets that appeared since the last approved baseline.

Usage:
    python scripts/update_secrets_baseline.py              # update baseline
    python scripts/update_secrets_baseline.py --check      # CI mode: exit 1 if new secrets found
    python scripts/update_secrets_baseline.py --show       # print current findings

The baseline JSON structure:
    {
        "updated_at": "<ISO timestamp>",
        "findings": [
            {
                "file": "<relative path>",
                "line": <int>,
                "pattern": "<matched pattern name>",
                "hash": "<SHA256 of the matched line>",
                "approved": false
            }
        ]
    }

Approved findings (manually set ``approved: true``) are not treated as
violations in --check mode.
"""

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Patterns that indicate a potential secret.  Each entry is (name, regex).
SECRET_PATTERNS = [
    ("api_key",          re.compile(r'(?i)(api[_-]?key\s*[:=]\s*["\']?[A-Za-z0-9_-]{20,})')),
    ("password",         re.compile(r'(?i)(password\s*[:=]\s*["\']?[^\s"\']{8,})')),
    ("token",            re.compile(r'(?i)((?:access|auth|bearer|refresh)[_-]?token\s*[:=]\s*["\']?[A-Za-z0-9_.-]{20,})')),
    ("secret_key",       re.compile(r'(?i)(secret[_-]?key\s*[:=]\s*["\']?[A-Za-z0-9_-]{20,})')),
    ("aws_access_key",   re.compile(r'(AKIA[0-9A-Z]{16})')),
    ("private_key_header", re.compile(r'(-----BEGIN\s+(?:RSA |EC )?PRIVATE KEY-----)')),
]

# Directories / file patterns to skip entirely
SKIP_DIRS = {".venv", "node_modules", ".git", "__pycache__", ".pytest_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".egg-info"}
SKIP_FILES = {"secrets_baseline.json"}  # don't scan ourselves

BASELINE_PATH = Path(".fte") / "secrets_baseline.json"
REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def scan_repository() -> list[dict]:
    """Walk the repo tree and return raw findings."""
    findings = []
    for source_file in _iter_source_files():
        rel = source_file.relative_to(REPO_ROOT)
        try:
            text = source_file.read_text(errors="replace")
        except (PermissionError, OSError):
            continue

        for lineno, line in enumerate(text.splitlines(), start=1):
            for name, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    line_hash = hashlib.sha256(line.strip().encode()).hexdigest()
                    findings.append({
                        "file": str(rel),
                        "line": lineno,
                        "pattern": name,
                        "hash": line_hash,
                    })
                    break  # one finding per line is enough

    return findings


def load_baseline() -> dict:
    """Load the current baseline (empty baseline if missing)."""
    path = REPO_ROOT / BASELINE_PATH
    if not path.exists():
        return {"updated_at": "", "findings": []}
    return json.loads(path.read_text())


def merge_baseline(current: dict, new_findings: list[dict]) -> dict:
    """Merge new findings into the baseline, preserving approved flags."""
    approved_hashes = {
        f["hash"] for f in current.get("findings", []) if f.get("approved")
    }

    merged = []
    for f in new_findings:
        f["approved"] = f["hash"] in approved_hashes
        merged.append(f)

    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "findings": merged,
    }


def save_baseline(baseline: dict):
    """Write baseline to disk."""
    path = REPO_ROOT / BASELINE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(baseline, indent=2) + "\n")


def check_mode(baseline: dict) -> int:
    """CI check: exit 1 if any unapproved finding exists."""
    unapproved = [f for f in baseline.get("findings", []) if not f.get("approved")]
    if unapproved:
        print(f"[FAIL] {len(unapproved)} unapproved secret(s) found:")
        for f in unapproved:
            print(f"  {f['file']}:{f['line']} — pattern: {f['pattern']}")
        print("\nTo suppress: set \"approved\": true in .fte/secrets_baseline.json")
        return 1
    print("[PASS] No unapproved secrets.")
    return 0


# ---------------------------------------------------------------------------
# File iteration helpers
# ---------------------------------------------------------------------------


def _iter_source_files():
    """Yield every scannable file under REPO_ROOT."""
    for path in sorted(REPO_ROOT.rglob("*")):
        if not path.is_file():
            continue
        # Skip directories
        if any(skip in path.parts for skip in SKIP_DIRS):
            continue
        if any(path.name.endswith(s) for s in SKIP_SUFFIXES):
            continue
        if path.name in SKIP_FILES:
            continue
        yield path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    import argparse

    parser = argparse.ArgumentParser(description="FTE secrets-baseline updater")
    parser.add_argument("--check", action="store_true", help="CI mode – exit 1 on unapproved secrets")
    parser.add_argument("--show", action="store_true", help="Print current findings")
    args = parser.parse_args()

    if args.show:
        baseline = load_baseline()
        print(json.dumps(baseline, indent=2))
        return

    # Scan
    print("Scanning repository…")
    findings = scan_repository()
    print(f"  Found {len(findings)} potential secret(s)")

    # Merge with existing baseline
    current = load_baseline()
    baseline = merge_baseline(current, findings)

    if args.check:
        sys.exit(check_mode(baseline))
    else:
        save_baseline(baseline)
        print(f"  Baseline written to {BASELINE_PATH}")
        unapproved = sum(1 for f in baseline["findings"] if not f["approved"])
        print(f"  {unapproved} unapproved  |  {len(findings) - unapproved} approved")


if __name__ == "__main__":
    main()
