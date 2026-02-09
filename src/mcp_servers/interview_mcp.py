"""
Interview MCP Server — discovery conversation toolkit for understanding user intent
and agreeing on approach before taking action.

TOOLS:
    interview_analyze_request       Analyze request for ambiguities and intent signals
    interview_generate_why          Generate WHY questions (laddering, 5 whys)
    interview_surface_assumptions   Surface hidden assumptions from request
    interview_generate_options      Generate solution options based on intent
    interview_generate_summary      Generate understanding summary
    interview_validate_depth        Check if understanding is deep enough
    interview_detect_antipatterns   Detect discovery antipatterns
    interview_classify_request      Classify if request needs full discovery
    interview_generate_probes       Generate probing questions for vague terms
    interview_generate_confirmation Generate confirmation message for proceeding
"""

import json
import re
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("interview_mcp")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# WHY question templates
WHY_QUESTIONS = [
    {"q": "What problem does this solve?", "discovers": "Real need"},
    {"q": "Why is this needed now?", "discovers": "Urgency, context"},
    {"q": "What happens if we don't do this?", "discovers": "Stakes, priority"},
    {"q": "Who benefits and how?", "discovers": "Users, value"},
    {"q": "What led to this request?", "discovers": "Background, triggers"},
    {"q": "What does success look like?", "discovers": "Goals, criteria"},
]

# Assumption categories
ASSUMPTION_CATEGORIES = {
    "context": ["platform", "environment", "existing systems", "architecture"],
    "users": ["who they are", "expertise level", "needs", "permissions"],
    "scale": ["volume", "performance", "growth expectations", "limits"],
    "scope": ["included features", "excluded features", "boundaries", "phases"],
    "quality": ["standards", "constraints", "requirements", "compliance"],
    "timeline": ["urgency", "deadlines", "dependencies", "phases"],
    "integration": ["existing systems", "APIs", "data sources", "third parties"],
}

# Vague terms that need probing
VAGUE_TERMS = {
    "fast": "What response time is acceptable?",
    "quick": "What timeline are you thinking?",
    "scalable": "What scale? 100 users? 1 million?",
    "simple": "Simple for whom? What complexity is okay?",
    "secure": "What threats? What compliance requirements?",
    "good": "What makes it 'good' for your use case?",
    "better": "Better in what way specifically?",
    "easy": "Easy for whom to do what?",
    "efficient": "Efficient in terms of time, cost, or resources?",
    "robust": "What failure scenarios should it handle?",
    "flexible": "Flexible to accommodate what kinds of changes?",
    "reliable": "What uptime/availability is required?",
    "modern": "What specific modern features/approaches?",
    "clean": "Clean in terms of code, design, or output?",
    "nice": "What would make it 'nice' specifically?",
}

# Discovery antipatterns
ANTIPATTERNS = [
    {
        "pattern": "skip_why",
        "symptom": "Jumping to solution without asking WHY",
        "fix": "Always ask why before how",
    },
    {
        "pattern": "hidden_assumptions",
        "symptom": "Not surfacing what you're assuming",
        "fix": "Explicitly state and validate assumptions",
    },
    {
        "pattern": "surface_accept",
        "symptom": "Accepting request at face value",
        "fix": "Dig deeper with laddering/5 whys",
    },
    {
        "pattern": "no_confirm",
        "symptom": "Proceeding without explicit confirmation",
        "fix": "Get explicit 'yes, proceed'",
    },
    {
        "pattern": "over_question",
        "symptom": "Too many questions for simple requests",
        "fix": "Match depth to complexity",
    },
    {
        "pattern": "leading_questions",
        "symptom": "Questions that assume the answer",
        "fix": "Use open, neutral questions",
    },
    {
        "pattern": "ignore_context",
        "symptom": "Not using available information",
        "fix": "Review context before asking",
    },
]

# Request complexity signals
COMPLEXITY_SIGNALS = {
    "high": [
        "multiple",
        "integrate",
        "migrate",
        "architecture",
        "redesign",
        "complex",
        "enterprise",
        "scale",
    ],
    "medium": ["add", "update", "modify", "change", "improve", "enhance", "fix"],
    "low": ["simple", "small", "quick", "just", "only", "basic", "minor", "typo"],
}

# Solution vs intent indicators
SOLUTION_INDICATORS = [
    "use",
    "add",
    "implement",
    "create",
    "build",
    "make",
    "put",
    "install",
]
INTENT_INDICATORS = [
    "need",
    "want",
    "problem",
    "issue",
    "help",
    "struggling",
    "goal",
    "trying",
]

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

