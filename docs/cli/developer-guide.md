# CLI Developer Guide

**Digital FTE AI Assistant - Developer Documentation**

Version: 1.0.0
Last Updated: 2026-01-29

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Adding New Commands](#adding-new-commands)
5. [Testing Guidelines](#testing-guidelines)
6. [Error Handling](#error-handling)
7. [Styling and UX](#styling-and-ux)
8. [Contributing](#contributing)

---

## Architecture Overview

### Design Principles

The Digital FTE CLI follows these core principles:

1. **Command Composition** - Commands are organized in hierarchical groups
2. **Separation of Concerns** - Business logic separate from CLI presentation
3. **Rich User Experience** - Styled output using Rich library
4. **Comprehensive Testing** - Every command has integration tests
5. **Error-First Design** - Explicit error handling with custom exceptions
6. **Configuration Management** - Centralized config with multiple sources

### Technology Stack

- **Click** - Command-line interface framework
- **Rich** - Terminal styling and formatting
- **Pydantic** - Data validation and settings
- **PyYAML** - Configuration file parsing
- **Pytest** - Testing framework
- **PM2** - Process management (via subprocess)

### Architecture Layers

```
┌─────────────────────────────────────┐
│   CLI Layer (src/cli/)              │
│   - Click commands                  │
│   - Rich formatting                 │
│   - User interaction                │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│   Service Layer (src/cli/)          │
│   - Business logic                  │
│   - Validation                      │
│   - External integrations           │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│   Data Layer (vault, config)        │
│   - Filesystem operations           │
│   - Configuration management        │
│   - State persistence               │
└─────────────────────────────────────┘
```

---

## Project Structure

```
src/cli/
├── __init__.py                 # Package initialization
├── main.py                     # CLI entry point, main group
├── config.py                   # Configuration management
├── errors.py                   # Custom exception hierarchy
├── utils.py                    # Shared utility functions
├── checkpoint.py               # State tracking and persistence
│
├── init.py                     # fte init command
├── status.py                   # fte status command
├── vault.py                    # fte vault group (list, create, move)
├── watcher.py                  # fte watcher group (start, stop, status, logs)
├── mcp.py                      # fte mcp group (list, add, test, tools)
├── approval.py                 # fte approval group (pending, review)
└── briefing.py                 # fte briefing group (generate, view)

tests/cli/
├── test_vault.py               # Vault command tests
├── test_watcher.py             # Watcher command tests
├── test_mcp.py                 # MCP command tests
├── test_approval.py            # Approval command tests
├── test_briefing.py            # Briefing command tests
└── test_e2e.py                 # End-to-end integration tests

docs/cli/
├── user-guide.md               # User-facing documentation
└── developer-guide.md          # This document
```

---

## Core Components

### 1. Main CLI Group (`src/cli/main.py`)

The main CLI entry point using Click's group functionality.

**Key Features:**
- Top-level `@click.group()` decorator
- Sub-command registration with `cli.add_command()`
- Global options (--help, --version)
- Error handling wrapper

**Example Structure:**
```python
@click.group()
@click.version_option(version="1.0.0")
@click.pass_context
def cli(ctx):
    """Digital FTE CLI"""
    ctx.ensure_object(dict)

# Register sub-commands
from cli.vault import vault_group
cli.add_command(vault_group)
```

### 2. Command Groups

Each feature area is a separate command group (e.g., `vault`, `watcher`, `mcp`).

**Command Group Pattern:**
```python
import click
from rich.console import Console

console = Console()

@click.group(name="feature")
def feature_group():
    """Feature commands"""
    pass

@feature_group.command(name="action")
@click.argument("arg")
@click.option("--opt", help="Option help")
@click.pass_context
def feature_action_command(ctx, arg, opt):
    """Action description"""
    try:
        # 1. Validate inputs
        # 2. Perform action
        # 3. Display results with Rich
        # 4. Handle errors
        pass
    except CustomError as e:
        display_error(e, verbose=ctx.obj.get("verbose", False))
        ctx.exit(1)
```

### 3. Configuration Management (`src/cli/config.py`)

Centralized configuration using Pydantic models.

**Configuration Sources (Priority Order):**
1. Command-line arguments (`--vault-path`)
2. Environment variables (`FTE_VAULT_PATH`)
3. Config file (`~/.ai_employee_vault/config/config.yaml`)
4. Defaults

**Config Model:**
```python
from pydantic import BaseModel, Field

class VaultConfig(BaseModel):
    path: Path = Field(default=Path.home() / ".ai_employee_vault")
    auto_archive_days: int = 30

class Config(BaseModel):
    vault: VaultConfig
    # ... other sections

def get_config() -> Config:
    """Load configuration from all sources"""
    pass
```

### 4. Error Handling (`src/cli/errors.py`)

Custom exception hierarchy for explicit error handling.

**Exception Hierarchy:**
```
FTEError (base)
├── VaultError
│   ├── VaultNotFoundError
│   ├── VaultInvalidError
│   └── VaultOperationError
├── WatcherError
│   ├── WatcherNotFoundError
│   ├── PM2NotFoundError
│   └── WatcherValidationError
├── MCPError
│   ├── MCPNotFoundError
│   ├── MCPInvalidURLError
│   └── MCPHealthCheckError
├── ApprovalError
│   ├── ApprovalNotFoundError
│   ├── ApprovalExpiredError
│   └── ApprovalInvalidNonceError
└── BriefingError
    ├── BriefingNotFoundError
    └── PDFGenerationError
```

**Usage:**
```python
class CustomError(FTEError):
    """Custom error with context"""
    def __init__(self, detail: str):
        super().__init__(f"Custom error: {detail}")

# In command
try:
    if not valid:
        raise CustomError("Invalid input")
except CustomError as e:
    display_error(e, verbose=ctx.obj.get("verbose", False))
    ctx.exit(1)
```

### 5. Utilities (`src/cli/utils.py`)

Shared utility functions for common operations.

**Key Functions:**
```python
def display_success(message: str) -> None:
    """Display success message with ✓ icon"""

def display_error(error: Exception, verbose: bool = False) -> None:
    """Display error with optional traceback"""

def display_info(message: str) -> None:
    """Display info message with ℹ icon"""

def display_warning(message: str) -> None:
    """Display warning message"""

def resolve_vault_path(vault_path: Optional[Path] = None) -> Path:
    """Resolve vault path from multiple sources"""

def validate_vault_or_error(vault_path: Path) -> None:
    """Validate vault structure, raise on error"""
```

### 6. Checkpoint System (`src/cli/checkpoint.py`)

Tracks system state and command usage.

**Checkpoint Data:**
```python
class Checkpoint(BaseModel):
    vault: VaultCheckpoint
    watchers: WatcherCheckpoint
    mcp: MCPCheckpoint
    approvals: ApprovalCheckpoint
    briefings: BriefingCheckpoint
    usage: UsageCheckpoint

def get_checkpoint_manager() -> CheckpointManager:
    """Get singleton checkpoint manager"""

# Usage in commands
checkpoint_manager = get_checkpoint_manager()
checkpoint_manager.update_vault(action="create")
```

---

## Adding New Commands

### Step 1: Create Command Module

Create a new file `src/cli/my_feature.py`:

```python
"""
My Feature Commands

Description of what this feature does.
"""

from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from cli.config import get_config
from cli.errors import MyFeatureError
from cli.utils import (
    display_error,
    display_info,
    display_success,
    resolve_vault_path,
    validate_vault_or_error,
)

console = Console()


# Business logic functions
def my_business_logic(param: str) -> str:
    """
    Implement core business logic here.

    Args:
        param: Parameter description

    Returns:
        Result description

    Raises:
        MyFeatureError: When something goes wrong
    """
    # Implementation
    pass


# CLI Command Group
@click.group(name="myfeature")
def myfeature_group():
    """My feature commands"""
    pass


@myfeature_group.command(name="action")
@click.argument("arg")
@click.option(
    "--vault-path",
    type=click.Path(path_type=Path),
    help="Path to vault (overrides config)",
)
@click.pass_context
def myfeature_action_command(
    ctx: click.Context,
    arg: str,
    vault_path: Optional[Path]
):
    """
    Perform action on my feature.

    Examples:
        fte myfeature action value
        fte myfeature action value --vault-path ~/vault
    """
    try:
        # 1. Resolve configuration
        if vault_path is None:
            vault_path = resolve_vault_path()

        # 2. Validate vault
        validate_vault_or_error(vault_path)

        # 3. Perform business logic
        display_info("Processing...")
        result = my_business_logic(arg)

        # 4. Display results
        display_success(f"Action completed: {result}")

    except MyFeatureError as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)
```

### Step 2: Add Custom Errors

Add to `src/cli/errors.py`:

```python
class MyFeatureError(FTEError):
    """Base exception for my feature errors"""
    pass

class MyFeatureNotFoundError(MyFeatureError):
    """Raised when resource not found"""
    def __init__(self, resource_id: str):
        super().__init__(f"Resource not found: {resource_id}")
```

### Step 3: Register Command Group

In `src/cli/main.py`:

```python
# Import my feature command group
from cli.my_feature import myfeature_group
cli.add_command(myfeature_group)
```

### Step 4: Add Tests

Create `tests/cli/test_my_feature.py`:

```python
"""
Integration tests for fte myfeature commands.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.my_feature import (
    myfeature_action_command,
    myfeature_group,
    my_business_logic,
)


class TestMyBusinessLogic:
    """Test business logic functions"""

    def test_my_business_logic_success(self):
        """Test successful business logic"""
        result = my_business_logic("test")
        assert result == "expected"

    def test_my_business_logic_error(self):
        """Test business logic error handling"""
        with pytest.raises(MyFeatureError):
            my_business_logic("invalid")


class TestMyFeatureAction:
    """Test fte myfeature action command"""

    def test_myfeature_action_help(self):
        """Test command help"""
        runner = CliRunner()
        result = runner.invoke(myfeature_action_command, ['--help'])

        assert result.exit_code == 0
        assert "Perform action" in result.output

    def test_myfeature_action_success(self, tmp_path):
        """Test successful action"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        # Create required folders
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        result = runner.invoke(
            myfeature_action_command,
            ['test_arg', '--vault-path', str(vault_path)]
        )

        assert result.exit_code == 0
        assert "Action completed" in result.output

    def test_myfeature_action_invalid_vault(self, tmp_path):
        """Test action with invalid vault"""
        runner = CliRunner()
        invalid_vault = tmp_path / "invalid"
        invalid_vault.mkdir()

        result = runner.invoke(
            myfeature_action_command,
            ['test_arg', '--vault-path', str(invalid_vault)]
        )

        assert result.exit_code == 1


class TestMyFeatureGroup:
    """Test myfeature command group"""

    def test_myfeature_group_help(self):
        """Test command group help"""
        runner = CliRunner()
        result = runner.invoke(myfeature_group, ['--help'])

        assert result.exit_code == 0
        assert "myfeature" in result.output.lower()
```

### Step 5: Update Documentation

Add command documentation to:
- `docs/cli/user-guide.md` - User-facing examples
- `README.md` - Brief mention in features list

---

## Testing Guidelines

### Test Structure

Each command module should have a corresponding test file with these test classes:

1. **Business Logic Tests** - Test pure functions
2. **Command Tests** - Test CLI commands with CliRunner
3. **Integration Tests** - Test command interactions

### Testing Patterns

#### 1. Using CliRunner

```python
from click.testing import CliRunner

def test_command():
    runner = CliRunner()
    result = runner.invoke(my_command, ['arg', '--option', 'value'])

    assert result.exit_code == 0
    assert "expected output" in result.output
```

#### 2. Mocking External Dependencies

```python
from unittest.mock import patch, MagicMock

@patch('cli.my_feature.subprocess.run')
def test_with_subprocess(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="output")

    result = my_function()

    mock_run.assert_called_once_with(['command', 'arg'])
    assert result == "expected"
```

#### 3. Using Temporary Paths

```python
def test_with_vault(tmp_path):
    vault_path = tmp_path / "vault"
    vault_path.mkdir()

    # Create vault structure
    for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
        (vault_path / folder).mkdir()

    # Test command with vault
    runner = CliRunner()
    result = runner.invoke(command, ['--vault-path', str(vault_path)])

    assert result.exit_code == 0
```

#### 4. Testing Interactive Prompts

```python
from rich.prompt import Prompt, Confirm

@patch('cli.my_feature.Prompt.ask')
@patch('cli.my_feature.Confirm.ask')
def test_interactive(mock_confirm, mock_prompt):
    mock_prompt.return_value = "user input"
    mock_confirm.return_value = True

    result = interactive_function()

    mock_prompt.assert_called()
    mock_confirm.assert_called()
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/cli/test_my_feature.py

# Run with coverage
pytest --cov=src/cli --cov-report=html

# Run with verbose output
pytest -v

# Run specific test
pytest tests/cli/test_my_feature.py::TestClass::test_method
```

### Test Coverage Goals

- **Business Logic**: 100% coverage
- **CLI Commands**: 90%+ coverage
- **Error Handling**: All error paths tested
- **Integration**: End-to-end happy paths tested

---

## Error Handling

### Error Handling Pattern

```python
try:
    # 1. Validate inputs
    if not valid_input(arg):
        raise MyFeatureValidationError("Invalid input")

    # 2. Perform operation
    result = perform_operation(arg)

    # 3. Display success
    display_success(f"Operation completed: {result}")

except MyFeatureError as e:
    # Handle known errors
    display_error(e, verbose=ctx.obj.get("verbose", False))
    ctx.exit(1)
except Exception as e:
    # Handle unexpected errors
    display_error(e, verbose=ctx.obj.get("verbose", False))
    ctx.exit(1)
```

### Exit Codes

Follow standard Unix exit codes:

- **0** - Success
- **1** - General error
- **2** - Misuse of command (invalid arguments)
- **130** - Terminated by Ctrl+C (KeyboardInterrupt)

### Verbose Error Output

When `--verbose` flag is set, display full traceback:

```python
def display_error(error: Exception, verbose: bool = False) -> None:
    """Display error with optional traceback"""
    console.print(f"[red]Error:[/red] {error}")

    if verbose:
        console.print("\n[dim]Traceback:[/dim]")
        console.print_exception()
```

---

## Styling and UX

### Rich Library Usage

#### 1. Styled Text

```python
from rich.console import Console

console = Console()

# Success (green with ✓)
console.print("[green]✓[/green] Operation successful")

# Error (red with ✗)
console.print("[red]✗[/red] Operation failed")

# Info (blue with ℹ)
console.print("[blue]ℹ[/blue] Processing...")

# Warning (yellow with ⚠)
console.print("[yellow]⚠[/yellow] Warning message")
```

#### 2. Tables

```python
from rich.table import Table

table = Table(title="My Table", show_header=True, header_style="bold cyan")
table.add_column("Column 1", style="bold")
table.add_column("Column 2")
table.add_row("Value 1", "Value 2")

console.print(table)
```

#### 3. Progress Bars

```python
from rich.progress import Progress, SpinnerColumn, TextColumn

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    console=console,
) as progress:
    task_id = progress.add_task("Processing...", total=None)
    # Do work
    progress.update(task_id, description="Complete!")
```

#### 4. Panels

```python
from rich.panel import Panel

panel = Panel(
    "Content here",
    title="[bold]Panel Title[/bold]",
    border_style="cyan",
)
console.print(panel)
```

#### 5. Tree Views

```python
from rich.tree import Tree

tree = Tree("Root")
branch = tree.add("Branch 1")
branch.add("Leaf 1")
branch.add("Leaf 2")

console.print(tree)
```

### UX Guidelines

1. **Provide Feedback** - Always acknowledge user actions
2. **Clear Messages** - Use concise, actionable language
3. **Progressive Disclosure** - Show details only when needed (--verbose)
4. **Helpful Errors** - Include suggestions for resolution
5. **Consistent Formatting** - Use same patterns across commands
6. **Interactive When Appropriate** - Prompt for confirmation on destructive actions

---

## Contributing

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd digital-fte

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest
```

### Code Style

- **Formatter**: Black (line length 100)
- **Linter**: Ruff
- **Type Checker**: mypy (when used)
- **Docstrings**: Google style

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/
```

### Pull Request Process

1. **Create Feature Branch** - `git checkout -b feature/my-feature`
2. **Write Code** - Follow coding standards
3. **Add Tests** - Maintain coverage above 80%
4. **Update Docs** - Add to user-guide.md if needed
5. **Run Tests** - `pytest` must pass
6. **Commit** - Use conventional commits
7. **Push** - `git push origin feature/my-feature`
8. **Create PR** - Describe changes and link issues

### Conventional Commits

```
feat: Add new command for X
fix: Resolve issue with Y
docs: Update user guide for Z
test: Add tests for A
refactor: Simplify B logic
chore: Update dependencies
```

### Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create git tag: `git tag v1.0.0`
4. Push tag: `git push origin v1.0.0`
5. Build package: `python -m build`
6. Publish: `twine upload dist/*`

---

## Performance Considerations

### Optimization Strategies

1. **Lazy Loading** - Import modules only when needed
2. **Caching** - Cache expensive operations (MCP tool discovery)
3. **Parallel Execution** - Use concurrent health checks
4. **Minimal Dependencies** - Keep startup time low

### Performance Targets

- **Startup Time**: < 100ms for simple commands
- **Status Check**: < 2s for full system status
- **Vault Operations**: < 50ms for list operations

### Profiling

```bash
# Profile command execution
python -m cProfile -o profile.stats -m cli.main status

# Analyze results
python -m pstats profile.stats
```

---

## Security Considerations

### Sensitive Data

- **Never log secrets** - Redact tokens, passwords, API keys
- **Secure storage** - Use proper file permissions (0600)
- **Environment variables** - Prefer over config files for secrets

### Input Validation

- **Validate all inputs** - URLs, file paths, user input
- **Sanitize output** - Prevent injection attacks
- **Limit operations** - Rate limiting on external calls

### Approval Security

- **Nonce validation** - Prevent replay attacks
- **Integrity checks** - Detect tampering
- **Time limits** - Expire old approvals
- **Audit logging** - Track all decisions

---

## Appendix

### Useful Commands

```bash
# Clean build artifacts
rm -rf build/ dist/ *.egg-info

# Regenerate requirements
pip freeze > requirements.txt

# Check outdated packages
pip list --outdated

# Run type checking
mypy src/cli/

# Generate documentation
sphinx-build -b html docs/ docs/_build/
```

### Resources

- **Click Documentation**: https://click.palletsprojects.com/
- **Rich Documentation**: https://rich.readthedocs.io/
- **Pydantic Documentation**: https://docs.pydantic.dev/
- **Pytest Documentation**: https://docs.pytest.org/

---

**Last Updated:** 2026-01-29
**Version:** 1.0.0
