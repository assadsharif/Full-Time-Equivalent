"""
MCP Server Management Commands

Commands for managing Model Context Protocol (MCP) servers including
listing, adding, testing, and discovering tools.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import click
import keyring
import keyring.errors
import requests
import yaml
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from cli.checkpoint import get_checkpoint_manager
from cli.config import get_config
from cli.errors import (
    CLIError,
    MCPError,
    MCPHealthCheckError,
    MCPInvalidURLError,
    MCPNotFoundError,
    MCPRegistryError,
)
from cli.utils import (
    display_error,
    display_info,
    display_success,
    display_warning,
)

console = Console()

# Global cache for MCP tool discovery (cache for 5 minutes)
_TOOL_CACHE: Dict[str, Dict] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes


def get_mcp_registry_path() -> Path:
    """
    Get path to MCP registry file.

    Returns:
        Path to config/mcp_servers.yaml
    """
    config = get_config()
    config_dir = Path.cwd() / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "mcp_servers.yaml"


def load_mcp_registry() -> Dict:
    """
    Load MCP server registry from YAML file.

    Returns:
        Dictionary of MCP server configurations

    Raises:
        MCPRegistryError: If registry cannot be loaded
    """
    registry_path = get_mcp_registry_path()

    if not registry_path.exists():
        # Return empty registry
        return {"servers": {}}

    try:
        with open(registry_path, "r") as f:
            data = yaml.safe_load(f)
            return data if data else {"servers": {}}
    except yaml.YAMLError as e:
        raise MCPRegistryError(f"Failed to parse registry: {e}")
    except Exception as e:
        raise MCPRegistryError(f"Failed to load registry: {e}")


def save_mcp_registry(registry: Dict) -> None:
    """
    Save MCP server registry to YAML file.

    Args:
        registry: Dictionary of MCP server configurations

    Raises:
        MCPRegistryError: If registry cannot be saved
    """
    registry_path = get_mcp_registry_path()

    try:
        with open(registry_path, "w") as f:
            yaml.dump(registry, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        raise MCPRegistryError(f"Failed to save registry: {e}")


def validate_url(url: str) -> bool:
    """
    Validate MCP server URL.

    Args:
        url: URL to validate

    Returns:
        True if valid

    Raises:
        MCPInvalidURLError: If URL is invalid
    """
    try:
        parsed = urlparse(url)

        # Check scheme
        if parsed.scheme not in ["http", "https"]:
            raise MCPInvalidURLError(
                f"Invalid URL scheme: {parsed.scheme}. Must be http or https."
            )

        # Check netloc (hostname)
        if not parsed.netloc:
            raise MCPInvalidURLError("URL must have a hostname")

        # Check port if present
        if parsed.port:
            if parsed.port < 1 or parsed.port > 65535:
                raise MCPInvalidURLError(
                    f"Invalid port number: {parsed.port}. Must be 1-65535."
                )

        return True

    except ValueError as e:
        raise MCPInvalidURLError(f"Malformed URL: {e}")


def health_check_server(name: str, url: str, timeout: int = 5) -> Dict:
    """
    Perform health check on MCP server.

    Args:
        name: Server name
        url: Server URL
        timeout: Request timeout in seconds

    Returns:
        Dict with status and optional message

    Raises:
        MCPHealthCheckError: If health check fails
    """
    try:
        # Try /health endpoint first
        health_url = f"{url.rstrip('/')}/health"
        response = requests.get(health_url, timeout=timeout)

        if response.status_code == 200:
            return {
                "status": "healthy",
                "code": response.status_code,
                "message": "Server responding",
            }
        else:
            return {
                "status": "unhealthy",
                "code": response.status_code,
                "message": f"HTTP {response.status_code}",
            }

    except requests.exceptions.Timeout:
        return {"status": "unhealthy", "message": "Connection timeout"}
    except requests.exceptions.ConnectionError:
        return {"status": "unhealthy", "message": "Connection refused"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}


def get_server_tools(
    name: str, url: str, timeout: int = 5, use_cache: bool = True
) -> List[Dict]:
    """
    Get available tools from MCP server with caching.

    Args:
        name: Server name
        url: Server URL
        timeout: Request timeout in seconds
        use_cache: Whether to use cached results (default: True)

    Returns:
        List of tool definitions

    Raises:
        MCPError: If tools cannot be retrieved
    """
    # Check cache first
    if use_cache and name in _TOOL_CACHE:
        cache_entry = _TOOL_CACHE[name]
        cache_age = time.time() - cache_entry["timestamp"]

        if cache_age < _CACHE_TTL_SECONDS:
            # Cache is still valid
            return cache_entry["tools"]

    # Cache miss or expired - fetch from server
    try:
        tools_url = f"{url.rstrip('/')}/tools"
        response = requests.get(tools_url, timeout=timeout)

        if response.status_code != 200:
            raise MCPError(f"Failed to get tools (HTTP {response.status_code})")

        data = response.json()

        # Handle different response formats
        if isinstance(data, list):
            tools = data
        elif isinstance(data, dict) and "tools" in data:
            tools = data["tools"]
        else:
            raise MCPError("Unexpected response format from /tools endpoint")

        # Store in cache
        if use_cache:
            _TOOL_CACHE[name] = {"tools": tools, "timestamp": time.time()}

        return tools

    except requests.exceptions.Timeout:
        raise MCPError("Request timeout while fetching tools")
    except requests.exceptions.ConnectionError:
        raise MCPError("Connection failed while fetching tools")
    except json.JSONDecodeError:
        raise MCPError("Invalid JSON response from /tools endpoint")
    except Exception as e:
        raise MCPError(f"Failed to get tools: {e}")


def store_credentials(name: str, auth_file: Path) -> None:
    """
    Store MCP server credentials securely.

    Args:
        name: Server name
        auth_file: Path to auth credentials file

    Raises:
        MCPError: If credentials cannot be stored
    """
    try:
        # For now, just validate the file exists
        # In production, use keyring: keyring.set_password("fte-mcp", name, auth_data)
        if not auth_file.exists():
            raise MCPError(f"Auth file not found: {auth_file}")

        # Read auth file
        with open(auth_file, "r") as f:
            auth_data = f.read()

        # Validate it's JSON or YAML
        try:
            json.loads(auth_data)
        except json.JSONDecodeError:
            try:
                yaml.safe_load(auth_data)
            except yaml.YAMLError:
                raise MCPError("Auth file must be valid JSON or YAML")

        # Store credentials in OS keyring
        try:
            keyring.set_password("fte-mcp", name, auth_data)
            display_success(f"Credentials stored securely for '{name}' in OS keyring")
        except Exception as keyring_error:
            # Fallback: warn but don't fail if keyring unavailable
            display_warning(f"Could not store in keyring ({keyring_error})")
            display_info(f"Credentials validated for '{name}' but not stored securely")

    except Exception as e:
        raise MCPError(f"Failed to store credentials: {e}")


def retrieve_credentials(name: str) -> Optional[str]:
    """
    Retrieve MCP server credentials from OS keyring.

    Args:
        name: Server name

    Returns:
        Credentials as string if found, None otherwise
    """
    try:
        credentials = keyring.get_password("fte-mcp", name)
        return credentials
    except Exception:
        return None


def delete_credentials(name: str) -> bool:
    """
    Delete MCP server credentials from OS keyring.

    Args:
        name: Server name

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        keyring.delete_password("fte-mcp", name)
        return True
    except keyring.errors.PasswordDeleteError:
        return False
    except Exception:
        return False


