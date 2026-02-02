"""Tests for fastapi_backend_mcp — error-path-first, TDD-strict.

Tests cover all 8 MCP tools:
    1. fastapi_scaffold_project
    2. fastapi_generate_endpoint
    3. fastapi_generate_model
    4. fastapi_generate_schema
    5. fastapi_generate_error_handlers
    6. fastapi_suggest_crud_pattern
    7. fastapi_validate_project
    8. fastapi_diagnose_issue
"""

import json

import pytest
import pytest_asyncio

from mcp_servers.fastapi_backend_mcp import mcp

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse(raw: str) -> dict:
    """Parse JSON string from tool output."""
    return json.loads(raw)


# ===================================================================
# Section 1: Server Registration
# ===================================================================


class TestServerRegistration:
    """Verify FastMCP server metadata."""

    def test_server_name(self):
        assert mcp.name == "fastapi_backend_mcp"

    def test_tool_count(self):
        tools = mcp._tool_manager._tools
        assert len(tools) == 8, f"Expected 8 tools, got {len(tools)}: {list(tools.keys())}"

    def test_all_tool_names_present(self):
        tools = set(mcp._tool_manager._tools.keys())
        expected = {
            "fastapi_scaffold_project",
            "fastapi_generate_endpoint",
            "fastapi_generate_model",
            "fastapi_generate_schema",
            "fastapi_generate_error_handlers",
            "fastapi_suggest_crud_pattern",
            "fastapi_validate_project",
            "fastapi_diagnose_issue",
        }
        assert tools == expected


# ===================================================================
# Section 2: Input Validation (error paths first)
# ===================================================================


class TestInputValidation:
    """Validate Pydantic input models reject bad data."""

    # --- ScaffoldProjectInput ---

    def test_scaffold_empty_project_name_rejected(self):
        from mcp_servers.fastapi_backend_mcp import ScaffoldProjectInput
        with pytest.raises(Exception):
            ScaffoldProjectInput(project_name="")

    def test_scaffold_path_traversal_rejected(self):
        from mcp_servers.fastapi_backend_mcp import ScaffoldProjectInput
        with pytest.raises(Exception):
            ScaffoldProjectInput(project_name="../evil")

    def test_scaffold_extra_fields_rejected(self):
        from mcp_servers.fastapi_backend_mcp import ScaffoldProjectInput
        with pytest.raises(Exception):
            ScaffoldProjectInput(project_name="myapp", unknown_field="bad")

    # --- GenerateEndpointInput ---

    def test_endpoint_empty_resource_rejected(self):
        from mcp_servers.fastapi_backend_mcp import GenerateEndpointInput
        with pytest.raises(Exception):
            GenerateEndpointInput(resource_name="", operations=["list"])

    def test_endpoint_invalid_operation_rejected(self):
        from mcp_servers.fastapi_backend_mcp import GenerateEndpointInput
        with pytest.raises(Exception):
            GenerateEndpointInput(resource_name="todo", operations=["fly"])

    def test_endpoint_empty_operations_rejected(self):
        from mcp_servers.fastapi_backend_mcp import GenerateEndpointInput
        with pytest.raises(Exception):
            GenerateEndpointInput(resource_name="todo", operations=[])

    # --- GenerateModelInput ---

    def test_model_empty_name_rejected(self):
        from mcp_servers.fastapi_backend_mcp import GenerateModelInput
        with pytest.raises(Exception):
            GenerateModelInput(model_name="", fields=[{"name": "title", "type": "str"}])

    def test_model_empty_fields_rejected(self):
        from mcp_servers.fastapi_backend_mcp import GenerateModelInput
        with pytest.raises(Exception):
            GenerateModelInput(model_name="Todo", fields=[])

    def test_model_field_missing_name_rejected(self):
        from mcp_servers.fastapi_backend_mcp import GenerateModelInput
        with pytest.raises(Exception):
            GenerateModelInput(model_name="Todo", fields=[{"type": "str"}])

    def test_model_field_missing_type_rejected(self):
        from mcp_servers.fastapi_backend_mcp import GenerateModelInput
        with pytest.raises(Exception):
            GenerateModelInput(model_name="Todo", fields=[{"name": "title"}])

    # --- GenerateSchemaInput ---

    def test_schema_empty_name_rejected(self):
        from mcp_servers.fastapi_backend_mcp import GenerateSchemaInput
        with pytest.raises(Exception):
            GenerateSchemaInput(model_name="", fields=[{"name": "title", "type": "str"}])

    def test_schema_empty_fields_rejected(self):
        from mcp_servers.fastapi_backend_mcp import GenerateSchemaInput
        with pytest.raises(Exception):
            GenerateSchemaInput(model_name="Todo", fields=[])

    # --- SuggestCrudPatternInput ---

    def test_crud_pattern_invalid_name_rejected(self):
        from mcp_servers.fastapi_backend_mcp import SuggestCrudPatternInput
        with pytest.raises(Exception):
            SuggestCrudPatternInput(pattern_name="teleport")

    # --- ValidateProjectInput ---

    def test_validate_empty_files_rejected(self):
        from mcp_servers.fastapi_backend_mcp import ValidateProjectInput
        with pytest.raises(Exception):
            ValidateProjectInput(project_files={})

    # --- DiagnoseIssueInput ---

    def test_diagnose_empty_symptom_rejected(self):
        from mcp_servers.fastapi_backend_mcp import DiagnoseIssueInput
        with pytest.raises(Exception):
            DiagnoseIssueInput(symptom="")

    def test_diagnose_invalid_symptom_rejected(self):
        from mcp_servers.fastapi_backend_mcp import DiagnoseIssueInput
        with pytest.raises(Exception):
            DiagnoseIssueInput(symptom="alien_invasion")


