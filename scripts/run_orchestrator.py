#!/usr/bin/env python3
"""
Orchestrator entry point.

Modes:
  default        — continuous loop (Ctrl-C or .claude_stop to stop)
  --once         — single sweep then exit (good for CI / cron)
  --dry-run      — simulate Claude invocations without running Claude
  --config PATH  — load config from YAML (default: config/orchestrator.yaml)
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from orchestrator.models import OrchestratorConfig  # noqa: E402
from orchestrator.scheduler import Orchestrator      # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Digital FTE Orchestrator")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single sweep and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate Claude invocations (no real Claude calls)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "config" / "orchestrator.yaml",
        help="Path to orchestrator YAML config",
    )

    args = parser.parse_args()

    # Load config
    config = OrchestratorConfig.from_yaml(args.config)
    # Expand ~ in vault_path
    config.vault_path = config.vault_path.expanduser()

    orchestrator = Orchestrator(config=config, dry_run=args.dry_run)

    if args.once:
        orchestrator.run_once()
    else:
        orchestrator.run()


if __name__ == "__main__":
    main()
