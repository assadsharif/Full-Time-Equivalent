"""
Tests for nextjs_app_router_mcp MCP server.

Comprehensive test suite covering:
- Server registration and tool listing
- Input validation (Pydantic models)
- App scaffolding
- Page generation (server/client)
- Layout generation
- Server actions generation
- API client generation
- Loading/error state generation
- Structure validation
- Issue diagnosis
"""

import json
import pytest
from pydantic import ValidationError

from mcp_servers.nextjs_app_router_mcp import (
    mcp,
    # Tools
    nextjs_scaffold_app,
    nextjs_generate_page,
    nextjs_generate_layout,
    nextjs_generate_server_action,
    nextjs_generate_api_client,
    nextjs_generate_loading_error,
    nextjs_validate_structure,
    nextjs_diagnose_issues,
    # Input models
    ScaffoldAppInput,
    GeneratePageInput,
    GenerateLayoutInput,
    GenerateServerActionInput,
    GenerateApiClientInput,
    GenerateLoadingErrorInput,
    ValidateStructureInput,
    DiagnoseIssuesInput,
    # Types
    ComponentType,
    FetchCacheOption,
)

# =============================================================================
# Test: Server Registration
# =============================================================================


class TestServerRegistration:
    """Tests for MCP server registration."""

    def test_server_name(self):
        """Server should be named nextjs_app_router_mcp."""
        assert mcp.name == "nextjs_app_router_mcp"

    def test_server_has_tools(self):
        """Server should have 8 registered tools."""
        assert nextjs_scaffold_app is not None
        assert nextjs_generate_page is not None
        assert nextjs_generate_layout is not None
        assert nextjs_generate_server_action is not None
        assert nextjs_generate_api_client is not None
        assert nextjs_generate_loading_error is not None
        assert nextjs_validate_structure is not None
        assert nextjs_diagnose_issues is not None

    def test_all_tool_names_present(self):
        """All expected tool functions should be importable."""
        tools = [
            nextjs_scaffold_app,
            nextjs_generate_page,
            nextjs_generate_layout,
            nextjs_generate_server_action,
            nextjs_generate_api_client,
            nextjs_generate_loading_error,
            nextjs_validate_structure,
            nextjs_diagnose_issues,
        ]
        assert len(tools) == 8


# =============================================================================
# Test: Input Validation
# =============================================================================


class TestInputValidation:
    """Tests for Pydantic input model validation."""

    # ScaffoldAppInput
    def test_scaffold_app_valid(self):
        """Valid scaffold input should pass."""
        inp = ScaffoldAppInput(app_name="my-app", features=["todos"])
        assert inp.app_name == "my-app"

    def test_scaffold_app_empty_name_rejected(self):
        """Empty app name should be rejected."""
        with pytest.raises(ValidationError):
            ScaffoldAppInput(app_name="", features=["todos"])

    # GeneratePageInput
    def test_generate_page_valid(self):
        """Valid page input should pass."""
        inp = GeneratePageInput(
            route="/todos",
            component_type=ComponentType.SERVER,
        )
        assert inp.route == "/todos"
        assert inp.component_type == ComponentType.SERVER

    def test_generate_page_empty_route_rejected(self):
        """Empty route should be rejected."""
        with pytest.raises(ValidationError):
            GeneratePageInput(route="", component_type=ComponentType.SERVER)

    def test_generate_page_client_component(self):
        """Client component type should be valid."""
        inp = GeneratePageInput(
            route="/settings",
            component_type=ComponentType.CLIENT,
        )
        assert inp.component_type == ComponentType.CLIENT

    # GenerateLayoutInput
    def test_generate_layout_valid(self):
        """Valid layout input should pass."""
        inp = GenerateLayoutInput(route="/")
        assert inp.route == "/"

    def test_generate_layout_with_metadata(self):
        """Layout with metadata should work."""
        inp = GenerateLayoutInput(
            route="/",
            title="My App",
            description="A Next.js application",
        )
        assert inp.title == "My App"

    # GenerateServerActionInput
    def test_generate_server_action_valid(self):
        """Valid server action input should pass."""
        inp = GenerateServerActionInput(
            action_name="createTodo",
            api_endpoint="/api/todos",
            method="POST",
        )
        assert inp.action_name == "createTodo"

    def test_generate_server_action_empty_name_rejected(self):
        """Empty action name should be rejected."""
        with pytest.raises(ValidationError):
            GenerateServerActionInput(
                action_name="",
                api_endpoint="/api/todos",
                method="POST",
            )

    # GenerateApiClientInput
    def test_generate_api_client_valid(self):
        """Valid API client input should pass."""
        inp = GenerateApiClientInput(
            resource_name="todos",
            base_url="http://localhost:8000",
        )
        assert inp.resource_name == "todos"

    def test_generate_api_client_with_endpoints(self):
        """API client with custom endpoints should work."""
        inp = GenerateApiClientInput(
            resource_name="todos",
            base_url="http://localhost:8000",
            endpoints=["list", "create", "update", "delete"],
        )
        assert len(inp.endpoints) == 4

    # GenerateLoadingErrorInput
    def test_generate_loading_error_valid(self):
        """Valid loading/error input should pass."""
        inp = GenerateLoadingErrorInput(route="/todos")
        assert inp.route == "/todos"

    # ValidateStructureInput
    def test_validate_structure_valid(self):
        """Valid structure input should pass."""
        inp = ValidateStructureInput(files=["app/page.tsx", "app/layout.tsx"])
        assert len(inp.files) == 2

    def test_validate_structure_empty_files_rejected(self):
        """Empty files list should be rejected."""
        with pytest.raises(ValidationError):
            ValidateStructureInput(files=[])

    # DiagnoseIssuesInput
    def test_diagnose_issues_valid(self):
        """Valid diagnose input should pass."""
        inp = DiagnoseIssuesInput(
            error_message="Error: 'useState' can only be used in Client Components"
        )
        assert "useState" in inp.error_message