# ===================================================================
# Section 3: fastapi_scaffold_project
# ===================================================================


class TestScaffoldProject:
    """Test project scaffolding tool."""

    @pytest.mark.asyncio
    async def test_scaffold_basic_project(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_scaffold_project"].run(
            {"project_name": "myapp"},
        ))
        assert result["status"] == "success"
        assert "files" in result
        files = result["files"]
        # Should contain key files
        filenames = [f["path"] for f in files]
        assert "main.py" in filenames
        assert "database.py" in filenames
        assert "requirements.txt" in filenames

    @pytest.mark.asyncio
    async def test_scaffold_with_resource(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_scaffold_project"].run(
            {"project_name": "myapp", "resource_name": "todo"},
        ))
        assert result["status"] == "success"
        filenames = [f["path"] for f in result["files"]]
        assert any("routers/" in f for f in filenames)
        assert any("schemas/" in f or "schemas.py" in f for f in filenames)

    @pytest.mark.asyncio
    async def test_scaffold_with_database_type(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_scaffold_project"].run(
            {"project_name": "myapp", "database_type": "sqlite"},
        ))
        assert result["status"] == "success"
        # database.py should reference sqlite
        db_file = next(f for f in result["files"] if f["path"] == "database.py")
        assert "sqlite" in db_file["content"].lower()

    @pytest.mark.asyncio
    async def test_scaffold_contains_env_example(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_scaffold_project"].run(
            {"project_name": "myapp"},
        ))
        filenames = [f["path"] for f in result["files"]]
        assert ".env.example" in filenames

    @pytest.mark.asyncio
    async def test_scaffold_no_hardcoded_secrets(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_scaffold_project"].run(
            {"project_name": "myapp"},
        ))
        for f in result["files"]:
            content = f["content"]
            assert "password" not in content.lower() or "os.getenv" in content or ".env" in f["path"].lower() or "example" in f["path"].lower()


# ===================================================================
# Section 4: fastapi_generate_endpoint
# ===================================================================


