"""
SQLModel ORM MCP Server.

Provides 8 tools for generating SQLModel ORM code:
- sqlmodel_generate_table: Generate table model definition
- sqlmodel_generate_schemas: Generate Create/Update/Read schemas
- sqlmodel_generate_relationship: Generate relationship code
- sqlmodel_generate_crud: Generate CRUD operations
- sqlmodel_generate_queries: Generate query patterns
- sqlmodel_generate_database_config: Generate database configuration
- sqlmodel_validate_model: Validate model definition
- sqlmodel_diagnose_issues: Diagnose common SQLModel issues

Based on: .claude/skills/sqlmodel-orm/
"""

import json
import re
from enum import Enum
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# =============================================================================
# MCP Server Instance
# =============================================================================

mcp = FastMCP("sqlmodel_orm_mcp")


# =============================================================================
# Enums
# =============================================================================


class RelationshipType(str, Enum):
    """Supported relationship types."""

    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"
    SELF_REFERENTIAL = "self_referential"


class DatabaseType(str, Enum):
    """Supported database types."""

    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    MYSQL = "mysql"


# =============================================================================
# Input Models
# =============================================================================


class FieldDefinition(BaseModel):
    """Definition of a SQLModel field."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(..., min_length=1, description="Field name")
    type: str = Field(
        ..., min_length=1, description="Python type (str, int, float, bool, datetime)"
    )
    optional: bool = Field(default=False, description="Whether field is Optional")
    default: Optional[Any] = Field(default=None, description="Default value")
    primary_key: bool = Field(default=False, description="Is primary key")
    foreign_key: Optional[str] = Field(
        default=None, description="Foreign key reference (table.column)"
    )
    unique: bool = Field(default=False, description="Unique constraint")
    index: bool = Field(default=False, description="Create index")
    max_length: Optional[int] = Field(
        default=None, description="Max length for strings"
    )
    min_length: Optional[int] = Field(
        default=None, description="Min length for strings"
    )
    ge: Optional[int] = Field(
        default=None, description="Greater than or equal (for numbers)"
    )
    le: Optional[int] = Field(
        default=None, description="Less than or equal (for numbers)"
    )


class GenerateTableInput(BaseModel):
    """Input for generating a SQLModel table."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    model_name: str = Field(
        ..., min_length=1, description="Model class name (PascalCase)"
    )
    table_name: str = Field(
        ..., min_length=1, description="Database table name (snake_case)"
    )
    fields: list[FieldDefinition] = Field(
        ..., min_length=1, description="Field definitions"
    )
    include_timestamps: bool = Field(
        default=False, description="Include created_at/updated_at"
    )

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        if not v or not v[0].isupper():
            raise ValueError("Model name must be PascalCase")
        return v


class GenerateSchemasInput(BaseModel):
    """Input for generating API schemas."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    model_name: str = Field(..., min_length=1, description="Model class name")
    fields: list[FieldDefinition] = Field(
        ..., min_length=1, description="Field definitions"
    )

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        if not v:
            raise ValueError("Model name is required")
        return v


class GenerateRelationshipInput(BaseModel):
    """Input for generating relationship code."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    parent_model: str = Field(..., min_length=1, description="Parent model name")
    child_model: str = Field(..., min_length=1, description="Child model name")
    relationship_type: RelationshipType = Field(..., description="Type of relationship")
    cascade_delete: bool = Field(default=False, description="Enable cascade delete")


class GenerateCrudInput(BaseModel):
    """Input for generating CRUD operations."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    model_name: str = Field(..., min_length=1, description="Model class name")

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        if not v:
            raise ValueError("Model name is required")
        return v


class GenerateQueriesInput(BaseModel):
    """Input for generating query patterns."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    model_name: str = Field(..., min_length=1, description="Model class name")
    include_pagination: bool = Field(
        default=True, description="Include pagination query"
    )
    filter_fields: Optional[list[str]] = Field(
        default=None, description="Fields to filter by"
    )


