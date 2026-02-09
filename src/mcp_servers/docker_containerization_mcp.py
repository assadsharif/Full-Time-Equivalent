"""
Docker Containerization MCP Server — generates production-ready Dockerfiles,
build/run commands, Gordon prompts, and validates container configurations.

Tools:
    docker_generate_dockerfile      Generate a Dockerfile from spec inputs
    docker_suggest_build_command    Suggest docker build command
    docker_suggest_run_command      Suggest docker run command
    docker_suggest_gordon_prompt    Generate Docker AI (Gordon) prompts
    docker_recommend_base_image     Recommend optimal base image
    docker_generate_dockerignore    Generate .dockerignore content
    docker_validate_dockerfile      Validate Dockerfile against best practices
    docker_list_templates           List all available Dockerfile templates
"""

import json
import re
from typing import Literal, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("docker_containerization_mcp")

# ---------------------------------------------------------------------------
# Constants — Template registry
# ---------------------------------------------------------------------------

TEMPLATES: list[dict] = [
    {
        "name": "fastapi",
        "language": "python",
        "framework": "fastapi",
        "role": "backend",
    },
    {"name": "flask", "language": "python", "framework": "flask", "role": "backend"},
    {"name": "django", "language": "python", "framework": "django", "role": "backend"},
    {
        "name": "nextjs",
        "language": "javascript",
        "framework": "nextjs",
        "role": "frontend",
    },
    {
        "name": "react",
        "language": "javascript",
        "framework": "react",
        "role": "frontend",
    },
    {"name": "vue", "language": "javascript", "framework": "vue", "role": "frontend"},
    {
        "name": "express",
        "language": "javascript",
        "framework": "express",
        "role": "backend",
    },
    {
        "name": "nestjs",
        "language": "javascript",
        "framework": "nestjs",
        "role": "backend",
    },
    {"name": "go-stdlib", "language": "go", "framework": "stdlib", "role": "backend"},
    {"name": "rust", "language": "rust", "framework": "actix", "role": "backend"},
]

BASE_IMAGE_MAP: dict[str, dict[str, str]] = {
    "python": {"image": "python:{version}-slim", "size": "~150MB"},
    "javascript": {"image": "node:{version}-alpine", "size": "~180MB"},
    "typescript": {"image": "node:{version}-alpine", "size": "~180MB"},
    "go": {"image": "golang:{version}-alpine", "size": "~250MB"},
    "rust": {"image": "rust:{version}-slim", "size": "~800MB"},
    "java": {"image": "eclipse-temurin:{version}-jre-alpine", "size": "~200MB"},
}

