"""
Token Warden MCP Server — system-level token governor with global pre-hook
enforcement, automatic mode switching, and hard budget limits.

CONTROL-PLANE TOOLS:
    tw_enable_hook           Enable global pre-hook enforcement
    tw_disable_hook          Disable global pre-hook (DESIGN mode only)
    tw_set_mode              Switch mode (DESIGN/EXECUTION)
    tw_detect_mode           Auto-detect mode from task text
    tw_set_budget            Set token budgets (request/skill/mcp/session)
    tw_get_state             Query current policy state
    tw_enforce               Enforce policy on payload (pre-hook entry)
    tw_check_budget          Check if budget allows operation
    tw_terminate             Return budget-exceeded termination
    tw_audit                 Audit session token usage

DESIGN LAW: Exceeding budget = termination, not summarization.
FAIL-CLOSED: On error → EXECUTION mode, v=0, minimum budgets.
"""

import hashlib
import json
import re
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("token_warden_mcp")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODE_EXECUTION = "EXECUTION"
MODE_DESIGN = "DESIGN"

# Mode detection patterns
EXECUTION_PATTERNS = [
    "build",
    "create",
    "implement",
    "fix",
    "generate",
    "write",
    "add",
    "remove",
    "delete",
    "update",
    "deploy",
]
DESIGN_PATTERNS = [
    "design",
    "analyze",
    "plan",
    "explore",
    "consider",
    "evaluate",
    "compare",
    "assess",
    "review",
    "think",
]

# Verbosity configs per mode
MODE_CONFIGS = {
    MODE_EXECUTION: {
        "v": 0,
        "prose": False,
        "explain": False,
        "alternatives": False,
        "exploration": False,
        "cot": False,
    },
    MODE_DESIGN: {
        "v": 2,
        "prose": True,
        "explain": True,
        "alternatives": True,
        "exploration": True,
        "cot": True,
    },
}

# Default budgets (tokens)
DEFAULT_BUDGETS = {
    "request": 500,
    "skill": 1000,
    "mcp": 300,
    "session": 50000,
}

# Minimum budgets (fail-closed)
MIN_BUDGETS = {
    "request": 100,
    "skill": 200,
    "mcp": 50,
    "session": 5000,
}

# Waste patterns for audit
WASTE_PATTERNS = [
    {"p": r"let me explain", "t": "prose", "w": 50},
    {"p": r"here's what", "t": "explain", "w": 30},
    {"p": r"alternatively", "t": "alt", "w": 100},
    {"p": r"you could also", "t": "alt", "w": 80},
    {"p": r"note that", "t": "comment", "w": 20},
    {"p": r"keep in mind", "t": "comment", "w": 25},
    {"p": r"it's worth", "t": "prose", "w": 40},
    {"p": r"in other words", "t": "explain", "w": 30},
    {"p": r"to summarize", "t": "prose", "w": 50},
    {"p": r"let's think", "t": "cot", "w": 60},
    {"p": r"step by step", "t": "cot", "w": 40},
    {"p": r"first,?.+second", "t": "cot", "w": 50},
]

# Blocked phrases for stripping
BLOCKED = [
    "let me",
    "here's",
    "alternatively",
    "you could",
    "another option",
    "consider",
    "it's worth",
    "note that",
    "to clarify",
    "in summary",
]

# ---------------------------------------------------------------------------
# Global state (per-process, reset on failure)
# ---------------------------------------------------------------------------

_STATE = {
    "hook_enabled": True,
    "mode": MODE_EXECUTION,
    "budgets": DEFAULT_BUDGETS.copy(),
    "whitelist": [],
    "session_used": 0,
}


def _reset_to_safe():
    """Fail-closed: reset to safest state."""
    global _STATE
    _STATE = {
        "hook_enabled": True,
        "mode": MODE_EXECUTION,
        "budgets": MIN_BUDGETS.copy(),
        "whitelist": [],
        "session_used": 0,
    }


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

_CFG = ConfigDict(str_strip_whitespace=True, extra="forbid")


