"""
FastAPI Backend MCP Server — generates project scaffolds, CRUD endpoints,
models, schemas, error handlers, and provides diagnostic guidance.

Tools:
    fastapi_scaffold_project       Generate full FastAPI project structure
    fastapi_generate_endpoint      Generate CRUD router for a resource
    fastapi_generate_model         Generate SQLModel database model
    fastapi_generate_schema        Generate Pydantic request/response schemas
    fastapi_generate_error_handlers Generate error handling boilerplate
    fastapi_suggest_crud_pattern   Suggest advanced CRUD pattern implementation
    fastapi_validate_project       Validate project against quality checklist
    fastapi_diagnose_issue         Diagnose common FastAPI issues
"""

import json
import re
import textwrap
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("fastapi_backend_mcp")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_OPERATIONS = ("list", "get", "create", "update", "delete")

VALID_CRUD_PATTERNS = (
    "pagination",
    "filtering",
    "sorting",
    "bulk_operations",
    "soft_delete",
    "search",
    "upsert",
    "partial_update",
)

VALID_SYMPTOMS = (
    "server_wont_start",
    "422_validation_error",
    "cors_error",
    "database_connection_failed",
    "500_internal_error",
    "dependency_injection_error",
    "async_issues",
    "response_model_mismatch",
    "path_parameter_issues",
)

VALID_DATABASE_TYPES = ("postgresql", "sqlite", "mysql")

# Secrets pattern for validation
_SECRETS_PATTERN = re.compile(
    r"""(?:password|secret|token|api_key|credential)\s*=\s*["'][^"']+["']""",
    re.IGNORECASE,
)

# Matches hardcoded DB URLs: DATABASE_URL = "postgresql://user:pass@host/db"
_HARDCODED_URL_PATTERN = re.compile(
    r"""(?:DATABASE_URL|DB_URL)\s*=\s*["'](?:postgresql|mysql|sqlite)\S+["']""",
    re.IGNORECASE,
)


def _check_path_traversal(v: str) -> str:
    if ".." in v:
        raise ValueError("Path traversal not allowed: '..' in path")
    return v


# ---------------------------------------------------------------------------
# Pydantic Input Models
# ---------------------------------------------------------------------------


class FieldSpec(BaseModel):
    """Specification for a single model/schema field."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    optional: bool = Field(False)
    default: Optional[str] = Field(None)
    max_length: Optional[int] = Field(None)
    index: bool = Field(False)
    unique: bool = Field(False)
    foreign_key: Optional[str] = Field(None)


class ScaffoldProjectInput(BaseModel):
    """Input for fastapi_scaffold_project."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    project_name: str = Field(..., min_length=1, description="Project name")
    resource_name: Optional[str] = Field(
        None, description="Initial resource to scaffold"
    )
    database_type: Optional[str] = Field(
        None, description="Database type: postgresql, sqlite, mysql"
    )

    @field_validator("project_name")
    @classmethod
    def validate_project_name(cls, v: str) -> str:
        return _check_path_traversal(v)

    @field_validator("database_type")
    @classmethod
    def validate_database_type(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_DATABASE_TYPES:
            raise ValueError(f"database_type must be one of {VALID_DATABASE_TYPES}")
        return v


class GenerateEndpointInput(BaseModel):
    """Input for fastapi_generate_endpoint."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    resource_name: str = Field(
        ..., min_length=1, description="Resource name (e.g. 'todo')"
    )
    operations: list[str] = Field(
        ..., min_length=1, description="CRUD operations to include"
    )
    prefix: Optional[str] = Field(None, description="Custom URL prefix")

    @field_validator("resource_name")
    @classmethod
    def validate_resource_name(cls, v: str) -> str:
        return _check_path_traversal(v)

    @field_validator("operations")
    @classmethod
    def validate_operations(cls, v: list[str]) -> list[str]:
        for op in v:
            if op not in VALID_OPERATIONS:
                raise ValueError(
                    f"Invalid operation '{op}'. Must be one of {VALID_OPERATIONS}"
                )
        return v


class GenerateModelInput(BaseModel):
    """Input for fastapi_generate_model."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    model_name: str = Field(..., min_length=1, description="Model class name")
    fields: list[FieldSpec] = Field(..., min_length=1, description="Field definitions")
    table_name: Optional[str] = Field(None, description="Custom table name")
    timestamps: bool = Field(False, description="Add created_at/updated_at")
    soft_delete: bool = Field(False, description="Add deleted_at for soft deletes")


class GenerateSchemaInput(BaseModel):
    """Input for fastapi_generate_schema."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    model_name: str = Field(
        ..., min_length=1, description="Model name for schema generation"
    )
    fields: list[FieldSpec] = Field(..., min_length=1, description="Field definitions")
    include_update: bool = Field(False, description="Generate Update schema")
    include_list: bool = Field(False, description="Generate paginated list schema")


class GenerateErrorHandlersInput(BaseModel):
    """Input for fastapi_generate_error_handlers."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    include_request_id: bool = Field(False, description="Include request ID middleware")
    include_logging: bool = Field(False, description="Include logging setup")


class SuggestCrudPatternInput(BaseModel):
    """Input for fastapi_suggest_crud_pattern."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    pattern_name: str = Field(..., description="CRUD pattern name")

    @field_validator("pattern_name")
    @classmethod
    def validate_pattern_name(cls, v: str) -> str:
        if v not in VALID_CRUD_PATTERNS:
            raise ValueError(f"pattern_name must be one of {VALID_CRUD_PATTERNS}")
        return v


class ValidateProjectInput(BaseModel):
    """Input for fastapi_validate_project."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    project_files: dict[str, str] = Field(
        ..., min_length=1, description="Map of filename -> content"
    )

    @field_validator("project_files")
    @classmethod
    def validate_project_files(cls, v: dict[str, str]) -> dict[str, str]:
        if not v:
            raise ValueError("project_files must not be empty")
        return v


