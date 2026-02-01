"""
Integration tests for fte mcp commands.

Tests MCP server management including list, add, test, and tools.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml
from click.testing import CliRunner

from cli.mcp import (
    get_mcp_registry_path,
    health_check_server,
    load_mcp_registry,
    mcp_add_command,
    mcp_group,
    mcp_list_command,
    mcp_test_command,
    mcp_tools_command,
    save_mcp_registry,
    validate_url,
)


class TestURLValidation:
    """Test URL validation"""

    def test_validate_valid_http_url(self):
        """Test validation passes for valid HTTP URL"""
        assert validate_url("http://example.com") is True
        assert validate_url("http://localhost:8080") is True

    def test_validate_valid_https_url(self):
        """Test validation passes for valid HTTPS URL"""
        assert validate_url("https://example.com") is True
        assert validate_url("https://api.example.com:443") is True

    def test_validate_invalid_scheme(self):
        """Test validation fails for invalid scheme"""
        from cli.errors import MCPInvalidURLError

        with pytest.raises(MCPInvalidURLError):
            validate_url("ftp://example.com")

        with pytest.raises(MCPInvalidURLError):
            validate_url("ws://example.com")

    def test_validate_no_hostname(self):
        """Test validation fails when hostname missing"""
        from cli.errors import MCPInvalidURLError

        with pytest.raises(MCPInvalidURLError):
            validate_url("http://")

    def test_validate_invalid_port(self):
        """Test validation fails for invalid port"""
        from cli.errors import MCPInvalidURLError

        with pytest.raises(MCPInvalidURLError):
            validate_url("http://example.com:99999")


class TestMCPRegistry:
    """Test MCP registry operations"""

    def test_load_registry_empty(self, tmp_path, monkeypatch):
        """Test loading registry when file doesn't exist"""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

        registry = load_mcp_registry()

        assert registry == {"servers": {}}

    def test_save_and_load_registry(self, tmp_path, monkeypatch):
        """Test saving and loading registry"""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

        # Save registry
        test_registry = {
            "servers": {
                "test-server": {
                    "url": "https://example.com",
                    "auth": False,
                }
            }
        }
        save_mcp_registry(test_registry)

        # Load registry
        loaded = load_mcp_registry()

        assert loaded == test_registry

    def test_load_registry_invalid_yaml(self, tmp_path, monkeypatch):
        """Test loading registry with invalid YAML"""
        from cli.errors import MCPRegistryError

        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

        # Create invalid YAML file
        registry_path = get_mcp_registry_path()
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text("invalid: yaml: content:")

        with pytest.raises(MCPRegistryError):
            load_mcp_registry()


class TestMCPList:
    """Test fte mcp list command"""

    def test_mcp_list_help(self):
        """Test mcp list command help"""
        runner = CliRunner()
        result = runner.invoke(mcp_list_command, ['--help'])

        assert result.exit_code == 0
        assert "List all MCP servers" in result.output

    @patch('cli.mcp.load_mcp_registry')
    def test_mcp_list_empty_registry(self, mock_load):
        """Test list with no servers configured"""
        runner = CliRunner()

        # Mock empty registry
        mock_load.return_value = {"servers": {}}

        result = runner.invoke(mcp_list_command)

        assert result.exit_code == 0
        assert "No MCP servers" in result.output

    @patch('cli.mcp.health_check_server')
    @patch('cli.mcp.load_mcp_registry')
    def test_mcp_list_with_servers(self, mock_load, mock_health):
        """Test list with configured servers"""
        runner = CliRunner()

        # Mock registry with servers
        mock_load.return_value = {
            "servers": {
                "test-server": {
                    "url": "https://example.com",
                    "auth": True,
                    "tools_count": 5
                }
            }
        }

        # Mock health check
        mock_health.return_value = {
            "status": "healthy",
            "code": 200,
            "message": "Server responding"
        }

        result = runner.invoke(mcp_list_command)

        assert result.exit_code == 0
        assert "test-server" in result.output
        assert "example.com" in result.output


