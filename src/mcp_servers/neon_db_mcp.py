"""
Neon DB MCP Server — generates database configurations, connection strings,
environment setups, health checks, and troubleshoots Neon PostgreSQL issues.

Tools:
    neon_generate_db_config          Generate database.py engine/session code
    neon_generate_connection_string   Build properly formatted connection strings
    neon_generate_env_config         Generate .env files for environments
    neon_generate_fastapi_integration Generate FastAPI lifespan + dependency code
    neon_generate_branch_strategy    Generate branch strategy for environments
    neon_detect_antipatterns         Detect common Neon/PostgreSQL anti-patterns
    neon_troubleshoot_connection     Diagnose connection issues from error messages
    neon_generate_health_check       Generate health check endpoint code
    neon_recommend_pool_config       Recommend connection pool settings
    neon_generate_migration_workflow  Generate safe migration workflow with branching
"""

import json
import re
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("neon_db_mcp")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_ENVIRONMENTS = ("development", "staging", "production")
VALID_POOL_STRATEGIES = ("direct", "pooler", "auto")
VALID_SSL_MODES = ("require", "verify-ca", "verify-full", "prefer", "disable")
VALID_DEPLOYMENT_TARGETS = ("fastapi", "serverless", "lambda", "vercel", "docker")

# ---------------------------------------------------------------------------
# Pool size recommendations
# ---------------------------------------------------------------------------

POOL_CONFIGS: dict[str, dict] = {
    "development": {
        "pool_size": 2,
        "max_overflow": 5,
        "pool_timeout": 30,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
        "echo": True,
        "description": "Minimal pool for local development",
    },
    "staging": {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
        "echo": False,
        "description": "Moderate pool for staging/testing",
    },
    "production": {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
        "echo": False,
        "description": "Production pool with higher capacity",
    },
}

# ---------------------------------------------------------------------------
# Anti-pattern definitions
# ---------------------------------------------------------------------------

ANTIPATTERNS: dict[str, dict] = {
    "hardcoded-credentials": {
        "description": "Connection string with credentials hardcoded in source code",
        "detection": "DATABASE_URL assigned as string literal (not os.getenv)",
        "impact": "Secrets exposed in version control, security breach risk",
        "fix": "Use os.getenv('DATABASE_URL') or pydantic_settings.BaseSettings",
        "severity": "critical",
    },
    "missing-ssl-mode": {
        "description": "Connection string without sslmode=require parameter",
        "detection": "DATABASE_URL missing ?sslmode=require",
        "impact": "Connection will fail with Neon (SSL required)",
        "fix": "Append ?sslmode=require to connection string",
        "severity": "critical",
    },
    "env-file-committed": {
        "description": ".env file containing secrets committed to git",
        "detection": ".env not in .gitignore",
        "impact": "Database credentials exposed in repository history",
        "fix": "Add .env, .env.local, .env.production to .gitignore; commit only .env.example",
        "severity": "critical",
    },
    "no-cold-start-handling": {
        "description": "No retry logic for Neon compute cold starts",
        "detection": "Database calls without retry/backoff logic",
        "impact": "First request after idle period (5min free tier) may timeout",
        "fix": "Add exponential backoff retry (max_retries=3, sleep=2^attempt)",
        "severity": "high",
    },
    "pool-exhaustion-risk": {
        "description": "Connection pool not configured or too large for tier",
        "detection": "Default pool_size or pool_size > 20 on free tier",
        "impact": "Too many connections errors, request timeouts",
        "fix": "Set pool_size=5, max_overflow=10, pool_pre_ping=True",
        "severity": "high",
    },
    "session-leak": {
        "description": "Database sessions not properly closed",
        "detection": "Session() without context manager or yield",
        "impact": "Connection pool exhaustion, resource leak",
        "fix": "Use 'with Session(engine) as session:' or FastAPI Depends(get_session)",
        "severity": "high",
    },
    "same-branch-dev-prod": {
        "description": "Same database branch used for development and production",
        "detection": "Single DATABASE_URL for all environments",
        "impact": "Development changes affect production data",
        "fix": "Create separate Neon branches: main (prod), development, staging",
        "severity": "high",
    },
    "no-startup-verification": {
        "description": "Application starts without verifying database connection",
        "detection": "No SELECT 1 health check in lifespan/startup",
        "impact": "App starts but silently fails on first database request",
        "fix": "Add connection verification in FastAPI lifespan with SELECT 1",
        "severity": "medium",
    },
    "no-connect-timeout": {
        "description": "No connection timeout configured",
        "detection": "Missing connect_timeout in connection string or engine args",
        "impact": "Hanging requests on network issues",
        "fix": "Add ?connect_timeout=10 to URL or connect_args={'connect_timeout': 10}",
        "severity": "medium",
    },
    "direct-connection-serverless": {
        "description": "Using direct connection instead of pooler in serverless",
        "detection": "Non-pooler endpoint in Lambda/Vercel/serverless deployment",
        "impact": "Too many direct connections, connection limits exceeded",
        "fix": "Use Neon pooler endpoint: ep-xxx-pooler.region.aws.neon.tech",
        "severity": "medium",
    },
    "large-blobs-in-db": {
        "description": "Storing large binary files directly in database",
        "detection": "bytes/LargeBinary columns for file storage",
        "impact": "Slow queries, increased storage costs, poor performance",
        "fix": "Store files in S3/R2, keep only file_url reference in database",
        "severity": "medium",
    },
    "latest-no-pinned-version": {
        "description": "Not pinning PostgreSQL/driver versions",
        "detection": "No version constraints on psycopg2/asyncpg/sqlmodel",
        "impact": "Breaking changes on dependency updates",
        "fix": "Pin versions: psycopg2-binary>=2.9,<3.0; sqlmodel>=0.0.14",
        "severity": "low",
    },
}

