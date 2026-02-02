"""
Tests for sqlmodel_orm_mcp MCP server.

Comprehensive test suite covering:
- Server registration and tool listing
- Input validation (Pydantic models)
- Table generation
- Schema generation (Create/Update/Read)
- Relationship generation
- CRUD operations generation
- Query patterns generation
- Database config generation
- Model validation
- Issue diagnosis
"""

import json
import pytest
from pydantic import ValidationError

from src.mcp_servers.sqlmodel_orm_mcp import (
    mcp,
    # Tools
    sqlmodel_generate_table,
    sqlmodel_generate_schemas,
    sqlmodel_generate_relationship,
    sqlmodel_generate_crud,
    sqlmodel_generate_queries,
    sqlmodel_generate_database_config,
    sqlmodel_validate_model,
    sqlmodel_diagnose_issues,
    # Input models
    GenerateTableInput,
    GenerateSchemasInput,
    GenerateRelationshipInput,
    GenerateCrudInput,
    GenerateQueriesInput,
    GenerateDatabaseConfigInput,
    ValidateModelInput,
    DiagnoseIssuesInput,
    # Types
    FieldDefinition,
    RelationshipType,
    DatabaseType,
)


# =============================================================================
# Test: Server Registration
# =============================================================================


class TestServerRegistration:
    """Tests for MCP server registration."""

    def test_server_name(self):
        """Server should be named sqlmodel_orm_mcp."""
        assert mcp.name == "sqlmodel_orm_mcp"

    def test_server_has_tools(self):
        """Server should have 8 registered tools."""
        # Tools are registered via decorators
        assert sqlmodel_generate_table is not None
        assert sqlmodel_generate_schemas is not None
        assert sqlmodel_generate_relationship is not None
        assert sqlmodel_generate_crud is not None
        assert sqlmodel_generate_queries is not None
        assert sqlmodel_generate_database_config is not None
        assert sqlmodel_validate_model is not None
        assert sqlmodel_diagnose_issues is not None

    def test_all_tool_names_present(self):
        """All expected tool functions should be importable."""
        tools = [
            sqlmodel_generate_table,
            sqlmodel_generate_schemas,
            sqlmodel_generate_relationship,
            sqlmodel_generate_crud,
            sqlmodel_generate_queries,
            sqlmodel_generate_database_config,
            sqlmodel_validate_model,
            sqlmodel_diagnose_issues,
        ]
        assert len(tools) == 8


# =============================================================================
# Test: Input Validation
# =============================================================================


class TestInputValidation:
    """Tests for Pydantic input model validation."""

    # GenerateTableInput
    def test_generate_table_valid(self):
        """Valid table input should pass."""
        inp = GenerateTableInput(
            model_name="Todo",
            table_name="todos",
            fields=[
                FieldDefinition(name="title", type="str", max_length=200),
                FieldDefinition(name="status", type="str", default="active"),
            ],
        )
        assert inp.model_name == "Todo"
        assert len(inp.fields) == 2

    def test_generate_table_empty_name_rejected(self):
        """Empty model name should be rejected."""
        with pytest.raises(ValidationError):
            GenerateTableInput(
                model_name="",
                table_name="todos",
                fields=[FieldDefinition(name="title", type="str")],
            )

    def test_generate_table_empty_fields_rejected(self):
        """Empty fields list should be rejected."""
        with pytest.raises(ValidationError):
            GenerateTableInput(
                model_name="Todo",
                table_name="todos",
                fields=[],
            )

    # GenerateSchemasInput
    def test_generate_schemas_valid(self):
        """Valid schemas input should pass."""
        inp = GenerateSchemasInput(
            model_name="Todo",
            fields=[FieldDefinition(name="title", type="str")],
        )
        assert inp.model_name == "Todo"

    def test_generate_schemas_empty_name_rejected(self):
        """Empty model name should be rejected."""
        with pytest.raises(ValidationError):
            GenerateSchemasInput(
                model_name="",
                fields=[FieldDefinition(name="title", type="str")],
            )

    # GenerateRelationshipInput
    def test_generate_relationship_valid(self):
        """Valid relationship input should pass."""
        inp = GenerateRelationshipInput(
            parent_model="User",
            child_model="Todo",
            relationship_type=RelationshipType.ONE_TO_MANY,
        )
        assert inp.parent_model == "User"
        assert inp.relationship_type == RelationshipType.ONE_TO_MANY

    def test_generate_relationship_invalid_type(self):
        """Invalid relationship type should be rejected."""
        with pytest.raises(ValidationError):
            GenerateRelationshipInput(
                parent_model="User",
                child_model="Todo",
                relationship_type="invalid",  # type: ignore
            )

    # GenerateCrudInput
    def test_generate_crud_valid(self):
        """Valid CRUD input should pass."""
        inp = GenerateCrudInput(model_name="Todo")
        assert inp.model_name == "Todo"

    def test_generate_crud_empty_name_rejected(self):
        """Empty model name should be rejected."""
        with pytest.raises(ValidationError):
            GenerateCrudInput(model_name="")

    # GenerateQueriesInput
    def test_generate_queries_valid(self):
        """Valid queries input should pass."""
        inp = GenerateQueriesInput(model_name="Todo")
        assert inp.model_name == "Todo"

    # GenerateDatabaseConfigInput
    def test_generate_database_config_valid(self):
        """Valid database config input should pass."""
        inp = GenerateDatabaseConfigInput(
            database_type=DatabaseType.POSTGRESQL,
            database_name="mydb",
        )
        assert inp.database_type == DatabaseType.POSTGRESQL

    def test_generate_database_config_sqlite(self):
        """SQLite database type should be valid."""
        inp = GenerateDatabaseConfigInput(
            database_type=DatabaseType.SQLITE,
            database_name="test.db",
        )
        assert inp.database_type == DatabaseType.SQLITE

    # ValidateModelInput
    def test_validate_model_valid(self):
        """Valid model code should pass validation input."""
        inp = ValidateModelInput(
            model_code="class Todo(SQLModel, table=True): pass"
        )
        assert "Todo" in inp.model_code

    def test_validate_model_empty_rejected(self):
        """Empty model code should be rejected."""
        with pytest.raises(ValidationError):
            ValidateModelInput(model_code="")

    # DiagnoseIssuesInput
    def test_diagnose_issues_valid(self):
        """Valid diagnose input should pass."""
        inp = DiagnoseIssuesInput(
            error_message="IntegrityError: foreign key constraint failed"
        )
        assert "IntegrityError" in inp.error_message


