# Digital FTE (Full-Time Employee) AI Assistant

**A file-driven AI assistant with Command-Line Interface for task management, monitoring, and executive briefings.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## 🚀 Overview

Digital FTE is an intelligent AI assistant system that operates through a file-driven control plane. It provides:

- **📁 Vault Management** - Organize tasks in an Obsidian-compatible vault
- **👀 Event Watchers** - Monitor Gmail, WhatsApp, and filesystem events
- **🔗 MCP Integration** - Connect external services via Model Context Protocol
- **✅ Approval Workflows** - Human-in-the-loop for high-risk actions
- **📊 CEO Briefings** - Automated weekly executive summaries

---

## 📋 Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [CLI Commands](#-cli-commands)
- [Documentation](#-documentation)
- [Architecture](#-architecture)
- [Development](#-development)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

### Command-Line Interface

```bash
fte init                        # Initialize AI Employee vault
fte status                      # Show system health
fte vault list inbox            # List tasks
fte watcher start gmail         # Start Gmail watcher
fte mcp add github-api URL      # Add MCP server
fte approval review ID          # Review approval request
fte briefing generate --pdf     # Generate CEO briefing
```

### Core Capabilities

- **🗂️ Task Management**: Organize work in inbox/needs_action/done folders
- **⚡ Real-time Monitoring**: Watch for new emails, messages, and file changes
- **🔌 External Integrations**: Connect APIs and services via MCP servers
- **🔒 Security Controls**: Approval system with nonce validation and expiry
- **📈 Executive Reporting**: Auto-generate weekly briefings from completed tasks
- **🎨 Rich CLI UX**: Styled terminal output with tables, panels, and progress bars

---

## 📥 Installation

### Prerequisites

- **Python 3.11+**
- **PM2** (for watcher daemons): `npm install -g pm2`
- **wkhtmltopdf** (optional, for PDF briefings): `apt-get install wkhtmltopdf`

### From Source

```bash
# Clone repository
git clone <repository-url>
cd digital-fte

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package
pip install -e .

# Verify installation
fte --version
```

### Shell Completion (Optional)

**Bash:**
```bash
echo 'source /path/to/scripts/completion/fte-completion.bash' >> ~/.bashrc
source ~/.bashrc
```

**Zsh:**
```bash
echo 'source /path/to/scripts/completion/fte-completion.zsh' >> ~/.zshrc
source ~/.zshrc
```

---

## 🎯 Quick Start

### 1. Initialize Your Vault

```bash
fte init
```

This creates:
```
~/.ai_employee_vault/
├── Inbox/           # New tasks
├── Needs_Action/    # Tasks requiring attention
├── Done/            # Completed tasks
├── Approvals/       # Pending approvals
├── Briefings/       # Generated reports
└── config/
    └── mcp_servers.yaml
```

### 2. Check System Status

```bash
fte status
```

### 3. Create Your First Task

```bash
fte vault create --task "Review Q1 reports" --priority high
```

### 4. Start Monitoring

```bash
fte watcher start gmail
fte watcher status
```

### 5. Generate Weekly Briefing

```bash
fte briefing generate --pdf
```

---

## 🎮 CLI Commands

### Global Options

```bash
--verbose, -v     # Enable verbose logging (DEBUG level)
--quiet, -q       # Suppress non-error output (ERROR level only)
--no-color        # Disable colored output (for CI/CD)
--help            # Show command help
```

### Core Commands

#### `fte init` - Initialize Vault

```bash
fte init [--vault-path PATH] [--force]
```

Create a new AI Employee vault with proper folder structure.

#### `fte status` - System Status

```bash
fte status [--vault-path PATH] [--json]
```

Display comprehensive system health including:
- Vault structure validation
- Watcher status (Gmail, WhatsApp, Filesystem)
- MCP server health checks
- Pending approval count

#### `fte vault` - Vault Management

```bash
fte vault list FOLDER [--vault-path PATH]
fte vault create [--task TEXT] [--priority high|medium|low]
fte vault move TASK_FILE FROM_FOLDER TO_FOLDER
```

Manage tasks across vault folders (inbox, needs_action, done).

#### `fte watcher` - Watcher Lifecycle

```bash
fte watcher start NAME [--vault-path PATH]
fte watcher stop NAME
fte watcher status
fte watcher logs NAME [--tail N] [--follow]
```

Control daemon processes that monitor external events (gmail, whatsapp, filesystem).

#### `fte mcp` - MCP Server Management

```bash
fte mcp list [--vault-path PATH]
fte mcp add NAME URL [--auth-file PATH]
fte mcp test NAME [--timeout N]
fte mcp tools NAME
```

Manage Model Context Protocol (MCP) server integrations.

#### `fte approval` - Approval Workflow

```bash
fte approval pending [--vault-path PATH]
fte approval review APPROVAL_ID
```

Review and approve/reject high-risk actions with interactive prompts.

#### `fte briefing` - CEO Briefings

```bash
fte briefing generate [--days N] [--pdf]
fte briefing view
```

Generate and view weekly executive summary reports.

---

## 📚 Documentation

- **[CLI User Guide](docs/cli/user-guide.md)** - Complete command reference with examples
- **[Developer Guide](docs/cli/developer-guide.md)** - Architecture and contribution guidelines
- **[Feature Specifications](specs/)** - Detailed feature specs and implementation plans

---

## 🏗️ Architecture

### Component Overview

```
┌─────────────────────────────────────┐
│   CLI Layer (src/cli/)              │
│   - Click commands                  │
│   - Rich formatting                 │
│   - User interaction                │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│   Service Layer                     │
│   - Business logic                  │
│   - External integrations           │
│   - Validation                      │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│   Data Layer                        │
│   - File-based vault                │
│   - Configuration (YAML)            │
│   - State persistence (JSON)        │
└─────────────────────────────────────┘
```

### Technology Stack

- **CLI Framework**: Click 8.x
- **Terminal UI**: Rich 14.x
- **Data Validation**: Pydantic 2.x
- **Process Management**: PM2 (via subprocess)
- **Configuration**: PyYAML
- **Testing**: Pytest + Coverage
- **HTTP Client**: Requests

### Project Structure

```
digital-fte/
├── src/
│   ├── cli/               # CLI commands and utilities
│   ├── control_plane/     # State machine and models
│   ├── logging/           # Structured logging
│   └── utils/             # Shared utilities
├── tests/                 # Integration tests
├── docs/                  # Documentation
├── scripts/               # Shell completion, utilities
└── specs/                 # Feature specifications
```

---

## 💻 Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run with coverage
pytest --cov=src/cli --cov-report=html

# Format code
black src/ tests/

# Lint code
ruff check src/ tests/
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/cli/test_vault.py

# Run with verbose output
pytest -v

# Run specific test
pytest tests/cli/test_vault.py::TestVaultList::test_list_inbox
```

### Adding New Commands

1. Create command module in `src/cli/my_feature.py`
2. Define Click command group and commands
3. Register in `src/cli/main.py`
4. Add tests in `tests/cli/test_my_feature.py`
5. Update documentation in `docs/cli/user-guide.md`

See [Developer Guide](docs/cli/developer-guide.md) for detailed instructions.

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/my-feature`
3. **Make changes and add tests**
4. **Run tests**: `pytest`
5. **Format code**: `black src/ tests/`
6. **Commit changes**: Use [conventional commits](https://www.conventionalcommits.org/)
7. **Push to branch**: `git push origin feature/my-feature`
8. **Create Pull Request**

### Coding Standards

- **Style**: Black formatter (line length 100)
- **Linting**: Ruff
- **Docstrings**: Google style
- **Test Coverage**: Maintain above 80%
- **Type Hints**: Preferred but not required

---

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.

---

## 🔒 Security

### Reporting Vulnerabilities

Please report security vulnerabilities to [security@example.com](mailto:security@example.com).

### Security Features

- **Approval Nonces**: Prevent replay attacks
- **Integrity Validation**: Detect file tampering
- **Time-Limited Approvals**: Automatic expiry
- **Audit Logging**: Track all approval decisions
- **No Secrets in Logs**: Automatic redaction

### Security Audit

Regular dependency audits with `pip-audit`:
```bash
pip-audit
```

**Last Audit**: 2026-01-29 - No known vulnerabilities

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Click** - Excellent CLI framework
- **Rich** - Beautiful terminal formatting
- **PM2** - Reliable process management
- **Model Context Protocol** - Extensible integration standard

---

## 📧 Support

- **Documentation**: [docs/cli/](docs/cli/)
- **Issues**: Report bugs and feature requests on GitHub
- **Discussions**: Ask questions in GitHub Discussions

---

## 🗺️ Roadmap

### Current (v1.0.0)
- ✅ CLI foundation with 7 command groups
- ✅ Vault management and task organization
- ✅ Watcher lifecycle (Gmail, WhatsApp, Filesystem)
- ✅ MCP server integration
- ✅ Approval workflows with security
- ✅ CEO briefing generation

### Future
- 🔄 Web dashboard for vault visualization
- 🔄 AI agent autonomous mode
- 🔄 Multi-user support with RBAC
- 🔄 Plugin system for custom integrations
- 🔄 Cloud sync for vault backup

---

**Built with ❤️ using Python, Click, and Rich**