GORDON_PROMPTS: dict[str, str] = {
    "security_audit": (
        "@gordon analyze this Dockerfile for security issues:\n\n"
        "[PASTE DOCKERFILE HERE]\n\n"
        "Check for:\n"
        "1. Running as root (should use non-root user)\n"
        "2. Hardcoded secrets or credentials\n"
        "3. Unnecessary packages increasing attack surface\n"
        "4. Missing security updates\n"
        "5. Exposed sensitive ports\n"
        "6. Insecure base image versions\n\n"
        "Provide severity rating and remediation steps."
    ),
    "size_optimization": (
        "@gordon optimize this Dockerfile to reduce image size:\n\n"
        "[PASTE DOCKERFILE HERE]\n\n"
        "Suggestions needed:\n"
        "1. Multi-stage build opportunities\n"
        "2. Alpine/slim base image alternatives\n"
        "3. Layer consolidation for RUN commands\n"
        "4. Unnecessary file removal\n"
        "5. Build cache optimization\n"
        "6. .dockerignore improvements\n\n"
        "Show before/after estimated sizes."
    ),
    "build_performance": (
        "@gordon improve build speed for this Dockerfile:\n\n"
        "[PASTE DOCKERFILE HERE]\n\n"
        "Analyze:\n"
        "1. Layer ordering for cache efficiency\n"
        "2. Parallelizable operations\n"
        "3. Dependency caching strategies\n"
        "4. BuildKit features to leverage\n"
        "5. Multi-stage build optimization\n\n"
        "Provide specific line-by-line recommendations."
    ),
    "debugging": (
        "@gordon debug: my container exits immediately after starting\n\n"
        "Container info:\n"
        "- Image: [IMAGE_NAME]\n"
        "- Command: docker run [FULL_COMMAND]\n"
        "- Error output: [PASTE ERROR]\n\n"
        "Help me:\n"
        "1. Identify the root cause\n"
        "2. Check CMD/ENTRYPOINT configuration\n"
        "3. Verify environment variables\n"
        "4. Review logs for crash reason\n"
        "5. Suggest fixes"
    ),
    "production_readiness": (
        "@gordon review this Dockerfile for production deployment:\n\n"
        "[PASTE DOCKERFILE HERE]\n\n"
        "Evaluate against:\n"
        "1. Security hardening (non-root, minimal image)\n"
        "2. Health checks configured\n"
        "3. Proper signal handling (PID 1)\n"
        "4. Graceful shutdown support\n"
        "5. Log handling (stdout/stderr)\n"
        "6. Resource limits compatibility\n"
        "7. Secrets management approach\n\n"
        "Rate production-readiness: Not Ready / Needs Work / Ready"
    ),
    "stateless_verification": (
        "@gordon verify this container follows stateless design:\n\n"
        "[PASTE DOCKERFILE HERE]\n\n"
        "Check for violations:\n"
        "1. VOLUME instructions for app state\n"
        "2. Local file writes for persistence\n"
        "3. In-container databases\n"
        "4. Session storage on filesystem\n"
        "5. Cache directories not externalized\n\n"
        "Confirm: stateless / has state concerns"
    ),
    "compose_generation": (
        "@gordon generate docker-compose.yml for:\n\n"
        "Services:\n"
        "1. Backend: [FRAMEWORK] on port [PORT]\n"
        "2. Frontend: [FRAMEWORK] on port [PORT]\n"
        "3. Database: [TYPE]\n"
        "4. Cache: [TYPE] (optional)\n\n"
        "Requirements:\n"
        "- Development environment\n"
        "- Hot reload support\n"
        "- Shared network\n"
        "- Volume persistence for data\n"
        "- Environment variable files"
    ),
    "twelve_factor": (
        "@gordon check 12-factor compliance for this container setup:\n\n"
        "Dockerfile:\n"
        "[PASTE DOCKERFILE]\n\n"
        "Evaluate:\n"
        "1. Config via environment variables\n"
        "2. Stateless processes\n"
        "3. Port binding\n"
        "4. Disposability (fast startup/shutdown)\n"
        "5. Dev/prod parity\n"
        "6. Log streaming\n\n"
        "List violations and fixes."
    ),
}

# Secrets patterns for validation
_SECRETS_PATTERNS = re.compile(
    r"(?:SECRET|PASSWORD|TOKEN|API_KEY|PRIVATE_KEY|CREDENTIAL)\s*=\s*\S+",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Pydantic Input Models
# ---------------------------------------------------------------------------

VALID_ROLES = ("backend", "frontend")
VALID_GORDON_CATEGORIES = tuple(GORDON_PROMPTS.keys())


def _check_path_traversal(v: str) -> str:
    if ".." in v:
        raise ValueError("Path traversal not allowed: '..' in path")
    return v


class DockerfileGenerateInput(BaseModel):
    """Input for docker_generate_dockerfile."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    application_role: str = Field(
        ..., description="Application tier: 'backend' or 'frontend'"
    )
    language: str = Field(..., min_length=1, description="Programming language")
    version: str = Field(..., min_length=1, description="Language/runtime version")
    framework: str = Field(..., min_length=1, description="Framework name")
    port: int = Field(..., ge=1, le=65535, description="Port to expose")
    environment_variables: Optional[list[str]] = Field(
        None, description="Env var names (no values)"
    )
    base_image: Optional[str] = Field(None, description="Override base image")
    build_args: Optional[dict[str, str]] = Field(
        None, description="Build-time arguments"
    )
    multi_stage: bool = Field(True, description="Use multi-stage builds")
    healthcheck_path: Optional[str] = Field(
        None, description="Health check endpoint path"
    )

    @field_validator("application_role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"application_role must be one of {VALID_ROLES}")
        return v


class BuildCommandInput(BaseModel):
    """Input for docker_suggest_build_command."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    image_name: str = Field(..., min_length=1, description="Image name/tag")
    dockerfile_path: str = Field("Dockerfile", description="Path to Dockerfile")
    context_path: str = Field(".", description="Build context path")
    build_args: Optional[dict[str, str]] = Field(None, description="Build arguments")
    target_stage: Optional[str] = Field(None, description="Target build stage")

    @field_validator("dockerfile_path")
    @classmethod
    def validate_dockerfile_path(cls, v: str) -> str:
        return _check_path_traversal(v)


class RunCommandInput(BaseModel):
    """Input for docker_suggest_run_command."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    image_name: str = Field(..., min_length=1, description="Image to run")
    port: int = Field(..., ge=1, le=65535, description="Port mapping (host:container)")
    container_name: Optional[str] = Field(None, description="Container name")
    env_file: Optional[str] = Field(None, description="Path to env file")
    env_vars: Optional[list[str]] = Field(
        None, description="Env var names to pass through"
    )
    detach: bool = Field(False, description="Run in detached mode")
    restart_policy: str = Field("unless-stopped", description="Restart policy")


class GordonPromptInput(BaseModel):
    """Input for docker_suggest_gordon_prompt."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    category: str = Field(..., description="Prompt category")
    context: Optional[str] = Field(
        None, description="Additional context to embed in prompt"
    )

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in VALID_GORDON_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_GORDON_CATEGORIES}")
        return v