def display_server_list(registry: Dict) -> None:
    """
    Display MCP servers in Rich table.

    Args:
        registry: MCP server registry
    """
    servers = registry.get("servers", {})

    if not servers:
        console.print("[yellow]No MCP servers configured[/yellow]")
        console.print("\nAdd a server with: fte mcp add <name> <url>")
        return

    # Create table
    table = Table(
        title="MCP Servers",
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column("Name", style="bold")
    table.add_column("URL")
    table.add_column("Status")
    table.add_column("Tools", justify="right")
    table.add_column("Auth")

    # Add rows
    for name, config in servers.items():
        url = config.get("url", "")
        has_auth = "✓" if config.get("auth", False) else "-"

        # Perform health check
        health = health_check_server(name, url, timeout=3)
        status = health.get("status", "unknown")

        # Color code status
        if status == "healthy":
            status_colored = "[green]healthy[/green]"
        else:
            status_colored = f"[red]unhealthy[/red]"
            if health.get("message"):
                status_colored += f" ({health['message']})"

        # Get tools count (from cached value or dash)
        tools_count = str(config.get("tools_count", "-"))

        table.add_row(
            name,
            url,
            status_colored,
            tools_count,
            has_auth,
        )

    console.print(table)


def display_server_tools(name: str, tools: List[Dict]) -> None:
    """
    Display MCP server tools in Rich tree structure.

    Args:
        name: Server name
        tools: List of tool definitions
    """
    if not tools:
        console.print(f"[yellow]No tools available from '{name}'[/yellow]")
        return

    # Create tree
    tree = Tree(
        f"[bold cyan]MCP Server: {name}[/bold cyan]",
        guide_style="dim",
    )

    for tool in tools:
        tool_name = tool.get("name", "unknown")
        tool_desc = tool.get("description", "")

        # Add tool node
        tool_node = tree.add(f"[bold]{tool_name}[/bold]")

        if tool_desc:
            tool_node.add(f"[dim]{tool_desc}[/dim]")

        # Add parameters
        params = tool.get("parameters", {})
        if params:
            params_node = tool_node.add("[yellow]Parameters:[/yellow]")

            # Handle different parameter formats
            if isinstance(params, dict):
                properties = params.get("properties", {})
                required = params.get("required", [])

                for param_name, param_info in properties.items():
                    param_type = param_info.get("type", "any")
                    param_desc = param_info.get("description", "")
                    is_required = param_name in required

                    param_label = f"{param_name}: {param_type}"
                    if is_required:
                        param_label += " [red](required)[/red]"

                    param_node = params_node.add(param_label)
                    if param_desc:
                        param_node.add(f"[dim]{param_desc}[/dim]")

    console.print(tree)


# CLI Commands


@click.group(name="mcp")
def mcp_group():
    """MCP server management commands"""
    pass


@mcp_group.command(name="list")
@click.pass_context
def mcp_list_command(ctx: click.Context):
    """
    List all MCP servers.

    Displays all configured MCP servers with their status, URL,
    and available tools count.

    Examples:
        fte mcp list
    """
    try:
        display_info("Loading MCP server registry...")

        registry = load_mcp_registry()

        console.print()  # Blank line
        display_server_list(registry)

    except (MCPRegistryError, MCPError) as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)


