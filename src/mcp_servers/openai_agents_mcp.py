"""
OpenAI Agents SDK MCP Server — generates agent definitions, tool bindings,
handoff configurations, guardrails, session setup, and structured output schemas.

Tools:
    agents_generate_agent        Generate Agent definition code
    agents_generate_tool         Generate @function_tool decorator code
    agents_generate_handoff      Generate multi-agent handoff configuration
    agents_generate_guardrail    Generate input/output guardrail code
    agents_generate_session      Generate session persistence setup
    agents_generate_structured   Generate structured output with Pydantic
    agents_generate_runner       Generate Runner execution code
    agents_generate_mcp_integration  Generate MCP server integration
    agents_detect_antipatterns   Detect common Agents SDK anti-patterns
    agents_generate_scaffold     Generate complete agent scaffold
"""

import json
import re
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("openai_agents_mcp")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_MODELS = (
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
    "o1",
    "o1-mini",
)
VALID_SESSION_TYPES = ("memory", "sqlite", "redis")
VALID_RUNNER_MODES = ("sync", "async", "stream")
VALID_GUARDRAIL_TYPES = ("input", "output")

# ---------------------------------------------------------------------------
# Anti-patterns
# ---------------------------------------------------------------------------

ANTIPATTERNS: dict[str, dict] = {
    "vague-instructions": {
        "description": "Agent instructions are too vague (e.g., 'be helpful')",
        "detection": "Instructions under 20 characters or generic phrases",
        "impact": "Agent behavior unpredictable, poor task completion",
        "fix": "Write specific, action-oriented instructions with constraints",
        "severity": "high",
    },
    "missing-tool-docstring": {
        "description": "Tool function lacks docstring or Args section",
        "detection": "No docstring or no 'Args:' in docstring",
        "impact": "LLM cannot understand tool purpose or parameters",
        "fix": "Add descriptive docstring with Args section documenting each parameter",
        "severity": "critical",
    },
    "no-guardrails": {
        "description": "User-facing agent has no input/output guardrails",
        "detection": "Agent with empty guardrails lists",
        "impact": "Vulnerable to prompt injection, harmful outputs",
        "fix": "Add InputGuardrail for PII/injection, OutputGuardrail for safety",
        "severity": "high",
    },
    "memory-session-production": {
        "description": "Using in-memory session in production",
        "detection": "No session parameter or session type is 'memory'",
        "impact": "Conversation history lost on restart, no multi-instance support",
        "fix": "Use SQLiteSession for dev, RedisSession for production",
        "severity": "high",
    },
    "run-sync-in-async": {
        "description": "Using Runner.run_sync in async context",
        "detection": "run_sync called inside async function",
        "impact": "Blocks event loop, degrades performance",
        "fix": "Use 'await Runner.run()' in async contexts",
        "severity": "medium",
    },
    "circular-handoff": {
        "description": "Agents can hand off in a cycle without termination",
        "detection": "A→B and B→A handoffs without condition",
        "impact": "Infinite loop, token exhaustion",
        "fix": "Add termination conditions or limit handoff depth",
        "severity": "critical",
    },
    "no-output-type": {
        "description": "Agent returns free text when structured data expected",
        "detection": "No output_type but downstream code expects schema",
        "impact": "Parsing failures, type errors",
        "fix": "Define Pydantic model and set output_type parameter",
        "severity": "medium",
    },
    "no-error-handling": {
        "description": "Tool functions don't handle exceptions",
        "detection": "No try/except in tool function body",
        "impact": "Unhandled errors crash agent execution",
        "fix": "Wrap tool logic in try/except, return error message on failure",
        "severity": "medium",
    },
}

# ---------------------------------------------------------------------------
# Code templates
# ---------------------------------------------------------------------------

AGENT_TEMPLATE = '''from agents import Agent

{name_lower}_agent = Agent(
    name="{name}",
    instructions="""{instructions}""",
    model="{model}",
    tools=[{tools}],{output_type}{handoffs}{guardrails}
)
'''

TOOL_TEMPLATE = '''from agents import function_tool

@function_tool
def {name}({params}) -> {return_type}:
    """{description}

    Args:
{args_doc}
    """
{body}
'''

GUARDRAIL_TEMPLATE = '''from agents import {decorator}

@{decorator}
async def {name}({param}: str) -> bool:
    """{description}"""
{body}
'''

