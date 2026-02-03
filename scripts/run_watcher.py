#!/usr/bin/env python3
"""
Watcher Entry Point.

Run watchers from command line or PM2.

Usage:
    python -m scripts.run_watcher filesystem --watch-path ./Input_Documents
    python -m scripts.run_watcher gmail --credentials ~/.credentials/gmail.json
"""

import argparse
import sys
from pathlib import Path


def run_filesystem_watcher(args):
    """Run filesystem watcher."""
    from src.watchers.filesystem_watcher import FileSystemWatcher

    watcher = FileSystemWatcher(
        vault_path=args.vault_path,
        watch_path=args.watch_path,
        recursive=args.recursive,
    )
    watcher.run()


def run_gmail_watcher(args):
    """Run Gmail watcher."""
    try:
        from src.watchers.gmail_watcher import GmailWatcher
    except ImportError:
        print("Gmail watcher not implemented yet.")
        sys.exit(1)

    watcher = GmailWatcher(
        vault_path=args.vault_path,
        credentials_file=args.credentials,
        token_file=args.token,
        poll_interval=args.poll_interval,
    )
    watcher.run()


def run_whatsapp_watcher(args):
    """Run WhatsApp watcher."""
    import os

    try:
        from src.watchers.whatsapp_watcher import WhatsAppWatcher
    except ImportError as e:
        print(f"WhatsApp watcher dependencies not installed: {e}")
        print("Install with: pip install flask requests")
        sys.exit(1)

    # Get verify token from args or environment
    verify_token = args.verify_token or os.environ.get("WHATSAPP_VERIFY_TOKEN", "")
    if not verify_token:
        print("Error: No verify token configured")
        print("Set --verify-token or WHATSAPP_VERIFY_TOKEN environment variable")
        sys.exit(1)

    watcher = WhatsAppWatcher(
        vault_path=args.vault_path,
        verify_token=verify_token,
        port=args.port,
        host=args.host,
    )
    watcher.run()


def main():
    parser = argparse.ArgumentParser(
        description="Run Digital FTE watchers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Common arguments
    parser.add_argument(
        "--vault-path",
        type=Path,
        default=Path("./vault"),
        help="Path to Obsidian vault (default: ./vault)",
    )

    subparsers = parser.add_subparsers(dest="watcher", help="Watcher to run")

    # Filesystem watcher
    fs_parser = subparsers.add_parser("filesystem", help="Run filesystem watcher")
    fs_parser.add_argument(
        "--watch-path",
        type=Path,
        default=Path("./Input_Documents"),
        help="Directory to monitor (default: ./Input_Documents)",
    )
    fs_parser.add_argument(
        "--recursive",
        action="store_true",
        default=True,
        help="Monitor subdirectories recursively",
    )
    fs_parser.set_defaults(func=run_filesystem_watcher)

    # Gmail watcher
    gmail_parser = subparsers.add_parser("gmail", help="Run Gmail watcher")
    gmail_parser.add_argument(
        "--credentials",
        type=Path,
        default=Path("~/.credentials/gmail_credentials.json"),
        help="OAuth2 credentials file",
    )
    gmail_parser.add_argument(
        "--token",
        type=Path,
        default=Path("~/.credentials/gmail_token.json"),
        help="Token storage file",
    )
    gmail_parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Poll interval in seconds (default: 30)",
    )
    gmail_parser.set_defaults(func=run_gmail_watcher)

    # WhatsApp watcher
    wa_parser = subparsers.add_parser("whatsapp", help="Run WhatsApp watcher")
    wa_parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Webhook server port (default: 5000)",
    )
    wa_parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Webhook server host (default: 0.0.0.0)",
    )
    wa_parser.add_argument(
        "--verify-token",
        default=None,
        help="Webhook verify token (or set WHATSAPP_VERIFY_TOKEN env var)",
    )
    wa_parser.set_defaults(func=run_whatsapp_watcher)

    args = parser.parse_args()

    if not args.watcher:
        parser.print_help()
        sys.exit(1)

    # Expand user paths
    args.vault_path = args.vault_path.expanduser()

    args.func(args)


if __name__ == "__main__":
    main()