_CFG = ConfigDict(str_strip_whitespace=True, extra="forbid")


class AnalyzeRequestInput(BaseModel):
    model_config = _CFG
    request: str = Field(
        ..., min_length=1, max_length=5000, description="User request to analyze"
    )


class GenerateWhyInput(BaseModel):
    model_config = _CFG
    request: str = Field(..., min_length=1, max_length=2000, description="User request")
    context: str = Field(default="", max_length=2000, description="Additional context")
    technique: str = Field(
        default="mixed", description="Technique: laddering, five_whys, or mixed"
    )

    @field_validator("technique")
    @classmethod
    def _validate_technique(cls, v: str) -> str:
        v = v.lower().replace("-", "_").replace(" ", "_")
        if v not in ("laddering", "five_whys", "mixed"):
            raise ValueError("technique must be laddering, five_whys, or mixed")
        return v


class SurfaceAssumptionsInput(BaseModel):
    model_config = _CFG
    request: str = Field(..., min_length=1, max_length=2000, description="User request")
    domain: str = Field(
        default="software",
        description="Domain: software, document, automation, general",
    )
    existing_context: dict[str, str] = Field(
        default_factory=dict, description="Known context"
    )


class GenerateOptionsInput(BaseModel):
    model_config = _CFG
    intent: str = Field(
        ..., min_length=1, max_length=500, description="Discovered intent (WHY)"
    )
    constraints: list[str] = Field(
        default_factory=list, description="Known constraints"
    )
    num_options: int = Field(
        default=3, ge=2, le=5, description="Number of options to generate"
    )


class GenerateSummaryInput(BaseModel):
    model_config = _CFG
    problem_why: str = Field(
        ..., min_length=1, max_length=500, description="Problem/intent (WHY)"
    )
    solution_what: str = Field(
        ..., min_length=1, max_length=500, description="Solution (WHAT)"
    )
    key_decisions: list[str] = Field(
        default_factory=list, description="Key decisions made"
    )
    out_of_scope: list[str] = Field(
        default_factory=list, description="What's not included"
    )
    format: str = Field(
        default="standard", description="Format: quick, standard, or detailed"
    )

    @field_validator("format")
    @classmethod
    def _validate_format(cls, v: str) -> str:
        if v.lower() not in ("quick", "standard", "detailed"):
            raise ValueError("format must be quick, standard, or detailed")
        return v.lower()


class ValidateDepthInput(BaseModel):
    model_config = _CFG
    understanding: dict = Field(
        ..., description="Current understanding {why, what, assumptions, scope}"
    )


class DetectAntipatternsInput(BaseModel):
    model_config = _CFG
    conversation: str = Field(
        ..., min_length=10, max_length=10000, description="Conversation to analyze"
    )


class ClassifyRequestInput(BaseModel):
    model_config = _CFG
    request: str = Field(
        ..., min_length=1, max_length=2000, description="User request to classify"
    )


class GenerateProbesInput(BaseModel):
    model_config = _CFG
    text: str = Field(
        ..., min_length=1, max_length=2000, description="Text containing vague terms"
    )
    max_probes: int = Field(
        default=3, ge=1, le=5, description="Maximum probes to generate"
    )


class GenerateConfirmationInput(BaseModel):
    model_config = _CFG
    understanding: str = Field(
        ..., min_length=1, max_length=1000, description="Summary of understanding"
    )
    next_action: str = Field(
        ..., min_length=1, max_length=500, description="What will happen next"
    )


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


def _find_vague_terms(text: str) -> list[dict]:
    """Find vague terms in text that need probing."""
    found = []
    text_lower = text.lower()
    for term, probe in VAGUE_TERMS.items():
        if term in text_lower:
            found.append({"term": term, "probe": probe})
    return found


def _detect_solution_vs_intent(text: str) -> dict:
    """Detect if request states solution or intent."""
    text_lower = text.lower()

    solution_score = sum(1 for s in SOLUTION_INDICATORS if s in text_lower)
    intent_score = sum(1 for i in INTENT_INDICATORS if i in text_lower)

    if solution_score > intent_score:
        return {
            "type": "solution",
            "recommendation": "Dig deeper to discover intent behind the solution",
        }
    elif intent_score > solution_score:
        return {
            "type": "intent",
            "recommendation": "Good - user is expressing the problem/need",
        }
    else:
        return {
            "type": "mixed",
            "recommendation": "Clarify whether this is the problem or a proposed solution",
        }


