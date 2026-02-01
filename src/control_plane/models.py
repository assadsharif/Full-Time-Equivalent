"""
Data models for File-Driven Control Plane

Constitutional compliance:
- Section 2 (Source of Truth): Models represent file-backed entities
- Section 4 (File-Driven Control Plane): WorkflowState enum defines fixed folder states
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional
import yaml


class WorkflowState(Enum):
    """
    Valid workflow states for task files.

    Constitutional requirement (Section 4): Fixed set of workflow folders.
    Each state corresponds to a folder at repository root.
    """
    INBOX = "Inbox"
    NEEDS_ACTION = "Needs_Action"
    PLANS = "Plans"
    PENDING_APPROVAL = "Pending_Approval"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    DONE = "Done"


@dataclass
class TaskFile:
    """
    Entity representing a task file on disk.

    Constitutional requirement (Section 2): Files are the source of truth.
    All task state is derived from file location and contents.
    """
    id: str
    state: WorkflowState
    priority: str
    created_at: datetime
    modified_at: datetime
    metadata: Dict[str, Any]
    file_path: Path
    content: str

    @staticmethod
    def from_file(file_path: Path) -> "TaskFile":
        """
        Load TaskFile from disk by parsing YAML frontmatter and markdown content.

        Constitutional requirement (Section 2): Files on disk are the source of truth.

        Args:
            file_path: Path to the task file

        Returns:
            TaskFile instance with parsed data

        Raises:
            FileNotFoundError: If file does not exist
            ValueError: If YAML frontmatter is invalid or missing required fields
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Task file not found: {file_path}")

        # Read file content
        raw_content = file_path.read_text(encoding='utf-8')

        # Parse YAML frontmatter
        if not raw_content.startswith('---'):
            raise ValueError(f"Task file missing YAML frontmatter: {file_path}")

        # Split frontmatter and content
        parts = raw_content.split('---', 2)
        if len(parts) < 3:
            raise ValueError(f"Invalid YAML frontmatter format: {file_path}")

        frontmatter_text = parts[1]
        markdown_content = parts[2].strip()

        # Parse YAML
        frontmatter = yaml.safe_load(frontmatter_text)
        if not frontmatter:
            raise ValueError(f"Empty YAML frontmatter: {file_path}")

        # Extract required fields
        task_id = frontmatter.get('id')
        if not task_id:
            raise ValueError(f"Missing 'id' field in frontmatter: {file_path}")

        state_str = frontmatter.get('state')
        if not state_str:
            raise ValueError(f"Missing 'state' field in frontmatter: {file_path}")

        # Convert state string to WorkflowState enum
        try:
            state = WorkflowState(state_str)
        except ValueError:
            raise ValueError(f"Invalid state '{state_str}' in frontmatter: {file_path}")

        priority = frontmatter.get('priority', 'P3')  # Default priority

        # Parse timestamps (YAML automatically parses ISO8601 to datetime objects)
        created_at = frontmatter.get('created_at')
        if not created_at:
            raise ValueError(f"Missing 'created_at' field in frontmatter: {file_path}")
        # If YAML didn't parse it, parse it manually
        if isinstance(created_at, str):
            if created_at.endswith('Z'):
                created_at = created_at[:-1] + '+00:00'
            created_at = datetime.fromisoformat(created_at)

        modified_at = frontmatter.get('modified_at')
        if not modified_at:
            raise ValueError(f"Missing 'modified_at' field in frontmatter: {file_path}")
        # If YAML didn't parse it, parse it manually
        if isinstance(modified_at, str):
            if modified_at.endswith('Z'):
                modified_at = modified_at[:-1] + '+00:00'
            modified_at = datetime.fromisoformat(modified_at)

        # Extract metadata (optional)
        metadata = frontmatter.get('metadata', {})

        return TaskFile(
            id=task_id,
            state=state,
            priority=priority,
            created_at=created_at,
            modified_at=modified_at,
            metadata=metadata,
            file_path=file_path,
            content=markdown_content
        )

    def to_file(self, file_path: Path) -> None:
        """
        Write TaskFile to disk with YAML frontmatter and markdown content.

        Constitutional requirement (Section 2): Files are the source of truth.
        This method persists task state to disk.

        Args:
            file_path: Path where the task file should be written

        Raises:
            IOError: If file cannot be written
        """
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Build YAML frontmatter
        frontmatter = {
            'id': self.id,
            'state': self.state.value,  # Use enum value (e.g., "Inbox")
            'priority': self.priority,
            'created_at': self.created_at.isoformat(),
            'modified_at': self.modified_at.isoformat(),
            'metadata': self.metadata
        }

        # Serialize frontmatter to YAML
        yaml_content = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)

        # Build complete file content
        file_content = f"---\n{yaml_content}---\n\n{self.content}\n"

        # Write to disk
        file_path.write_text(file_content, encoding='utf-8')

    def derive_state_from_location(self) -> WorkflowState:
        """
        Derive workflow state from file location on disk.

        Constitutional requirement (Section 4): Folder location defines workflow state.
        The parent folder name determines the state, not the frontmatter.

        Returns:
            WorkflowState enum corresponding to the parent folder

        Raises:
            ValueError: If parent folder doesn't match any valid workflow state
        """
        # Get parent folder name
        folder_name = self.file_path.parent.name

        # Find matching WorkflowState by folder value
        for state in WorkflowState:
            if state.value == folder_name:
                return state

        # If no match found, raise error
        raise ValueError(
            f"Invalid workflow folder '{folder_name}'. "
            f"Must be one of: {[s.value for s in WorkflowState]}"
        )

    def update_state(self) -> "TaskFile":
        """
        Update the state field to match the file's current location.

        Constitutional requirement (Section 4): Folder location is the source of truth.
        This method syncs the frontmatter state with the actual file location.

        Returns:
            Self for method chaining

        Raises:
            ValueError: If file location doesn't match any valid workflow state
        """
        # Derive state from current file location
        derived_state = self.derive_state_from_location()

        # Update state field if it differs
        if self.state != derived_state:
            self.state = derived_state
            # Update modified timestamp
            self.modified_at = datetime.now()

        return self


@dataclass
class StateTransition:
    """
    Entity representing a state transition event.

    Constitutional requirement (Section 8): All state changes must be logged.
    """
    transition_id: str
    task_id: str
    from_state: WorkflowState
    to_state: WorkflowState
    timestamp: datetime
    reason: str
    actor: str  # 'system' or 'human'
    logged: bool
    error: Optional[str] = None