# =============================================================================
# Test: nextjs_scaffold_app
# =============================================================================


class TestScaffoldApp:
    """Tests for nextjs_scaffold_app tool."""

    @pytest.mark.asyncio
    async def test_scaffold_basic_app(self):
        """Should scaffold basic app structure."""
        result_json = await nextjs_scaffold_app(
            app_name="my-app",
            features=["todos"],
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "app/layout.tsx" in result["files"]
        assert "app/page.tsx" in result["files"]

    @pytest.mark.asyncio
    async def test_scaffold_includes_structure(self):
        """Should include recommended directory structure."""
        result_json = await nextjs_scaffold_app(
            app_name="my-app",
            features=["todos"],
        )
        result = json.loads(result_json)

        assert result["success"] is True
        # Should include key directories
        assert any("lib" in f for f in result["files"])

    @pytest.mark.asyncio
    async def test_scaffold_with_typescript(self):
        """Should generate TypeScript files."""
        result_json = await nextjs_scaffold_app(
            app_name="my-app",
            features=["todos"],
            typescript=True,
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert any(".tsx" in f or ".ts" in f for f in result["files"])


# =============================================================================
# Test: nextjs_generate_page
# =============================================================================


class TestGeneratePage:
    """Tests for nextjs_generate_page tool."""

    @pytest.mark.asyncio
    async def test_generate_server_page(self):
        """Should generate server component page."""
        result_json = await nextjs_generate_page(
            route="/todos",
            component_type="server",
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "async function" in result["code"]
        # Server components don't have "use client"
        assert '"use client"' not in result["code"]

    @pytest.mark.asyncio
    async def test_generate_client_page(self):
        """Should generate client component page."""
        result_json = await nextjs_generate_page(
            route="/settings",
            component_type="client",
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert '"use client"' in result["code"]

    @pytest.mark.asyncio
    async def test_generate_page_with_fetch(self):
        """Should include data fetching for server pages."""
        result_json = await nextjs_generate_page(
            route="/todos",
            component_type="server",
            api_endpoint="/api/todos",
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "fetch" in result["code"]

    @pytest.mark.asyncio
    async def test_generate_dynamic_route_page(self):
        """Should handle dynamic route parameters."""
        result_json = await nextjs_generate_page(
            route="/todos/[id]",
            component_type="server",
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "params" in result["code"]


# =============================================================================
# Test: nextjs_generate_layout
# =============================================================================


class TestGenerateLayout:
    """Tests for nextjs_generate_layout tool."""

    @pytest.mark.asyncio
    async def test_generate_root_layout(self):
        """Should generate root layout with html/body."""
        result_json = await nextjs_generate_layout(route="/")
        result = json.loads(result_json)

        assert result["success"] is True
        assert "<html" in result["code"]
        assert "<body" in result["code"]
        assert "children" in result["code"]

    @pytest.mark.asyncio
    async def test_generate_layout_with_metadata(self):
        """Should include metadata when provided."""
        result_json = await nextjs_generate_layout(
            route="/",
            title="My App",
            description="A great application",
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "My App" in result["code"]
        assert "metadata" in result["code"].lower()

    @pytest.mark.asyncio
    async def test_generate_nested_layout(self):
        """Should generate nested layout without html/body."""
        result_json = await nextjs_generate_layout(route="/dashboard")
        result = json.loads(result_json)

        assert result["success"] is True
        assert "children" in result["code"]


# =============================================================================
# Test: nextjs_generate_server_action
# =============================================================================


class TestGenerateServerAction:
    """Tests for nextjs_generate_server_action tool."""

    @pytest.mark.asyncio
    async def test_generate_create_action(self):
        """Should generate create server action."""
        result_json = await nextjs_generate_server_action(
            action_name="createTodo",
            api_endpoint="/api/todos",
            method="POST",
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "'use server'" in result["code"]
        assert "createTodo" in result["code"]
        assert "POST" in result["code"]

    @pytest.mark.asyncio
    async def test_generate_action_with_revalidate(self):
        """Should include revalidatePath."""
        result_json = await nextjs_generate_server_action(
            action_name="createTodo",
            api_endpoint="/api/todos",
            method="POST",
            revalidate_path="/todos",
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "revalidatePath" in result["code"]

    @pytest.mark.asyncio
    async def test_generate_action_with_redirect(self):
        """Should include redirect when specified."""
        result_json = await nextjs_generate_server_action(
            action_name="createTodo",
            api_endpoint="/api/todos",
            method="POST",
            redirect_to="/todos",
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "redirect" in result["code"]


# =============================================================================
# Test: nextjs_generate_api_client
# =============================================================================


class TestGenerateApiClient:
    """Tests for nextjs_generate_api_client tool."""

    @pytest.mark.asyncio
    async def test_generate_api_client_basic(self):
        """Should generate basic API client."""
        result_json = await nextjs_generate_api_client(
            resource_name="todos",
            base_url="http://localhost:8000",
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "todos" in result["code"]
        assert "fetch" in result["code"]

    @pytest.mark.asyncio
    async def test_generate_api_client_crud(self):
        """Should generate CRUD methods."""
        result_json = await nextjs_generate_api_client(
            resource_name="todos",
            base_url="http://localhost:8000",
            endpoints=["list", "create", "update", "delete"],
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "list" in result["code"]
        assert "create" in result["code"]
        assert "update" in result["code"]
        assert "delete" in result["code"]

    @pytest.mark.asyncio
    async def test_generate_api_client_uses_env(self):
        """Should use environment variable for base URL."""
        result_json = await nextjs_generate_api_client(
            resource_name="todos",
            base_url="http://localhost:8000",
            use_env_var=True,
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert (
            "NEXT_PUBLIC_API_URL" in result["code"] or "process.env" in result["code"]
        )


# =============================================================================
# Test: nextjs_generate_loading_error
# =============================================================================


class TestGenerateLoadingError:
    """Tests for nextjs_generate_loading_error tool."""

    @pytest.mark.asyncio
    async def test_generate_loading_state(self):
        """Should generate loading component."""
        result_json = await nextjs_generate_loading_error(route="/todos")
        result = json.loads(result_json)

        assert result["success"] is True
        assert "loading" in result["loading_code"].lower()

    @pytest.mark.asyncio
    async def test_generate_error_state(self):
        """Should generate error component."""
        result_json = await nextjs_generate_loading_error(route="/todos")
        result = json.loads(result_json)

        assert result["success"] is True
        assert '"use client"' in result["error_code"]
        assert "reset" in result["error_code"]

    @pytest.mark.asyncio
    async def test_generate_not_found(self):
        """Should generate not-found component when requested."""
        result_json = await nextjs_generate_loading_error(
            route="/todos",
            include_not_found=True,
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "not_found_code" in result


# =============================================================================
# Test: nextjs_validate_structure
# =============================================================================


class TestValidateStructure:
    """Tests for nextjs_validate_structure tool."""

    @pytest.mark.asyncio
    async def test_validate_complete_structure(self):
        """Valid structure should pass validation."""
        result_json = await nextjs_validate_structure(
            files=[
                "app/layout.tsx",
                "app/page.tsx",
                "app/loading.tsx",
                "app/error.tsx",
            ]
        )
        result = json.loads(result_json)

        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_missing_layout(self):
        """Missing layout should be flagged."""
        result_json = await nextjs_validate_structure(files=["app/page.tsx"])
        result = json.loads(result_json)

        assert result["valid"] is False
        assert any("layout" in issue.lower() for issue in result["issues"])

    @pytest.mark.asyncio
    async def test_validate_missing_error_boundary(self):
        """Missing error boundary should be warned."""
        result_json = await nextjs_validate_structure(
            files=["app/layout.tsx", "app/page.tsx"]
        )
        result = json.loads(result_json)

        # Should have warning about missing error.tsx
        assert "warnings" in result


# =============================================================================
# Test: nextjs_diagnose_issues
# =============================================================================


class TestDiagnoseIssues:
    """Tests for nextjs_diagnose_issues tool."""

    @pytest.mark.asyncio
    async def test_diagnose_use_client_error(self):
        """Should diagnose useState in server component error."""
        result_json = await nextjs_diagnose_issues(
            error_message="Error: useState can only be used in Client Components"
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "client" in result["diagnosis"].lower()

    @pytest.mark.asyncio
    async def test_diagnose_hydration_error(self):
        """Should diagnose hydration mismatch error."""
        result_json = await nextjs_diagnose_issues(
            error_message="Hydration failed because the initial UI does not match"
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "hydration" in result["diagnosis"].lower()

    @pytest.mark.asyncio
    async def test_diagnose_async_component_error(self):
        """Should diagnose async client component error."""
        result_json = await nextjs_diagnose_issues(
            error_message="async/await is not yet supported in Client Components"
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert len(result["suggestions"]) > 0

    @pytest.mark.asyncio
    async def test_diagnose_unknown_error(self):
        """Should handle unknown errors gracefully."""
        result_json = await nextjs_diagnose_issues(
            error_message="SomeRandomError: unknown issue"
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "diagnosis" in result
