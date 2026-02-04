#!/usr/bin/env python3
"""
Gmail Watcher — Digital FTE Silver Tier

Two modes:
  LIVE   – real Gmail via OAuth2  (set GMAIL_CREDENTIALS env var)
  SIM    – synthetic email stream for demo / CI  (default)

Both modes write identical Markdown tasks into the vault Inbox,
so the downstream Task Processor and CEO Briefing see real work.
"""

import json
import os
import sys
import time
import random
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
VAULT_PATH     = Path.home() / "AI_Employee_Vault"
INBOX_PATH     = VAULT_PATH / "Inbox"
ATTACHMENTS    = VAULT_PATH / "Attachments"
LOG_PATH       = VAULT_PATH / "watcher_gmail.log"
CREDS_PATH     = Path(os.getenv("GMAIL_CREDENTIALS",
                      str(Path.home() / ".credentials" / "gmail_credentials.json")))
TOKEN_PATH     = CREDS_PATH.parent / "gmail_token.json"

# ---------------------------------------------------------------------------
# Simulated email corpus (realistic variety)
# ---------------------------------------------------------------------------
SIM_EMAILS = [
    {
        "sender": "ceo@company.com",
        "subject": "[URGENT] Q1 Board Presentation – Slides needed by Friday",
        "body": (
            "Hi team,\n\n"
            "We need the updated Q1 presentation slides by end of day Friday.\n"
            "Please include:\n"
            "  • Revenue summary\n"
            "  • Customer acquisition metrics\n"
            "  • Product roadmap update\n\n"
            "This is high priority – board meets next Monday.\n\n"
            "Thanks,\nCEO"
        ),
        "priority": "urgent",
        "labels": ["INBOX", "UNREAD"],
    },
    {
        "sender": "devops@company.com",
        "subject": "Production Alert: API latency spike on eu-west-1",
        "body": (
            "🚨 Alert triggered at 06:42 UTC\n\n"
            "Service : payments-api\n"
            "Region  : eu-west-1\n"
            "p95 latency: 2.4 s  (threshold 800 ms)\n"
            "Error rate : 12 %\n\n"
            "Auto-scaled to 6 pods – latency still elevated.\n"
            "Manual investigation required.\n"
        ),
        "priority": "urgent",
        "labels": ["INBOX", "UNREAD"],
    },
    {
        "sender": "client@acme-corp.com",
        "subject": "Project Kickoff – Digital Transformation",
        "body": (
            "Hello,\n\n"
            "We are excited to kick off the Digital Transformation project.\n"
            "Could you please schedule a 1-hour discovery call this week?\n\n"
            "Preferred slots:\n"
            "  • Tue 10:00–11:00 UTC\n"
            "  • Thu 14:00–15:00 UTC\n\n"
            "Looking forward to it.\n\nBest,\nSarah – Acme Corp"
        ),
        "priority": "high",
        "labels": ["INBOX", "UNREAD"],
    },
    {
        "sender": "hr@company.com",
        "subject": "Action Required: Complete your 2026 goals by March 1",
        "body": (
            "Reminder: Annual goal-setting is due by March 1.\n\n"
            "Please log in to the HR portal and:\n"
            "  1. Update your 2026 objectives\n"
            "  2. Align with your manager\n"
            "  3. Submit for approval\n\n"
            "Portal: https://hr.company.com/goals\n"
        ),
        "priority": "high",
        "labels": ["INBOX", "UNREAD"],
    },
    {
        "sender": "security@company.com",
        "subject": "Security Audit Report – Action Items",
        "body": (
            "The quarterly security audit is complete.\n\n"
            "Critical findings (must remediate within 48 h):\n"
            "  • Outdated TLS certificates on staging\n"
            "  • Unrestricted SSH access from 0.0.0.0/0\n\n"
            "High findings (2 weeks):\n"
            "  • Rotate service-account keys\n"
            "  • Enable WAF on public ALBs\n\n"
            "Full report attached.\n"
        ),
        "priority": "urgent",
        "labels": ["INBOX", "UNREAD"],
    },
    {
        "sender": "newsletter@tech-digest.com",
        "subject": "Weekly Tech Digest: AI & Cloud updates",
        "body": (
            "📰 This week in tech:\n\n"
            "• New serverless GPU offerings from major clouds\n"
            "• Kubernetes 1.32 release highlights\n"
            "• Top 5 open-source AI frameworks\n\n"
            "Read more at techdigest.example.com\n"
        ),
        "priority": "low",
        "labels": ["INBOX", "UNREAD", "PROMOTIONS"],
    },
    {
        "sender": "qa@company.com",
        "subject": "Regression suite – 3 failures in payment flow",
        "body": (
            "Latest nightly run flagged 3 regressions:\n\n"
            "  1. Checkout fails when coupon applied after sign-in\n"
            "  2. Refund confirmation email not sent\n"
            "  3. Cart total rounds incorrectly for JPY\n\n"
            "Test report: /reports/regression-2026-02-04.html\n\n"
            "Needs investigation before next deploy.\n"
        ),
        "priority": "high",
        "labels": ["INBOX", "UNREAD"],
    },
    {
        "sender": "design@company.com",
        "subject": "New dashboard mockups ready for review",
        "body": (
            "Hi,\n\n"
            "The v2 dashboard mockups are ready in Figma.\n"
            "Key changes:\n"
            "  • Unified navigation bar\n"
            "  • Dark-mode support\n"
            "  • Real-time KPI widgets\n\n"
            "Please review and leave comments by EOD Thursday.\n\n"
            "Figma link: https://figma.com/file/dashboard-v2\n"
        ),
        "priority": "medium",
        "labels": ["INBOX", "UNREAD"],
    },
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid(subject: str) -> str:
    """Deterministic short ID from subject so duplicates are skippable."""
    return hashlib.md5(subject.encode()).hexdigest()[:8]


def _slug(subject: str) -> str:
    """URL-safe slug from subject."""
    import re
    return re.sub(r"[^a-zA-Z0-9]+", "-", subject).strip("-")[:60].lower()


def _task_md(email: dict, received_at: str) -> str:
    """Render an email dict into a vault task Markdown file."""
    priority_badge = {"urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
    badge = priority_badge.get(email["priority"], "⚪")

    return (
        f"# {email['subject']}\n\n"
        f"**Priority**: {badge} {email['priority'].capitalize()}\n"
        f"**Created**: {received_at}\n"
        f"**Status**: New\n"
        f"**Source**: Gmail Watcher\n"
        f"**From**: {email['sender']}\n\n"
        f"---\n\n"
        f"## Email Body\n\n"
        f"{email['body']}\n\n"
        f"---\n\n"
        f"## Requirements\n"
        f"- [ ] Review email contents\n"
        f"- [ ] Determine action needed\n"
        f"- [ ] Assign or process\n"
        f"- [ ] Mark complete\n\n"
        f"## Notes\n"
        f"Auto-generated by Gmail Watcher.\n"
    )


# ---------------------------------------------------------------------------
# Simulated Gmail feed
# ---------------------------------------------------------------------------

class SimGmailWatcher:
    """Simulated Gmail watcher – fires one email every `interval` seconds."""

    def __init__(self, interval: int = 20):
        self.interval  = interval
        self.queue     = list(SIM_EMAILS)          # copy
        random.shuffle(self.queue)
        self.processed = 0
        self.errors    = 0

    # -- internal ----------------------------------------------------------
    def _already_exists(self, subject: str) -> bool:
        slug = _slug(subject)
        return any(slug in p.name for p in INBOX_PATH.glob("*.md"))

    def _write_task(self, email: dict) -> Path:
        slug  = _slug(email["subject"])
        uid   = _uid(email["subject"])
        fname = f"gmail-{uid}-{slug}.md"
        path  = INBOX_PATH / fname
        path.write_text(_task_md(email, datetime.now().isoformat()))
        return path

    def _log(self, msg: str):
        line = f"[{datetime.now().isoformat()}] {msg}\n"
        print(line, end="", flush=True)
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a") as fh:
            fh.write(line)

    # -- public ------------------------------------------------------------
    def run(self):
        INBOX_PATH.mkdir(parents=True, exist_ok=True)

        self._log("=" * 58)
        self._log("Gmail Watcher started (SIM mode)")
        self._log(f"  Vault  : {VAULT_PATH}")
        self._log(f"  Inbox  : {INBOX_PATH}")
        self._log(f"  Emails : {len(self.queue)} in queue")
        self._log(f"  Interval: {self.interval} s")
        self._log("=" * 58)

        idx = 0
        while True:
            if idx >= len(self.queue):
                # Recycle
                idx = 0
                random.shuffle(self.queue)

            email = self.queue[idx]
            idx  += 1

            if self._already_exists(email["subject"]):
                self._log(f"  ⏭  Skip (exists): {email['subject'][:55]}")
                time.sleep(self.interval)
                continue

            try:
                path = self._write_task(email)
                self.processed += 1
                self._log(f"  ✓  [{email['priority']:6s}] {email['subject'][:55]}")
                self._log(f"       → {path.name}")
            except Exception as exc:
                self.errors += 1
                self._log(f"  ✗  Error: {exc}")

            time.sleep(self.interval)


# ---------------------------------------------------------------------------
# Live Gmail watcher (thin wrapper around the project's GmailWatcher class)
# ---------------------------------------------------------------------------

class LiveGmailWatcher:
    """Delegates to src.watchers.gmail_watcher.GmailWatcher after validating creds."""

    def __init__(self):
        if not CREDS_PATH.exists():
            raise FileNotFoundError(
                f"OAuth2 credentials not found: {CREDS_PATH}\n"
                "1. Go to https://console.cloud.google.com\n"
                "2. Enable Gmail API\n"
                "3. Create OAuth2 client (Desktop app)\n"
                "4. Download credentials.json → ~/.credentials/gmail_credentials.json\n"
            )

    def run(self):
        # Add project src to path so the watcher module resolves
        project_root = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(project_root / "src"))

        from watchers.gmail_watcher import GmailWatcher   # noqa: E402

        watcher = GmailWatcher(
            vault_path=VAULT_PATH,
            credentials_file=CREDS_PATH,
            token_file=TOKEN_PATH,
            poll_interval=30,
            max_results=10,
        )
        watcher.run()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    mode = os.getenv("GMAIL_MODE", "").lower()

    # Auto-detect: if credentials file exists use live, otherwise sim
    if mode not in ("live", "sim"):
        mode = "live" if CREDS_PATH.exists() else "sim"

    if mode == "live":
        print("Starting Gmail Watcher in LIVE mode…")
        LiveGmailWatcher().run()
    else:
        print("Starting Gmail Watcher in SIM mode…")
        SimGmailWatcher(interval=20).run()


if __name__ == "__main__":
    main()