class TestMCPAdd:
    """Test fte mcp add command"""

    def test_mcp_add_help(self):
        """Test mcp add command help"""
        runner = CliRunner()
        result = runner.invoke(mcp_add_command, ['--help'])

        assert result.exit_code == 0
        assert "Add new MCP server" in result.output
        assert "--auth-file" in result.output

    @patch('cli.mcp.get_checkpoint_manager')
    @patch('cli.mcp.save_mcp_registry')
    @patch('cli.mcp.load_mcp_registry')
    def test_mcp_add_success(
        self,
        mock_load,
        mock_save,
        mock_checkpoint
    ):
        """Test adding MCP server successfully"""
        runner = CliRunner()

        # Mock empty registry
        mock_load.return_value = {"servers": {}}

        # Mock checkpoint manager
        mock_mgr = MagicMock()
        mock_checkpoint.return_value = mock_mgr

        result = runner.invoke(
            mcp_add_command,
            ['test-server', 'https://example.com']
        )

        assert result.exit_code == 0
        assert "added successfully" in result.output.lower()
        mock_save.assert_called_once()

    def test_mcp_add_invalid_url(self):
        """Test add fails with invalid URL"""
        runner = CliRunner()

        result = runner.invoke(
            mcp_add_command,
            ['test-server', 'ftp://invalid.com']
        )

        assert result.exit_code == 1
        assert "Invalid URL scheme" in result.output

    @patch('cli.mcp.get_checkpoint_manager')
    @patch('cli.mcp.save_mcp_registry')
    @patch('cli.mcp.load_mcp_registry')
    def test_mcp_add_with_auth_file(
        self,
        mock_load,
        mock_save,
        mock_checkpoint,
        tmp_path
    ):
        """Test adding MCP server with auth file"""
        runner = CliRunner()

        # Mock empty registry
        mock_load.return_value = {"servers": {}}

        # Mock checkpoint manager
        mock_mgr = MagicMock()
        mock_checkpoint.return_value = mock_mgr

        # Create auth file
        auth_file = tmp_path / "auth.json"
        auth_file.write_text('{"api_key": "test"}')

        result = runner.invoke(
            mcp_add_command,
            ['test-server', 'https://example.com', '--auth-file', str(auth_file)]
        )

        assert result.exit_code == 0
        assert "added successfully" in result.output.lower()

    @patch('cli.mcp.get_checkpoint_manager')
    @patch('cli.mcp.save_mcp_registry')
    @patch('cli.mcp.load_mcp_registry')
    def test_mcp_add_duplicate_server(
        self,
        mock_load,
        mock_save,
        mock_checkpoint
    ):
        """Test adding duplicate server updates configuration"""
        runner = CliRunner()

        # Mock registry with existing server
        mock_load.return_value = {
            "servers": {
                "test-server": {
                    "url": "https://old.com",
                    "auth": False
                }
            }
        }

        # Mock checkpoint manager
        mock_mgr = MagicMock()
        mock_checkpoint.return_value = mock_mgr

        result = runner.invoke(
            mcp_add_command,
            ['test-server', 'https://new.com']
        )

        assert result.exit_code == 0
        assert "already exists" in result.output.lower()


class TestMCPTest:
    """Test fte mcp test command"""

    def test_mcp_test_help(self):
        """Test mcp test command help"""
        runner = CliRunner()
        result = runner.invoke(mcp_test_command, ['--help'])

        assert result.exit_code == 0
        assert "Test MCP server connection" in result.output
        assert "--timeout" in result.output

    @patch('cli.mcp.health_check_server')
    @patch('cli.mcp.load_mcp_registry')
    def test_mcp_test_success(self, mock_load, mock_health):
        """Test successful server health check"""
        runner = CliRunner()

        # Mock registry with server
        mock_load.return_value = {
            "servers": {
                "test-server": {
                    "url": "https://example.com",
                    "auth": False
                }
            }
        }

        # Mock healthy response
        mock_health.return_value = {
            "status": "healthy",
            "code": 200,
            "message": "Server responding"
        }

        result = runner.invoke(mcp_test_command, ['test-server'])

        assert result.exit_code == 0
        assert "healthy" in result.output.lower()

    @patch('cli.mcp.load_mcp_registry')
    def test_mcp_test_server_not_found(self, mock_load):
        """Test when server not found in registry"""
        runner = CliRunner()

        # Mock empty registry
        mock_load.return_value = {"servers": {}}

        result = runner.invoke(mcp_test_command, ['nonexistent'])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    @patch('cli.mcp.health_check_server')
    @patch('cli.mcp.load_mcp_registry')
    def test_mcp_test_unhealthy(self, mock_load, mock_health):
        """Test when server is unhealthy"""
        runner = CliRunner()

        # Mock registry with server
        mock_load.return_value = {
            "servers": {
                "test-server": {
                    "url": "https://example.com",
                    "auth": False
                }
            }
        }

        # Mock unhealthy response
        mock_health.return_value = {
            "status": "unhealthy",
            "message": "Connection timeout"
        }

        result = runner.invoke(mcp_test_command, ['test-server'])

        assert result.exit_code == 1
        assert "unhealthy" in result.output.lower()