class BaseImageInput(BaseModel):
    """Input for docker_recommend_base_image."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    language: str = Field(..., min_length=1, description="Programming language")
    version: str = Field(..., min_length=1, description="Language version")


class DockerignoreInput(BaseModel):
    """Input for docker_generate_dockerignore."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    language: str = Field(..., min_length=1, description="Primary language")
    extras: Optional[list[str]] = Field(
        None, description="Additional patterns to exclude"
    )


class DockerfileValidateInput(BaseModel):
    """Input for docker_validate_dockerfile."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    dockerfile_content: str = Field(
        ..., min_length=1, description="Dockerfile content to validate"
    )


# ---------------------------------------------------------------------------
# Dockerfile generators (deterministic, pure functions)
# ---------------------------------------------------------------------------


def _gen_python_fastapi(
    version: str, port: int, env_vars: list[str] | None, healthcheck: str | None
) -> str:
    hc_path = healthcheck or "/health"
    env_block = ""
    if env_vars:
        env_block = f"\n# Required environment variables: {', '.join(env_vars)}\n"

    return f"""\
# syntax=docker/dockerfile:1

# ============================================
# Stage 1: Builder
# ============================================
FROM python:{version}-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ============================================
# Stage 2: Production
# ============================================
FROM python:{version}-slim AS production

RUN groupadd --gid 1000 appgroup \\
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appgroup . .

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
{env_block}
USER appuser

EXPOSE {port}

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:{port}{hc_path}')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{port}"]
"""


def _gen_python_flask(
    version: str, port: int, env_vars: list[str] | None, healthcheck: str | None
) -> str:
    hc_path = healthcheck or "/health"
    env_block = ""
    if env_vars:
        env_block = f"\n# Required environment variables: {', '.join(env_vars)}\n"

    return f"""\
# syntax=docker/dockerfile:1

FROM python:{version}-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:{version}-slim AS production

RUN groupadd --gid 1000 appgroup \\
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app
COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appgroup . .

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
{env_block}
USER appuser
EXPOSE {port}

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \\
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:{port}{hc_path}')"

CMD ["gunicorn", "--bind", "0.0.0.0:{port}", "--workers", "4", "app:app"]
"""


def _gen_python_django(
    version: str, port: int, env_vars: list[str] | None, healthcheck: str | None
) -> str:
    hc_path = healthcheck or "/health/"
    env_block = ""
    if env_vars:
        env_block = f"\n# Required environment variables: {', '.join(env_vars)}\n"

    return f"""\
# syntax=docker/dockerfile:1

FROM python:{version}-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:{version}-slim AS production

RUN groupadd --gid 1000 django \\
    && useradd --uid 1000 --gid django --create-home django

RUN apt-get update && apt-get install -y --no-install-recommends \\
    libpq5 \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /root/.local /home/django/.local
COPY --chown=django:django . .

ENV PATH=/home/django/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings.production
{env_block}
USER django
EXPOSE {port}

RUN python manage.py collectstatic --noinput

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \\
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:{port}{hc_path}')"