class EnableHookInput(BaseModel):
    model_config = _CFG
    whitelist: list[str] = Field(default_factory=list, description="Allowed paths")

    @field_validator("whitelist")
    @classmethod
    def _no_traversal(cls, v: list[str]) -> list[str]:
        for p in v:
            if ".." in p:
                raise ValueError("Path traversal blocked")
        return v


class SetModeInput(BaseModel):
    model_config = _CFG
    mode: str = Field(..., description="EXECUTION or DESIGN")

    @field_validator("mode")
    @classmethod
    def _check_mode(cls, v: str) -> str:
        v = v.upper()
        if v not in (MODE_EXECUTION, MODE_DESIGN):
            raise ValueError("mode must be EXECUTION or DESIGN")
        return v


class DetectModeInput(BaseModel):
    model_config = _CFG
    task: str = Field(..., min_length=1, max_length=2000, description="Task text")
    override: Optional[str] = Field(default=None, description="Explicit mode override")

    @field_validator("override")
    @classmethod
    def _check_override(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.upper()
            if v not in (MODE_EXECUTION, MODE_DESIGN):
                raise ValueError("override must be EXECUTION or DESIGN")
        return v


class SetBudgetInput(BaseModel):
    model_config = _CFG
    request: Optional[int] = Field(default=None, ge=50, le=10000)
    skill: Optional[int] = Field(default=None, ge=100, le=20000)
    mcp: Optional[int] = Field(default=None, ge=25, le=5000)
    session: Optional[int] = Field(default=None, ge=1000, le=500000)


class EnforceInput(BaseModel):
    model_config = _CFG
    payload: str = Field(..., min_length=1, description="Payload to enforce")
    context_paths: list[str] = Field(
        default_factory=list, description="Paths in context"
    )
    est_tokens: int = Field(default=0, ge=0, description="Estimated output tokens")


class CheckBudgetInput(BaseModel):
    model_config = _CFG
    scope: str = Field(..., description="request, skill, mcp, or session")
    tokens: int = Field(..., ge=0, description="Tokens to check")

    @field_validator("scope")
    @classmethod
    def _check_scope(cls, v: str) -> str:
        if v not in ("request", "skill", "mcp", "session"):
            raise ValueError("scope must be request, skill, mcp, or session")
        return v


class AuditInput(BaseModel):
    model_config = _CFG
    messages: list[str] = Field(..., min_length=1, description="Messages to audit")


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


def _detect_mode(task: str, override: Optional[str]) -> str:
    """Auto-detect mode from task text."""
    if override:
        return override

    lower = task.lower()

    exec_score = sum(1 for p in EXECUTION_PATTERNS if p in lower)
    design_score = sum(1 for p in DESIGN_PATTERNS if p in lower)

    if exec_score > design_score:
        return MODE_EXECUTION
    if design_score > exec_score:
        return MODE_DESIGN

    # Default to EXECUTION (fail-closed)
    return MODE_EXECUTION


def _strip_context(payload: str, whitelist: list[str]) -> tuple[str, int]:
    """Strip non-whitelisted file references."""
    if not whitelist:
        return payload, 0

    lines = payload.split("\n")
    kept = []
    stripped = 0

    for line in lines:
        has_path = re.search(r"[/\\][\w\-./\\]+\.\w+", line)
        if has_path:
            allowed = any(w in line for w in whitelist)
            if not allowed:
                stripped += 1
                continue
        kept.append(line)

    return "\n".join(kept), stripped


def _strip_prose(text: str, mode_cfg: dict) -> tuple[str, int]:
    """Strip disallowed prose based on mode config."""
    if mode_cfg["prose"]:
        return text, 0

    lines = text.split("\n")
    kept = []
    stripped = 0

    for line in lines:
        lower = line.lower()
        blocked = any(b in lower for b in BLOCKED)
        if blocked:
            stripped += 1
            continue
        kept.append(line)

    return "\n".join(kept), stripped


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: max(chars/4, words)."""
    return max(len(text) // 4, len(text.split()))


def _audit_waste(messages: list[str]) -> dict:
    """Audit messages for token waste."""
    total = 0
    findings = []

    for i, msg in enumerate(messages):
        msg_waste = 0
        patterns = []

        for wp in WASTE_PATTERNS:
            matches = len(re.findall(wp["p"], msg, re.IGNORECASE))
            if matches:
                msg_waste += matches * wp["w"]
                patterns.append({"p": wp["p"], "c": matches, "t": wp["t"]})

        if patterns:
            findings.append({"i": i, "w": msg_waste, "ps": patterns})
            total += msg_waste

    return {"total": total, "findings": findings, "n": len(messages)}


def _hash_state() -> str:
    """Deterministic hash of current state."""
    data = f"{_STATE['hook_enabled']}|{_STATE['mode']}|{json.dumps(_STATE['budgets'], sort_keys=True)}|{','.join(sorted(_STATE['whitelist']))}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def tw_enable_hook(
    whitelist: list[str] | None = None,
) -> str:
    """Enable global pre-hook enforcement. Returns confirmation."""
    try:
        inp = EnableHookInput(whitelist=whitelist or [])
        _STATE["hook_enabled"] = True
        _STATE["whitelist"] = inp.whitelist
        return json.dumps(
            {"enabled": True, "whitelist": inp.whitelist, "hash": _hash_state()}
        )
    except Exception:
        _reset_to_safe()
        return json.dumps({"enabled": True, "fail_closed": True, "hash": _hash_state()})


@mcp.tool()
async def tw_disable_hook() -> str:
    """Disable global pre-hook. Only allowed in DESIGN mode."""
    if _STATE["mode"] != MODE_DESIGN:
        return json.dumps(
            {"error": "DENIED", "reason": "Hook disable blocked in EXECUTION mode"}
        )

    _STATE["hook_enabled"] = False
    return json.dumps({"enabled": False, "hash": _hash_state()})


@mcp.tool()
async def tw_set_mode(
    mode: str,
) -> str:
    """Switch mode (EXECUTION/DESIGN). Returns new config."""
    try:
        inp = SetModeInput(mode=mode)
        _STATE["mode"] = inp.mode
        cfg = MODE_CONFIGS[inp.mode]
        return json.dumps({"mode": inp.mode, "cfg": cfg, "hash": _hash_state()})
    except Exception:
        _reset_to_safe()
        return json.dumps(
            {"mode": MODE_EXECUTION, "fail_closed": True, "hash": _hash_state()}
        )


@mcp.tool()
async def tw_detect_mode(
    task: str,
    override: str | None = None,
) -> str:
    """Auto-detect mode from task text. Returns detected mode and config."""
    try:
        inp = DetectModeInput(task=task, override=override)
        detected = _detect_mode(inp.task, inp.override)
        _STATE["mode"] = detected
        cfg = MODE_CONFIGS[detected]
        return json.dumps(
            {
                "mode": detected,
                "cfg": cfg,
                "auto": inp.override is None,
                "hash": _hash_state(),
            }
        )
    except Exception:
        _reset_to_safe()
        return json.dumps(
            {"mode": MODE_EXECUTION, "fail_closed": True, "hash": _hash_state()}
        )


@mcp.tool()
async def tw_set_budget(
    request: int | None = None,
    skill: int | None = None,
    mcp: int | None = None,
    session: int | None = None,
) -> str:
    """Set token budgets. Returns updated budgets."""
    try:
        inp = SetBudgetInput(request=request, skill=skill, mcp=mcp, session=session)
        if inp.request is not None:
            _STATE["budgets"]["request"] = inp.request
        if inp.skill is not None:
            _STATE["budgets"]["skill"] = inp.skill
        if inp.mcp is not None:
            _STATE["budgets"]["mcp"] = inp.mcp
        if inp.session is not None:
            _STATE["budgets"]["session"] = inp.session
        return json.dumps({"budgets": _STATE["budgets"], "hash": _hash_state()})
    except Exception:
        _reset_to_safe()
        return json.dumps(
            {"budgets": MIN_BUDGETS, "fail_closed": True, "hash": _hash_state()}
        )


@mcp.tool()
async def tw_get_state() -> str:
    """Query current policy state. Returns full state."""
    return json.dumps(
        {
            "hook_enabled": _STATE["hook_enabled"],
            "mode": _STATE["mode"],
            "cfg": MODE_CONFIGS[_STATE["mode"]],
            "budgets": _STATE["budgets"],
            "whitelist": _STATE["whitelist"],
            "session_used": _STATE["session_used"],
            "hash": _hash_state(),
        }
    )


@mcp.tool()
async def tw_enforce(
    payload: str,
    context_paths: list[str] | None = None,
    est_tokens: int = 0,
) -> str:
    """Enforce policy on payload (pre-hook entry point). Returns enforced payload or termination."""
    try:
        inp = EnforceInput(
            payload=payload, context_paths=context_paths or [], est_tokens=est_tokens
        )

        # Skip enforcement if hook disabled (DESIGN mode only)
        if not _STATE["hook_enabled"]:
            return json.dumps({"payload": inp.payload, "enforced": False})

        mode_cfg = MODE_CONFIGS[_STATE["mode"]]

        # 1. Strip non-whitelisted context
        stripped_ctx, ctx_removed = _strip_context(inp.payload, _STATE["whitelist"])

        # 2. Strip disallowed prose
        stripped_prose, prose_removed = _strip_prose(stripped_ctx, mode_cfg)

        # 3. Check budget
        est = inp.est_tokens if inp.est_tokens > 0 else _estimate_tokens(stripped_prose)
        budget = _STATE["budgets"]["request"]

        if est > budget:
            return json.dumps(
                {
                    "TERMINATED": True,
                    "reason": "BUDGET_EXCEEDED",
                    "scope": "request",
                    "budget": budget,
                    "estimated": est,
                }
            )

        # 4. Update session usage
        _STATE["session_used"] += est
        if _STATE["session_used"] > _STATE["budgets"]["session"]:
            return json.dumps(
                {
                    "TERMINATED": True,
                    "reason": "SESSION_BUDGET_EXCEEDED",
                    "budget": _STATE["budgets"]["session"],
                    "used": _STATE["session_used"],
                }
            )

        return json.dumps(
            {
                "payload": stripped_prose,
                "enforced": True,
                "mode": _STATE["mode"],
                "ctx_stripped": ctx_removed,
                "prose_stripped": prose_removed,
                "est_tokens": est,
                "budget_remaining": budget - est,
            }
        )

    except Exception:
        _reset_to_safe()
        return json.dumps(
            {"TERMINATED": True, "reason": "ENFORCEMENT_FAILURE", "fail_closed": True}
        )


@mcp.tool()
async def tw_check_budget(
    scope: str,
    tokens: int,
) -> str:
    """Check if budget allows operation. Returns allow/deny."""
    try:
        inp = CheckBudgetInput(scope=scope, tokens=tokens)
        budget = _STATE["budgets"].get(inp.scope, MIN_BUDGETS.get(inp.scope, 100))

        if inp.scope == "session":
            remaining = budget - _STATE["session_used"]
            allowed = tokens <= remaining
            return json.dumps(
                {
                    "allowed": allowed,
                    "scope": inp.scope,
                    "budget": budget,
                    "used": _STATE["session_used"],
                    "remaining": remaining,
                    "requested": tokens,
                }
            )

        allowed = tokens <= budget
        return json.dumps(
            {
                "allowed": allowed,
                "scope": inp.scope,
                "budget": budget,
                "requested": tokens,
            }
        )

    except Exception:
        return json.dumps({"allowed": False, "fail_closed": True})


@mcp.tool()
async def tw_terminate(
    reason: str,
    scope: str,
    budget: int,
    used: int,
) -> str:
    """Return structured budget-exceeded termination. No prose. No fallback."""
    return json.dumps(
        {
            "TERMINATED": True,
            "reason": reason,
            "scope": scope,
            "budget": budget,
            "used": used,
        }
    )


@mcp.tool()
async def tw_audit(
    messages: list[str],
) -> str:
    """Audit session for token waste patterns. Returns waste report."""
    try:
        inp = AuditInput(messages=messages)
        return json.dumps(_audit_waste(inp.messages))
    except Exception:
        return json.dumps({"total": 0, "findings": [], "n": 0, "error": True})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
