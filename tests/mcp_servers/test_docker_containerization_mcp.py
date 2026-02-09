"""
Tests for Docker Containerization MCP Server.

Written FIRST per TDD contract. Covers: input validation, tool behavior,
template selection, command generation, Gordon prompt generation,
validation logic, and server registration.
"""

import json

import pytest
from pydantic import ValidationError

from mcp_servers.docker_containerization_mcp import (
    DockerfileGenerateInput,
    BuildCommandInput,
    RunCommandInput,
    GordonPromptInput,
    BaseImageInput,
    DockerignoreInput,
    DockerfileValidateInput,
    mcp,
    docker_generate_dockerfile,
    docker_suggest_build_command,
    docker_suggest_run_command,
    docker_suggest_gordon_prompt,
    docker_recommend_base_image,
    docker_generate_dockerignore,
    docker_validate_dockerfile,
    docker_list_templates,
)

# ---------------------------------------------------------------------------
# Server Registration
# ---------------------------------------------------------------------------


class TestServerRegistration:
    def test_server_name(self):
        assert mcp.name == "docker_containerization_mcp"

    def test_server_has_eight_tools(self):
        tools = mcp._tool_manager._tools
        assert (
            len(tools) == 8
        ), f"Expected 8 tools, got {len(tools)}: {list(tools.keys())}"

    def test_tool_names(self):
        tool_names = set(mcp._tool_manager._tools.keys())
        expected = {
            "docker_generate_dockerfile",
            "docker_suggest_build_command",
            "docker_suggest_run_command",
            "docker_suggest_gordon_prompt",
            "docker_recommend_base_image",
            "docker_generate_dockerignore",
            "docker_validate_dockerfile",
            "docker_list_templates",
        }
        assert tool_names == expected


# ---------------------------------------------------------------------------
# Input Validation — DockerfileGenerateInput
# ---------------------------------------------------------------------------


class TestDockerfileGenerateInputValidation:
    def test_valid_backend(self):
        inp = DockerfileGenerateInput(
            application_role="backend",
            language="python",
            version="3.13",
            framework="fastapi",
            port=8000,
        )
        assert inp.application_role == "backend"
        assert inp.language == "python"

    def test_valid_frontend(self):
        inp = DockerfileGenerateInput(
            application_role="frontend",
            language="javascript",
            version="20",
            framework="nextjs",
            port=3000,
        )
        assert inp.application_role == "frontend"

    def test_rejects_invalid_role(self):
        with pytest.raises(ValidationError):
            DockerfileGenerateInput(
                application_role="middleware",
                language="python",
                version="3.13",
                framework="fastapi",
                port=8000,
            )

    def test_rejects_empty_language(self):
        with pytest.raises(ValidationError):
            DockerfileGenerateInput(
                application_role="backend",
                language="",
                version="3.13",
                framework="fastapi",
                port=8000,
            )

    def test_rejects_invalid_port(self):
        with pytest.raises(ValidationError):
            DockerfileGenerateInput(
                application_role="backend",
                language="python",
                version="3.13",
                framework="fastapi",
                port=99999,
            )

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            DockerfileGenerateInput(
                application_role="backend",
                language="python",
                version="3.13",
                framework="fastapi",
                port=8000,
                secret="hack",
            )

    def test_strips_whitespace(self):
        inp = DockerfileGenerateInput(
            application_role="  backend  ",
            language="  python  ",
            version="3.13",
            framework="fastapi",
            port=8000,
        )
        assert inp.application_role == "backend"
        assert inp.language == "python"

    def test_optional_env_vars(self):
        inp = DockerfileGenerateInput(
            application_role="backend",
            language="python",
            version="3.13",
            framework="fastapi",
            port=8000,
            environment_variables=["DATABASE_URL", "JWT_SECRET"],
        )
        assert inp.environment_variables == ["DATABASE_URL", "JWT_SECRET"]

    def test_multi_stage_default_true(self):
        inp = DockerfileGenerateInput(
            application_role="backend",
            language="python",
            version="3.13",
            framework="fastapi",
            port=8000,
        )
        assert inp.multi_stage is True


# ---------------------------------------------------------------------------
# Input Validation — BuildCommandInput
# ---------------------------------------------------------------------------


class TestBuildCommandInputValidation:
    def test_valid_input(self):
        inp = BuildCommandInput(
            image_name="myapp-backend", dockerfile_path="Dockerfile"
        )
        assert inp.image_name == "myapp-backend"

    def test_rejects_empty_image_name(self):
        with pytest.raises(ValidationError):
            BuildCommandInput(image_name="", dockerfile_path="Dockerfile")

    def test_rejects_path_traversal(self):
        with pytest.raises(ValidationError, match="[Pp]ath traversal"):
            BuildCommandInput(
                image_name="myapp", dockerfile_path="../../etc/Dockerfile"
            )


