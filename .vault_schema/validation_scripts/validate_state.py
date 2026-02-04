#!/usr/bin/env python3
"""
State Transition Validator

Validates that task files obey the allowed state-transition graph
defined in state_transitions.md.  Checks:
  - Current state is valid for the folder the file lives in
  - state_history entries are chronologically ordered
  - No transitions out of terminal states appear in history
  - retry_count is consistent with error_queue transitions
"""

import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple
import yaml


# Allowed transitions: from_state -> set of to_states
ALLOWED_TRANSITIONS: Dict[str, set] = {
    "inbox":            {"needs_action", "pending_approval"},
    "needs_action":     {"in_progress", "pending_approval", "error_queue"},
    "in_progress":      {"done", "pending_approval", "error_queue"},
    "pending_approval": {"in_progress", "rejected"},
    "error_queue":      {"needs_action", "failed"},
    # Terminal — no outgoing transitions
    "done":             set(),
    "rejected":         set(),
    "failed":           set(),
}

TERMINAL_STATES = {"done", "rejected", "failed"}

# Which states are valid inside which folders
FOLDER_STATE_MAP: Dict[str, set] = {
    "inbox":          {"inbox"},
    "needs_action":   {"needs_action", "error_queue"},
    "in_progress":    {"in_progress"},
    "approvals":      {"pending_approval"},
    "done":           {"done", "rejected", "failed"},
}

MAX_RETRIES_DEFAULT = 3


class StateValidationError:
    def __init__(self, file: str, message: str):
        self.file = file
        self.message = message

    def __str__(self):
        return f"  ❌ {self.file}: {self.message}"


def extract_frontmatter(content: str) -> dict | None:
    """Extract YAML frontmatter from a markdown file."""
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return None
    return yaml.safe_load(match.group(1))


def validate_folder_state(folder: str, state: str) -> bool:
    """Check that the state is valid for the given folder."""
    allowed = FOLDER_STATE_MAP.get(folder.lower())
    if allowed is None:
        return True  # Unknown folder — skip
    return state in allowed


def validate_history_transitions(history: List[dict]) -> List[str]:
    """Return list of invalid transition descriptions found in history."""
    errors: List[str] = []
    for i in range(1, len(history)):
        prev = history[i - 1].get("state", "")
        curr = history[i].get("state", "")
        allowed = ALLOWED_TRANSITIONS.get(prev, set())
        if curr not in allowed:
            errors.append(f"{prev} → {curr} (history[{i}])")
    return errors


def validate_history_order(history: List[dict]) -> bool:
    """Check timestamps are monotonically increasing."""
    timestamps = [h.get("timestamp", "") for h in history]
    return timestamps == sorted(timestamps)


def validate_task_file(task_path: Path, folder_name: str) -> List[StateValidationError]:
    """Validate state transitions for a single task file."""
    errors: List[StateValidationError] = []
    content = task_path.read_text()
    fm = extract_frontmatter(content)
    if fm is None:
        errors.append(StateValidationError(task_path.name, "no frontmatter found"))
        return errors

    state = fm.get("state")
    if state is None:
        errors.append(StateValidationError(task_path.name, "missing 'state' field"))
        return errors

    # Folder vs state check
    if not validate_folder_state(folder_name, state):
        errors.append(StateValidationError(
            task_path.name,
            f"state '{state}' invalid in folder '{folder_name}'"
        ))

    # History checks
    history: List[dict] = fm.get("state_history", [])
    if history:
        if not validate_history_order(history):
            errors.append(StateValidationError(task_path.name, "state_history timestamps not in order"))

        bad_transitions = validate_history_transitions(history)
        for bt in bad_transitions:
            errors.append(StateValidationError(task_path.name, f"invalid transition {bt}"))

        # Last history entry should match current state
        last_state = history[-1].get("state")
        if last_state != state:
            errors.append(StateValidationError(
                task_path.name,
                f"state '{state}' does not match last history entry '{last_state}'"
            ))

    # Retry count vs error_queue
    retry_count = fm.get("retry_count", 0)
    if state == "failed" and retry_count < MAX_RETRIES_DEFAULT:
        errors.append(StateValidationError(
            task_path.name,
            f"state 'failed' but retry_count={retry_count} < max ({MAX_RETRIES_DEFAULT})"
        ))

    return errors


def validate_vault_states(vault_path: Path) -> Tuple[List[StateValidationError], int]:
    """
    Walk all task-bearing folders and validate state rules.

    Returns (errors, files_checked).
    """
    task_folders = ["Inbox", "Needs_Action", "In_Progress", "Done", "Approvals"]
    all_errors: List[StateValidationError] = []
    checked = 0

    for folder_name in task_folders:
        folder_path = vault_path / folder_name
        if not folder_path.is_dir():
            continue
        for md_file in folder_path.glob("*.md"):
            if md_file.name.startswith("."):
                continue
            all_errors.extend(validate_task_file(md_file, folder_name))
            checked += 1

    return all_errors, checked


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_state.py <vault_path>")
        sys.exit(1)

    vault_path = Path(sys.argv[1]).expanduser().resolve()
    if not vault_path.is_dir():
        print(f"❌ Path is not a directory: {vault_path}")
        sys.exit(1)

    print(f"🔍 Validating state transitions in: {vault_path}\n")
    errors, checked = validate_vault_states(vault_path)

    print(f"   Checked {checked} task file(s)")
    if errors:
        print(f"\n🚨 {len(errors)} state violation(s):\n")
        for e in errors:
            print(e)
        sys.exit(1)
    else:
        print("\n✅ All state transitions valid")
        sys.exit(0)


if __name__ == "__main__":
    main()