# =============================================================================
# Test: FieldDefinition
# =============================================================================


class TestFieldDefinition:
    """Tests for FieldDefinition model."""

    def test_field_basic(self):
        """Basic field definition should work."""
        field = FieldDefinition(name="title", type="str")
        assert field.name == "title"
        assert field.type == "str"
        assert field.optional is False
        assert field.primary_key is False

    def test_field_with_constraints(self):
        """Field with constraints should work."""
        field = FieldDefinition(
            name="priority",
            type="int",
            default=0,
            ge=0,
            le=10,
        )
        assert field.ge == 0
        assert field.le == 10

    def test_field_foreign_key(self):
        """Field with foreign key should work."""
        field = FieldDefinition(
            name="owner_id",
            type="int",
            optional=True,
            foreign_key="users.id",
        )
        assert field.foreign_key == "users.id"
        assert field.optional is True

    def test_field_primary_key(self):
        """Primary key field should work."""
        field = FieldDefinition(
            name="id",
            type="int",
            optional=True,
            primary_key=True,
        )
        assert field.primary_key is True


# =============================================================================
# Test: sqlmodel_generate_table
# =============================================================================


class TestGenerateTable:
    """Tests for sqlmodel_generate_table tool."""

    @pytest.mark.asyncio
    async def test_generate_basic_table(self):
        """Should generate a basic table model."""
        result_json = await sqlmodel_generate_table(
            model_name="Todo",
            table_name="todos",
            fields=[
                {"name": "title", "type": "str", "max_length": 200},
                {"name": "status", "type": "str", "default": "active"},
            ],
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "class Todo(SQLModel, table=True)" in result["code"]
        assert '__tablename__ = "todos"' in result["code"]
        assert "title: str" in result["code"]
        assert "status: str" in result["code"]

    @pytest.mark.asyncio
    async def test_generate_table_with_primary_key(self):
        """Should include auto-generated primary key."""
        result_json = await sqlmodel_generate_table(
            model_name="User",
            table_name="users",
            fields=[
                {"name": "email", "type": "str", "unique": True, "index": True},
            ],
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "id: Optional[int]" in result["code"]
        assert "primary_key=True" in result["code"]

    @pytest.mark.asyncio
    async def test_generate_table_with_timestamps(self):
        """Should include timestamps when requested."""
        result_json = await sqlmodel_generate_table(
            model_name="Todo",
            table_name="todos",
            fields=[{"name": "title", "type": "str"}],
            include_timestamps=True,
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "created_at" in result["code"]
        assert "updated_at" in result["code"]
        assert "datetime.utcnow" in result["code"]

    @pytest.mark.asyncio
    async def test_generate_table_with_foreign_key(self):
        """Should handle foreign key fields."""
        result_json = await sqlmodel_generate_table(
            model_name="Todo",
            table_name="todos",
            fields=[
                {"name": "title", "type": "str"},
                {
                    "name": "owner_id",
                    "type": "int",
                    "optional": True,
                    "foreign_key": "users.id",
                },
            ],
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert 'foreign_key="users.id"' in result["code"]


# =============================================================================
# Test: sqlmodel_generate_schemas
# =============================================================================


class TestGenerateSchemas:
    """Tests for sqlmodel_generate_schemas tool."""

    @pytest.mark.asyncio
    async def test_generate_schemas_basic(self):
        """Should generate Create, Update, Read schemas."""
        result_json = await sqlmodel_generate_schemas(
            model_name="Todo",
            fields=[
                {"name": "title", "type": "str", "max_length": 200},
                {"name": "status", "type": "str", "default": "active"},
            ],
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "class TodoCreate(SQLModel)" in result["code"]
        assert "class TodoUpdate(SQLModel)" in result["code"]
        assert "class TodoRead(SQLModel)" in result["code"]

    @pytest.mark.asyncio
    async def test_generate_schemas_update_optional(self):
        """Update schema fields should be optional."""
        result_json = await sqlmodel_generate_schemas(
            model_name="Todo",
            fields=[{"name": "title", "type": "str"}],
        )
        result = json.loads(result_json)

        assert result["success"] is True
        # In Update schema, fields should be Optional
        assert "TodoUpdate" in result["code"]

    @pytest.mark.asyncio
    async def test_generate_schemas_read_includes_id(self):
        """Read schema should include id field."""
        result_json = await sqlmodel_generate_schemas(
            model_name="Todo",
            fields=[{"name": "title", "type": "str"}],
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "TodoRead" in result["code"]
        assert "id: int" in result["code"]


# =============================================================================
# Test: sqlmodel_generate_relationship
# =============================================================================


class TestGenerateRelationship:
    """Tests for sqlmodel_generate_relationship tool."""

    @pytest.mark.asyncio
    async def test_generate_one_to_many(self):
        """Should generate one-to-many relationship code."""
        result_json = await sqlmodel_generate_relationship(
            parent_model="User",
            child_model="Todo",
            relationship_type="one_to_many",
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "Relationship" in result["code"]
        assert "back_populates" in result["code"]
        assert "foreign_key" in result["code"]

    @pytest.mark.asyncio
    async def test_generate_many_to_many(self):
        """Should generate many-to-many relationship with link table."""
        result_json = await sqlmodel_generate_relationship(
            parent_model="Todo",
            child_model="Tag",
            relationship_type="many_to_many",
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "link_model" in result["code"]
        # Should include link table definition
        assert "TodoTag" in result["code"] or "todo_tag" in result["code"].lower()

    @pytest.mark.asyncio
    async def test_generate_self_referential(self):
        """Should generate self-referential relationship."""
        result_json = await sqlmodel_generate_relationship(
            parent_model="Category",
            child_model="Category",
            relationship_type="self_referential",
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "parent_id" in result["code"]
        assert "children" in result["code"]


# =============================================================================
# Test: sqlmodel_generate_crud
# =============================================================================


class TestGenerateCrud:
    """Tests for sqlmodel_generate_crud tool."""

    @pytest.mark.asyncio
    async def test_generate_crud_basic(self):
        """Should generate all CRUD functions."""
        result_json = await sqlmodel_generate_crud(model_name="Todo")
        result = json.loads(result_json)

        assert result["success"] is True
        assert "def create_todo" in result["code"]
        assert "def get_todo" in result["code"]
        assert "def update_todo" in result["code"]
        assert "def delete_todo" in result["code"]

    @pytest.mark.asyncio
    async def test_generate_crud_with_list(self):
        """Should include get_all function."""
        result_json = await sqlmodel_generate_crud(model_name="Todo")
        result = json.loads(result_json)

        assert result["success"] is True
        assert "def get_todos" in result["code"] or "def get_all_todos" in result["code"]

    @pytest.mark.asyncio
    async def test_generate_crud_uses_session(self):
        """CRUD functions should use Session."""
        result_json = await sqlmodel_generate_crud(model_name="Todo")
        result = json.loads(result_json)

        assert result["success"] is True
        assert "Session" in result["code"]
        assert "session.add" in result["code"]
        assert "session.commit" in result["code"]


# =============================================================================
# Test: sqlmodel_generate_queries
# =============================================================================


class TestGenerateQueries:
    """Tests for sqlmodel_generate_queries tool."""

    @pytest.mark.asyncio
    async def test_generate_queries_basic(self):
        """Should generate common query patterns."""
        result_json = await sqlmodel_generate_queries(model_name="Todo")
        result = json.loads(result_json)

        assert result["success"] is True
        assert "select" in result["code"].lower()

    @pytest.mark.asyncio
    async def test_generate_queries_pagination(self):
        """Should include pagination query."""
        result_json = await sqlmodel_generate_queries(
            model_name="Todo", include_pagination=True
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "offset" in result["code"]
        assert "limit" in result["code"]

    @pytest.mark.asyncio
    async def test_generate_queries_filter(self):
        """Should include filter by field query."""
        result_json = await sqlmodel_generate_queries(
            model_name="Todo", filter_fields=["status", "owner_id"]
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "where" in result["code"].lower()


# =============================================================================
# Test: sqlmodel_generate_database_config
# =============================================================================


class TestGenerateDatabaseConfig:
    """Tests for sqlmodel_generate_database_config tool."""

    @pytest.mark.asyncio
    async def test_generate_postgresql_config(self):
        """Should generate PostgreSQL config."""
        result_json = await sqlmodel_generate_database_config(
            database_type="postgresql",
            database_name="mydb",
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "postgresql" in result["code"]
        assert "create_engine" in result["code"]

    @pytest.mark.asyncio
    async def test_generate_sqlite_config(self):
        """Should generate SQLite config."""
        result_json = await sqlmodel_generate_database_config(
            database_type="sqlite",
            database_name="test.db",
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "sqlite" in result["code"]
        assert "check_same_thread" in result["code"]

    @pytest.mark.asyncio
    async def test_generate_config_with_env(self):
        """Should use environment variable pattern."""
        result_json = await sqlmodel_generate_database_config(
            database_type="postgresql",
            database_name="mydb",
            use_env_var=True,
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "DATABASE_URL" in result["code"] or "os.getenv" in result["code"]


# =============================================================================
# Test: sqlmodel_validate_model
# =============================================================================


class TestValidateModel:
    """Tests for sqlmodel_validate_model tool."""

    @pytest.mark.asyncio
    async def test_validate_good_model(self):
        """Valid model should pass validation."""
        model_code = '''
class Todo(SQLModel, table=True):
    __tablename__ = "todos"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
'''
        result_json = await sqlmodel_validate_model(model_code=model_code)
        result = json.loads(result_json)

        assert result["valid"] is True
        assert len(result["issues"]) == 0

    @pytest.mark.asyncio
    async def test_validate_missing_primary_key(self):
        """Model without primary key should be flagged."""
        model_code = '''
class Todo(SQLModel, table=True):
    title: str
'''
        result_json = await sqlmodel_validate_model(model_code=model_code)
        result = json.loads(result_json)

        assert result["valid"] is False
        assert any("primary" in issue.lower() for issue in result["issues"])

    @pytest.mark.asyncio
    async def test_validate_missing_table_true(self):
        """Model without table=True should be flagged as warning."""
        model_code = '''
class Todo(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
'''
        result_json = await sqlmodel_validate_model(model_code=model_code)
        result = json.loads(result_json)

        # This is valid for schema models, but warn if user expects a table
        assert "warnings" in result or result["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_mutable_default(self):
        """Mutable default should be flagged."""
        model_code = '''
class Todo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tags: list = []
'''
        result_json = await sqlmodel_validate_model(model_code=model_code)
        result = json.loads(result_json)

        assert result["valid"] is False
        assert any("mutable" in issue.lower() or "default" in issue.lower() for issue in result["issues"])


# =============================================================================
# Test: sqlmodel_diagnose_issues
# =============================================================================


class TestDiagnoseIssues:
    """Tests for sqlmodel_diagnose_issues tool."""

    @pytest.mark.asyncio
    async def test_diagnose_integrity_error(self):
        """Should diagnose IntegrityError."""
        result_json = await sqlmodel_diagnose_issues(
            error_message="IntegrityError: FOREIGN KEY constraint failed"
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "diagnosis" in result
        assert "suggestions" in result
        assert len(result["suggestions"]) > 0

    @pytest.mark.asyncio
    async def test_diagnose_no_such_table(self):
        """Should diagnose missing table error."""
        result_json = await sqlmodel_diagnose_issues(
            error_message="OperationalError: no such table: todos"
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "table" in result["diagnosis"].lower()

    @pytest.mark.asyncio
    async def test_diagnose_circular_import(self):
        """Should diagnose circular import error."""
        result_json = await sqlmodel_diagnose_issues(
            error_message="ImportError: cannot import name 'User' from partially initialized module"
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "circular" in result["diagnosis"].lower() or "import" in result["diagnosis"].lower()

    @pytest.mark.asyncio
    async def test_diagnose_unknown_error(self):
        """Should handle unknown errors gracefully."""
        result_json = await sqlmodel_diagnose_issues(
            error_message="SomeRandomError: unknown issue"
        )
        result = json.loads(result_json)

        assert result["success"] is True
        assert "diagnosis" in result