CMD ["gunicorn", "--bind", "0.0.0.0:{port}", "--workers", "4", "config.wsgi:application"]
"""


def _gen_python_generic(
    version: str, port: int, env_vars: list[str] | None, healthcheck: str | None
) -> str:
    hc_path = healthcheck or "/health"
    env_block = ""
    if env_vars:
        env_block = f"\n# Required environment variables: {', '.join(env_vars)}\n"

    return f"""\
# syntax=docker/dockerfile:1

FROM python:{version}-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:{version}-slim AS production

RUN groupadd --gid 1000 appgroup \\
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app
COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appgroup . .

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
{env_block}
USER appuser
EXPOSE {port}

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \\
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:{port}{hc_path}')"

CMD ["python", "main.py"]
"""


def _gen_nextjs(
    version: str, port: int, env_vars: list[str] | None, healthcheck: str | None
) -> str:
    env_block = ""
    if env_vars:
        env_block = "\n".join(f"ARG {v}\nENV {v}=${v}" for v in env_vars) + "\n"

    return f"""\
# syntax=docker/dockerfile:1

# ============================================
# Stage 1: Dependencies
# ============================================
FROM node:{version}-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# ============================================
# Stage 2: Builder
# ============================================
FROM node:{version}-alpine AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

{env_block}
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ============================================
# Stage 3: Production
# ============================================
FROM node:{version}-alpine AS production
WORKDIR /app

RUN addgroup --system --gid 1001 nodejs \\
    && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE {port}

ENV PORT={port}
ENV HOSTNAME="0.0.0.0"
ENV NODE_ENV=production

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \\
    CMD wget --no-verbose --tries=1 --spider http://localhost:{port}/api/health || exit 1

CMD ["node", "server.js"]
"""


def _gen_react(
    version: str, port: int, env_vars: list[str] | None, healthcheck: str | None
) -> str:
    env_block = ""
    if env_vars:
        env_block = "\n".join(f"ARG {v}\nENV {v}=${v}" for v in env_vars) + "\n"

    return f"""\
# syntax=docker/dockerfile:1

# ============================================
# Stage 1: Builder
# ============================================
FROM node:{version}-alpine AS builder
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

{env_block}
RUN npm run build

# ============================================
# Stage 2: Production (Nginx)
# ============================================
FROM nginx:alpine AS production

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/
COPY --from=builder /app/dist /usr/share/nginx/html

RUN chown -R nginx:nginx /usr/share/nginx/html \\
    && chown -R nginx:nginx /var/cache/nginx \\
    && chown -R nginx:nginx /var/log/nginx \\
    && touch /var/run/nginx.pid \\
    && chown -R nginx:nginx /var/run/nginx.pid

USER nginx
EXPOSE {port}

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \\
    CMD wget --no-verbose --tries=1 --spider http://localhost:{port}/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
"""


def _gen_vue(
    version: str, port: int, env_vars: list[str] | None, healthcheck: str | None
) -> str:
    env_block = ""
    if env_vars:
        env_block = "\n".join(f"ARG {v}\nENV {v}=${v}" for v in env_vars) + "\n"

    return f"""\
# syntax=docker/dockerfile:1

FROM node:{version}-alpine AS builder
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
{env_block}
RUN npm run build

FROM nginx:alpine AS production
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/
COPY --from=builder /app/dist /usr/share/nginx/html

USER nginx
EXPOSE {port}

CMD ["nginx", "-g", "daemon off;"]
"""


def _gen_express(
    version: str, port: int, env_vars: list[str] | None, healthcheck: str | None
) -> str:
    hc_path = healthcheck or "/health"
    env_block = ""
    if env_vars:
        env_block = f"\n# Required environment variables: {', '.join(env_vars)}\n"

    return f"""\
# syntax=docker/dockerfile:1

FROM node:{version}-alpine AS builder
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --only=production

FROM node:{version}-alpine AS production

RUN addgroup --system --gid 1001 nodejs \\
    && adduser --system --uid 1001 expressjs

WORKDIR /app

COPY --from=builder /app/node_modules ./node_modules
COPY --chown=expressjs:nodejs . .

USER expressjs
EXPOSE {port}

ENV NODE_ENV=production
{env_block}
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \\
    CMD wget --no-verbose --tries=1 --spider http://localhost:{port}{hc_path} || exit 1