class DiagnoseIssueInput(BaseModel):
    """Input for fastapi_diagnose_issue."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    symptom: str = Field(..., min_length=1, description="Issue symptom identifier")

    @field_validator("symptom")
    @classmethod
    def validate_symptom(cls, v: str) -> str:
        if v not in VALID_SYMPTOMS:
            raise ValueError(f"symptom must be one of {VALID_SYMPTOMS}")
        return v


# ---------------------------------------------------------------------------
# Code generators (deterministic, pure functions)
# ---------------------------------------------------------------------------


def _gen_main_py(project_name: str, resource_name: str | None) -> str:
    router_import = ""
    router_include = ""
    if resource_name:
        plural = (
            resource_name + "s" if not resource_name.endswith("s") else resource_name
        )
        router_import = f"from routers import {plural}\n"
        router_include = f"app.include_router({plural}.router)\n"

    return f'''\
"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import create_db_and_tables
{router_import}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    create_db_and_tables()
    yield


app = FastAPI(
    title="{project_name}",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
{router_include}

@app.get("/")
async def root():
    """Root endpoint."""
    return {{"message": "{project_name}", "version": "1.0.0"}}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {{"status": "healthy"}}
'''


def _gen_database_py(database_type: str | None) -> str:
    db_type = database_type or "postgresql"

    if db_type == "sqlite":
        extra_args = ', connect_args={"check_same_thread": False}'
        db_comment = "# Database type: sqlite"
    elif db_type == "mysql":
        extra_args = ""
        db_comment = "# Database type: mysql"
    else:
        extra_args = ""
        db_comment = "# Database type: postgresql"

    return f'''\
"""Database configuration and session management."""
{db_comment}
from sqlmodel import SQLModel, Session, create_engine
from typing import Generator
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

engine = create_engine(DATABASE_URL, echo=True{extra_args})


def create_db_and_tables():
    """Create all database tables."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Dependency to get database session."""
    with Session(engine) as session:
        yield session