def _assess_complexity(text: str) -> dict:
    """Assess request complexity based on signals."""
    text_lower = text.lower()

    scores = {
        level: sum(1 for kw in keywords if kw in text_lower)
        for level, keywords in COMPLEXITY_SIGNALS.items()
    }

    # Determine level
    if scores["high"] >= 2 or len(text) > 500:
        level = "high"
        discovery = "full"
    elif scores["low"] >= 2 and scores["high"] == 0:
        level = "low"
        discovery = "quick"
    else:
        level = "medium"
        discovery = "standard"

    return {"level": level, "discovery_depth": discovery, "signals": scores}


def _generate_laddering_questions(request: str) -> list[dict]:
    """Generate laddering questions to dig deeper."""
    return [
        {
            "question": f'When you say "{request[:50]}...", what problem does this solve?',
            "purpose": "Surface real need",
        },
        {
            "question": "Why is that important for you/your users?",
            "purpose": "Dig into importance",
        },
        {
            "question": "What happens if this problem isn't solved?",
            "purpose": "Understand stakes",
        },
        {
            "question": "What does the ideal outcome look like?",
            "purpose": "Define success",
        },
    ]


def _generate_five_whys(request: str) -> list[dict]:
    """Generate 5 whys question chain."""
    return [
        {
            "level": 1,
            "question": "Why do you need this?",
            "purpose": "First level intent",
        },
        {"level": 2, "question": "Why is that the case?", "purpose": "Deeper context"},
        {"level": 3, "question": "Why does that matter?", "purpose": "Importance"},
        {"level": 4, "question": "Why is that a priority now?", "purpose": "Timing"},
        {
            "level": 5,
            "question": "Why is this the approach?",
            "purpose": "Root cause/need",
        },
    ]


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def interview_analyze_request(
    request: str,
) -> str:
    """Analyze a user request to identify ambiguities, intent signals, and discovery needs."""
    try:
        inp = AnalyzeRequestInput(request=request)

        # Analyze various aspects
        vague_terms = _find_vague_terms(inp.request)
        solution_intent = _detect_solution_vs_intent(inp.request)
        complexity = _assess_complexity(inp.request)

        # Count ambiguity signals
        ambiguities = []
        if vague_terms:
            ambiguities.append(
                f"Contains {len(vague_terms)} vague term(s) needing clarification"
            )
        if solution_intent["type"] == "solution":
            ambiguities.append(
                "States a solution without expressing the underlying problem"
            )
        if "?" not in inp.request and len(inp.request) < 100:
            ambiguities.append("Brief request may lack important context")

        # Recommended questions
        recommended_questions = [q["q"] for q in WHY_QUESTIONS[:3]]

        return json.dumps(
            {
                "request_length": len(inp.request),
                "complexity": complexity,
                "solution_vs_intent": solution_intent,
                "vague_terms": vague_terms,
                "ambiguities": ambiguities,
                "needs_discovery": len(ambiguities) > 0 or complexity["level"] != "low",
                "recommended_questions": recommended_questions,
            }
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def interview_generate_why(
    request: str,
    context: str = "",
    technique: str = "mixed",
) -> str:
    """Generate WHY questions using laddering, 5 whys, or mixed technique."""
    try:
        inp = GenerateWhyInput(request=request, context=context, technique=technique)

        questions = []

        if inp.technique == "laddering" or inp.technique == "mixed":
            laddering = _generate_laddering_questions(inp.request)
            questions.extend([{**q, "technique": "laddering"} for q in laddering])

        if inp.technique == "five_whys" or inp.technique == "mixed":
            five_whys = _generate_five_whys(inp.request)
            questions.extend([{**q, "technique": "five_whys"} for q in five_whys])

        # Add core WHY questions
        for wq in WHY_QUESTIONS[:4]:
            questions.append(
                {
                    "question": wq["q"],
                    "purpose": wq["discovers"],
                    "technique": "core_why",
                }
            )

        # Deduplicate by question text
        seen = set()
        unique = []
        for q in questions:
            if q["question"] not in seen:
                seen.add(q["question"])
                unique.append(q)

        return json.dumps(
            {
                "questions": unique[:8],  # Limit to 8 questions
                "technique": inp.technique,
                "recommendation": "Start with 1-2 questions, build on answers",
            }
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def interview_surface_assumptions(
    request: str,
    domain: str = "software",
    existing_context: dict[str, str] | None = None,
) -> str:
    """Surface hidden assumptions that should be validated before proceeding."""
    try:
        inp = SurfaceAssumptionsInput(
            request=request, domain=domain, existing_context=existing_context or {}
        )

        assumptions = []

        # Domain-specific assumptions
        if inp.domain == "software":
            assumptions.extend(
                [
                    {
                        "category": "context",
                        "assumption": "This is for a web application",
                        "validate": "Is this web, mobile, desktop, or API?",
                    },
                    {
                        "category": "users",
                        "assumption": "Users are moderately technical",
                        "validate": "Who are the target users?",
                    },
                    {
                        "category": "scale",
                        "assumption": "Standard scale (100s-1000s of users)",
                        "validate": "What scale are we building for?",
                    },
                    {
                        "category": "integration",
                        "assumption": "Standalone feature",
                        "validate": "Does this integrate with existing systems?",
                    },
                ]
            )
        elif inp.domain == "document":
            assumptions.extend(
                [
                    {
                        "category": "context",
                        "assumption": "Single document/artifact",
                        "validate": "Is this one document or a template?",
                    },
                    {
                        "category": "users",
                        "assumption": "Internal audience",
                        "validate": "Who will read this?",
                    },
                    {
                        "category": "quality",
                        "assumption": "Professional tone",
                        "validate": "What tone/style is appropriate?",
                    },
                ]
            )
        else:
            assumptions.extend(
                [
                    {
                        "category": "context",
                        "assumption": "Current environment/tools",
                        "validate": "What environment/tools are we working with?",
                    },
                    {
                        "category": "scope",
                        "assumption": "Single task",
                        "validate": "Is this part of something larger?",
                    },
                ]
            )

        # Check what's already known
        for cat in ASSUMPTION_CATEGORIES:
            if cat in inp.existing_context:
                assumptions = [a for a in assumptions if a["category"] != cat]

        # Format for presentation
        assumption_text = "I'm assuming:\n"
        for a in assumptions[:6]:
            assumption_text += f"- {a['assumption']}\n"
        assumption_text += "\nAre these correct?"

        return json.dumps(
            {
                "assumptions": assumptions[:6],
                "categories_covered": list(set(a["category"] for a in assumptions)),
                "formatted_text": assumption_text,
                "known_context": list(inp.existing_context.keys()),
            }
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def interview_generate_options(
    intent: str,
    constraints: list[str] | None = None,
    num_options: int = 3,
) -> str:
    """Generate solution options based on discovered intent."""
    try:
        inp = GenerateOptionsInput(
            intent=intent, constraints=constraints or [], num_options=num_options
        )

        # Template for options
        options_template = f"""Given that you need: {inp.intent}

We could approach this in several ways:

1. **[Approach A]**
   - How: [Description]
   - Trade-off: [Pros/cons]
   - Best if: [When to choose]

2. **[Approach B]**
   - How: [Description]
   - Trade-off: [Pros/cons]
   - Best if: [When to choose]

3. **[Approach C]**
   - How: [Description]
   - Trade-off: [Pros/cons]
   - Best if: [When to choose]

Which fits your intent best?"""

        # Guidance for filling in
        guidance = [
            "Options should address the WHY (intent), not just surface WHAT",
            "Include trade-offs to help user make informed decision",
            "Indicate when each option is best suited",
            "Respect stated constraints in all options",
        ]

        return json.dumps(
            {
                "intent": inp.intent,
                "constraints": inp.constraints,
                "template": options_template,
                "num_options": inp.num_options,
                "guidance": guidance,
            }
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def interview_generate_summary(
    problem_why: str,
    solution_what: str,
    key_decisions: list[str] | None = None,
    out_of_scope: list[str] | None = None,
    format: str = "standard",
) -> str:
    """Generate understanding summary for confirmation before proceeding."""
    try:
        inp = GenerateSummaryInput(
            problem_why=problem_why,
            solution_what=solution_what,
            key_decisions=key_decisions or [],
            out_of_scope=out_of_scope or [],
            format=format,
        )

        if inp.format == "quick":
            summary = f"""Got it: {inp.solution_what} to solve {inp.problem_why}

Proceeding with this approach. Confirm?"""

        elif inp.format == "standard":
            decisions_text = (
                "\n".join([f"- {d}" for d in inp.key_decisions])
                if inp.key_decisions
                else "- None specified"
            )
            scope_text = (
                "\n".join([f"- {s}" for s in inp.out_of_scope])
                if inp.out_of_scope
                else "- Nothing explicitly excluded"
            )

            summary = f"""## Understanding

**Problem (WHY)**: {inp.problem_why}

**Solution (WHAT)**: {inp.solution_what}

**Key decisions**:
{decisions_text}

**Not included**:
{scope_text}

Does this capture it correctly?"""

        else:  # detailed
            decisions_text = (
                "\n".join([f"- {d}" for d in inp.key_decisions])
                if inp.key_decisions
                else "- None specified"
            )
            scope_text = (
                "\n".join([f"- {s}" for s in inp.out_of_scope])
                if inp.out_of_scope
                else "- Nothing explicitly excluded"
            )

            summary = f"""## Comprehensive Understanding Summary

### Problem Statement (WHY)
{inp.problem_why}

### Proposed Solution (WHAT)
{inp.solution_what}

### Key Decisions Made
{decisions_text}

### Explicitly Out of Scope
{scope_text}

### Confirmation Required

Before proceeding:
1. Does the problem statement accurately capture your need?
2. Does the proposed solution address that need?
3. Are any key decisions missing or incorrect?
4. Is the scope boundary clear?

Please confirm or correct any part of this understanding."""

        return json.dumps(
            {
                "summary": summary,
                "format": inp.format,
                "components": {
                    "problem": inp.problem_why,
                    "solution": inp.solution_what,
                    "decisions": inp.key_decisions,
                    "out_of_scope": inp.out_of_scope,
                },
            }
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def interview_validate_depth(
    understanding: dict,
) -> str:
    """Check if understanding is deep enough to proceed."""
    try:
        inp = ValidateDepthInput(understanding=understanding)
        u = inp.understanding

        checklist = [
            {
                "item": "Know WHY (intent/problem)",
                "check": bool(u.get("why")),
                "critical": True,
            },
            {
                "item": "Know WHAT (solution)",
                "check": bool(u.get("what")),
                "critical": True,
            },
            {
                "item": "Assumptions surfaced",
                "check": bool(u.get("assumptions")),
                "critical": True,
            },
            {
                "item": "Assumptions validated",
                "check": u.get("assumptions_validated", False),
                "critical": True,
            },
            {
                "item": "Know who benefits",
                "check": bool(u.get("beneficiaries")),
                "critical": False,
            },
            {
                "item": "Scope boundaries clear",
                "check": bool(u.get("scope") or u.get("out_of_scope")),
                "critical": False,
            },
            {
                "item": "User confirmed understanding",
                "check": u.get("confirmed", False),
                "critical": True,
            },
        ]

        passed = sum(1 for c in checklist if c["check"])
        critical_passed = sum(1 for c in checklist if c["critical"] and c["check"])
        critical_total = sum(1 for c in checklist if c["critical"])

        ready = critical_passed == critical_total

        missing = [c["item"] for c in checklist if not c["check"]]
        critical_missing = [
            c["item"] for c in checklist if c["critical"] and not c["check"]
        ]

        verdict = "READY to proceed" if ready else "NOT READY - need more discovery"

        return json.dumps(
            {
                "ready": ready,
                "verdict": verdict,
                "score": f"{passed}/{len(checklist)}",
                "critical_score": f"{critical_passed}/{critical_total}",
                "checklist": checklist,
                "missing": missing,
                "critical_missing": critical_missing,
                "recommendation": (
                    "Proceed with implementation"
                    if ready
                    else f"Address: {', '.join(critical_missing[:2])}"
                ),
            }
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def interview_detect_antipatterns(
    conversation: str,
) -> str:
    """Detect discovery antipatterns in conversation."""
    try:
        inp = DetectAntipatternsInput(conversation=conversation)
        conv_lower = inp.conversation.lower()

        findings = []

        # Check for antipatterns
        # Skip WHY: solution without asking why
        if (
            any(s in conv_lower for s in ["let me", "i'll create", "i'll implement"])
            and "why" not in conv_lower
        ):
            findings.append(
                {
                    "pattern": "skip_why",
                    "evidence": "Proceeded to solution without asking WHY",
                    "fix": "Ask 'What problem does this solve?' before implementing",
                }
            )

        # Hidden assumptions: no assumption statement
        if "assuming" not in conv_lower and "assume" not in conv_lower:
            findings.append(
                {
                    "pattern": "hidden_assumptions",
                    "evidence": "No assumptions explicitly stated",
                    "fix": "State: 'I'm assuming X, Y, Z - are these correct?'",
                }
            )

        # No confirmation: proceeding without user OK
        if "proceed" in conv_lower and not any(
            c in conv_lower for c in ["confirm", "correct?", "okay?", "yes"]
        ):
            findings.append(
                {
                    "pattern": "no_confirm",
                    "evidence": "Proceeding without explicit confirmation",
                    "fix": "Ask 'Does this capture it correctly?' before proceeding",
                }
            )

        # Over-questioning: too many questions at once
        question_marks = inp.conversation.count("?")
        if question_marks > 8:
            findings.append(
                {
                    "pattern": "over_question",
                    "evidence": f"Too many questions ({question_marks}) in one exchange",
                    "fix": "Limit to 1-4 questions per round, build on answers",
                }
            )

        # Score
        severity = "high" if len(findings) >= 2 else "medium" if findings else "low"

        return json.dumps(
            {
                "findings": findings,
                "count": len(findings),
                "severity": severity,
                "recommendation": (
                    findings[0]["fix"] if findings else "Discovery process looks good"
                ),
            }
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def interview_classify_request(
    request: str,
) -> str:
    """Classify if request needs full discovery or can proceed quickly."""
    try:
        inp = ClassifyRequestInput(request=request)

        complexity = _assess_complexity(inp.request)
        solution_intent = _detect_solution_vs_intent(inp.request)
        vague_terms = _find_vague_terms(inp.request)

        # Calculate discovery need
        signals = {
            "complexity_high": complexity["level"] == "high",
            "is_solution_not_intent": solution_intent["type"] == "solution",
            "has_vague_terms": len(vague_terms) > 0,
            "request_short": len(inp.request) < 50,
            "request_long": len(inp.request) > 300,
        }

        needs_signals = sum(1 for v in signals.values() if v)

        if needs_signals >= 3:
            classification = "full_discovery"
            recommendation = (
                "Conduct full WHY + assumptions discovery before proceeding"
            )
        elif needs_signals >= 1:
            classification = "quick_check"
            recommendation = "Quick confirmation of intent and key assumptions"
        else:
            classification = "proceed"
            recommendation = "Clear request - can proceed with brief confirmation"

        return json.dumps(
            {
                "classification": classification,
                "complexity": complexity["level"],
                "discovery_depth": complexity["discovery_depth"],
                "signals": signals,
                "needs_signals_count": needs_signals,
                "recommendation": recommendation,
                "suggested_first_question": (
                    WHY_QUESTIONS[0]["q"] if classification != "proceed" else None
                ),
            }
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def interview_generate_probes(
    text: str,
    max_probes: int = 3,
) -> str:
    """Generate probing questions for vague terms found in text."""
    try:
        inp = GenerateProbesInput(text=text, max_probes=max_probes)

        vague_found = _find_vague_terms(inp.text)

        probes = []
        for vt in vague_found[: inp.max_probes]:
            probes.append(
                {
                    "term": vt["term"],
                    "probe": vt["probe"],
                    "context": f'You mentioned "{vt["term"]}" - {vt["probe"]}',
                }
            )

        # If no vague terms found, provide generic probes
        if not probes:
            probes = [
                {
                    "term": None,
                    "probe": "Can you tell me more about what you mean?",
                    "context": "Clarification needed",
                },
                {
                    "term": None,
                    "probe": "What would success look like here?",
                    "context": "Defining success",
                },
            ]

        formatted = "To clarify:\n"
        for i, p in enumerate(probes, 1):
            formatted += f"{i}. {p['context']}\n"

        return json.dumps(
            {
                "probes": probes,
                "count": len(probes),
                "vague_terms_found": [v["term"] for v in vague_found],
                "formatted": formatted,
            }
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def interview_generate_confirmation(
    understanding: str,
    next_action: str,
) -> str:
    """Generate confirmation message before proceeding with action."""
    try:
        inp = GenerateConfirmationInput(
            understanding=understanding, next_action=next_action
        )

        confirmation = f"""## Confirmation Required

{inp.understanding}

**Next step**: {inp.next_action}

Please confirm:
- [ ] Understanding is correct
- [ ] Ready to proceed

Reply "yes" or "proceed" to continue, or correct anything above."""

        short_form = f"""Got it: {inp.understanding[:100]}{"..." if len(inp.understanding) > 100 else ""}

Next: {inp.next_action}

Proceed? (yes/no)"""

        return json.dumps(
            {
                "confirmation": confirmation,
                "short_form": short_form,
                "understanding": inp.understanding,
                "next_action": inp.next_action,
                "waiting_for": "explicit user confirmation",
            }
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