# ---------------------------------------------------------------------------
# Connection error lookup
# ---------------------------------------------------------------------------

CONNECTION_ERRORS: dict[str, dict] = {
    "connection refused": {
        "cause": "Wrong host/port or endpoint not running",
        "solutions": [
            "Verify endpoint URL from Neon Console",
            "Check if Neon project is active (not suspended)",
            "Ensure endpoint format: ep-xxx.region.aws.neon.tech",
        ],
    },
    "authentication failed": {
        "cause": "Invalid username or password",
        "solutions": [
            "Reset password in Neon Console → Connection Details",
            "Verify username matches Neon role",
            "Check for special characters in password (URL-encode them)",
        ],
    },
    "ssl required": {
        "cause": "Connection string missing sslmode parameter",
        "solutions": [
            "Add ?sslmode=require to DATABASE_URL",
            "Neon requires SSL for all connections",
        ],
    },
    "database does not exist": {
        "cause": "Wrong database name in connection string",
        "solutions": [
            "Default database is 'neondb'",
            "Check database name in Neon Console",
            "Verify the path component of DATABASE_URL",
        ],
    },
    "timeout": {
        "cause": "Network issue or compute cold start",
        "solutions": [
            "Check network/firewall/VPN settings",
            "Neon free tier suspends after 5 min idle — add retry logic",
            "Add connect_timeout=10 to connection string",
            "Use pool_pre_ping=True in engine config",
        ],
    },
    "too many connections": {
        "cause": "Connection pool too large or connections not released",
        "solutions": [
            "Reduce pool_size (free tier limit ~100 connections)",
            "Use Neon pooler endpoint (ep-xxx-pooler.neon.tech)",
            "Check for session leaks (missing context managers)",
            "Add pool_recycle=3600 to recycle stale connections",
        ],
    },
    "connection reset": {
        "cause": "Connection dropped by server (idle timeout or compute suspend)",
        "solutions": [
            "Enable pool_pre_ping=True to detect stale connections",
            "Set pool_recycle=1800 to refresh connections",
            "Add retry logic with exponential backoff",
        ],
    },
    "ssl certificate verify failed": {
        "cause": "SSL certificate validation issue",
        "solutions": [
            "Use sslmode=require (not verify-full) for development",
            "Ensure system CA certificates are up to date",
            "For Docker: install ca-certificates package",
        ],
    },
    "could not translate host name": {
        "cause": "DNS resolution failure for Neon endpoint",
        "solutions": [
            "Check endpoint hostname spelling",
            "Verify DNS resolution: nslookup ep-xxx.region.aws.neon.tech",
            "Check network connectivity",
        ],
    },
    "password authentication failed": {
        "cause": "Wrong password for the specified role",
        "solutions": [
            "Reset password in Neon Console",
            "URL-encode special characters in password",
            "Verify you're connecting to the correct project/branch",
        ],
    },
}

# ---------------------------------------------------------------------------
# Branch strategy templates
# ---------------------------------------------------------------------------

BRANCH_STRATEGIES: dict[str, dict] = {
    "simple": {
        "description": "Two branches: main (production) + development",
        "branches": [
            {"name": "main", "purpose": "Production database", "persistent": True},
            {
                "name": "development",
                "purpose": "Local development and testing",
                "persistent": True,
            },
        ],
        "use_case": "Solo developer, small project",
    },
    "standard": {
        "description": "Three branches: main + staging + development",
        "branches": [
            {"name": "main", "purpose": "Production database", "persistent": True},
            {
                "name": "staging",
                "purpose": "Pre-production testing",
                "persistent": True,
            },
            {
                "name": "development",
                "purpose": "Active development",
                "persistent": True,
            },
        ],
        "use_case": "Team project, CI/CD pipeline",
    },
    "feature-branching": {
        "description": "Main + staging + development + ephemeral feature branches",
        "branches": [
            {"name": "main", "purpose": "Production", "persistent": True},
            {"name": "staging", "purpose": "Pre-production", "persistent": True},
            {
                "name": "development",
                "purpose": "Active development",
                "persistent": True,
            },
            {
                "name": "feature-*",
                "purpose": "Per-feature isolated testing",
                "persistent": False,
            },
        ],
        "use_case": "Team with feature branch workflow, PR-based testing",
    },
}

# ---------------------------------------------------------------------------
# Quality gate checklist
# ---------------------------------------------------------------------------

QUALITY_GATES: list[dict] = [
    {
        "category": "Connection",
        "item": "DATABASE_URL loads from environment (not hardcoded)",
        "severity": "critical",
    },
    {
        "category": "Connection",
        "item": "Connection string includes ?sslmode=require",
        "severity": "critical",
    },
    {"category": "Security", "item": ".env is in .gitignore", "severity": "critical"},
    {
        "category": "Security",
        "item": ".env.example template committed (no real credentials)",
        "severity": "high",
    },
    {
        "category": "Connection",
        "item": "Connection test passes (SELECT 1)",
        "severity": "high",
    },
    {
        "category": "Startup",
        "item": "Tables create successfully on startup",
        "severity": "high",
    },
    {
        "category": "Startup",
        "item": "FastAPI lifespan verifies connection",
        "severity": "medium",
    },
    {
        "category": "Environment",
        "item": "Separate dev/staging/prod connection strings",
        "severity": "medium",
    },
    {
        "category": "Pool",
        "item": "Connection pool configured with pool_pre_ping=True",
        "severity": "medium",
    },
    {
        "category": "Pool",
        "item": "pool_recycle set to prevent stale connections",
        "severity": "medium",
    },
    {
        "category": "Resilience",
        "item": "Retry logic for cold start handling",
        "severity": "medium",
    },
    {"category": "Resilience", "item": "connect_timeout configured", "severity": "low"},
]