# ---------------------------------------------------------------------------
# Input Validation — RunCommandInput
# ---------------------------------------------------------------------------


class TestRunCommandInputValidation:
    def test_valid_input(self):
        inp = RunCommandInput(image_name="myapp:latest", port=8000)
        assert inp.image_name == "myapp:latest"

    def test_rejects_empty_image_name(self):
        with pytest.raises(ValidationError):
            RunCommandInput(image_name="", port=8000)


# ---------------------------------------------------------------------------
# Input Validation — GordonPromptInput
# ---------------------------------------------------------------------------


class TestGordonPromptInputValidation:
    def test_valid_category(self):
        inp = GordonPromptInput(category="security_audit")
        assert inp.category == "security_audit"

    def test_rejects_invalid_category(self):
        with pytest.raises(ValidationError):
            GordonPromptInput(category="invalid_category_xyz")


# ---------------------------------------------------------------------------
# Input Validation — DockerfileValidateInput
# ---------------------------------------------------------------------------


class TestDockerfileValidateInputValidation:
    def test_valid_input(self):
        inp = DockerfileValidateInput(
            dockerfile_content="FROM python:3.13-slim\nRUN echo hello"
        )
        assert "FROM" in inp.dockerfile_content

    def test_rejects_empty(self):
        with pytest.raises(ValidationError):
            DockerfileValidateInput(dockerfile_content="")


# ---------------------------------------------------------------------------
# Tool: docker_generate_dockerfile
# ---------------------------------------------------------------------------