class TestGenerateEndpoint:
    """Test endpoint/router generation tool."""

    @pytest.mark.asyncio
    async def test_endpoint_list_operation(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_generate_endpoint"].run(
            {"resource_name": "todo", "operations": ["list"]},
        ))
        assert result["status"] == "success"
        assert "code" in result
        assert "router.get" in result["code"].lower() or "@router.get" in result["code"]

    @pytest.mark.asyncio
    async def test_endpoint_create_operation(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_generate_endpoint"].run(
            {"resource_name": "todo", "operations": ["create"]},
        ))
        code = result["code"]
        assert "@router.post" in code
        assert "201" in code or "HTTP_201_CREATED" in code

    @pytest.mark.asyncio
    async def test_endpoint_delete_operation(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_generate_endpoint"].run(
            {"resource_name": "todo", "operations": ["delete"]},
        ))
        code = result["code"]
        assert "@router.delete" in code
        assert "204" in code or "HTTP_204_NO_CONTENT" in code

    @pytest.mark.asyncio
    async def test_endpoint_all_crud_operations(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_generate_endpoint"].run(
            {"resource_name": "todo", "operations": ["list", "get", "create", "update", "delete"]},
        ))
        code = result["code"]
        assert "@router.get" in code
        assert "@router.post" in code
        assert "@router.put" in code
        assert "@router.delete" in code

    @pytest.mark.asyncio
    async def test_endpoint_custom_prefix(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_generate_endpoint"].run(
            {"resource_name": "todo", "operations": ["list"], "prefix": "/v2/todos"},
        ))
        assert "/v2/todos" in result["code"]

    @pytest.mark.asyncio
    async def test_endpoint_includes_error_handling(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_generate_endpoint"].run(
            {"resource_name": "todo", "operations": ["get"]},
        ))
        code = result["code"]
        assert "HTTPException" in code or "404" in code


# ===================================================================
# Section 5: fastapi_generate_model
# ===================================================================


class TestGenerateModel:
    """Test SQLModel generation tool."""

    @pytest.mark.asyncio
    async def test_model_basic(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_generate_model"].run(
            {"model_name": "Todo", "fields": [
                {"name": "title", "type": "str"},
                {"name": "status", "type": "str"},
            ]},
        ))
        assert result["status"] == "success"
        code = result["code"]
        assert "class Todo" in code
        assert "SQLModel" in code
        assert "table=True" in code
        assert "title" in code
        assert "status" in code

    @pytest.mark.asyncio
    async def test_model_with_timestamps(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_generate_model"].run(
            {"model_name": "Todo", "fields": [
                {"name": "title", "type": "str"},
            ], "timestamps": True},
        ))
        code = result["code"]
        assert "created_at" in code
        assert "updated_at" in code

    @pytest.mark.asyncio
    async def test_model_with_soft_delete(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_generate_model"].run(
            {"model_name": "Todo", "fields": [
                {"name": "title", "type": "str"},
            ], "soft_delete": True},
        ))
        code = result["code"]
        assert "deleted_at" in code

    @pytest.mark.asyncio
    async def test_model_custom_table_name(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_generate_model"].run(
            {"model_name": "Todo", "fields": [
                {"name": "title", "type": "str"},
            ], "table_name": "my_todos"},
        ))
        code = result["code"]
        assert "my_todos" in code

    @pytest.mark.asyncio
    async def test_model_includes_primary_key(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_generate_model"].run(
            {"model_name": "Todo", "fields": [
                {"name": "title", "type": "str"},
            ]},
        ))
        code = result["code"]
        assert "primary_key" in code


# ===================================================================
# Section 6: fastapi_generate_schema
# ===================================================================


class TestGenerateSchema:
    """Test Pydantic schema generation tool."""

    @pytest.mark.asyncio
    async def test_schema_basic(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_generate_schema"].run(
            {"model_name": "Todo", "fields": [
                {"name": "title", "type": "str"},
                {"name": "status", "type": "str"},
            ]},
        ))
        assert result["status"] == "success"
        code = result["code"]
        assert "TodoBase" in code or "TodoCreate" in code
        assert "TodoResponse" in code

    @pytest.mark.asyncio
    async def test_schema_includes_create(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_generate_schema"].run(
            {"model_name": "Todo", "fields": [
                {"name": "title", "type": "str"},
            ]},
        ))
        assert "TodoCreate" in result["code"]

    @pytest.mark.asyncio
    async def test_schema_includes_update(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_generate_schema"].run(
            {"model_name": "Todo", "fields": [
                {"name": "title", "type": "str"},
            ], "include_update": True},
        ))
        assert "TodoUpdate" in result["code"]

    @pytest.mark.asyncio
    async def test_schema_includes_list_response(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_generate_schema"].run(
            {"model_name": "Todo", "fields": [
                {"name": "title", "type": "str"},
            ], "include_list": True},
        ))
        code = result["code"]
        assert "PaginatedResponse" in code or "ListResponse" in code or "TodoList" in code

    @pytest.mark.asyncio
    async def test_schema_response_has_id(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_generate_schema"].run(
            {"model_name": "Todo", "fields": [
                {"name": "title", "type": "str"},
            ]},
        ))
        code = result["code"]
        assert "id:" in code or "id :" in code

    @pytest.mark.asyncio
    async def test_schema_response_has_from_attributes(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_generate_schema"].run(
            {"model_name": "Todo", "fields": [
                {"name": "title", "type": "str"},
            ]},
        ))
        code = result["code"]
        assert "from_attributes" in code