SESSION_TEMPLATES = {
    "memory": "# In-memory session (development only)\nsession = None  # Default in-memory",
    "sqlite": """from agents.sessions import SQLiteSession

session = SQLiteSession("{db_path}")
""",
    "redis": """from agents.sessions import RedisSession

session = RedisSession(url="{redis_url}", session_id="{session_id}")
""",
}

RUNNER_TEMPLATES = {
    "sync": """from agents import Runner

result = Runner.run_sync({agent}, "{prompt}")
print(result.final_output)
""",
    "async": """from agents import Runner

async def run_agent():
    result = await Runner.run({agent}, "{prompt}", session=session)
    return result.final_output
""",
    "stream": """from agents import Runner

async def stream_agent():
    async for event in Runner.run_stream({agent}, "{prompt}"):
        if event.type == "text_delta":
            print(event.text, end="", flush=True)
""",
}

MCP_INTEGRATION_TEMPLATE = '''from agents import Agent
from agents.mcp import MCPServerStdio

{agent_name}_agent = Agent(
    name="{agent_name}",
    instructions="""{instructions}""",
    mcp_servers=[
        MCPServerStdio("{command}", {args}),
    ],
)
'''

STRUCTURED_OUTPUT_TEMPLATE = '''from pydantic import BaseModel
from typing import Optional
from agents import Agent

class {class_name}(BaseModel):
{fields}

{agent_name}_agent = Agent(
    name="{agent_name}",
    instructions="""{instructions}""",
    model="{model}",
    output_type={class_name},
)
'''

HANDOFF_TEMPLATE = '''from agents import Agent, handoff

{agent_defs}

{main_agent} = Agent(
    name="{main_name}",
    instructions="""{main_instructions}""",
    handoffs=[{handoff_list}],
)
'''

# ---------------------------------------------------------------------------
# Pydantic input models
# ---------------------------------------------------------------------------

_CFG = ConfigDict(str_strip_whitespace=True, extra="forbid")


