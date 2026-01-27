"""
Pytest fixtures for File-Driven Control Plane tests

Provides isolated file system fixtures for testing.
Constitutional compliance: Section 2 (Source of Truth) - tests verify file-based state
"""

import pytest
from pathlib import Path


@pytest.fixture
def isolated_fs(tmp_path):
    """
    Create isolated file system with 8 workflow folders.

    Constitutional requirement (Section 4): Exactly 8 workflow folders.

    Returns:
        Path: Root directory containing workflow folders
    """
    # Create 8 workflow folders
    workflow_folders = [
        "Inbox",
        "Needs_Action",
        "Plans",
        "Pending_Approval",
        "Approved",
        "Rejected",
        "Done",
        "Logs",
    ]

    for folder in workflow_folders:
        (tmp_path / folder).mkdir()

    return tmp_path