# ===================================================================
# Section 7: fastapi_generate_error_handlers
# ===================================================================


class TestGenerateErrorHandlers:
    """Test error handler generation tool."""

    @pytest.mark.asyncio
    async def test_error_handlers_basic(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_generate_error_handlers"].run({}))
        assert result["status"] == "success"
        code = result["code"]
        assert "exception_handler" in code

    @pytest.mark.asyncio
    async def test_error_handlers_includes_validation(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_generate_error_handlers"].run({}))
        code = result["code"]
        assert "RequestValidationError" in code or "validation" in code.lower()

    @pytest.mark.asyncio
    async def test_error_handlers_with_request_id(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_generate_error_handlers"].run(
            {"include_request_id": True},
        ))
        code = result["code"]
        assert "request_id" in code.lower() or "Request-ID" in code or "X-Request-ID" in code

    @pytest.mark.asyncio
    async def test_error_handlers_with_logging(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_generate_error_handlers"].run(
            {"include_logging": True},
        ))
        code = result["code"]
        assert "logging" in code or "logger" in code


# ===================================================================
# Section 8: fastapi_suggest_crud_pattern
# ===================================================================


class TestSuggestCrudPattern:
    """Test CRUD pattern suggestion tool."""

    @pytest.mark.asyncio
    async def test_pagination_pattern(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_suggest_crud_pattern"].run(
            {"pattern_name": "pagination"},
        ))
        assert result["status"] == "success"
        assert "code" in result
        assert "page" in result["code"].lower() or "offset" in result["code"].lower()

    @pytest.mark.asyncio
    async def test_filtering_pattern(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_suggest_crud_pattern"].run(
            {"pattern_name": "filtering"},
        ))
        assert result["status"] == "success"
        assert "Query" in result["code"]

    @pytest.mark.asyncio
    async def test_bulk_operations_pattern(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_suggest_crud_pattern"].run(
            {"pattern_name": "bulk_operations"},
        ))
        assert result["status"] == "success"
        assert "bulk" in result["code"].lower()

    @pytest.mark.asyncio
    async def test_soft_delete_pattern(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_suggest_crud_pattern"].run(
            {"pattern_name": "soft_delete"},
        ))
        assert result["status"] == "success"
        assert "deleted_at" in result["code"]

    @pytest.mark.asyncio
    async def test_sorting_pattern(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_suggest_crud_pattern"].run(
            {"pattern_name": "sorting"},
        ))
        assert result["status"] == "success"
        assert "sort" in result["code"].lower() or "order_by" in result["code"]

    @pytest.mark.asyncio
    async def test_search_pattern(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_suggest_crud_pattern"].run(
            {"pattern_name": "search"},
        ))
        assert result["status"] == "success"
        assert "search" in result["code"].lower() or "ilike" in result["code"]

    @pytest.mark.asyncio
    async def test_upsert_pattern(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_suggest_crud_pattern"].run(
            {"pattern_name": "upsert"},
        ))
        assert result["status"] == "success"
        assert "upsert" in result["code"].lower() or "create or update" in result["code"].lower()

    @pytest.mark.asyncio
    async def test_pattern_has_notes(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_suggest_crud_pattern"].run(
            {"pattern_name": "pagination"},
        ))
        assert "notes" in result
        assert isinstance(result["notes"], list)
        assert len(result["notes"]) > 0


# ===================================================================
# Section 9: fastapi_validate_project
# ===================================================================


