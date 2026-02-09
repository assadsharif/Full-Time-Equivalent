"""
Vault Initializer tests (spec 008).

Coverage map:
  TestInitialize        — fresh vault, idempotent re-run, partial vault filled,
                          all folders present, schemas written, seed docs created
  TestCheckStructure    — fully initialized reports nothing missing,
                          empty dir reports all missing, partial dir reports gaps
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from src.vault.initializer import CORE_FOLDERS, VaultInitializer, _SCHEMAS

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def empty_dir():
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def initialized_vault(empty_dir):
    """Return a vault path that has already been fully initialized."""
    VaultInitializer(empty_dir).initialize()
    return empty_dir


# ===========================================================================
# TestInitialize
# ===========================================================================


class TestInitialize:
    def test_fresh_vault_creates_all_folders(self, empty_dir):
        created = VaultInitializer(empty_dir).initialize()
        for folder in CORE_FOLDERS:
            assert (empty_dir / folder).is_dir(), f"folder {folder} missing"
        # every folder should appear in created list
        folder_items = [c for c in created if c.startswith("folder:")]
        assert len(folder_items) == len(CORE_FOLDERS)

    def test_fresh_vault_creates_schemas(self, empty_dir):
        created = VaultInitializer(empty_dir).initialize()
        schema_dir = empty_dir / ".vault_schema" / "frontmatter_schemas"
        for name in _SCHEMAS:
            assert (schema_dir / name).is_file(), f"schema {name} missing"
        schema_items = [c for c in created if c.startswith("schema:")]
        assert len(schema_items) == len(_SCHEMAS)

    def test_fresh_vault_creates_seed_docs(self, empty_dir):
        created = VaultInitializer(empty_dir).initialize()
        assert (empty_dir / "Dashboard.md").is_file()
        assert (empty_dir / "Company_Handbook.md").is_file()
        assert (empty_dir / "Templates" / "task_template.md").is_file()
        file_items = [c for c in created if c.startswith("file:")]
        assert len(file_items) == 3  # Dashboard, Handbook, task_template

    def test_idempotent_second_run_creates_nothing(self, initialized_vault):
        created = VaultInitializer(initialized_vault).initialize()
        assert created == []

    def test_partial_vault_only_fills_gaps(self, empty_dir):
        # Pre-create some folders so they are NOT in created list
        (empty_dir / "Inbox").mkdir()
        (empty_dir / "Done").mkdir()
        created = VaultInitializer(empty_dir).initialize()
        # Inbox and Done should NOT appear
        assert "folder:Inbox" not in created
        assert "folder:Done" not in created
        # Others should appear
        assert "folder:Needs_Action" in created

    def test_existing_dashboard_not_overwritten(self, empty_dir):
        # Pre-create Dashboard with custom content
        empty_dir.mkdir(exist_ok=True)
        sentinel = "# My Custom Dashboard\n"
        (empty_dir / "Dashboard.md").write_text(sentinel)
        VaultInitializer(empty_dir).initialize()
        assert (empty_dir / "Dashboard.md").read_text() == sentinel

    def test_dashboard_contains_folder_names(self, empty_dir):
        VaultInitializer(empty_dir).initialize()
        dash = (empty_dir / "Dashboard.md").read_text()
        for folder in CORE_FOLDERS:
            assert folder in dash

    def test_handbook_contains_core_principles(self, empty_dir):
        VaultInitializer(empty_dir).initialize()
        hb = (empty_dir / "Company_Handbook.md").read_text()
        assert "File-Driven" in hb
        assert "Human-in-the-Loop" in hb
        assert "Fail-Safe" in hb

    def test_schema_content_is_valid_yaml(self, initialized_vault):
        import yaml

        schema_dir = initialized_vault / ".vault_schema" / "frontmatter_schemas"
        for name in _SCHEMAS:
            data = yaml.safe_load((schema_dir / name).read_text())
            assert "required_fields" in data

    def test_nonexistent_parent_is_created(self, empty_dir):
        nested = empty_dir / "a" / "b" / "vault"
        VaultInitializer(nested).initialize()
        assert nested.is_dir()
        assert (nested / "Inbox").is_dir()


# ===========================================================================
# TestCheckStructure
# ===========================================================================


class TestCheckStructure:
    def test_fully_initialized_reports_nothing_missing(self, initialized_vault):
        missing = VaultInitializer(initialized_vault).check_structure()
        assert missing == {"folders": [], "schemas": [], "files": []}

    def test_empty_dir_reports_all_missing(self, empty_dir):
        missing = VaultInitializer(empty_dir).check_structure()
        assert set(missing["folders"]) == set(CORE_FOLDERS)
        assert set(missing["schemas"]) == set(_SCHEMAS.keys())
        assert "Dashboard.md" in missing["files"]
        assert "Company_Handbook.md" in missing["files"]

    def test_partial_dir_reports_exact_gaps(self, empty_dir):
        # Create only Inbox folder and Dashboard
        (empty_dir / "Inbox").mkdir()
        (empty_dir / "Dashboard.md").write_text("# D\n")
        missing = VaultInitializer(empty_dir).check_structure()
        assert "Inbox" not in missing["folders"]
        assert "Dashboard.md" not in missing["files"]
        # Everything else is still missing
        assert len(missing["folders"]) == len(CORE_FOLDERS) - 1
        assert "Company_Handbook.md" in missing["files"]

    def test_nonexistent_vault_path_reports_all_missing(self):
        missing = VaultInitializer(Path("/nonexistent/vault")).check_structure()
        assert len(missing["folders"]) == len(CORE_FOLDERS)
        assert len(missing["schemas"]) == len(_SCHEMAS)
        assert len(missing["files"]) == 2