class GenerateDatabaseConfigInput(BaseModel):
    """Input for generating database configuration."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    database_type: DatabaseType = Field(..., description="Database type")
    database_name: str = Field(..., min_length=1, description="Database name")
    use_env_var: bool = Field(
        default=True, description="Use environment variable for URL"
    )
    host: str = Field(default="localhost", description="Database host")
    port: Optional[int] = Field(default=None, description="Database port")
    username: str = Field(default="user", description="Database username")


class ValidateModelInput(BaseModel):
    """Input for validating model code."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    model_code: str = Field(..., min_length=1, description="SQLModel code to validate")

    @field_validator("model_code")
    @classmethod
    def validate_model_code(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Model code is required")
        return v


class DiagnoseIssuesInput(BaseModel):
    """Input for diagnosing SQLModel issues."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    error_message: str = Field(
        ..., min_length=1, description="Error message to diagnose"
    )
    model_code: Optional[str] = Field(default=None, description="Related model code")


# =============================================================================
# Helper Functions
# =============================================================================


def _to_snake_case(name: str) -> str:
    """Convert PascalCase to snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _generate_field_code(field: FieldDefinition, is_schema: bool = False) -> str:
    """Generate code for a single field."""
    parts = []

    # Type annotation
    type_str = field.type
    if field.optional or (field.foreign_key and not is_schema):
        type_str = f"Optional[{field.type}]"

    parts.append(f"    {field.name}: {type_str}")

    # Field definition
    field_args = []

    if field.optional or field.primary_key:
        field_args.append("default=None")

    if field.default is not None and not field.optional:
        if isinstance(field.default, str):
            field_args.append(f'default="{field.default}"')
        else:
            field_args.append(f"default={field.default}")

    if field.primary_key:
        field_args.append("primary_key=True")

    if field.foreign_key and not is_schema:
        field_args.append(f'foreign_key="{field.foreign_key}"')

    if field.unique:
        field_args.append("unique=True")

    if field.index:
        field_args.append("index=True")

    if field.max_length:
        field_args.append(f"max_length={field.max_length}")

    if field.min_length:
        field_args.append(f"min_length={field.min_length}")

    if field.ge is not None:
        field_args.append(f"ge={field.ge}")

    if field.le is not None:
        field_args.append(f"le={field.le}")

    if field_args:
        parts.append(f" = Field({', '.join(field_args)})")

    return "".join(parts)


# =============================================================================
# MCP Tools
# =============================================================================


@mcp.tool()
async def sqlmodel_generate_table(
    model_name: str,
    table_name: str,
    fields: list[dict[str, Any]],
    include_timestamps: bool = False,
) -> str:
    """
    Generate a SQLModel table definition.

    Args:
        model_name: Model class name (PascalCase)
        table_name: Database table name (snake_case)
        fields: List of field definitions
        include_timestamps: Include created_at/updated_at fields

    Returns:
        JSON with generated code
    """
    # Validate input
    field_objs = [FieldDefinition(**f) for f in fields]
    _input = GenerateTableInput(
        model_name=model_name,
        table_name=table_name,
        fields=field_objs,
        include_timestamps=include_timestamps,
    )

    # Generate imports
    imports = [
        "from sqlmodel import SQLModel, Field",
        "from typing import Optional",
    ]
    if include_timestamps:
        imports.append("from datetime import datetime")

    # Check if any field has foreign key
    has_fk = any(f.foreign_key for f in field_objs)
    if has_fk:
        # Relationship import might be needed
        pass

    # Generate class
    lines = [
        "",
        f"class {model_name}(SQLModel, table=True):",
        f'    __tablename__ = "{table_name}"',
        "",
    ]

    # Add primary key if not present
    has_pk = any(f.primary_key for f in field_objs)
    if not has_pk:
        lines.append("    id: Optional[int] = Field(default=None, primary_key=True)")

    # Add fields
    for field in field_objs:
        lines.append(_generate_field_code(field))

    # Add timestamps
    if include_timestamps:
        lines.append("")
        lines.append(
            "    created_at: datetime = Field(default_factory=datetime.utcnow)"
        )
        lines.append(
            "    updated_at: datetime = Field(default_factory=datetime.utcnow)"
        )

    code = "\n".join(imports) + "\n" + "\n".join(lines)

    return json.dumps(
        {
            "success": True,
            "code": code,
            "model_name": model_name,
            "table_name": table_name,
            "field_count": len(field_objs),
        }
    )


@mcp.tool()
async def sqlmodel_generate_schemas(
    model_name: str,
    fields: list[dict[str, Any]],
) -> str:
    """
    Generate Create, Update, and Read schemas for FastAPI.

    Args:
        model_name: Model class name
        fields: List of field definitions

    Returns:
        JSON with generated schema code
    """
    field_objs = [FieldDefinition(**f) for f in fields]
    _input = GenerateSchemasInput(model_name=model_name, fields=field_objs)

    # Generate imports
    imports = [
        "from sqlmodel import SQLModel, Field",
        "from typing import Optional",
    ]

    lines = []

    # Create schema - required fields for creation
    lines.append("")
    lines.append(f"class {model_name}Create(SQLModel):")
    lines.append(f'    """Schema for creating a {model_name}."""')
    for field in field_objs:
        if not field.primary_key:  # Don't include PK in create
            lines.append(_generate_field_code(field, is_schema=True))

    # Update schema - all fields optional
    lines.append("")
    lines.append(f"class {model_name}Update(SQLModel):")
    lines.append(f'    """Schema for updating a {model_name}."""')
    for field in field_objs:
        if not field.primary_key:
            # Make all fields optional in update
            type_str = f"Optional[{field.type}]"
            field_args = ["default=None"]
            if field.max_length:
                field_args.append(f"max_length={field.max_length}")
            if field.min_length:
                field_args.append(f"min_length={field.min_length}")
            lines.append(
                f"    {field.name}: {type_str} = Field({', '.join(field_args)})"
            )

    # Read schema - includes id
    lines.append("")
    lines.append(f"class {model_name}Read(SQLModel):")
    lines.append(f'    """Schema for reading a {model_name}."""')
    lines.append("    id: int")
    for field in field_objs:
        if not field.primary_key:
            type_str = field.type
            if field.optional:
                type_str = f"Optional[{field.type}]"
            lines.append(f"    {field.name}: {type_str}")

    code = "\n".join(imports) + "\n" + "\n".join(lines)

    return json.dumps(
        {
            "success": True,
            "code": code,
            "schemas": [
                f"{model_name}Create",
                f"{model_name}Update",
                f"{model_name}Read",
            ],
        }
    )


@mcp.tool()
async def sqlmodel_generate_relationship(
    parent_model: str,
    child_model: str,
    relationship_type: str,
    cascade_delete: bool = False,
) -> str:
    """
    Generate relationship code between models.

    Args:
        parent_model: Parent model name
        child_model: Child model name
        relationship_type: one_to_many, many_to_many, or self_referential
        cascade_delete: Enable cascade delete

    Returns:
        JSON with relationship code
    """
    _input = GenerateRelationshipInput(
        parent_model=parent_model,
        child_model=child_model,
        relationship_type=RelationshipType(relationship_type),
        cascade_delete=cascade_delete,
    )

    parent_snake = _to_snake_case(parent_model)
    child_snake = _to_snake_case(child_model)

    imports = [
        "from sqlmodel import SQLModel, Field, Relationship",
        "from typing import Optional, List",
    ]

    lines = []

    if relationship_type == "one_to_many":
        # Parent model
        cascade_kwargs = ""
        if cascade_delete:
            cascade_kwargs = (
                ',\n        sa_relationship_kwargs={"cascade": "all, delete-orphan"}'
            )

        lines.append("")
        lines.append(f"# Add to {parent_model} model:")
        lines.append(
            f'    {child_snake}s: List["{child_model}"] = Relationship(back_populates="{parent_snake}"{cascade_kwargs})'
        )

        # Child model
        lines.append("")
        lines.append(f"# Add to {child_model} model:")
        lines.append(
            f'    {parent_snake}_id: Optional[int] = Field(default=None, foreign_key="{parent_snake}s.id")'
        )
        lines.append(
            f'    {parent_snake}: Optional[{parent_model}] = Relationship(back_populates="{child_snake}s")'
        )

    elif relationship_type == "many_to_many":
        # Link table
        link_table = f"{parent_model}{child_model}"
        link_table_name = f"{parent_snake}_{child_snake}"

        lines.append("")
        lines.append("# Link table (association table)")
        lines.append(f"class {link_table}(SQLModel, table=True):")
        lines.append(f'    __tablename__ = "{link_table_name}"')
        lines.append("")
        lines.append(
            f'    {parent_snake}_id: int = Field(foreign_key="{parent_snake}s.id", primary_key=True)'
        )
        lines.append(
            f'    {child_snake}_id: int = Field(foreign_key="{child_snake}s.id", primary_key=True)'
        )

        # Parent model
        lines.append("")
        lines.append(f"# Add to {parent_model} model:")
        lines.append(
            f'    {child_snake}s: List["{child_model}"] = Relationship(back_populates="{parent_snake}s", link_model={link_table})'
        )

        # Child model
        lines.append("")
        lines.append(f"# Add to {child_model} model:")
        lines.append(
            f'    {parent_snake}s: List[{parent_model}] = Relationship(back_populates="{child_snake}s", link_model={link_table})'
        )

    elif relationship_type == "self_referential":
        lines.append("")
        lines.append(f"# Self-referential relationship in {parent_model}:")
        lines.append(
            f'    parent_id: Optional[int] = Field(default=None, foreign_key="{parent_snake}s.id")'
        )
        lines.append("")
        lines.append(f'    parent: Optional["{parent_model}"] = Relationship(')
        lines.append('        back_populates="children",')
        lines.append(
            f'        sa_relationship_kwargs={{"remote_side": "{parent_model}.id"}}'
        )
        lines.append("    )")
        lines.append(
            f'    children: List["{parent_model}"] = Relationship(back_populates="parent")'
        )

    code = "\n".join(imports) + "\n" + "\n".join(lines)

    return json.dumps(
        {
            "success": True,
            "code": code,
            "relationship_type": relationship_type,
            "parent": parent_model,
            "child": child_model,
        }
    )


@mcp.tool()
async def sqlmodel_generate_crud(model_name: str) -> str:
    """
    Generate CRUD operations for a model.

    Args:
        model_name: Model class name

    Returns:
        JSON with CRUD function code
    """
    _input = GenerateCrudInput(model_name=model_name)

    snake_name = _to_snake_case(model_name)

    imports = [
        "from sqlmodel import Session, select",
        "from typing import Optional, List",
        f"from .models import {model_name}, {model_name}Create, {model_name}Update",
    ]

    code = "\n".join(imports) + f"""


def create_{snake_name}(session: Session, data: {model_name}Create) -> {model_name}:
    \"\"\"Create a new {model_name}.\"\"\"
    db_obj = {model_name}.model_validate(data)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_{snake_name}(session: Session, {snake_name}_id: int) -> Optional[{model_name}]:
    \"\"\"Get a {model_name} by ID.\"\"\"
    return session.get({model_name}, {snake_name}_id)


def get_{snake_name}s(session: Session, skip: int = 0, limit: int = 100) -> List[{model_name}]:
    \"\"\"Get all {model_name}s with pagination.\"\"\"
    statement = select({model_name}).offset(skip).limit(limit)
    return session.exec(statement).all()


def update_{snake_name}(
    session: Session,
    {snake_name}_id: int,
    data: {model_name}Update
) -> Optional[{model_name}]:
    \"\"\"Update a {model_name}.\"\"\"
    db_obj = session.get({model_name}, {snake_name}_id)
    if not db_obj:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_obj, key, value)

    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def delete_{snake_name}(session: Session, {snake_name}_id: int) -> bool:
    \"\"\"Delete a {model_name}.\"\"\"
    db_obj = session.get({model_name}, {snake_name}_id)
    if not db_obj:
        return False

    session.delete(db_obj)
    session.commit()
    return True
"""

    return json.dumps(
        {
            "success": True,
            "code": code,
            "functions": [
                f"create_{snake_name}",
                f"get_{snake_name}",
                f"get_{snake_name}s",
                f"update_{snake_name}",
                f"delete_{snake_name}",
            ],
        }
    )


@mcp.tool()
async def sqlmodel_generate_queries(
    model_name: str,
    include_pagination: bool = True,
    filter_fields: Optional[list[str]] = None,
) -> str:
    """
    Generate common query patterns.

    Args:
        model_name: Model class name
        include_pagination: Include pagination query
        filter_fields: Fields to generate filter queries for

    Returns:
        JSON with query code
    """
    _input = GenerateQueriesInput(
        model_name=model_name,
        include_pagination=include_pagination,
        filter_fields=filter_fields,
    )

    snake_name = _to_snake_case(model_name)

    imports = [
        "from sqlmodel import Session, select",
        "from typing import Optional, List",
        f"from .models import {model_name}",
    ]

    lines = []

    # Basic queries
    lines.append(f"""

def get_{snake_name}_by_id(session: Session, {snake_name}_id: int) -> Optional[{model_name}]:
    \"\"\"Get single {model_name} by ID.\"\"\"
    return session.get({model_name}, {snake_name}_id)


def get_all_{snake_name}s(session: Session) -> List[{model_name}]:
    \"\"\"Get all {model_name}s.\"\"\"
    statement = select({model_name})
    return session.exec(statement).all()
""")

    # Pagination
    if include_pagination:
        lines.append(f"""

def get_{snake_name}s_paginated(
    session: Session,
    offset: int = 0,
    limit: int = 10
) -> List[{model_name}]:
    \"\"\"Get {model_name}s with pagination.\"\"\"
    statement = select({model_name}).offset(offset).limit(limit)
    return session.exec(statement).all()
""")

    # Filter queries
    if filter_fields:
        for field in filter_fields:
            lines.append(f"""

def get_{snake_name}s_by_{field}(
    session: Session,
    {field}: str
) -> List[{model_name}]:
    \"\"\"Get {model_name}s filtered by {field}.\"\"\"
    statement = select({model_name}).where({model_name}.{field} == {field})
    return session.exec(statement).all()
""")

    code = "\n".join(imports) + "".join(lines)

    return json.dumps(
        {
            "success": True,
            "code": code,
            "include_pagination": include_pagination,
            "filter_fields": filter_fields or [],
        }
    )


@mcp.tool()
async def sqlmodel_generate_database_config(
    database_type: str,
    database_name: str,
    use_env_var: bool = True,
    host: str = "localhost",
    port: Optional[int] = None,
    username: str = "user",
) -> str:
    """
    Generate database configuration code.

    Args:
        database_type: postgresql, sqlite, or mysql
        database_name: Database name
        use_env_var: Use environment variable for connection URL
        host: Database host
        port: Database port
        username: Database username

    Returns:
        JSON with database config code
    """
    _input = GenerateDatabaseConfigInput(
        database_type=DatabaseType(database_type),
        database_name=database_name,
        use_env_var=use_env_var,
        host=host,
        port=port,
        username=username,
    )

    # Default ports
    default_ports = {
        "postgresql": 5432,
        "sqlite": None,
        "mysql": 3306,
    }
    actual_port = port or default_ports.get(database_type)

    imports = [
        "import os",
        "from sqlmodel import SQLModel, create_engine, Session",
        "from contextlib import contextmanager",
    ]

    if database_type == "sqlite":
        if use_env_var:
            url_code = (
                f'DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///{database_name}")'
            )
        else:
            url_code = f'DATABASE_URL = "sqlite:///{database_name}"'

        engine_code = """
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite
    echo=True  # Set to False in production
)
"""
    else:
        # PostgreSQL or MySQL
        if use_env_var:
            url_code = f"""DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "{database_type}://{username}:password@{host}:{actual_port}/{database_name}"
)"""
        else:
            url_code = f'DATABASE_URL = "{database_type}://{username}:password@{host}:{actual_port}/{database_name}"'

        engine_code = """
engine = create_engine(DATABASE_URL, echo=True)  # Set echo=False in production
"""

    code = "\n".join(imports) + f"""


# Database configuration
# Database type: {database_type}
{url_code}
{engine_code}

def create_db_and_tables():
    \"\"\"Create all tables in the database.\"\"\"
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session():
    \"\"\"Get a database session.\"\"\"
    with Session(engine) as session:
        yield session


# For FastAPI dependency injection
def get_db():
    \"\"\"FastAPI dependency for database session.\"\"\"
    with Session(engine) as session:
        yield session
"""

    return json.dumps(
        {
            "success": True,
            "code": code,
            "database_type": database_type,
            "database_name": database_name,
            "use_env_var": use_env_var,
        }
    )


@mcp.tool()
async def sqlmodel_validate_model(model_code: str) -> str:
    """
    Validate a SQLModel definition for common issues.

    Args:
        model_code: SQLModel code to validate

    Returns:
        JSON with validation results
    """
    _input = ValidateModelInput(model_code=model_code)

    issues: list[str] = []
    warnings: list[str] = []

    # Check for table=True
    has_table_true = "table=True" in model_code
    if not has_table_true and "SQLModel" in model_code:
        warnings.append(
            "Model does not have table=True - this is a schema, not a table model"
        )

    # Check for primary key
    has_primary_key = (
        "primary_key=True" in model_code or "primary_key = True" in model_code
    )
    if has_table_true and not has_primary_key:
        issues.append("Table model is missing a primary key field")

    # Check for mutable defaults
    mutable_patterns = [
        r":\s*list\s*=\s*\[\]",
        r":\s*dict\s*=\s*\{\}",
        r":\s*set\s*=\s*set\(\)",
    ]
    for pattern in mutable_patterns:
        if re.search(pattern, model_code):
            issues.append(
                "Mutable default value detected (use default_factory instead)"
            )
            break

    # Check for Optional without default=None
    optional_fields = re.findall(r":\s*Optional\[.*?\](?!\s*=)", model_code)
    if optional_fields:
        warnings.append("Optional fields should have default=None")

    # Check for relationship without back_populates
    if "Relationship(" in model_code and "back_populates" not in model_code:
        warnings.append("Relationship without back_populates may cause sync issues")

    # Check for __tablename__
    if has_table_true and "__tablename__" not in model_code:
        warnings.append("Consider adding explicit __tablename__ for clarity")

    valid = len(issues) == 0

    return json.dumps(
        {
            "valid": valid,
            "issues": issues,
            "warnings": warnings,
            "checks_performed": [
                "primary_key_check",
                "mutable_default_check",
                "optional_default_check",
                "relationship_back_populates_check",
                "tablename_check",
            ],
        }
    )


@mcp.tool()
async def sqlmodel_diagnose_issues(
    error_message: str,
    model_code: Optional[str] = None,
) -> str:
    """
    Diagnose common SQLModel issues from error messages.

    Args:
        error_message: Error message to diagnose
        model_code: Related model code (optional)

    Returns:
        JSON with diagnosis and suggestions
    """
    _input = DiagnoseIssuesInput(error_message=error_message, model_code=model_code)

    error_lower = error_message.lower()

    diagnosis = ""
    suggestions: list[str] = []

    # IntegrityError - Foreign Key
    if "integrityerror" in error_lower and "foreign key" in error_lower:
        diagnosis = "Foreign key constraint violation - referenced record doesn't exist or is being deleted"
        suggestions = [
            "Ensure the referenced record exists before creating the relationship",
            "Check if cascade delete is properly configured",
            "Verify foreign key column matches the referenced table's primary key type",
        ]

    # OperationalError - No such table
    elif "operationalerror" in error_lower and "no such table" in error_lower:
        diagnosis = "Table does not exist in the database"
        suggestions = [
            "Run SQLModel.metadata.create_all(engine) to create tables",
            "Check if the model has table=True",
            "Verify database connection and migrations",
        ]

    # ImportError - Circular
    elif "importerror" in error_lower and (
        "circular" in error_lower or "partially initialized" in error_lower
    ):
        diagnosis = "Circular import detected between model modules"
        suggestions = [
            "Use TYPE_CHECKING for forward references",
            "Use string annotations for relationship type hints",
            "Consider consolidating related models in one file",
            "Example: from typing import TYPE_CHECKING; if TYPE_CHECKING: from .user import User",
        ]

    # AttributeError - No attribute
    elif "attributeerror" in error_lower:
        diagnosis = "Model or field attribute not found"
        suggestions = [
            "Check field name spelling",
            "Ensure relationship is properly defined with back_populates",
            "Verify the model is imported correctly",
        ]

    # ProgrammingError - Column doesn't exist
    elif "programmingerror" in error_lower and "column" in error_lower:
        diagnosis = "Database schema mismatch - column doesn't exist or has wrong type"
        suggestions = [
            "Run database migration (alembic upgrade head)",
            "Recreate tables if in development",
            "Check for mismatched field names between model and database",
        ]

    # Generic/Unknown
    else:
        diagnosis = "SQLModel/SQLAlchemy error detected"
        suggestions = [
            "Check the full traceback for more details",
            "Verify database connection settings",
            "Ensure all model imports are correct",
            "Check SQLModel and SQLAlchemy documentation",
        ]

    return json.dumps(
        {
            "success": True,
            "diagnosis": diagnosis,
            "suggestions": suggestions,
            "error_type": (
                error_message.split(":")[0] if ":" in error_message else "Unknown"
            ),
        }
    )


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    mcp.run(transport="stdio")