class TestValidateProject:
    """Test project validation tool."""

    @pytest.mark.asyncio
    async def test_validate_complete_project(self):
        project_files = {
            "main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
            "database.py": 'DATABASE_URL = os.getenv("DATABASE_URL")\n',
            "requirements.txt": "fastapi\nuvicorn\n",
            ".env.example": "DATABASE_URL=\n",
            "routers/todos.py": "@router.get('/')\n",
        }
        result = _parse(await mcp._tool_manager._tools["fastapi_validate_project"].run(
            {"project_files": project_files},
        ))
        assert result["status"] == "success"
        assert "checks" in result

    @pytest.mark.asyncio
    async def test_validate_missing_main_py(self):
        project_files = {
            "database.py": "x = 1\n",
        }
        result = _parse(await mcp._tool_manager._tools["fastapi_validate_project"].run(
            {"project_files": project_files},
        ))
        warnings = result.get("warnings", [])
        assert any("main.py" in w.lower() for w in warnings)

    @pytest.mark.asyncio
    async def test_validate_missing_database(self):
        project_files = {
            "main.py": "from fastapi import FastAPI\n",
        }
        result = _parse(await mcp._tool_manager._tools["fastapi_validate_project"].run(
            {"project_files": project_files},
        ))
        warnings = result.get("warnings", [])
        assert any("database" in w.lower() for w in warnings)

    @pytest.mark.asyncio
    async def test_validate_hardcoded_secrets(self):
        project_files = {
            "main.py": "from fastapi import FastAPI\n",
            "database.py": 'DATABASE_URL = "postgresql://user:password@localhost/db"\n',
        }
        result = _parse(await mcp._tool_manager._tools["fastapi_validate_project"].run(
            {"project_files": project_files},
        ))
        warnings = result.get("warnings", [])
        assert any("secret" in w.lower() or "hardcod" in w.lower() for w in warnings)

    @pytest.mark.asyncio
    async def test_validate_no_cors(self):
        project_files = {
            "main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
        }
        result = _parse(await mcp._tool_manager._tools["fastapi_validate_project"].run(
            {"project_files": project_files},
        ))
        warnings = result.get("warnings", [])
        assert any("cors" in w.lower() for w in warnings)

    @pytest.mark.asyncio
    async def test_validate_checks_structure(self):
        project_files = {
            "main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
        }
        result = _parse(await mcp._tool_manager._tools["fastapi_validate_project"].run(
            {"project_files": project_files},
        ))
        checks = result["checks"]
        assert isinstance(checks, dict)
        assert "has_main_py" in checks
        assert "has_database" in checks


# ===================================================================
# Section 10: fastapi_diagnose_issue
# ===================================================================


class TestDiagnoseIssue:
    """Test issue diagnosis tool."""

    @pytest.mark.asyncio
    async def test_diagnose_422_error(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_diagnose_issue"].run(
            {"symptom": "422_validation_error"},
        ))
        assert result["status"] == "success"
        assert "diagnosis" in result
        assert "solutions" in result
        assert len(result["solutions"]) > 0

    @pytest.mark.asyncio
    async def test_diagnose_cors_error(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_diagnose_issue"].run(
            {"symptom": "cors_error"},
        ))
        assert result["status"] == "success"
        assert "CORS" in result["diagnosis"] or "cors" in result["diagnosis"].lower()

    @pytest.mark.asyncio
    async def test_diagnose_server_wont_start(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_diagnose_issue"].run(
            {"symptom": "server_wont_start"},
        ))
        assert result["status"] == "success"
        assert len(result["solutions"]) > 0

    @pytest.mark.asyncio
    async def test_diagnose_500_error(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_diagnose_issue"].run(
            {"symptom": "500_internal_error"},
        ))
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_diagnose_db_connection(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_diagnose_issue"].run(
            {"symptom": "database_connection_failed"},
        ))
        assert result["status"] == "success"
        assert "database" in result["diagnosis"].lower() or "connection" in result["diagnosis"].lower()

    @pytest.mark.asyncio
    async def test_diagnose_dependency_injection(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_diagnose_issue"].run(
            {"symptom": "dependency_injection_error"},
        ))
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_diagnose_async_issues(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_diagnose_issue"].run(
            {"symptom": "async_issues"},
        ))
        assert result["status"] == "success"
        assert "async" in result["diagnosis"].lower() or "await" in result["diagnosis"].lower()

    @pytest.mark.asyncio
    async def test_diagnose_response_model_mismatch(self):
        result = _parse(await mcp._tool_manager._tools["fastapi_diagnose_issue"].run(
            {"symptom": "response_model_mismatch"},
        ))
        assert result["status"] == "success"