class TestMCPTools:
    """Test fte mcp tools command"""

    def test_mcp_tools_help(self):
        """Test mcp tools command help"""
        runner = CliRunner()
        result = runner.invoke(mcp_tools_command, ['--help'])

        assert result.exit_code == 0
        assert "List available tools" in result.output

    @patch('cli.mcp.save_mcp_registry')
    @patch('cli.mcp.get_server_tools')
    @patch('cli.mcp.load_mcp_registry')
    def test_mcp_tools_success(
        self,
        mock_load,
        mock_get_tools,
        mock_save
    ):
        """Test listing server tools successfully"""
        runner = CliRunner()

        # Mock registry with server
        mock_load.return_value = {
            "servers": {
                "test-server": {
                    "url": "https://example.com",
                    "auth": False
                }
            }
        }

        # Mock tools response
        mock_get_tools.return_value = [
            {
                "name": "test_tool",
                "description": "A test tool",
                "parameters": {
                    "properties": {
                        "param1": {
                            "type": "string",
                            "description": "First parameter"
                        }
                    },
                    "required": ["param1"]
                }
            }
        ]

        result = runner.invoke(mcp_tools_command, ['test-server'])

        assert result.exit_code == 0
        assert "test_tool" in result.output

    @patch('cli.mcp.load_mcp_registry')
    def test_mcp_tools_server_not_found(self, mock_load):
        """Test when server not found in registry"""
        runner = CliRunner()

        # Mock empty registry
        mock_load.return_value = {"servers": {}}

        result = runner.invoke(mcp_tools_command, ['nonexistent'])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    @patch('cli.mcp.save_mcp_registry')
    @patch('cli.mcp.get_server_tools')
    @patch('cli.mcp.load_mcp_registry')
    def test_mcp_tools_empty(
        self,
        mock_load,
        mock_get_tools,
        mock_save
    ):
        """Test when server has no tools"""
        runner = CliRunner()

        # Mock registry with server
        mock_load.return_value = {
            "servers": {
                "test-server": {
                    "url": "https://example.com",
                    "auth": False
                }
            }
        }

        # Mock empty tools response
        mock_get_tools.return_value = []

        result = runner.invoke(mcp_tools_command, ['test-server'])

        assert result.exit_code == 0
        assert "No tools" in result.output


class TestHealthCheck:
    """Test health check functionality"""

    @patch('cli.mcp.requests.get')
    def test_health_check_success(self, mock_get):
        """Test successful health check"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = health_check_server("test", "https://example.com")

        assert result["status"] == "healthy"
        assert result["code"] == 200

    @patch('cli.mcp.requests.get')
    def test_health_check_timeout(self, mock_get):
        """Test health check timeout"""
        import requests

        # Mock timeout
        mock_get.side_effect = requests.exceptions.Timeout()

        result = health_check_server("test", "https://example.com")

        assert result["status"] == "unhealthy"
        assert "timeout" in result["message"].lower()

    @patch('cli.mcp.requests.get')
    def test_health_check_connection_error(self, mock_get):
        """Test health check connection error"""
        import requests

        # Mock connection error
        mock_get.side_effect = requests.exceptions.ConnectionError()

        result = health_check_server("test", "https://example.com")

        assert result["status"] == "unhealthy"
        assert "refused" in result["message"].lower()


class TestMCPGroup:
    """Test MCP command group"""

    def test_mcp_group_help(self):
        """Test MCP group help"""
        runner = CliRunner()
        result = runner.invoke(mcp_group, ['--help'])

        assert result.exit_code == 0
        assert "mcp" in result.output.lower()
        assert "list" in result.output
        assert "add" in result.output
        assert "test" in result.output
        assert "tools" in result.output