# ---------------------------------------------------------------------------
# Pydantic input models
# ---------------------------------------------------------------------------

_CFG = ConfigDict(str_strip_whitespace=True, extra="forbid")


class NeonGenerateDbConfigInput(BaseModel):
    model_config = _CFG
    environment: str = Field(
        default="development",
        description="Target environment: development, staging, production",
    )
    include_pool_config: bool = Field(
        default=True, description="Include connection pool settings"
    )
    include_session_factory: bool = Field(
        default=True, description="Include get_session dependency"
    )
    include_connection_check: bool = Field(
        default=True, description="Include connection verification function"
    )

    @field_validator("environment")
    @classmethod
    def _check_env(cls, v: str) -> str:
        if v not in VALID_ENVIRONMENTS:
            raise ValueError(f"environment must be one of {VALID_ENVIRONMENTS}")
        return v


class NeonGenerateConnectionStringInput(BaseModel):
    model_config = _CFG
    username: str = Field(default="<username>", description="Database username")
    host: str = Field(
        default="<endpoint>",
        description="Neon endpoint hostname (ep-xxx.region.aws.neon.tech)",
    )
    database: str = Field(default="neondb", description="Database name")
    use_pooler: bool = Field(
        default=False, description="Use Neon pgBouncer pooler endpoint"
    )
    ssl_mode: str = Field(
        default="require", description="SSL mode: require, verify-ca, verify-full"
    )
    connect_timeout: Optional[int] = Field(
        default=10, ge=1, le=60, description="Connection timeout in seconds"
    )
    region: str = Field(default="us-east-2", description="AWS region for Neon endpoint")

    @field_validator("ssl_mode")
    @classmethod
    def _check_ssl(cls, v: str) -> str:
        if v not in VALID_SSL_MODES:
            raise ValueError(f"ssl_mode must be one of {VALID_SSL_MODES}")
        return v

    @field_validator("host")
    @classmethod
    def _check_host(cls, v: str) -> str:
        if ".." in v or "/" in v:
            raise ValueError("host must not contain path traversal characters")
        return v


class NeonGenerateEnvConfigInput(BaseModel):
    model_config = _CFG
    environments: list[str] = Field(
        default=["development", "production"],
        description="Environments to generate configs for",
    )
    include_example: bool = Field(
        default=True, description="Include .env.example template"
    )
    include_gitignore: bool = Field(
        default=True, description="Include .gitignore entries"
    )

    @field_validator("environments")
    @classmethod
    def _check_envs(cls, v: list[str]) -> list[str]:
        for env in v:
            if env not in VALID_ENVIRONMENTS:
                raise ValueError(
                    f"Each environment must be one of {VALID_ENVIRONMENTS}"
                )
        return v


class NeonGenerateFastapiInput(BaseModel):
    model_config = _CFG
    include_lifespan: bool = Field(
        default=True, description="Include lifespan with connection verification"
    )
    include_health_endpoint: bool = Field(
        default=True, description="Include /health/db endpoint"
    )
    include_table_creation: bool = Field(
        default=True, description="Include create_db_and_tables in lifespan"
    )


class NeonGenerateBranchStrategyInput(BaseModel):
    model_config = _CFG
    strategy: str = Field(
        default="standard", description="Strategy: simple, standard, feature-branching"
    )
    project_name: str = Field(
        default="myapp", description="Project name for branch naming"
    )

    @field_validator("strategy")
    @classmethod
    def _check_strategy(cls, v: str) -> str:
        if v not in BRANCH_STRATEGIES:
            raise ValueError(
                f"strategy must be one of {list(BRANCH_STRATEGIES.keys())}"
            )
        return v

    @field_validator("project_name")
    @classmethod
    def _check_name(cls, v: str) -> str:
        if not re.match(r"^[a-z][a-z0-9\-]*$", v):
            raise ValueError("project_name must be lowercase alphanumeric with hyphens")
        return v