'''


def _gen_requirements() -> str:
    return """\
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlmodel==0.0.14
psycopg2-binary==2.9.9
python-dotenv==1.0.0
"""


def _gen_env_example(database_type: str | None) -> str:
    db_type = database_type or "postgresql"

    if db_type == "sqlite":
        url_example = "sqlite:///./app.db"
    elif db_type == "mysql":
        url_example = "mysql+pymysql://user:password@localhost:3306/database"
    else:
        url_example = "postgresql://user:password@localhost:5432/database"

    return f"""\
# Database
DATABASE_URL={url_example}

# Environment
ENVIRONMENT=development
"""


def _gen_gitignore() -> str:
    return """\
.env
.env.local
.env.production
__pycache__/
*.pyc
.venv/
venv/
"""


def _gen_router(resource_name: str, operations: list[str], prefix: str | None) -> str:
    singular = resource_name
    plural = resource_name + "s" if not resource_name.endswith("s") else resource_name
    cap = singular.capitalize()
    url_prefix = prefix or f"/api/{plural}"

    lines = [
        f'"""{ cap } API endpoints."""',
        "from fastapi import APIRouter, Depends, HTTPException, status",
        "from sqlmodel import Session, select",
        "",
        "from database import get_session",
        f"# from models.{singular} import {cap}",
        f"# from schemas.{singular} import {cap}Create, {cap}Update, {cap}Response",
        "",
        f'router = APIRouter(prefix="{url_prefix}", tags=["{plural}"])',
        "",
    ]

    if "list" in operations:
        lines.extend(
            [
                "",
                f'@router.get("/")',
                f"async def list_{plural}(session: Session = Depends(get_session)):",
                f'    """List all {plural}."""',
                f"    # statement = select({cap})",
                f"    # return session.exec(statement).all()",
                f"    return []",
                "",
            ]
        )

    if "get" in operations:
        lines.extend(
            [
                "",
                f'@router.get("/{{{singular}_id}}")',
                f"async def get_{singular}({singular}_id: int, session: Session = Depends(get_session)):",
                f'    """Get a single {singular} by ID."""',
                f"    # {singular} = session.get({cap}, {singular}_id)",
                f"    # if not {singular}:",
                f'    #     raise HTTPException(status_code=404, detail="{cap} not found")',
                f"    # return {singular}",
                f'    raise HTTPException(status_code=404, detail="{cap} not found")',
                "",
            ]
        )

    if "create" in operations:
        lines.extend(
            [
                "",
                f'@router.post("/", status_code=status.HTTP_201_CREATED)',
                f"async def create_{singular}(session: Session = Depends(get_session)):",
                f'    """Create a new {singular}."""',
                f"    # Implement creation logic",
                f"    pass",
                "",
            ]
        )

    if "update" in operations:
        lines.extend(
            [
                "",
                f'@router.put("/{{{singular}_id}}")',
                f"async def update_{singular}({singular}_id: int, session: Session = Depends(get_session)):",
                f'    """Update an existing {singular}."""',
                f"    # Implement update logic",
                f"    pass",
                "",
            ]
        )

    if "delete" in operations:
        lines.extend(
            [
                "",
                f'@router.delete("/{{{singular}_id}}", status_code=status.HTTP_204_NO_CONTENT)',
                f"async def delete_{singular}({singular}_id: int, session: Session = Depends(get_session)):",
                f'    """Delete a {singular}."""',
                f"    # Implement delete logic",
                f"    pass",
                "",
            ]
        )

    return "\n".join(lines)


def _gen_model(
    model_name: str,
    fields: list[dict],
    table_name: str | None,
    timestamps: bool,
    soft_delete: bool,
) -> str:
    tbl = table_name or (model_name.lower() + "s")

    lines = [
        f'"""SQLModel definition for {model_name}."""',
        "from sqlmodel import SQLModel, Field",
        "from typing import Optional",
    ]

    need_datetime = timestamps or soft_delete
    if need_datetime:
        lines.append("from datetime import datetime")

    lines.extend(["", ""])

    lines.append(f"class {model_name}(SQLModel, table=True):")
    lines.append(f'    __tablename__ = "{tbl}"')
    lines.append("")
    lines.append("    id: int | None = Field(default=None, primary_key=True)")

    for f in fields:
        field_parts = []
        if f.get("optional"):
            type_str = f"Optional[{f['type']}]"
            field_parts.append(f"default=None")
        else:
            type_str = f["type"]

        if f.get("max_length"):
            field_parts.append(f"max_length={f['max_length']}")
        if f.get("index"):
            field_parts.append("index=True")
        if f.get("unique"):
            field_parts.append("unique=True")
        if f.get("foreign_key"):
            field_parts.append(f'foreign_key="{f["foreign_key"]}"')
        if f.get("default") is not None and not f.get("optional"):
            field_parts.append(f'default="{f["default"]}"')

        if field_parts:
            lines.append(
                f"    {f['name']}: {type_str} = Field({', '.join(field_parts)})"
            )
        else:
            lines.append(f"    {f['name']}: {type_str}")

    if timestamps:
        lines.append(
            "    created_at: datetime = Field(default_factory=datetime.utcnow)"
        )
        lines.append(
            "    updated_at: datetime = Field(default_factory=datetime.utcnow)"
        )

    if soft_delete:
        lines.append("    deleted_at: Optional[datetime] = Field(default=None)")

    lines.append("")
    return "\n".join(lines)


def _gen_schema(
    model_name: str,
    fields: list[dict],
    include_update: bool,
    include_list: bool,
) -> str:
    lines = [
        f'"""Pydantic schemas for {model_name}."""',
        "from pydantic import BaseModel, Field",
        "from datetime import datetime",
        "from typing import Optional, List",
        "",
        "",
    ]

    # Base schema
    lines.append(f"class {model_name}Base(BaseModel):")
    lines.append(f'    """{model_name} base schema with shared fields."""')
    for f in fields:
        field_parts = []
        if f.get("optional"):
            type_str = f"Optional[{f['type']}]"
            field_parts.append("default=None")
        else:
            type_str = f["type"]
            field_parts.append("...")

        if f.get("max_length"):
            field_parts.append(f"max_length={f['max_length']}")

        lines.append(f"    {f['name']}: {type_str} = Field({', '.join(field_parts)})")

    lines.extend(["", ""])

    # Create schema
    lines.append(f"class {model_name}Create({model_name}Base):")
    lines.append(f'    """{model_name} creation schema."""')
    lines.append("    pass")
    lines.extend(["", ""])

    # Update schema (optional)
    if include_update:
        lines.append(f"class {model_name}Update(BaseModel):")
        lines.append(f'    """{model_name} update schema (all fields optional)."""')
        for f in fields:
            field_parts = ["default=None"]
            if f.get("max_length"):
                field_parts.append(f"max_length={f['max_length']}")
            lines.append(
                f"    {f['name']}: Optional[{f['type']}] = Field({', '.join(field_parts)})"
            )
        lines.extend(["", ""])

    # Response schema
    lines.append(f"class {model_name}Response({model_name}Base):")
    lines.append(f'    """{model_name} response schema."""')
    lines.append("    id: int")
    lines.append("    created_at: datetime")
    lines.append("    updated_at: datetime")
    lines.append("")
    lines.append("    class Config:")
    lines.append("        from_attributes = True")
    lines.extend(["", ""])

    # List schema (optional)
    if include_list:
        lines.append(f"class {model_name}ListResponse(BaseModel):")
        lines.append(f'    """Paginated list response for {model_name}."""')
        lines.append(f"    items: List[{model_name}Response]")
        lines.append("    total: int")
        lines.append("    page: int")
        lines.append("    page_size: int")
        lines.append("    pages: int")
        lines.append("")

    return "\n".join(lines)


def _gen_error_handlers(include_request_id: bool, include_logging: bool) -> str:
    lines = [
        '"""Error handling and exception handlers for FastAPI."""',
        "from fastapi import FastAPI, Request",
        "from fastapi.responses import JSONResponse",
        "from fastapi.exceptions import RequestValidationError",
    ]

    if include_logging:
        lines.append("import logging")
        lines.append("")
        lines.append("logger = logging.getLogger(__name__)")

    if include_request_id:
        lines.append("import uuid")
        lines.append("from starlette.middleware.base import BaseHTTPMiddleware")

    lines.extend(["", ""])

    if include_request_id:
        lines.extend(
            [
                "class RequestIDMiddleware(BaseHTTPMiddleware):",
                '    """Add X-Request-ID to every request/response."""',
                "",
                "    async def dispatch(self, request: Request, call_next):",
                "        request_id = str(uuid.uuid4())",
                "        request.state.request_id = request_id",
                "        response = await call_next(request)",
                '        response.headers["X-Request-ID"] = request_id',
                "        return response",
                "",
                "",
            ]
        )

    lines.extend(
        [
            "def register_exception_handlers(app: FastAPI) -> None:",
            '    """Register global exception handlers on the app."""',
            "",
            "    @app.exception_handler(RequestValidationError)",
            "    async def validation_exception_handler(request: Request, exc: RequestValidationError):",
            '        """Handle Pydantic validation errors."""',
        ]
    )

    if include_logging:
        lines.append('        logger.error(f"Validation error: {exc.errors()}")')

    lines.extend(
        [
            "        return JSONResponse(",
            "            status_code=422,",
            "            content={",
            '                "detail": "Validation error",',
            '                "errors": exc.errors(),',
            "            },",
            "        )",
            "",
            "    @app.exception_handler(Exception)",
            "    async def general_exception_handler(request: Request, exc: Exception):",
            '        """Catch-all for unexpected errors."""',
        ]
    )

    if include_logging:
        lines.append(
            '        logger.error(f"Unexpected error: {str(exc)}", exc_info=True)'
        )

    lines.extend(
        [
            "        return JSONResponse(",
            "            status_code=500,",
            '            content={"detail": "Internal server error"},',
            "        )",
            "",
        ]
    )

    if include_request_id:
        lines.extend(
            [
                "",
                "def register_middleware(app: FastAPI) -> None:",
                '    """Register middleware on the app."""',
                "    app.add_middleware(RequestIDMiddleware)",
                "",
            ]
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CRUD pattern templates
# ---------------------------------------------------------------------------

CRUD_PATTERNS: dict[str, dict] = {
    "pagination": {
        "code": textwrap.dedent("""\
            from pydantic import BaseModel
            from fastapi import Query
            from sqlmodel import select, func

            class PaginatedResponse(BaseModel):
                items: list
                total: int
                page: int
                page_size: int
                pages: int

            @router.get("/paginated")
            async def list_paginated(
                page: int = Query(1, ge=1),
                page_size: int = Query(10, ge=1, le=100),
                session: Session = Depends(get_session),
            ):
                count_query = select(func.count()).select_from(Model)
                total = session.exec(count_query).one()
                query = select(Model).offset((page - 1) * page_size).limit(page_size)
                items = session.exec(query).all()
                return PaginatedResponse(
                    items=items,
                    total=total,
                    page=page,
                    page_size=page_size,
                    pages=(total + page_size - 1) // page_size,
                )
        """),
        "notes": [
            "Replace 'Model' with your SQLModel class",
            "page_size max of 100 prevents large queries",
            "Returns total count for client-side pagination UI",
        ],
    },
    "filtering": {
        "code": textwrap.dedent("""\
            from typing import Optional
            from fastapi import Query
            from sqlmodel import select

            @router.get("/")
            async def list_filtered(
                status: Optional[str] = Query(None, regex="^(active|completed)$"),
                title: Optional[str] = Query(None, min_length=1),
                limit: int = Query(100, ge=1, le=1000),
                offset: int = Query(0, ge=0),
                session: Session = Depends(get_session),
            ):
                query = select(Model)
                if status:
                    query = query.where(Model.status == status)
                if title:
                    query = query.where(Model.title.contains(title))
                query = query.offset(offset).limit(limit)
                return session.exec(query).all()
        """),
        "notes": [
            "Use Query() with regex for enum-like validation",
            "Always apply limit to prevent unbounded queries",
            "Add index on frequently filtered columns",
        ],
    },
    "sorting": {
        "code": textwrap.dedent("""\
            from fastapi import Query
            from sqlmodel import select, asc, desc

            @router.get("/")
            async def list_sorted(
                sort_by: str = Query("created_at", regex="^(id|title|status|created_at)$"),
                sort_order: str = Query("asc", regex="^(asc|desc)$"),
                session: Session = Depends(get_session),
            ):
                query = select(Model)
                column = getattr(Model, sort_by)
                if sort_order == "desc":
                    query = query.order_by(desc(column))
                else:
                    query = query.order_by(asc(column))
                return session.exec(query).all()
        """),
        "notes": [
            "Whitelist sortable columns via regex to prevent injection",
            "Default sort by created_at for consistent ordering",
            "Add database index on sortable columns",
        ],
    },
    "bulk_operations": {
        "code": textwrap.dedent("""\
            from fastapi import status
            from sqlmodel import select

            @router.post("/bulk", status_code=status.HTTP_201_CREATED)
            async def bulk_create(
                items_data: list[ItemCreate],
                session: Session = Depends(get_session),
            ):
                if len(items_data) > 100:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot create more than 100 items at once",
                    )
                items = [Model(**item.model_dump()) for item in items_data]
                session.add_all(items)
                session.commit()
                for item in items:
                    session.refresh(item)
                return items

            @router.delete("/bulk", status_code=status.HTTP_204_NO_CONTENT)
            async def bulk_delete(
                item_ids: list[int],
                session: Session = Depends(get_session),
            ):
                if len(item_ids) > 100:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot delete more than 100 items at once",
                    )
                query = select(Model).where(Model.id.in_(item_ids))
                items = session.exec(query).all()
                if not items:
                    raise HTTPException(status_code=404, detail="No items found")
                for item in items:
                    session.delete(item)
                session.commit()
        """),
        "notes": [
            "Always cap bulk operations (100 is a safe default)",
            "Use transactions (session.commit at the end)",
            "Return 204 for bulk delete, 201 for bulk create",
        ],
    },
    "soft_delete": {
        "code": textwrap.dedent("""\
            from datetime import datetime
            from fastapi import status
            from sqlmodel import select

            @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
            async def soft_delete(
                item_id: int,
                session: Session = Depends(get_session),
            ):
                item = session.get(Model, item_id)
                if not item or item.deleted_at:
                    raise HTTPException(status_code=404, detail="Item not found")
                item.deleted_at = datetime.utcnow()
                session.add(item)
                session.commit()

            @router.get("/")
            async def list_items(
                include_deleted: bool = False,
                session: Session = Depends(get_session),
            ):
                query = select(Model)
                if not include_deleted:
                    query = query.where(Model.deleted_at == None)  # noqa: E711
                return session.exec(query).all()
        """),
        "notes": [
            "Add deleted_at: Optional[datetime] = Field(default=None) to model",
            "Filter out soft-deleted records by default",
            "Consider a scheduled job to purge old soft-deleted records",
        ],
    },
    "search": {
        "code": textwrap.dedent("""\
            from fastapi import Query
            from sqlmodel import select

            @router.get("/search")
            async def search_items(
                q: str = Query(..., min_length=1),
                session: Session = Depends(get_session),
            ):
                query = select(Model).where(Model.title.ilike(f"%{q}%"))
                return session.exec(query).all()
        """),
        "notes": [
            "ilike provides case-insensitive LIKE matching",
            "For full-text search, consider PostgreSQL tsvector",
            "Add a GIN index for better search performance",
        ],
    },
    "upsert": {
        "code": textwrap.dedent("""\
            from datetime import datetime

            @router.put("/upsert/{item_id}")
            async def upsert_item(
                item_id: int,
                item_data: ItemCreate,
                session: Session = Depends(get_session),
            ):
                \"\"\"Create or update an item (upsert pattern).\"\"\"
                item = session.get(Model, item_id)
                if item:
                    for key, value in item_data.model_dump().items():
                        setattr(item, key, value)
                    item.updated_at = datetime.utcnow()
                else:
                    item = Model(id=item_id, **item_data.model_dump())
                session.add(item)
                session.commit()
                session.refresh(item)
                return item
        """),
        "notes": [
            "Upsert = update if exists, insert if not",
            "Some databases support native UPSERT (INSERT ON CONFLICT)",
            "Useful for idempotent API endpoints",
        ],
    },
    "partial_update": {
        "code": textwrap.dedent("""\
            from datetime import datetime
            from fastapi import status

            @router.patch("/{item_id}")
            async def partial_update(
                item_id: int,
                item_data: ItemUpdate,
                session: Session = Depends(get_session),
            ):
                item = session.get(Model, item_id)
                if not item:
                    raise HTTPException(status_code=404, detail="Item not found")
                update_data = item_data.model_dump(exclude_unset=True)
                if not update_data:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No fields to update",
                    )
                for key, value in update_data.items():
                    setattr(item, key, value)
                item.updated_at = datetime.utcnow()
                session.add(item)
                session.commit()
                session.refresh(item)
                return item
        """),
        "notes": [
            "Use PATCH for partial updates, PUT for full replacement",
            "exclude_unset=True ignores fields not sent by the client",
            "Always update the updated_at timestamp",
        ],
    },
}


# ---------------------------------------------------------------------------
# Diagnostic knowledge base
# ---------------------------------------------------------------------------

DIAGNOSES: dict[str, dict] = {
    "server_wont_start": {
        "diagnosis": "Server fails to start — common causes include port conflicts, missing modules, or incorrect app path.",
        "solutions": [
            "Check if port is in use: lsof -i :8000 and kill the process",
            "Use a different port: uvicorn main:app --port 8001",
            "Verify module path: pip install -e . or set PYTHONPATH",
            "Check app path matches: uvicorn main:app (file is main.py, variable is app)",
        ],
    },
    "422_validation_error": {
        "diagnosis": "422 Unprocessable Entity — request body does not match the Pydantic schema.",
        "solutions": [
            "Check JSON body keys match schema field names exactly",
            "Verify field types (send number, not string '10.5' for float fields)",
            "Ensure all required fields are included in the request body",
            "Check Content-Type header is 'application/json'",
            "Use /docs endpoint to test with correct schema",
        ],
    },
    "cors_error": {
        "diagnosis": "CORS error — browser blocks cross-origin requests when CORSMiddleware is not configured or misconfigured.",
        "solutions": [
            "Add CORSMiddleware to your FastAPI app",
            "Set allow_origins to your frontend URL (e.g., ['http://localhost:3000'])",
            "For development, use allow_origins=['*'] (not for production)",
            "Ensure allow_credentials=True if sending cookies",
            "Check that allow_methods and allow_headers are set to ['*']",
        ],
    },
    "database_connection_failed": {
        "diagnosis": "Database connection failed — OperationalError or 'Connection refused' typically means the database is unreachable.",
        "solutions": [
            "Verify DATABASE_URL environment variable is set correctly",
            "Ensure .env file is loaded: call load_dotenv() before os.getenv()",
            "Check database server is running and accessible",
            "Verify credentials and database name in the connection string",
            'Test connection: python -c "from sqlalchemy import create_engine, text; ..."',
        ],
    },
    "500_internal_error": {
        "diagnosis": "500 Internal Server Error — an unhandled exception occurred in the application.",
        "solutions": [
            "Run with uvicorn main:app --reload to see detailed tracebacks",
            "Add logging: import logging; logging.basicConfig(level=logging.DEBUG)",
            "Add a global exception handler to catch and log all errors",
            "Check database operations for unhandled IntegrityError/SQLAlchemyError",
            "Review the full traceback in the terminal output",
        ],
    },
    "dependency_injection_error": {
        "diagnosis": "Dependency injection error — common when using Depends() incorrectly or calling dependencies directly.",
        "solutions": [
            "Use Depends(get_session), NOT get_session() (no parentheses call)",
            "Ensure dependency function uses 'yield' for cleanup (generator pattern)",
            "For class-based dependencies, accept Depends in __init__",
            "Verify the dependency function signature matches what the endpoint expects",
        ],
    },
    "async_issues": {
        "diagnosis": "Async/await issues — blocking the event loop or forgetting to await coroutines.",
        "solutions": [
            "Don't use async def with synchronous database calls — use def instead",
            "Always await async functions: result = await async_function()",
            "For sync code in async endpoints, use run_in_executor()",
            "Check for 'RuntimeWarning: coroutine was never awaited' in logs",
            "Use async database drivers (asyncpg) for true async DB operations",
        ],
    },
    "response_model_mismatch": {
        "diagnosis": "Response model mismatch — ResponseValidationError when returned data doesn't match the response_model schema.",
        "solutions": [
            "Ensure all required fields in response_model are present in the return value",
            "Add 'class Config: from_attributes = True' to response models for ORM objects",
            "Check that field types match (e.g., datetime fields are actual datetime objects)",
            "Remove response_model temporarily to see the raw response and identify mismatches",
        ],
    },
    "path_parameter_issues": {
        "diagnosis": "Path parameter issues — 404 errors for valid paths, often caused by route ordering or type conversion.",
        "solutions": [
            "Put specific routes before parameterized ones: /users/me before /users/{id}",
            "Use type hints for auto-conversion: async def get_item(item_id: int)",
            "Check route prefix doesn't conflict with other routers",
            "Verify the parameter name in the path matches the function parameter name",
        ],
    },
}


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def fastapi_scaffold_project(
    project_name: str,
    resource_name: str | None = None,
    database_type: str | None = None,
) -> str:
    """Generate a complete FastAPI project structure with best practices.

    Returns JSON: {status, files}
    Each file has: {path, content}
    Includes main.py, database.py, router, schemas, env files, requirements.
    """
    files = []

    # main.py
    files.append(
        {
            "path": "main.py",
            "content": _gen_main_py(project_name, resource_name),
        }
    )

    # database.py
    files.append(
        {
            "path": "database.py",
            "content": _gen_database_py(database_type),
        }
    )

    # requirements.txt
    files.append(
        {
            "path": "requirements.txt",
            "content": _gen_requirements(),
        }
    )

    # .env.example
    files.append(
        {
            "path": ".env.example",
            "content": _gen_env_example(database_type),
        }
    )

    # .gitignore
    files.append(
        {
            "path": ".gitignore",
            "content": _gen_gitignore(),
        }
    )

    # Router for resource
    if resource_name:
        plural = (
            resource_name + "s" if not resource_name.endswith("s") else resource_name
        )
        files.append(
            {
                "path": f"routers/{plural}.py",
                "content": _gen_router(
                    resource_name,
                    ["list", "get", "create", "update", "delete"],
                    None,
                ),
            }
        )

        files.append(
            {
                "path": f"routers/__init__.py",
                "content": "",
            }
        )

        files.append(
            {
                "path": f"schemas/{resource_name}.py",
                "content": _gen_schema(
                    resource_name.capitalize(),
                    [{"name": "name", "type": "str"}],
                    include_update=True,
                    include_list=False,
                ),
            }
        )

        files.append(
            {
                "path": f"schemas/__init__.py",
                "content": "",
            }
        )

    return json.dumps(
        {
            "status": "success",
            "files": files,
        }
    )


@mcp.tool()
async def fastapi_generate_endpoint(
    resource_name: str,
    operations: list[str],
    prefix: str | None = None,
) -> str:
    """Generate a FastAPI CRUD router for a resource.

    Returns JSON: {status, code}
    Includes proper HTTP status codes and error handling.
    """
    code = _gen_router(resource_name, operations, prefix)

    return json.dumps(
        {
            "status": "success",
            "code": code,
        }
    )


@mcp.tool()
async def fastapi_generate_model(
    model_name: str,
    fields: list[dict],
    table_name: str | None = None,
    timestamps: bool = False,
    soft_delete: bool = False,
) -> str:
    """Generate a SQLModel database model definition.

    Returns JSON: {status, code}
    Includes primary key, field constraints, and optional timestamps/soft delete.
    """
    code = _gen_model(model_name, fields, table_name, timestamps, soft_delete)

    return json.dumps(
        {
            "status": "success",
            "code": code,
        }
    )


@mcp.tool()
async def fastapi_generate_schema(
    model_name: str,
    fields: list[dict],
    include_update: bool = False,
    include_list: bool = False,
) -> str:
    """Generate Pydantic request/response schemas for a resource.

    Returns JSON: {status, code}
    Generates Base, Create, Response schemas. Optionally Update and List schemas.
    """
    code = _gen_schema(model_name, fields, include_update, include_list)

    return json.dumps(
        {
            "status": "success",
            "code": code,
        }
    )


@mcp.tool()
async def fastapi_generate_error_handlers(
    include_request_id: bool = False,
    include_logging: bool = False,
) -> str:
    """Generate error handling boilerplate for FastAPI.

    Returns JSON: {status, code}
    Includes global exception handlers, validation error handling,
    and optionally request ID middleware and logging.
    """
    code = _gen_error_handlers(include_request_id, include_logging)

    return json.dumps(
        {
            "status": "success",
            "code": code,
        }
    )


@mcp.tool()
async def fastapi_suggest_crud_pattern(
    pattern_name: str,
) -> str:
    """Suggest implementation code for an advanced CRUD pattern.

    Returns JSON: {status, pattern, code, notes}
    Patterns: pagination, filtering, sorting, bulk_operations,
    soft_delete, search, upsert, partial_update
    """
    pattern = CRUD_PATTERNS[pattern_name]

    return json.dumps(
        {
            "status": "success",
            "pattern": pattern_name,
            "code": pattern["code"],
            "notes": pattern["notes"],
        }
    )


@mcp.tool()
async def fastapi_validate_project(
    project_files: dict[str, str],
) -> str:
    """Validate a FastAPI project against the quality gate checklist.

    Returns JSON: {status, checks, warnings}
    Checks for main.py, database config, CORS, env files, and security.
    """
    checks = {}
    warnings = []

    # Check main.py exists
    checks["has_main_py"] = "main.py" in project_files
    if not checks["has_main_py"]:
        warnings.append("Missing main.py — FastAPI app entry point not found")

    # Check database config
    checks["has_database"] = "database.py" in project_files or any(
        "database" in k.lower() for k in project_files
    )
    if not checks["has_database"]:
        warnings.append("Missing database.py — no database configuration found")

    # Check requirements
    checks["has_requirements"] = (
        "requirements.txt" in project_files or "pyproject.toml" in project_files
    )
    if not checks["has_requirements"]:
        warnings.append("Missing requirements.txt — no dependency manifest found")

    # Check env example
    checks["has_env_example"] = ".env.example" in project_files
    if not checks["has_env_example"]:
        warnings.append("Missing .env.example — no environment template for team")

    # Check CORS configuration
    main_content = project_files.get("main.py", "")
    checks["has_cors"] = (
        "CORSMiddleware" in main_content or "cors" in main_content.lower()
    )
    if not checks["has_cors"]:
        warnings.append(
            "No CORS middleware configured — frontend requests may be blocked"
        )

    # Check for routers
    checks["has_routers"] = any("routers/" in k for k in project_files)

    # Check for hardcoded secrets
    has_secrets = False
    for filename, content in project_files.items():
        if filename.startswith(".env") and "example" not in filename:
            continue
        if _SECRETS_PATTERN.search(content) or _HARDCODED_URL_PATTERN.search(content):
            has_secrets = True
            break

    checks["no_hardcoded_secrets"] = not has_secrets
    if has_secrets:
        warnings.append(
            "Possible hardcoded secrets detected — use environment variables"
        )

    # Check DATABASE_URL from env
    db_content = project_files.get("database.py", "")
    checks["uses_env_for_db"] = "os.getenv" in db_content or "environ" in db_content
    if not checks["uses_env_for_db"] and checks["has_database"]:
        warnings.append(
            "DATABASE_URL may not be loaded from environment — use os.getenv()"
        )

    return json.dumps(
        {
            "status": "success",
            "checks": checks,
            "warnings": warnings,
        }
    )


@mcp.tool()
async def fastapi_diagnose_issue(
    symptom: str,
) -> str:
    """Diagnose a common FastAPI issue and suggest solutions.

    Returns JSON: {status, diagnosis, solutions}
    Symptoms: server_wont_start, 422_validation_error, cors_error,
    database_connection_failed, 500_internal_error,
    dependency_injection_error, async_issues,
    response_model_mismatch, path_parameter_issues
    """
    entry = DIAGNOSES[symptom]

    return json.dumps(
        {
            "status": "success",
            "diagnosis": entry["diagnosis"],
            "solutions": entry["solutions"],
        }
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