class AgentInput(BaseModel):
    model_config = _CFG
    name: str = Field(..., min_length=1, max_length=50, description="Agent name")
    instructions: str = Field(
        ..., min_length=10, max_length=2000, description="System instructions"
    )
    model: str = Field(default="gpt-4o", description="LLM model")
    tools: list[str] = Field(default_factory=list, description="Tool function names")
    output_type: Optional[str] = Field(
        default=None, description="Pydantic model name for structured output"
    )
    handoffs: list[str] = Field(
        default_factory=list, description="Agent names for handoffs"
    )
    input_guardrails: list[str] = Field(
        default_factory=list, description="Input guardrail function names"
    )
    output_guardrails: list[str] = Field(
        default_factory=list, description="Output guardrail function names"
    )

    @field_validator("name")
    @classmethod
    def _check_name(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", v):
            raise ValueError("name must be alphanumeric starting with letter")
        return v

    @field_validator("model")
    @classmethod
    def _check_model(cls, v: str) -> str:
        if v not in VALID_MODELS:
            raise ValueError(f"model must be one of {VALID_MODELS}")
        return v


class ToolInput(BaseModel):
    model_config = _CFG
    name: str = Field(..., min_length=1, max_length=50, description="Function name")
    description: str = Field(
        ..., min_length=10, max_length=500, description="Tool description"
    )
    params: list[dict] = Field(
        ...,
        min_length=1,
        description="Parameters [{name, type, description, default?}]",
    )
    return_type: str = Field(default="str", description="Return type annotation")
    body: str = Field(default="    pass", description="Function body")

    @field_validator("name")
    @classmethod
    def _check_name(cls, v: str) -> str:
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError("name must be snake_case")
        return v


class HandoffInput(BaseModel):
    model_config = _CFG
    main_agent: str = Field(..., description="Main agent name")
    main_instructions: str = Field(
        ..., min_length=10, description="Main agent instructions"
    )
    delegate_agents: list[dict] = Field(
        ..., min_length=1, description="Agents to delegate to [{name, instructions}]"
    )


class GuardrailInput(BaseModel):
    model_config = _CFG
    name: str = Field(
        ..., min_length=1, max_length=50, description="Guardrail function name"
    )
    guardrail_type: str = Field(..., description="input or output")
    description: str = Field(
        ..., min_length=10, description="What the guardrail checks"
    )
    body: str = Field(
        default="    return True", description="Function body returning bool"
    )

    @field_validator("guardrail_type")
    @classmethod
    def _check_type(cls, v: str) -> str:
        if v not in VALID_GUARDRAIL_TYPES:
            raise ValueError(f"guardrail_type must be one of {VALID_GUARDRAIL_TYPES}")
        return v


class SessionInput(BaseModel):
    model_config = _CFG
    session_type: str = Field(default="sqlite", description="memory, sqlite, or redis")
    db_path: str = Field(default="conversations.db", description="SQLite database path")
    redis_url: str = Field(
        default="redis://localhost:6379", description="Redis connection URL"
    )
    session_id: str = Field(default="default", description="Session identifier")

    @field_validator("session_type")
    @classmethod
    def _check_type(cls, v: str) -> str:
        if v not in VALID_SESSION_TYPES:
            raise ValueError(f"session_type must be one of {VALID_SESSION_TYPES}")
        return v


class StructuredOutputInput(BaseModel):
    model_config = _CFG
    class_name: str = Field(
        ..., min_length=1, max_length=50, description="Pydantic model class name"
    )
    fields: list[dict] = Field(
        ..., min_length=1, description="Fields [{name, type, description?}]"
    )
    agent_name: str = Field(..., description="Agent name")
    instructions: str = Field(..., min_length=10, description="Agent instructions")
    model: str = Field(default="gpt-4o", description="LLM model")

    @field_validator("class_name")
    @classmethod
    def _check_class(cls, v: str) -> str:
        if not re.match(r"^[A-Z][A-Za-z0-9]*$", v):
            raise ValueError("class_name must be PascalCase")
        return v


class RunnerInput(BaseModel):
    model_config = _CFG
    mode: str = Field(default="sync", description="sync, async, or stream")
    agent_var: str = Field(default="agent", description="Agent variable name")
    prompt: str = Field(default="Hello!", description="Initial prompt")
    include_session: bool = Field(
        default=False, description="Include session parameter"
    )

    @field_validator("mode")
    @classmethod
    def _check_mode(cls, v: str) -> str:
        if v not in VALID_RUNNER_MODES:
            raise ValueError(f"mode must be one of {VALID_RUNNER_MODES}")
        return v


class MCPIntegrationInput(BaseModel):
    model_config = _CFG
    agent_name: str = Field(..., description="Agent name")
    instructions: str = Field(..., min_length=10, description="Agent instructions")
    command: str = Field(..., description="MCP server command (e.g., 'npx')")
    args: list[str] = Field(..., min_length=1, description="MCP server arguments")


class DetectAntipatternsInput(BaseModel):
    model_config = _CFG
    code: str = Field(..., min_length=10, description="Code to analyze")
    include_fixes: bool = Field(default=True, description="Include fix recommendations")


class ScaffoldInput(BaseModel):
    model_config = _CFG
    agent_name: str = Field(..., description="Main agent name")
    instructions: str = Field(..., min_length=10, description="Agent instructions")
    model: str = Field(default="gpt-4o", description="LLM model")
    tools: list[dict] = Field(
        default_factory=list, description="Tools [{name, description, params}]"
    )
    output_type: Optional[dict] = Field(
        default=None, description="Structured output {class_name, fields}"
    )
    session_type: str = Field(default="sqlite", description="Session persistence type")
    include_guardrails: bool = Field(
        default=True, description="Include basic guardrails"
    )
    runner_mode: str = Field(default="async", description="Runner execution mode")


# ---------------------------------------------------------------------------
# Pure generator functions
# ---------------------------------------------------------------------------


def _gen_agent(inp: AgentInput) -> str:
    """Generate Agent definition code."""
    tools_str = ", ".join(inp.tools) if inp.tools else ""
    output_type_str = f"\n    output_type={inp.output_type}," if inp.output_type else ""
    handoffs_str = ""
    if inp.handoffs:
        handoff_list = ", ".join(f"handoff({a}_agent)" for a in inp.handoffs)
        handoffs_str = f"\n    handoffs=[{handoff_list}],"
    guardrails_str = ""
    if inp.input_guardrails:
        guardrails_str += f"\n    input_guardrails=[{', '.join(inp.input_guardrails)}],"
    if inp.output_guardrails:
        guardrails_str += (
            f"\n    output_guardrails=[{', '.join(inp.output_guardrails)}],"
        )

    return AGENT_TEMPLATE.format(
        name=inp.name,
        name_lower=inp.name.lower(),
        instructions=inp.instructions,
        model=inp.model,
        tools=tools_str,
        output_type=output_type_str,
        handoffs=handoffs_str,
        guardrails=guardrails_str,
    )


def _gen_tool(inp: ToolInput) -> str:
    """Generate @function_tool code."""
    params_list = []
    args_doc_lines = []

    for p in inp.params:
        pname = p["name"]
        ptype = p.get("type", "str")
        pdesc = p.get("description", "")
        pdefault = p.get("default")

        if pdefault is not None:
            params_list.append(
                f'{pname}: {ptype} = "{pdefault}"'
                if isinstance(pdefault, str)
                else f"{pname}: {ptype} = {pdefault}"
            )
        else:
            params_list.append(f"{pname}: {ptype}")

        args_doc_lines.append(f"        {pname}: {pdesc}")

    return TOOL_TEMPLATE.format(
        name=inp.name,
        params=", ".join(params_list),
        return_type=inp.return_type,
        description=inp.description,
        args_doc="\n".join(args_doc_lines),
        body=inp.body,
    )


def _gen_handoff(inp: HandoffInput) -> str:
    """Generate multi-agent handoff configuration."""
    agent_defs = []
    handoff_names = []

    for da in inp.delegate_agents:
        name = da["name"]
        instructions = da["instructions"]
        agent_defs.append(f'''{name.lower()}_agent = Agent(
    name="{name}",
    instructions="""{instructions}"""
)''')
        handoff_names.append(f"handoff({name.lower()}_agent)")

    return HANDOFF_TEMPLATE.format(
        agent_defs="\n\n".join(agent_defs),
        main_agent=inp.main_agent.lower() + "_agent",
        main_name=inp.main_agent,
        main_instructions=inp.main_instructions,
        handoff_list=", ".join(handoff_names),
    )


def _gen_guardrail(inp: GuardrailInput) -> str:
    """Generate guardrail code."""
    decorator = "InputGuardrail" if inp.guardrail_type == "input" else "OutputGuardrail"
    param = "input" if inp.guardrail_type == "input" else "output"

    return GUARDRAIL_TEMPLATE.format(
        decorator=decorator,
        name=inp.name,
        param=param,
        description=inp.description,
        body=inp.body,
    )


def _gen_session(inp: SessionInput) -> str:
    """Generate session persistence setup."""
    if inp.session_type == "memory":
        return SESSION_TEMPLATES["memory"]
    elif inp.session_type == "sqlite":
        return SESSION_TEMPLATES["sqlite"].format(db_path=inp.db_path)
    else:
        return SESSION_TEMPLATES["redis"].format(
            redis_url=inp.redis_url, session_id=inp.session_id
        )


def _gen_structured(inp: StructuredOutputInput) -> str:
    """Generate structured output code."""
    field_lines = []
    for f in inp.fields:
        fname = f["name"]
        ftype = f.get("type", "str")
        fdesc = f.get("description")
        if fdesc:
            field_lines.append(f"    {fname}: {ftype}  # {fdesc}")
        else:
            field_lines.append(f"    {fname}: {ftype}")

    return STRUCTURED_OUTPUT_TEMPLATE.format(
        class_name=inp.class_name,
        fields="\n".join(field_lines),
        agent_name=inp.agent_name.lower(),
        instructions=inp.instructions,
        model=inp.model,
    )


def _gen_runner(inp: RunnerInput) -> str:
    """Generate Runner execution code."""
    template = RUNNER_TEMPLATES[inp.mode]
    code = template.format(agent=inp.agent_var, prompt=inp.prompt)

    if inp.include_session and inp.mode == "sync":
        code = code.replace(")", ", session=session)")

    return code


def _gen_mcp_integration(inp: MCPIntegrationInput) -> str:
    """Generate MCP server integration code."""
    return MCP_INTEGRATION_TEMPLATE.format(
        agent_name=inp.agent_name.lower(),
        instructions=inp.instructions,
        command=inp.command,
        args=json.dumps(inp.args),
    )


def _detect_antipatterns(code: str, include_fixes: bool) -> list[dict]:
    """Detect anti-patterns in code."""
    findings = []

    # Check for vague instructions
    if re.search(r'instructions\s*=\s*["\'][^"\']{1,20}["\']', code):
        entry = {"pattern": "vague-instructions", **ANTIPATTERNS["vague-instructions"]}
        if not include_fixes:
            del entry["fix"]
        findings.append(entry)

    # Check for missing docstrings
    if re.search(r'@function_tool\s*\ndef\s+\w+\([^)]*\)[^:]*:\s*\n\s*[^"\']', code):
        entry = {
            "pattern": "missing-tool-docstring",
            **ANTIPATTERNS["missing-tool-docstring"],
        }
        if not include_fixes:
            del entry["fix"]
        findings.append(entry)

    # Check for no guardrails
    if re.search(r"Agent\s*\([^)]*\)", code) and "guardrails" not in code.lower():
        entry = {"pattern": "no-guardrails", **ANTIPATTERNS["no-guardrails"]}
        if not include_fixes:
            del entry["fix"]
        findings.append(entry)

    # Check for run_sync in async
    if re.search(r"async\s+def.*run_sync", code, re.DOTALL):
        entry = {"pattern": "run-sync-in-async", **ANTIPATTERNS["run-sync-in-async"]}
        if not include_fixes:
            del entry["fix"]
        findings.append(entry)

    # Check for no output_type when structured expected
    if "BaseModel" in code and "output_type" not in code:
        entry = {"pattern": "no-output-type", **ANTIPATTERNS["no-output-type"]}
        if not include_fixes:
            del entry["fix"]
        findings.append(entry)

    return findings


def _gen_scaffold(inp: ScaffoldInput) -> dict:
    """Generate complete agent scaffold."""
    sections = {}

    # Imports
    imports = ["from agents import Agent, Runner"]
    if inp.tools:
        imports.append("from agents import function_tool")
    if inp.include_guardrails:
        imports.append("from agents import InputGuardrail, OutputGuardrail")
    if inp.output_type:
        imports.append("from pydantic import BaseModel")
    sections["imports"] = "\n".join(imports)

    # Output type
    if inp.output_type:
        field_lines = []
        for f in inp.output_type.get("fields", []):
            field_lines.append(f"    {f['name']}: {f.get('type', 'str')}")
        sections["output_type"] = f"""class {inp.output_type["class_name"]}(BaseModel):
{chr(10).join(field_lines)}
"""

    # Tools
    if inp.tools:
        tool_codes = []
        for t in inp.tools:
            params = t.get(
                "params", [{"name": "query", "type": "str", "description": "Input"}]
            )
            tool_inp = ToolInput(
                name=t["name"],
                description=t.get("description", f"Perform {t['name']} operation"),
                params=params,
                return_type=t.get("return_type", "str"),
                body=t.get("body", "    pass"),
            )
            tool_codes.append(_gen_tool(tool_inp))
        sections["tools"] = "\n\n".join(tool_codes)

    # Guardrails
    if inp.include_guardrails:
        sections["guardrails"] = '''@InputGuardrail
async def block_pii(input: str) -> bool:
    """Block requests containing PII patterns."""
    import re
    pii_patterns = [r'\\b\\d{3}-\\d{2}-\\d{4}\\b', r'\\b\\d{16}\\b']
    return not any(re.search(p, input) for p in pii_patterns)

@OutputGuardrail
async def check_safety(output: str) -> bool:
    """Ensure output doesn't contain harmful content."""
    blocked = ["hack", "exploit", "bypass"]
    return not any(t in output.lower() for t in blocked)
'''

    # Session
    session_inp = SessionInput(session_type=inp.session_type)
    sections["session"] = _gen_session(session_inp)

    # Agent
    agent_inp = AgentInput(
        name=inp.agent_name,
        instructions=inp.instructions,
        model=inp.model,
        tools=[t["name"] for t in inp.tools] if inp.tools else [],
        output_type=inp.output_type["class_name"] if inp.output_type else None,
        input_guardrails=["block_pii"] if inp.include_guardrails else [],
        output_guardrails=["check_safety"] if inp.include_guardrails else [],
    )
    sections["agent"] = _gen_agent(agent_inp)

    # Runner
    runner_inp = RunnerInput(
        mode=inp.runner_mode,
        agent_var=f"{inp.agent_name.lower()}_agent",
        include_session=inp.session_type != "memory",
    )
    sections["runner"] = _gen_runner(runner_inp)

    return sections


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def agents_generate_agent(
    name: str,
    instructions: str,
    model: str = "gpt-4o",
    tools: list[str] | None = None,
    output_type: str | None = None,
    handoffs: list[str] | None = None,
    input_guardrails: list[str] | None = None,
    output_guardrails: list[str] | None = None,
) -> str:
    """Generate Agent definition code. Returns Python code string."""
    inp = AgentInput(
        name=name,
        instructions=instructions,
        model=model,
        tools=tools or [],
        output_type=output_type,
        handoffs=handoffs or [],
        input_guardrails=input_guardrails or [],
        output_guardrails=output_guardrails or [],
    )
    return json.dumps({"code": _gen_agent(inp)})


@mcp.tool()
async def agents_generate_tool(
    name: str,
    description: str,
    params: list[dict],
    return_type: str = "str",
    body: str = "    pass",
) -> str:
    """Generate @function_tool decorator code. Returns Python code string."""
    inp = ToolInput(
        name=name,
        description=description,
        params=params,
        return_type=return_type,
        body=body,
    )
    return json.dumps({"code": _gen_tool(inp)})


@mcp.tool()
async def agents_generate_handoff(
    main_agent: str,
    main_instructions: str,
    delegate_agents: list[dict],
) -> str:
    """Generate multi-agent handoff configuration. Returns Python code string."""
    inp = HandoffInput(
        main_agent=main_agent,
        main_instructions=main_instructions,
        delegate_agents=delegate_agents,
    )
    return json.dumps({"code": _gen_handoff(inp)})


@mcp.tool()
async def agents_generate_guardrail(
    name: str,
    guardrail_type: str,
    description: str,
    body: str = "    return True",
) -> str:
    """Generate input/output guardrail code. Returns Python code string."""
    inp = GuardrailInput(
        name=name,
        guardrail_type=guardrail_type,
        description=description,
        body=body,
    )
    return json.dumps({"code": _gen_guardrail(inp)})


@mcp.tool()
async def agents_generate_session(
    session_type: str = "sqlite",
    db_path: str = "conversations.db",
    redis_url: str = "redis://localhost:6379",
    session_id: str = "default",
) -> str:
    """Generate session persistence setup. Returns Python code string."""
    inp = SessionInput(
        session_type=session_type,
        db_path=db_path,
        redis_url=redis_url,
        session_id=session_id,
    )
    return json.dumps({"code": _gen_session(inp)})


@mcp.tool()
async def agents_generate_structured(
    class_name: str,
    fields: list[dict],
    agent_name: str,
    instructions: str,
    model: str = "gpt-4o",
) -> str:
    """Generate structured output with Pydantic model. Returns Python code string."""
    inp = StructuredOutputInput(
        class_name=class_name,
        fields=fields,
        agent_name=agent_name,
        instructions=instructions,
        model=model,
    )
    return json.dumps({"code": _gen_structured(inp)})


@mcp.tool()
async def agents_generate_runner(
    mode: str = "sync",
    agent_var: str = "agent",
    prompt: str = "Hello!",
    include_session: bool = False,
) -> str:
    """Generate Runner execution code. Returns Python code string."""
    inp = RunnerInput(
        mode=mode,
        agent_var=agent_var,
        prompt=prompt,
        include_session=include_session,
    )
    return json.dumps({"code": _gen_runner(inp)})


@mcp.tool()
async def agents_generate_mcp_integration(
    agent_name: str,
    instructions: str,
    command: str,
    args: list[str],
) -> str:
    """Generate MCP server integration code. Returns Python code string."""
    inp = MCPIntegrationInput(
        agent_name=agent_name,
        instructions=instructions,
        command=command,
        args=args,
    )
    return json.dumps({"code": _gen_mcp_integration(inp)})


@mcp.tool()
async def agents_detect_antipatterns(
    code: str,
    include_fixes: bool = True,
) -> str:
    """Detect common Agents SDK anti-patterns in code. Returns findings list."""
    inp = DetectAntipatternsInput(code=code, include_fixes=include_fixes)
    findings = _detect_antipatterns(inp.code, inp.include_fixes)
    return json.dumps({"findings": findings, "count": len(findings)})


@mcp.tool()
async def agents_generate_scaffold(
    agent_name: str,
    instructions: str,
    model: str = "gpt-4o",
    tools: list[dict] | None = None,
    output_type: dict | None = None,
    session_type: str = "sqlite",
    include_guardrails: bool = True,
    runner_mode: str = "async",
) -> str:
    """Generate complete agent scaffold with all components. Returns sections dict."""
    inp = ScaffoldInput(
        agent_name=agent_name,
        instructions=instructions,
        model=model,
        tools=tools or [],
        output_type=output_type,
        session_type=session_type,
        include_guardrails=include_guardrails,
        runner_mode=runner_mode,
    )
    sections = _gen_scaffold(inp)
    return json.dumps({"sections": sections})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