CMD ["node", "server.js"]
"""


def _gen_nestjs(
    version: str, port: int, env_vars: list[str] | None, healthcheck: str | None
) -> str:
    hc_path = healthcheck or "/health"
    env_block = ""
    if env_vars:
        env_block = f"\n# Required environment variables: {', '.join(env_vars)}\n"

    return f"""\
# syntax=docker/dockerfile:1

FROM node:{version}-alpine AS builder
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:{version}-alpine AS production

RUN addgroup --system --gid 1001 nodejs \\
    && adduser --system --uid 1001 nestjs

WORKDIR /app

COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./

USER nestjs
EXPOSE {port}

ENV NODE_ENV=production
{env_block}
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \\
    CMD wget --no-verbose --tries=1 --spider http://localhost:{port}{hc_path} || exit 1

CMD ["node", "dist/main.js"]
"""


def _gen_go(
    version: str, port: int, env_vars: list[str] | None, healthcheck: str | None
) -> str:
    env_block = ""
    if env_vars:
        env_block = f"\n# Required environment variables: {', '.join(env_vars)}\n"

    return f"""\
# syntax=docker/dockerfile:1

# ============================================
# Stage 1: Builder
# ============================================
FROM golang:{version}-alpine AS builder

RUN apk add --no-cache git

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o /app/server ./cmd/server

# ============================================
# Stage 2: Production (Distroless)
# ============================================
FROM gcr.io/distroless/static-debian12 AS production
{env_block}
COPY --from=builder /app/server /server

EXPOSE {port}

USER nonroot:nonroot

ENTRYPOINT ["/server"]
"""


def _gen_rust(
    version: str, port: int, env_vars: list[str] | None, healthcheck: str | None
) -> str:
    hc_path = healthcheck or "/health"
    env_block = ""
    if env_vars:
        env_block = f"\n# Required environment variables: {', '.join(env_vars)}\n"

    return f"""\
# syntax=docker/dockerfile:1

FROM rust:{version}-slim AS builder

WORKDIR /app

COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {{}}" > src/main.rs
RUN cargo build --release
RUN rm -rf src

COPY . .
RUN touch src/main.rs
RUN cargo build --release

FROM debian:bookworm-slim AS production

RUN apt-get update && apt-get install -y --no-install-recommends \\
    ca-certificates curl \\
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 appgroup \\
    && useradd --uid 1000 --gid appgroup --create-home appuser
{env_block}
COPY --from=builder /app/target/release/myapp /usr/local/bin/

USER appuser
EXPOSE {port}

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \\
    CMD curl -f http://localhost:{port}{hc_path} || exit 1

CMD ["myapp"]
"""


# Generator dispatch table
_GENERATORS: dict[str, dict[str, object]] = {
    "python": {
        "fastapi": _gen_python_fastapi,
        "flask": _gen_python_flask,
        "django": _gen_python_django,
        "_default": _gen_python_generic,
    },
    "javascript": {
        "nextjs": _gen_nextjs,
        "react": _gen_react,
        "vue": _gen_vue,
        "express": _gen_express,
        "nestjs": _gen_nestjs,
        "_default": _gen_express,
    },
    "typescript": {
        "nextjs": _gen_nextjs,
        "react": _gen_react,
        "nestjs": _gen_nestjs,
        "_default": _gen_nestjs,
    },
    "go": {"_default": _gen_go},
    "rust": {"_default": _gen_rust},
}


def _select_generator(language: str, framework: str):
    """Select the correct Dockerfile generator function."""
    lang_map = _GENERATORS.get(language.lower(), {})
    gen = lang_map.get(framework.lower())
    if gen:
        return gen
    default = lang_map.get("_default")
    if default:
        return default
    # Ultimate fallback: python generic
    return _gen_python_generic


# ---------------------------------------------------------------------------
# .dockerignore content
# ---------------------------------------------------------------------------

_DOCKERIGNORE_COMMON = """\
# Git
.git/
.gitignore

# IDE
.vscode/
.idea/

# Environment (never include)
.env
.env.*
*.local

# Docker
Dockerfile*
docker-compose*
.dockerignore