class NeonDetectAntipatternsInput(BaseModel):
    model_config = _CFG
    deployment_target: str = Field(
        default="fastapi",
        description="Deployment target: fastapi, serverless, lambda, vercel, docker",
    )
    include_fixes: bool = Field(default=True, description="Include fix recommendations")
    severity_filter: Optional[str] = Field(
        default=None, description="Filter by severity: critical, high, medium, low"
    )

    @field_validator("deployment_target")
    @classmethod
    def _check_target(cls, v: str) -> str:
        if v not in VALID_DEPLOYMENT_TARGETS:
            raise ValueError(
                f"deployment_target must be one of {VALID_DEPLOYMENT_TARGETS}"
            )
        return v

    @field_validator("severity_filter")
    @classmethod
    def _check_severity(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("critical", "high", "medium", "low"):
            raise ValueError(
                "severity_filter must be one of: critical, high, medium, low"
            )
        return v


class NeonTroubleshootInput(BaseModel):
    model_config = _CFG
    error_message: str = Field(
        ..., min_length=3, max_length=500, description="Error message to diagnose"
    )


class NeonGenerateHealthCheckInput(BaseModel):
    model_config = _CFG
    include_retry: bool = Field(
        default=True, description="Include retry logic for cold starts"
    )
    max_retries: int = Field(
        default=3, ge=1, le=10, description="Maximum retry attempts"
    )
    include_metrics: bool = Field(
        default=False, description="Include response time metrics"
    )


class NeonRecommendPoolInput(BaseModel):
    model_config = _CFG
    environment: str = Field(default="development", description="Target environment")
    deployment_target: str = Field(default="fastapi", description="Deployment target")
    expected_concurrency: Optional[int] = Field(
        default=None, ge=1, le=1000, description="Expected concurrent users"
    )

    @field_validator("environment")
    @classmethod
    def _check_env(cls, v: str) -> str:
        if v not in VALID_ENVIRONMENTS:
            raise ValueError(f"environment must be one of {VALID_ENVIRONMENTS}")
        return v

    @field_validator("deployment_target")
    @classmethod
    def _check_target(cls, v: str) -> str:
        if v not in VALID_DEPLOYMENT_TARGETS:
            raise ValueError(
                f"deployment_target must be one of {VALID_DEPLOYMENT_TARGETS}"
            )
        return v


class NeonGenerateMigrationWorkflowInput(BaseModel):
    model_config = _CFG
    strategy: str = Field(
        default="standard",
        description="Branch strategy: simple, standard, feature-branching",
    )
    migration_tool: str = Field(
        default="alembic", description="Migration tool: alembic, sqlmodel-direct"
    )
    include_rollback: bool = Field(
        default=True, description="Include rollback procedures"
    )

    @field_validator("strategy")
    @classmethod
    def _check_strategy(cls, v: str) -> str:
        if v not in BRANCH_STRATEGIES:
            raise ValueError(
                f"strategy must be one of {list(BRANCH_STRATEGIES.keys())}"
            )
        return v

    @field_validator("migration_tool")
    @classmethod
    def _check_tool(cls, v: str) -> str:
        if v not in ("alembic", "sqlmodel-direct"):
            raise ValueError("migration_tool must be one of: alembic, sqlmodel-direct")
        return v


# ---------------------------------------------------------------------------
# Pure generator / helper functions
# ---------------------------------------------------------------------------


def _gen_db_config(
    environment: str, include_pool: bool, include_session: bool, include_check: bool
) -> dict:
    """Generate database.py configuration code."""
    pool = POOL_CONFIGS[environment]

    imports = [
        "import os",
        "from sqlmodel import SQLModel, create_engine, Session",
        "from dotenv import load_dotenv",
    ]
    if include_check:
        imports.append("from sqlalchemy import text")

    lines = [
        '"""Database configuration for Neon PostgreSQL."""',
        "",
        *imports,
        "",
        "load_dotenv()",
        "",
        'DATABASE_URL = os.getenv("DATABASE_URL")',
        "if not DATABASE_URL:",
        '    raise ValueError("DATABASE_URL environment variable not set")',
        "",
    ]

    # Engine creation
    if include_pool:
        lines.extend(
            [
                "engine = create_engine(",
                "    DATABASE_URL,",
                f"    echo={pool['echo']},",
                f"    pool_size={pool['pool_size']},",
                f"    max_overflow={pool['max_overflow']},",
                f"    pool_timeout={pool['pool_timeout']},",
                f"    pool_recycle={pool['pool_recycle']},",
                f"    pool_pre_ping={pool['pool_pre_ping']},",
                ")",
            ]
        )
    else:
        lines.extend(
            [
                "engine = create_engine(DATABASE_URL, echo=True)",
            ]
        )

    lines.extend(
        [
            "",
            "",
            "def create_db_and_tables():",
            "    SQLModel.metadata.create_all(engine)",
        ]
    )

    if include_session:
        lines.extend(
            [
                "",
                "",
                "def get_session():",
                "    with Session(engine) as session:",
                "        yield session",
            ]
        )

    if include_check:
        lines.extend(
            [
                "",
                "",
                "def check_connection() -> bool:",
                '    """Verify database connection."""',
                "    try:",
                "        with Session(engine) as session:",
                '            session.exec(text("SELECT 1"))',
                '            print("Database connection successful")',
                "            return True",
                "    except Exception as e:",
                '        print(f"Database connection failed: {e}")',
                "        return False",
            ]
        )

    code = "\n".join(lines)

    return {
        "file": "database.py",
        "environment": environment,
        "pool_config": pool if include_pool else None,
        "code": code,
        "quality_gates": [
            g for g in QUALITY_GATES if g["category"] in ("Connection", "Pool")
        ],
    }


def _gen_connection_string(
    username: str,
    host: str,
    database: str,
    use_pooler: bool,
    ssl_mode: str,
    connect_timeout: Optional[int],
    region: str,
) -> dict:
    """Build a properly formatted Neon connection string."""
    # Add -pooler suffix if requested
    effective_host = host
    if use_pooler and "-pooler" not in host and host != "<endpoint>":
        parts = host.split(".", 1)
        if len(parts) == 2:
            effective_host = f"{parts[0]}-pooler.{parts[1]}"
        else:
            effective_host = f"{host}-pooler"

    params = [f"sslmode={ssl_mode}"]
    if connect_timeout:
        params.append(f"connect_timeout={connect_timeout}")

    query = "&".join(params)
    url = f"postgresql://{username}:<password>@{effective_host}/{database}?{query}"

    return {
        "connection_string": url,
        "components": {
            "scheme": "postgresql",
            "username": username,
            "password": "<password>",
            "host": effective_host,
            "database": database,
            "sslmode": ssl_mode,
            "connect_timeout": connect_timeout,
            "pooler": use_pooler,
        },
        "env_line": f"DATABASE_URL={url}",
        "notes": [
            "Replace <password> with actual password",
            "Never commit actual credentials to version control",
            "URL-encode special characters in password",
        ]
        + (
            ["Using Neon pooler endpoint (pgBouncer) for connection pooling"]
            if use_pooler
            else []
        ),
    }


def _gen_env_config(
    environments: list[str], include_example: bool, include_gitignore: bool
) -> dict:
    """Generate environment configuration files."""
    files: dict = {}

    for env in environments:
        endpoint = f"ep-{env[:3]}-branch"
        db_url = f"postgresql://<user>:<password>@{endpoint}.us-east-2.aws.neon.tech/neondb?sslmode=require"
        files[f".env.{env}"] = {
            "content": f"ENVIRONMENT={env}\nDATABASE_URL={db_url}\n",
            "description": f"{env.capitalize()} environment configuration",
        }

    if include_example:
        files[".env.example"] = {
            "content": (
                "# Database Configuration (copy to .env and fill in values)\n"
                "DATABASE_URL=postgresql://user:password@hostname/database?sslmode=require\n"
                "ENVIRONMENT=development\n"
            ),
            "description": "Template file — safe to commit (no real credentials)",
        }

    result: dict = {
        "files": files,
        "loader_code": (
            "import os\n"
            "from dotenv import load_dotenv\n\n"
            'env = os.getenv("ENVIRONMENT", "development")\n'
            'load_dotenv(f".env.{env}")\n'
        ),
    }

    if include_gitignore:
        result["gitignore_entries"] = [
            ".env",
            ".env.local",
            ".env.development",
            ".env.staging",
            ".env.production",
            ".env.*.local",
        ]
        result["gitignore_note"] = "Add these to .gitignore — commit only .env.example"

    return result


def _gen_fastapi_integration(
    include_lifespan: bool, include_health: bool, include_tables: bool
) -> dict:
    """Generate FastAPI integration code."""
    imports = ["from fastapi import FastAPI"]
    if include_lifespan:
        imports.append("from contextlib import asynccontextmanager")
    if include_health:
        imports.extend(["from fastapi import Depends, APIRouter, status"])
    imports.append("from database import create_db_and_tables, get_session, engine")
    if include_lifespan or include_health:
        imports.extend(["from sqlmodel import Session", "from sqlalchemy import text"])

    lines = [
        '"""FastAPI application with Neon database integration."""',
        "",
        *imports,
        "",
    ]

    if include_lifespan:
        lines.extend(
            [
                "",
                "@asynccontextmanager",
                "async def lifespan(app: FastAPI):",
                '    """Application lifespan: verify connection and create tables."""',
            ]
        )
        if include_tables:
            lines.append("    create_db_and_tables()")
        lines.extend(
            [
                "    try:",
                "        with Session(engine) as session:",
                '            session.exec(text("SELECT 1"))',
                '        print("Database connection verified")',
                "    except Exception as e:",
                '        print(f"Database connection failed: {e}")',
                "        raise",
                "    yield",
                "",
                "",
                "app = FastAPI(lifespan=lifespan)",
            ]
        )
    else:
        lines.extend(["", "app = FastAPI()"])

    if include_health:
        lines.extend(
            [
                "",
                "",
                '@app.get("/health/db", status_code=status.HTTP_200_OK)',
                "def database_health_check(session: Session = Depends(get_session)):",
                '    """Check database connectivity."""',
                "    try:",
                '        session.exec(text("SELECT 1"))',
                '        return {"status": "healthy", "database": "connected"}',
                "    except Exception as e:",
                '        return {"status": "unhealthy", "error": str(e)}',
            ]
        )

    code = "\n".join(lines)

    return {
        "file": "main.py",
        "code": code,
        "features": {
            "lifespan": include_lifespan,
            "health_endpoint": include_health,
            "table_creation": include_tables,
        },
    }


def _gen_branch_strategy(strategy: str, project_name: str) -> dict:
    """Generate branch strategy documentation and configuration."""
    defn = BRANCH_STRATEGIES[strategy]

    branches_detail = []
    for b in defn["branches"]:
        name = b["name"]
        if name == "feature-*":
            endpoint = f"ep-feature-xxx.us-east-2.aws.neon.tech"
        else:
            endpoint = f"ep-{project_name}-{name}.us-east-2.aws.neon.tech"

        branches_detail.append(
            {
                "name": name.replace("*", f"<feature-name>") if "*" in name else name,
                "purpose": b["purpose"],
                "persistent": b["persistent"],
                "endpoint": endpoint,
                "connection_string": f"postgresql://<user>:<pass>@{endpoint}/neondb?sslmode=require",
            }
        )

    tree_lines = ["main (production)"]
    for b in defn["branches"][1:]:
        name = b["name"]
        if name == "feature-*":
            tree_lines.append(f"    └── feature-<name> (ephemeral)")
        elif name == "staging":
            tree_lines.append(f"├── {name}")
        else:
            tree_lines.append(f"└── {name}")

    return {
        "strategy": strategy,
        "description": defn["description"],
        "use_case": defn["use_case"],
        "branches": branches_detail,
        "tree": "\n".join(tree_lines),
        "best_practices": [
            "Name branches descriptively (feature-user-auth, bugfix-todo-delete)",
            "Delete feature branches after merge",
            "Keep main, staging, development persistent",
            "Use production data carefully — anonymize if needed",
            "Each branch has its own compute endpoint",
        ],
    }


def _match_error(error_message: str) -> list[dict]:
    """Match error message against known connection errors."""
    lower = error_message.lower()
    matches = []
    for pattern, info in CONNECTION_ERRORS.items():
        if pattern in lower:
            matches.append(
                {
                    "matched_pattern": pattern,
                    "cause": info["cause"],
                    "solutions": info["solutions"],
                }
            )

    if not matches:
        matches.append(
            {
                "matched_pattern": None,
                "cause": "Unknown error — could not match to known patterns",
                "solutions": [
                    "Check DATABASE_URL format: postgresql://user:pass@host/db?sslmode=require",
                    "Verify Neon project is active in console",
                    "Test network connectivity to Neon endpoint",
                    "Enable SQLAlchemy logging: engine = create_engine(url, echo=True)",
                    "Check Neon status page: https://neon.tech/status",
                ],
            }
        )

    return matches


def _gen_health_check(
    include_retry: bool, max_retries: int, include_metrics: bool
) -> dict:
    """Generate health check code."""
    imports = [
        "from sqlmodel import Session",
        "from sqlalchemy import text",
    ]
    if include_retry:
        imports.extend(["import time", "from sqlalchemy.exc import OperationalError"])
    if include_metrics:
        imports.append("import time as _time")

    lines = [
        '"""Database health check utilities."""',
        "",
        *imports,
        "",
    ]

    if include_retry:
        lines.extend(
            [
                "",
                f"def check_connection_with_retry(engine, max_retries: int = {max_retries}) -> bool:",
                '    """Verify connection with retry for cold starts."""',
                "    for attempt in range(max_retries):",
                "        try:",
                "            with Session(engine) as session:",
                '                session.exec(text("SELECT 1"))',
                "            return True",
                "        except OperationalError:",
                "            if attempt < max_retries - 1:",
                "                time.sleep(2 ** attempt)  # Exponential backoff",
                "            else:",
                "                raise",
                "    return False",
            ]
        )

    lines.extend(
        [
            "",
            "",
            "def check_connection(engine) -> dict:",
            '    """Check database connection and return status."""',
        ]
    )

    if include_metrics:
        lines.extend(
            [
                "    start = _time.monotonic()",
            ]
        )

    lines.extend(
        [
            "    try:",
            "        with Session(engine) as session:",
            '            result = session.exec(text("SELECT version()"))',
            "            version = result.fetchone()[0]",
        ]
    )

    if include_metrics:
        lines.extend(
            [
                "        elapsed_ms = (_time.monotonic() - start) * 1000",
                "        return {",
                '            "status": "healthy",',
                '            "database": "connected",',
                '            "version": version,',
                '            "response_time_ms": round(elapsed_ms, 2),',
                "        }",
            ]
        )
    else:
        lines.extend(
            [
                "        return {",
                '            "status": "healthy",',
                '            "database": "connected",',
                '            "version": version,',
                "        }",
            ]
        )

    lines.extend(
        [
            "    except Exception as e:",
            "        return {",
            '            "status": "unhealthy",',
            '            "error": str(e),',
            "        }",
        ]
    )

    code = "\n".join(lines)

    return {
        "file": "health_check.py",
        "code": code,
        "features": {
            "retry_logic": include_retry,
            "max_retries": max_retries if include_retry else None,
            "response_metrics": include_metrics,
        },
    }


def _recommend_pool(
    environment: str, deployment_target: str, expected_concurrency: Optional[int]
) -> dict:
    """Recommend connection pool configuration."""
    base = POOL_CONFIGS[environment].copy()

    # Adjust for deployment target
    use_pooler = False
    notes = []

    if deployment_target in ("serverless", "lambda", "vercel"):
        use_pooler = True
        base["pool_size"] = min(base["pool_size"], 3)
        base["max_overflow"] = min(base["max_overflow"], 5)
        notes.append("Serverless: Use Neon pooler endpoint (ep-xxx-pooler.neon.tech)")
        notes.append("Keep pool small — many instances share connection limit")

    if deployment_target == "docker":
        notes.append("Docker: Install ca-certificates for SSL support")
        notes.append("Consider pool_pre_ping for container restarts")

    # Adjust for concurrency
    if expected_concurrency:
        if expected_concurrency <= 10:
            base["pool_size"] = 2
            base["max_overflow"] = 5
        elif expected_concurrency <= 50:
            base["pool_size"] = 5
            base["max_overflow"] = 10
        elif expected_concurrency <= 200:
            base["pool_size"] = 10
            base["max_overflow"] = 20
        else:
            base["pool_size"] = 15
            base["max_overflow"] = 30
            use_pooler = True
            notes.append("High concurrency: Neon pooler strongly recommended")

    engine_code = (
        "engine = create_engine(\n"
        "    DATABASE_URL,\n"
        f"    echo={base['echo']},\n"
        f"    pool_size={base['pool_size']},\n"
        f"    max_overflow={base['max_overflow']},\n"
        f"    pool_timeout={base['pool_timeout']},\n"
        f"    pool_recycle={base['pool_recycle']},\n"
        f"    pool_pre_ping={base['pool_pre_ping']},\n"
        ")"
    )

    return {
        "environment": environment,
        "deployment_target": deployment_target,
        "expected_concurrency": expected_concurrency,
        "use_neon_pooler": use_pooler,
        "pool_config": base,
        "engine_code": engine_code,
        "notes": notes,
        "neon_limits": {
            "free_tier": "~100 connections per endpoint",
            "pro_tier": "Configurable, higher limits",
            "pooler": "Up to 10,000 connections via pgBouncer",
        },
    }


def _gen_migration_workflow(
    strategy: str, migration_tool: str, include_rollback: bool
) -> dict:
    """Generate migration workflow with branching safety."""
    defn = BRANCH_STRATEGIES[strategy]

    if migration_tool == "alembic":
        migration_commands = {
            "generate": "alembic revision --autogenerate -m '<description>'",
            "upgrade": "alembic upgrade head",
            "downgrade": "alembic downgrade -1",
            "history": "alembic history --verbose",
            "current": "alembic current",
        }
    else:
        migration_commands = {
            "generate": "# SQLModel direct: modify models, then call create_db_and_tables()",
            "upgrade": "python -c 'from database import create_db_and_tables; create_db_and_tables()'",
            "downgrade": "# Manual: write SQL to revert changes",
            "history": "# Track changes in version control",
            "current": "# Check table structure: \\dt in psql",
        }

    steps = [
        {
            "step": 1,
            "name": "Create feature branch",
            "action": "Create Neon branch from staging (via Console or CLI)",
        },
        {
            "step": 2,
            "name": "Set DATABASE_URL",
            "action": "Point to feature branch endpoint",
        },
        {"step": 3, "name": "Run migration", "action": migration_commands["upgrade"]},
        {
            "step": 4,
            "name": "Test thoroughly",
            "action": "Run test suite against feature branch",
        },
        {
            "step": 5,
            "name": "Merge to staging",
            "action": "Apply migration to staging branch",
        },
        {"step": 6, "name": "Test in staging", "action": "Full integration test"},
        {
            "step": 7,
            "name": "Apply to production",
            "action": "Apply migration to main branch",
        },
        {
            "step": 8,
            "name": "Cleanup",
            "action": "Delete feature branch (if ephemeral)",
        },
    ]

    result: dict = {
        "strategy": strategy,
        "migration_tool": migration_tool,
        "commands": migration_commands,
        "workflow_steps": steps,
        "safety_checklist": [
            "Neon maintains point-in-time restore (7 days free, 30 days paid)",
            "Always test migration on feature/staging branch first",
            "Review generated migration SQL before applying",
            "Verify rollback works before applying to production",
            "Document all schema changes",
        ],
    }

    if include_rollback:
        result["rollback_procedure"] = {
            "steps": [
                {"step": 1, "action": "Identify the failing migration"},
                {"step": 2, "action": migration_commands["downgrade"]},
                {"step": 3, "action": "Or use Neon point-in-time restore via Console"},
                {"step": 4, "action": "Verify application works after rollback"},
                {"step": 5, "action": "Investigate root cause before retrying"},
            ],
            "neon_restore": "Console → Branches → Select branch → Restore → Choose timestamp",
        }

    return result


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def neon_generate_db_config(
    environment: str = "development",
    include_pool_config: bool = True,
    include_session_factory: bool = True,
    include_connection_check: bool = True,
) -> str:
    """Generate database.py configuration code for Neon PostgreSQL.

    Returns JSON with complete database.py code including engine creation,
    connection pool settings, session factory, and connection verification.
    """
    inp = NeonGenerateDbConfigInput(
        environment=environment,
        include_pool_config=include_pool_config,
        include_session_factory=include_session_factory,
        include_connection_check=include_connection_check,
    )
    result = _gen_db_config(
        inp.environment,
        inp.include_pool_config,
        inp.include_session_factory,
        inp.include_connection_check,
    )
    return json.dumps(result, indent=2)


@mcp.tool()
async def neon_generate_connection_string(
    username: str = "<username>",
    host: str = "<endpoint>",
    database: str = "neondb",
    use_pooler: bool = False,
    ssl_mode: str = "require",
    connect_timeout: int | None = 10,
    region: str = "us-east-2",
) -> str:
    """Build a properly formatted Neon PostgreSQL connection string.

    Returns JSON with the connection string, its components broken down,
    and the .env line ready to copy. Optionally configures the Neon
    pgBouncer pooler endpoint.
    """
    inp = NeonGenerateConnectionStringInput(
        username=username,
        host=host,
        database=database,
        use_pooler=use_pooler,
        ssl_mode=ssl_mode,
        connect_timeout=connect_timeout,
        region=region,
    )
    result = _gen_connection_string(
        inp.username,
        inp.host,
        inp.database,
        inp.use_pooler,
        inp.ssl_mode,
        inp.connect_timeout,
        inp.region,
    )
    return json.dumps(result, indent=2)


@mcp.tool()
async def neon_generate_env_config(
    environments: list[str] | None = None,
    include_example: bool = True,
    include_gitignore: bool = True,
) -> str:
    """Generate .env configuration files for multiple environments.

    Returns JSON with .env file contents for each environment, a .env.example
    template, .gitignore entries, and the environment loader code.
    """
    envs = environments or ["development", "production"]
    inp = NeonGenerateEnvConfigInput(
        environments=envs,
        include_example=include_example,
        include_gitignore=include_gitignore,
    )
    result = _gen_env_config(
        inp.environments, inp.include_example, inp.include_gitignore
    )
    return json.dumps(result, indent=2)


@mcp.tool()
async def neon_generate_fastapi_integration(
    include_lifespan: bool = True,
    include_health_endpoint: bool = True,
    include_table_creation: bool = True,
) -> str:
    """Generate FastAPI application code with Neon database integration.

    Returns JSON with main.py code including lifespan connection verification,
    table creation, and health check endpoint.
    """
    inp = NeonGenerateFastapiInput(
        include_lifespan=include_lifespan,
        include_health_endpoint=include_health_endpoint,
        include_table_creation=include_table_creation,
    )
    result = _gen_fastapi_integration(
        inp.include_lifespan,
        inp.include_health_endpoint,
        inp.include_table_creation,
    )
    return json.dumps(result, indent=2)


@mcp.tool()
async def neon_generate_branch_strategy(
    strategy: str = "standard",
    project_name: str = "myapp",
) -> str:
    """Generate a database branching strategy for dev/staging/prod environments.

    Returns JSON with branch details, connection strings, visual tree,
    and best practices for the selected strategy (simple, standard, feature-branching).
    """
    inp = NeonGenerateBranchStrategyInput(
        strategy=strategy,
        project_name=project_name,
    )
    result = _gen_branch_strategy(inp.strategy, inp.project_name)
    return json.dumps(result, indent=2)


@mcp.tool()
async def neon_detect_antipatterns(
    deployment_target: str = "fastapi",
    include_fixes: bool = True,
    severity_filter: str | None = None,
) -> str:
    """Detect common Neon/PostgreSQL anti-patterns and suggest fixes.

    Returns JSON with all known anti-patterns filtered by deployment target
    and severity, with detection criteria, impact, and fix recommendations.
    """
    inp = NeonDetectAntipatternsInput(
        deployment_target=deployment_target,
        include_fixes=include_fixes,
        severity_filter=severity_filter,
    )

    patterns = []
    for name, info in ANTIPATTERNS.items():
        if inp.severity_filter and info["severity"] != inp.severity_filter:
            continue

        # Filter for deployment-target-specific patterns
        if name == "direct-connection-serverless" and inp.deployment_target not in (
            "serverless",
            "lambda",
            "vercel",
        ):
            continue

        entry: dict = {
            "pattern": name,
            "description": info["description"],
            "detection": info["detection"],
            "impact": info["impact"],
            "severity": info["severity"],
        }
        if inp.include_fixes:
            entry["fix"] = info["fix"]
        patterns.append(entry)

    return json.dumps(
        {
            "deployment_target": inp.deployment_target,
            "antipatterns": patterns,
            "quality_gates": QUALITY_GATES,
        },
        indent=2,
    )


@mcp.tool()
async def neon_troubleshoot_connection(
    error_message: str,
) -> str:
    """Diagnose Neon connection issues from error messages.

    Provide the error message text and receive matched patterns with
    likely causes and step-by-step solutions.
    """
    inp = NeonTroubleshootInput(error_message=error_message)
    matches = _match_error(inp.error_message)

    return json.dumps(
        {
            "error_message": inp.error_message,
            "diagnoses": matches,
            "general_debug_steps": [
                "Enable SQLAlchemy logging: create_engine(url, echo=True)",
                "Test connection: python -c 'from database import check_connection; check_connection()'",
                "Verify URL format: postgresql://user:pass@host/db?sslmode=require",
                "Check Neon status: https://neon.tech/status",
            ],
        },
        indent=2,
    )


@mcp.tool()
async def neon_generate_health_check(
    include_retry: bool = True,
    max_retries: int = 3,
    include_metrics: bool = False,
) -> str:
    """Generate health check utility code for Neon database connections.

    Returns JSON with health check code including optional retry logic
    for cold starts and response time metrics.
    """
    inp = NeonGenerateHealthCheckInput(
        include_retry=include_retry,
        max_retries=max_retries,
        include_metrics=include_metrics,
    )
    result = _gen_health_check(inp.include_retry, inp.max_retries, inp.include_metrics)
    return json.dumps(result, indent=2)


@mcp.tool()
async def neon_recommend_pool_config(
    environment: str = "development",
    deployment_target: str = "fastapi",
    expected_concurrency: int | None = None,
) -> str:
    """Recommend connection pool configuration based on environment and workload.

    Returns JSON with pool settings, engine code, Neon pooler recommendation,
    and tier-specific connection limits.
    """
    inp = NeonRecommendPoolInput(
        environment=environment,
        deployment_target=deployment_target,
        expected_concurrency=expected_concurrency,
    )
    result = _recommend_pool(
        inp.environment, inp.deployment_target, inp.expected_concurrency
    )
    return json.dumps(result, indent=2)


@mcp.tool()
async def neon_generate_migration_workflow(
    strategy: str = "standard",
    migration_tool: str = "alembic",
    include_rollback: bool = True,
) -> str:
    """Generate a safe database migration workflow with Neon branching.

    Returns JSON with step-by-step migration workflow, commands for the
    selected tool (alembic or sqlmodel-direct), safety checklist, and
    rollback procedures.
    """
    inp = NeonGenerateMigrationWorkflowInput(
        strategy=strategy,
        migration_tool=migration_tool,
        include_rollback=include_rollback,
    )
    result = _gen_migration_workflow(
        inp.strategy, inp.migration_tool, inp.include_rollback
    )
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