@mcp_group.command(name="add")
@click.argument("name")
@click.argument("url")
@click.option(
    "--auth-file",
    type=click.Path(exists=True, path_type=Path),
    help="Path to authentication credentials file (JSON or YAML)",
)
@click.pass_context
def mcp_add_command(ctx: click.Context, name: str, url: str, auth_file: Optional[Path]):
    """
    Add new MCP server.

    Registers a new MCP server in the registry with optional authentication.

    Examples:
        fte mcp add my-server https://mcp.example.com
        fte mcp add secure-server https://api.example.com --auth-file auth.json
    """
    try:
        display_info(f"Adding MCP server '{name}'...")

        # Validate URL
        validate_url(url)
        display_success("✓ URL validation passed")

        # Load registry
        registry = load_mcp_registry()

        # Check if server already exists
        if name in registry.get("servers", {}):
            display_warning(f"Server '{name}' already exists. Updating configuration.")

        # Store credentials if provided
        has_auth = False
        if auth_file:
            store_credentials(name, auth_file)
            has_auth = True

        # Add to registry
        if "servers" not in registry:
            registry["servers"] = {}

        registry["servers"][name] = {
            "url": url,
            "auth": has_auth,
            "added_at": (
                click.get_current_context().obj.get("timestamp") if ctx.obj else None
            ),
        }

        # Save registry
        save_mcp_registry(registry)

        # Update checkpoint
        checkpoint_manager = get_checkpoint_manager()
        checkpoint_manager.update_mcp_server(name, "added")

        display_success(f"\n✓ MCP server '{name}' added successfully")
        display_info(f"Test connection: fte mcp test {name}")
        display_info(f"List available tools: fte mcp tools {name}")

    except (MCPInvalidURLError, MCPRegistryError, MCPError) as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)


@mcp_group.command(name="test")
@click.argument("name")
@click.option(
    "--timeout",
    default=5,
    type=int,
    help="Connection timeout in seconds (default: 5)",
)
@click.pass_context
def mcp_test_command(ctx: click.Context, name: str, timeout: int):
    """
    Test MCP server connection.

    Performs a health check on the specified MCP server to verify
    connectivity and availability.

    Examples:
        fte mcp test my-server
        fte mcp test my-server --timeout 10
    """
    try:
        display_info(f"Testing connection to '{name}'...")

        # Load registry
        registry = load_mcp_registry()
        servers = registry.get("servers", {})

        if name not in servers:
            raise MCPNotFoundError(
                f"MCP server '{name}' not found. List servers with: fte mcp list"
            )

        server_config = servers[name]
        url = server_config.get("url")

        # Perform health check
        health = health_check_server(name, url, timeout=timeout)
        status = health.get("status")

        console.print()  # Blank line

        if status == "healthy":
            display_success(f"✓ Server '{name}' is healthy")
            if health.get("code"):
                display_info(f"HTTP {health['code']}: {health.get('message', '')}")
        else:
            display_error(
                MCPHealthCheckError(
                    f"Server '{name}' is unhealthy: {health.get('message', 'Unknown error')}"
                ),
                verbose=False,
            )
            ctx.exit(1)

    except (MCPNotFoundError, MCPRegistryError, MCPHealthCheckError) as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)


@mcp_group.command(name="tools")
@click.argument("name")
@click.pass_context
def mcp_tools_command(ctx: click.Context, name: str):
    """
    List available tools from MCP server.

    Discovers and displays all tools provided by the specified MCP server
    including parameters and descriptions.

    Examples:
        fte mcp tools my-server
    """
    try:
        display_info(f"Discovering tools from '{name}'...")

        # Load registry
        registry = load_mcp_registry()
        servers = registry.get("servers", {})

        if name not in servers:
            raise MCPNotFoundError(
                f"MCP server '{name}' not found. List servers with: fte mcp list"
            )

        server_config = servers[name]
        url = server_config.get("url")

        # Get tools
        tools = get_server_tools(name, url)

        # Update registry with tools count
        server_config["tools_count"] = len(tools)
        save_mcp_registry(registry)

        console.print()  # Blank line
        display_server_tools(name, tools)

        console.print(f"\n[dim]Found {len(tools)} tools[/dim]")

    except (MCPNotFoundError, MCPRegistryError, MCPError) as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)