class TestDockerGenerateDockerfile:
    @pytest.mark.asyncio
    async def test_generates_fastapi_dockerfile(self):
        result = await docker_generate_dockerfile(
            application_role="backend",
            language="python",
            version="3.13",
            framework="fastapi",
            port=8000,
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert "FROM python:" in data["dockerfile"]
        assert "appuser" in data["dockerfile"]
        assert "EXPOSE" in data["dockerfile"]
        assert "HEALTHCHECK" in data["dockerfile"]

    @pytest.mark.asyncio
    async def test_generates_nextjs_dockerfile(self):
        result = await docker_generate_dockerfile(
            application_role="frontend",
            language="javascript",
            version="20",
            framework="nextjs",
            port=3000,
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert "FROM node:" in data["dockerfile"]
        assert "nextjs" in data["dockerfile"]

    @pytest.mark.asyncio
    async def test_generates_flask_dockerfile(self):
        result = await docker_generate_dockerfile(
            application_role="backend",
            language="python",
            version="3.13",
            framework="flask",
            port=5000,
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert "gunicorn" in data["dockerfile"]

    @pytest.mark.asyncio
    async def test_generates_express_dockerfile(self):
        result = await docker_generate_dockerfile(
            application_role="backend",
            language="javascript",
            version="20",
            framework="express",
            port=3000,
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert "FROM node:" in data["dockerfile"]

    @pytest.mark.asyncio
    async def test_generates_go_dockerfile(self):
        result = await docker_generate_dockerfile(
            application_role="backend",
            language="go",
            version="1.22",
            framework="stdlib",
            port=8080,
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert "golang" in data["dockerfile"]

    @pytest.mark.asyncio
    async def test_generates_react_dockerfile(self):
        result = await docker_generate_dockerfile(
            application_role="frontend",
            language="javascript",
            version="20",
            framework="react",
            port=80,
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert "nginx" in data["dockerfile"]

    @pytest.mark.asyncio
    async def test_includes_env_vars(self):
        result = await docker_generate_dockerfile(
            application_role="backend",
            language="python",
            version="3.13",
            framework="fastapi",
            port=8000,
            environment_variables=["DATABASE_URL", "JWT_SECRET"],
        )
        data = json.loads(result)
        assert "DATABASE_URL" in data["dockerfile"]

    @pytest.mark.asyncio
    async def test_nonroot_user_always_present(self):
        result = await docker_generate_dockerfile(
            application_role="backend",
            language="python",
            version="3.13",
            framework="fastapi",
            port=8000,
        )
        data = json.loads(result)
        assert "USER" in data["dockerfile"]

    @pytest.mark.asyncio
    async def test_unsupported_framework_returns_generic(self):
        result = await docker_generate_dockerfile(
            application_role="backend",
            language="python",
            version="3.13",
            framework="unknown_framework",
            port=8000,
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert "FROM" in data["dockerfile"]


# ---------------------------------------------------------------------------
# Tool: docker_suggest_build_command
# ---------------------------------------------------------------------------


class TestDockerSuggestBuildCommand:
    @pytest.mark.asyncio
    async def test_returns_build_command(self):
        result = await docker_suggest_build_command(
            image_name="myapp-backend",
            dockerfile_path="Dockerfile",
        )
        data = json.loads(result)
        assert "docker build" in data["command"]
        assert "myapp-backend" in data["command"]

    @pytest.mark.asyncio
    async def test_includes_build_args(self):
        result = await docker_suggest_build_command(
            image_name="myapp",
            dockerfile_path="Dockerfile",
            build_args={"PORT": "8000", "ENV": "production"},
        )
        data = json.loads(result)
        assert "--build-arg" in data["command"]
        assert "PORT=8000" in data["command"]

    @pytest.mark.asyncio
    async def test_includes_target_stage(self):
        result = await docker_suggest_build_command(
            image_name="myapp",
            dockerfile_path="Dockerfile",
            target_stage="production",
        )
        data = json.loads(result)
        assert "--target production" in data["command"]

    @pytest.mark.asyncio
    async def test_includes_context(self):
        result = await docker_suggest_build_command(
            image_name="myapp",
            dockerfile_path="Dockerfile.backend",
            context_path="./backend",
        )
        data = json.loads(result)
        assert "./backend" in data["command"]


# ---------------------------------------------------------------------------
# Tool: docker_suggest_run_command
# ---------------------------------------------------------------------------


class TestDockerSuggestRunCommand:
    @pytest.mark.asyncio
    async def test_returns_run_command(self):
        result = await docker_suggest_run_command(
            image_name="myapp:latest",
            port=8000,
        )
        data = json.loads(result)
        assert "docker run" in data["command"]
        assert "8000:8000" in data["command"]

    @pytest.mark.asyncio
    async def test_includes_env_file(self):
        result = await docker_suggest_run_command(
            image_name="myapp:latest",
            port=8000,
            env_file=".env",
        )
        data = json.loads(result)
        assert "--env-file .env" in data["command"]

    @pytest.mark.asyncio
    async def test_includes_detach(self):
        result = await docker_suggest_run_command(
            image_name="myapp:latest",
            port=8000,
            detach=True,
        )
        data = json.loads(result)
        assert "--detach" in data["command"]

    @pytest.mark.asyncio
    async def test_includes_container_name(self):
        result = await docker_suggest_run_command(
            image_name="myapp:latest",
            port=8000,
            container_name="my-backend",
        )
        data = json.loads(result)
        assert "--name my-backend" in data["command"]


# ---------------------------------------------------------------------------
# Tool: docker_suggest_gordon_prompt
# ---------------------------------------------------------------------------


class TestDockerSuggestGordonPrompt:
    @pytest.mark.asyncio
    async def test_security_audit_prompt(self):
        result = await docker_suggest_gordon_prompt(category="security_audit")
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["category"] == "security_audit"
        assert "@gordon" in data["prompt"]
        assert "security" in data["prompt"].lower()

    @pytest.mark.asyncio
    async def test_size_optimization_prompt(self):
        result = await docker_suggest_gordon_prompt(category="size_optimization")
        data = json.loads(result)
        assert "size" in data["prompt"].lower() or "optimize" in data["prompt"].lower()

    @pytest.mark.asyncio
    async def test_debugging_prompt(self):
        result = await docker_suggest_gordon_prompt(category="debugging")
        data = json.loads(result)
        assert "debug" in data["prompt"].lower()

    @pytest.mark.asyncio
    async def test_production_readiness_prompt(self):
        result = await docker_suggest_gordon_prompt(category="production_readiness")
        data = json.loads(result)
        assert "production" in data["prompt"].lower()

    @pytest.mark.asyncio
    async def test_with_context(self):
        result = await docker_suggest_gordon_prompt(
            category="security_audit",
            context="FastAPI backend with PostgreSQL",
        )
        data = json.loads(result)
        assert "FastAPI" in data["prompt"] or "@gordon" in data["prompt"]


# ---------------------------------------------------------------------------
# Tool: docker_recommend_base_image
# ---------------------------------------------------------------------------


class TestDockerRecommendBaseImage:
    @pytest.mark.asyncio
    async def test_python_recommendation(self):
        result = await docker_recommend_base_image(language="python", version="3.13")
        data = json.loads(result)
        assert data["status"] == "success"
        assert "python" in data["recommended_image"]
        assert "slim" in data["recommended_image"]

    @pytest.mark.asyncio
    async def test_node_recommendation(self):
        result = await docker_recommend_base_image(language="javascript", version="20")
        data = json.loads(result)
        assert "node" in data["recommended_image"]
        assert "alpine" in data["recommended_image"]

    @pytest.mark.asyncio
    async def test_go_recommendation(self):
        result = await docker_recommend_base_image(language="go", version="1.22")
        data = json.loads(result)
        assert "golang" in data["recommended_image"]

    @pytest.mark.asyncio
    async def test_unknown_language(self):
        result = await docker_recommend_base_image(language="brainfuck", version="1.0")
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["recommended_image"] is not None


# ---------------------------------------------------------------------------
# Tool: docker_generate_dockerignore
# ---------------------------------------------------------------------------


class TestDockerGenerateDockerignore:
    @pytest.mark.asyncio
    async def test_python_dockerignore(self):
        result = await docker_generate_dockerignore(language="python")
        data = json.loads(result)
        assert data["status"] == "success"
        assert "__pycache__" in data["content"]
        assert ".venv" in data["content"]

    @pytest.mark.asyncio
    async def test_javascript_dockerignore(self):
        result = await docker_generate_dockerignore(language="javascript")
        data = json.loads(result)
        assert "node_modules" in data["content"]

    @pytest.mark.asyncio
    async def test_always_excludes_env(self):
        result = await docker_generate_dockerignore(language="python")
        data = json.loads(result)
        assert ".env" in data["content"]

    @pytest.mark.asyncio
    async def test_always_excludes_git(self):
        result = await docker_generate_dockerignore(language="go")
        data = json.loads(result)
        assert ".git" in data["content"]


# ---------------------------------------------------------------------------
# Tool: docker_validate_dockerfile
# ---------------------------------------------------------------------------


class TestDockerValidateDockerfile:
    @pytest.mark.asyncio
    async def test_valid_dockerfile_passes(self):
        dockerfile = (
            "FROM python:3.13-slim\n"
            "RUN groupadd --gid 1000 app && useradd --uid 1000 --gid app app\n"
            "USER app\n"
            "EXPOSE 8000\n"
            "HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1\n"
            'CMD ["uvicorn", "main:app"]\n'
        )
        result = await docker_validate_dockerfile(dockerfile_content=dockerfile)
        data = json.loads(result)
        assert data["has_nonroot_user"] is True
        assert data["has_healthcheck"] is True

    @pytest.mark.asyncio
    async def test_detects_missing_user(self):
        dockerfile = 'FROM python:3.13-slim\nCMD ["python", "app.py"]\n'
        result = await docker_validate_dockerfile(dockerfile_content=dockerfile)
        data = json.loads(result)
        assert data["has_nonroot_user"] is False
        assert any(
            "non-root" in w.lower() or "user" in w.lower() for w in data["warnings"]
        )

    @pytest.mark.asyncio
    async def test_detects_missing_healthcheck(self):
        dockerfile = 'FROM python:3.13-slim\nUSER app\nCMD ["python", "app.py"]\n'
        result = await docker_validate_dockerfile(dockerfile_content=dockerfile)
        data = json.loads(result)
        assert data["has_healthcheck"] is False

    @pytest.mark.asyncio
    async def test_detects_latest_tag(self):
        dockerfile = 'FROM python:latest\nUSER app\nCMD ["python", "app.py"]\n'
        result = await docker_validate_dockerfile(dockerfile_content=dockerfile)
        data = json.loads(result)
        assert any("latest" in w.lower() for w in data["warnings"])

    @pytest.mark.asyncio
    async def test_detects_hardcoded_secrets(self):
        dockerfile = (
            "FROM python:3.13-slim\n"
            "ENV SECRET_KEY=mysecretvalue123\n"
            "ENV PASSWORD=admin\n"
            'CMD ["python", "app.py"]\n'
        )
        result = await docker_validate_dockerfile(dockerfile_content=dockerfile)
        data = json.loads(result)
        assert any(
            "secret" in w.lower() or "credential" in w.lower() for w in data["warnings"]
        )

    @pytest.mark.asyncio
    async def test_detects_no_from(self):
        dockerfile = 'RUN echo hello\nCMD ["echo", "hi"]\n'
        result = await docker_validate_dockerfile(dockerfile_content=dockerfile)
        data = json.loads(result)
        assert any("FROM" in w for w in data["warnings"])


# ---------------------------------------------------------------------------
# Tool: docker_list_templates
# ---------------------------------------------------------------------------


class TestDockerListTemplates:
    @pytest.mark.asyncio
    async def test_returns_all_templates(self):
        result = await docker_list_templates()
        data = json.loads(result)
        assert data["status"] == "success"
        templates = data["templates"]
        assert len(templates) >= 8

    @pytest.mark.asyncio
    async def test_templates_have_required_fields(self):
        result = await docker_list_templates()
        data = json.loads(result)
        for tmpl in data["templates"]:
            assert "name" in tmpl
            assert "language" in tmpl
            assert "framework" in tmpl
            assert "role" in tmpl

    @pytest.mark.asyncio
    async def test_includes_python_templates(self):
        result = await docker_list_templates()
        data = json.loads(result)
        languages = [t["language"] for t in data["templates"]]
        assert "python" in languages

    @pytest.mark.asyncio
    async def test_includes_javascript_templates(self):
        result = await docker_list_templates()
        data = json.loads(result)
        languages = [t["language"] for t in data["templates"]]
        assert "javascript" in languages