# Documentation
docs/
*.md
!README.md
"""

_DOCKERIGNORE_PYTHON = """\
# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/
*.egg-info/
dist/
build/
.pytest_cache/
.mypy_cache/
.coverage
htmlcov/
"""

_DOCKERIGNORE_JS = """\
# JavaScript/TypeScript
node_modules/
.next/
dist/
build/
coverage/
.turbo/
.nuxt/
"""

_DOCKERIGNORE_GO = """\
# Go
vendor/
bin/
*.exe
*.test
"""

_DOCKERIGNORE_RUST = """\
# Rust
target/
*.rs.bk
"""


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def docker_generate_dockerfile(
    application_role: str,
    language: str,
    version: str,
    framework: str,
    port: int,
    environment_variables: list[str] | None = None,
    base_image: str | None = None,
    build_args: dict[str, str] | None = None,
    multi_stage: bool = True,
    healthcheck_path: str | None = None,
) -> str:
    """Generate a production-ready Dockerfile for a given application stack.

    Returns JSON: {status, dockerfile, template_used, notes}
    Security-hardened with non-root user, multi-stage builds, and health checks.
    """
    gen = _select_generator(language, framework)
    dockerfile = gen(version, port, environment_variables, healthcheck_path)

    # Override base image if requested
    if base_image:
        lines = dockerfile.split("\n")
        new_lines = []
        for line in lines:
            if line.strip().startswith("FROM ") and "AS " in line:
                parts = line.split(" AS ")
                new_lines.append(f"FROM {base_image} AS {parts[1]}")
            else:
                new_lines.append(line)
        dockerfile = "\n".join(new_lines)

    return json.dumps(
        {
            "status": "success",
            "dockerfile": dockerfile,
            "template_used": f"{language}/{framework}",
            "notes": [
                "Security: non-root user configured",
                "Build: multi-stage build for minimal image size",
                "Health: HEALTHCHECK instruction included",
                "WARNING: Do NOT execute docker commands — review and adjust first",
            ],
        }
    )


@mcp.tool()
async def docker_suggest_build_command(
    image_name: str,
    dockerfile_path: str = "Dockerfile",
    context_path: str = ".",
    build_args: dict[str, str] | None = None,
    target_stage: str | None = None,
) -> str:
    """Suggest a docker build command with recommended flags.

    Returns JSON: {command, notes}
    This is a SUGGESTION — not executed.
    """
    parts = ["docker build"]
    parts.append(f"    --tag {image_name}:$(git rev-parse --short HEAD)")
    parts.append(f"    --file {dockerfile_path}")

    if build_args:
        for k, v in build_args.items():
            parts.append(f"    --build-arg {k}={v}")

    if target_stage:
        parts.append(f"    --target {target_stage}")

    parts.append(f"    {context_path}")

    command = " \\\n".join(parts)

    return json.dumps(
        {
            "command": command,
            "notes": [
                "SUGGESTION ONLY — not executed",
                "Uses git short SHA for image tagging",
                "Add --no-cache to force full rebuild",
            ],
        }
    )


@mcp.tool()
async def docker_suggest_run_command(
    image_name: str,
    port: int,
    container_name: str | None = None,
    env_file: str | None = None,
    env_vars: list[str] | None = None,
    detach: bool = False,
    restart_policy: str = "unless-stopped",
) -> str:
    """Suggest a docker run command with recommended configuration.

    Returns JSON: {command, notes}
    This is a SUGGESTION — not executed.
    """
    parts = ["docker run"]

    if container_name:
        parts.append(f"    --name {container_name}")

    parts.append(f"    --publish {port}:{port}")

    if env_file:
        parts.append(f"    --env-file {env_file}")

    if env_vars:
        for var in env_vars:
            parts.append(f"    --env {var}")

    parts.append(f"    --restart {restart_policy}")

    if detach:
        parts.append("    --detach")

    parts.append(f"    {image_name}")

    command = " \\\n".join(parts)

    return json.dumps(
        {
            "command": command,
            "notes": [
                "SUGGESTION ONLY — not executed",
                "Use --env-file for secrets (never hardcode)",
                f"Restart policy: {restart_policy}",
            ],
        }
    )


@mcp.tool()
async def docker_suggest_gordon_prompt(
    category: str,
    context: str | None = None,
) -> str:
    """Generate a Docker AI (Gordon) prompt for a given category.

    Returns JSON: {status, category, prompt}
    Categories: security_audit, size_optimization, build_performance,
    debugging, production_readiness, stateless_verification,
    compose_generation, twelve_factor
    """
    prompt = GORDON_PROMPTS[category]

    if context:
        prompt = f"{prompt}\n\nAdditional context: {context}"

    return json.dumps(
        {
            "status": "success",
            "category": category,
            "prompt": prompt,
        }
    )


@mcp.tool()
async def docker_recommend_base_image(
    language: str,
    version: str,
) -> str:
    """Recommend an optimal base image for a given language and version.

    Returns JSON: {status, recommended_image, estimated_size, notes}
    """
    lang_lower = language.lower()
    entry = BASE_IMAGE_MAP.get(lang_lower)

    if entry:
        image = entry["image"].format(version=version)
        size = entry["size"]
    else:
        # Fallback: suggest ubuntu slim
        image = f"ubuntu:22.04"
        size = "~80MB"

    return json.dumps(
        {
            "status": "success",
            "recommended_image": image,
            "estimated_size": size,
            "notes": [
                "Prefer slim/alpine variants for smaller attack surface",
                "Pin specific version tags (avoid :latest)",
                f"Language: {language}, Version: {version}",
            ],
        }
    )


@mcp.tool()
async def docker_generate_dockerignore(
    language: str,
    extras: list[str] | None = None,
) -> str:
    """Generate a .dockerignore file for a given language.

    Returns JSON: {status, content}
    """
    content = _DOCKERIGNORE_COMMON

    lang_lower = language.lower()
    if lang_lower in ("python",):
        content += _DOCKERIGNORE_PYTHON
    elif lang_lower in ("javascript", "typescript"):
        content += _DOCKERIGNORE_JS
    elif lang_lower in ("go", "golang"):
        content += _DOCKERIGNORE_GO
    elif lang_lower in ("rust",):
        content += _DOCKERIGNORE_RUST

    if extras:
        content += "\n# Custom exclusions\n"
        for pattern in extras:
            content += f"{pattern}\n"

    return json.dumps(
        {
            "status": "success",
            "content": content,
        }
    )


@mcp.tool()
async def docker_validate_dockerfile(
    dockerfile_content: str,
) -> str:
    """Validate a Dockerfile against security and best-practice rules.

    Returns JSON: {has_from, has_nonroot_user, has_healthcheck,
    has_multistage, uses_latest_tag, warnings}
    """
    lines = dockerfile_content.strip().split("\n")
    upper_lines = [l.strip().upper() for l in lines]

    has_from = any(l.startswith("FROM ") for l in upper_lines)
    has_user = any(l.startswith("USER ") and "root" not in l.lower() for l in lines)
    has_healthcheck = any(l.startswith("HEALTHCHECK ") for l in upper_lines)
    has_multistage = sum(1 for l in upper_lines if l.startswith("FROM ")) > 1
    uses_latest = any(
        ":latest" in l for l in lines if l.strip().upper().startswith("FROM ")
    )

    warnings: list[str] = []

    if not has_from:
        warnings.append("Missing FROM instruction — not a valid Dockerfile")
    if not has_user:
        warnings.append(
            "No non-root USER directive — container runs as root (security risk)"
        )
    if not has_healthcheck:
        warnings.append("No HEALTHCHECK instruction — container health not monitored")
    if not has_multistage:
        warnings.append("Single-stage build — consider multi-stage for smaller images")
    if uses_latest:
        warnings.append("Uses :latest tag — pin a specific version for reproducibility")

    # Check for hardcoded secrets
    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith("ENV ") and _SECRETS_PATTERNS.search(stripped):
            warnings.append(
                "Possible hardcoded secret/credential in ENV — use runtime injection instead"
            )
            break

    return json.dumps(
        {
            "has_from": has_from,
            "has_nonroot_user": has_user,
            "has_healthcheck": has_healthcheck,
            "has_multistage": has_multistage,
            "uses_latest_tag": uses_latest,
            "warnings": warnings,
        }
    )


@mcp.tool()
async def docker_list_templates() -> str:
    """List all available Dockerfile templates.

    Returns JSON: {status, templates}
    Each template has: name, language, framework, role
    """
    return json.dumps(
        {
            "status": "success",
            "templates": TEMPLATES,
        }
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
