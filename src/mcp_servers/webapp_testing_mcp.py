"""
Web Application Testing MCP Server — Playwright-based testing toolkit for
verifying frontend functionality, debugging UI behavior, and capturing screenshots.

TOOLS:
    webapp_generate_script          Generate Playwright test script
    webapp_generate_discovery       Generate element discovery script
    webapp_generate_screenshot      Generate screenshot capture script
    webapp_generate_form_test       Generate form testing script
    webapp_generate_navigation      Generate navigation testing script
    webapp_generate_assertions      Generate assertion testing script
    webapp_generate_server_cmd      Generate with_server.py command
    webapp_detect_antipatterns      Detect testing antipatterns in code
    webapp_suggest_selectors        Suggest Playwright selectors for elements
    webapp_generate_scaffold        Generate test scaffold for application
"""

import json
import re
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("webapp_testing_mcp")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Common selector strategies
SELECTOR_STRATEGIES = {
    "text": {
        "prefix": "text=",
        "desc": "Match visible text content",
        "example": 'text="Submit"',
    },
    "role": {
        "prefix": "role=",
        "desc": "ARIA role selector",
        "example": 'role=button[name="Submit"]',
    },
    "css": {"prefix": "", "desc": "CSS selector", "example": "button.submit-btn"},
    "id": {"prefix": "#", "desc": "Element ID", "example": "#submit-button"},
    "data_testid": {
        "prefix": "[data-testid=",
        "desc": "Test ID attribute",
        "example": '[data-testid="submit"]',
    },
    "placeholder": {
        "prefix": "[placeholder=",
        "desc": "Input placeholder",
        "example": '[placeholder="Enter email"]',
    },
    "label": {
        "prefix": "label=",
        "desc": "Associated label text",
        "example": 'label="Email address"',
    },
}

# Wait strategies
WAIT_STRATEGIES = {
    "networkidle": "page.wait_for_load_state('networkidle')",
    "domcontentloaded": "page.wait_for_load_state('domcontentloaded')",
    "load": "page.wait_for_load_state('load')",
    "selector": "page.wait_for_selector('{selector}')",
    "timeout": "page.wait_for_timeout({ms})",
    "url": "page.wait_for_url('{pattern}')",
}

# Testing antipatterns
ANTIPATTERNS = [
    {
        "pattern": r"time\.sleep\(",
        "issue": "Using time.sleep instead of Playwright waits",
        "fix": "Use page.wait_for_selector() or wait_for_load_state()",
    },
    {
        "pattern": r"headless\s*=\s*False",
        "issue": "Running browser in headed mode",
        "fix": "Use headless=True for CI/automation",
    },
    {
        "pattern": r"page\.goto\([^)]+\)\s*\n\s*page\.",
        "issue": "Missing wait after navigation",
        "fix": "Add page.wait_for_load_state('networkidle') after goto()",
    },
    {
        "pattern": r"\.click\(\)\s*\n\s*assert",
        "issue": "Missing wait after click",
        "fix": "Add wait or use expect() for assertions",
    },
    {
        "pattern": r"try:\s*\n\s*.*\n\s*except:",
        "issue": "Bare except clause in test",
        "fix": "Catch specific exceptions or use expect()",
    },
    {
        "pattern": r"page\.locator\(['\"]div['\"]\)",
        "issue": "Using generic 'div' selector",
        "fix": "Use specific selectors: data-testid, role, or text",
    },
    {
        "pattern": r"browser\.close\(\)(?!.*finally)",
        "issue": "browser.close() not in finally block",
        "fix": "Use try/finally or context manager",
    },
    {
        "pattern": r"localhost:\d+(?!/)",
        "issue": "Hardcoded port without trailing slash",
        "fix": "Consider using environment variables for URLs",
    },
]

# Form input types
FORM_INPUT_TYPES = [
    "text",
    "email",
    "password",
    "number",
    "tel",
    "url",
    "search",
    "date",
    "datetime-local",
    "time",
    "month",
    "week",
    "color",
    "file",
    "checkbox",
    "radio",
    "select",
    "textarea",
]

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

_CFG = ConfigDict(str_strip_whitespace=True, extra="forbid")


class GenerateScriptInput(BaseModel):
    model_config = _CFG
    url: str = Field(..., min_length=1, description="Target URL to test")
    actions: list[str] = Field(
        default_factory=list, description="Actions to perform (click, fill, etc.)"
    )
    headless: bool = Field(default=True, description="Run browser in headless mode")
    wait_strategy: str = Field(
        default="networkidle", description="Wait strategy after navigation"
    )

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://", "file://")):
            v = f"http://{v}"
        return v

    @field_validator("wait_strategy")
    @classmethod
    def _validate_wait(cls, v: str) -> str:
        if v not in WAIT_STRATEGIES:
            raise ValueError(
                f"Unknown wait strategy: {v}. Use: {list(WAIT_STRATEGIES.keys())}"
            )
        return v


class GenerateDiscoveryInput(BaseModel):
    model_config = _CFG
    url: str = Field(..., min_length=1, description="Target URL")
    element_types: list[str] = Field(
        default=["button", "a", "input"], description="Element types to discover"
    )
    screenshot_path: Optional[str] = Field(
        default=None, description="Path to save screenshot"
    )

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://", "file://")):
            v = f"http://{v}"
        return v


class GenerateScreenshotInput(BaseModel):
    model_config = _CFG
    url: str = Field(..., min_length=1, description="Target URL")
    output_path: str = Field(
        default="/tmp/screenshot.png", description="Screenshot output path"
    )
    full_page: bool = Field(default=True, description="Capture full page")
    viewport_width: int = Field(
        default=1280, ge=320, le=3840, description="Viewport width"
    )
    viewport_height: int = Field(
        default=720, ge=200, le=2160, description="Viewport height"
    )

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://", "file://")):
            v = f"http://{v}"
        return v

    @field_validator("output_path")
    @classmethod
    def _validate_path(cls, v: str) -> str:
        if ".." in v:
            raise ValueError("Path traversal not allowed")
        return v


class GenerateFormTestInput(BaseModel):
    model_config = _CFG
    url: str = Field(..., min_length=1, description="Form page URL")
    fields: dict[str, str] = Field(
        ..., description="Field selectors and values to fill"
    )
    submit_selector: str = Field(
        default="button[type=submit]", description="Submit button selector"
    )
    success_indicator: Optional[str] = Field(
        default=None, description="Selector or text indicating success"
    )

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://", "file://")):
            v = f"http://{v}"
        return v


class GenerateNavigationInput(BaseModel):
    model_config = _CFG
    base_url: str = Field(..., min_length=1, description="Starting URL")
    routes: list[str] = Field(..., min_length=1, description="Routes/paths to test")
    check_elements: dict[str, str] = Field(
        default_factory=dict, description="Route -> element selector to verify"
    )

    @field_validator("base_url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://", "file://")):
            v = f"http://{v}"
        return v.rstrip("/")


class GenerateAssertionsInput(BaseModel):
    model_config = _CFG
    url: str = Field(..., min_length=1, description="Target URL")
    assertions: list[dict] = Field(
        ..., min_length=1, description="Assertions: [{type, selector, expected}]"
    )

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://", "file://")):
            v = f"http://{v}"
        return v

    @field_validator("assertions")
    @classmethod
    def _validate_assertions(cls, v: list[dict]) -> list[dict]:
        valid_types = [
            "visible",
            "hidden",
            "text_contains",
            "text_equals",
            "count",
            "attribute",
            "enabled",
            "disabled",
        ]
        for a in v:
            if "type" not in a:
                raise ValueError("Each assertion needs 'type'")
            if a["type"] not in valid_types:
                raise ValueError(
                    f"Unknown assertion type: {a['type']}. Valid: {valid_types}"
                )
        return v


class GenerateServerCmdInput(BaseModel):
    model_config = _CFG
    servers: list[dict] = Field(
        ..., min_length=1, description="Server configs: [{command, port}]"
    )
    test_script: str = Field(
        ..., min_length=1, description="Path to test script to run"
    )

    @field_validator("servers")
    @classmethod
    def _validate_servers(cls, v: list[dict]) -> list[dict]:
        for s in v:
            if "command" not in s or "port" not in s:
                raise ValueError("Each server needs 'command' and 'port'")
        return v

    @field_validator("test_script")
    @classmethod
    def _validate_script(cls, v: str) -> str:
        if ".." in v:
            raise ValueError("Path traversal not allowed")
        return v


class DetectAntipatternsInput(BaseModel):
    model_config = _CFG
    code: str = Field(
        ..., min_length=10, max_length=50000, description="Test code to analyze"
    )


class SuggestSelectorsInput(BaseModel):
    model_config = _CFG
    html: str = Field(
        ..., min_length=10, max_length=50000, description="HTML snippet to analyze"
    )
    target_element: Optional[str] = Field(
        default=None, description="Specific element to target"
    )


class GenerateScaffoldInput(BaseModel):
    model_config = _CFG
    app_type: str = Field(..., description="Application type: spa, mpa, static")
    base_url: str = Field(
        default="http://localhost:3000", description="Application base URL"
    )
    test_cases: list[str] = Field(
        default_factory=list, description="Test case descriptions"
    )
    use_server_wrapper: bool = Field(
        default=False, description="Include with_server.py integration"
    )

    @field_validator("app_type")
    @classmethod
    def _validate_app_type(cls, v: str) -> str:
        v = v.lower()
        if v not in ("spa", "mpa", "static"):
            raise ValueError("app_type must be spa, mpa, or static")
        return v


# ---------------------------------------------------------------------------
# Code generators
# ---------------------------------------------------------------------------


def _generate_playwright_header(headless: bool = True) -> str:
    """Generate standard Playwright script header."""
    return f'''"""Playwright test script generated by webapp_testing_mcp"""
from playwright.sync_api import sync_playwright, expect

def run_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless={headless})
        context = browser.new_context()
        page = context.new_page()

        try:
'''


def _generate_playwright_footer() -> str:
    """Generate standard Playwright script footer."""
    return """        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    run_test()
"""


def _generate_wait_code(strategy: str, **kwargs) -> str:
    """Generate wait code based on strategy."""
    template = WAIT_STRATEGIES.get(strategy, WAIT_STRATEGIES["networkidle"])
    return template.format(**kwargs)


def _suggest_selector_for_element(tag: str, attrs: dict) -> list[dict]:
    """Suggest selectors for an element."""
    suggestions = []

    # Data-testid (preferred)
    if "data-testid" in attrs:
        suggestions.append(
            {
                "selector": f'[data-testid="{attrs["data-testid"]}"]',
                "strategy": "data_testid",
                "priority": 1,
            }
        )

    # ID
    if "id" in attrs:
        suggestions.append(
            {"selector": f'#{attrs["id"]}', "strategy": "id", "priority": 2}
        )

    # Role + name
    if "role" in attrs or tag in ("button", "link", "textbox"):
        role = attrs.get(
            "role", {"button": "button", "a": "link", "input": "textbox"}.get(tag, tag)
        )
        name = attrs.get("aria-label", attrs.get("name", ""))
        if name:
            suggestions.append(
                {
                    "selector": f'role={role}[name="{name}"]',
                    "strategy": "role",
                    "priority": 3,
                }
            )

    # Text content
    if "text" in attrs:
        suggestions.append(
            {"selector": f'text="{attrs["text"]}"', "strategy": "text", "priority": 4}
        )

    # Placeholder
    if "placeholder" in attrs:
        suggestions.append(
            {
                "selector": f'[placeholder="{attrs["placeholder"]}"]',
                "strategy": "placeholder",
                "priority": 5,
            }
        )

    # CSS class (lowest priority)
    if "class" in attrs:
        classes = attrs["class"].split()
        if classes:
            suggestions.append(
                {"selector": f"{tag}.{classes[0]}", "strategy": "css", "priority": 6}
            )

    return sorted(suggestions, key=lambda x: x["priority"])


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def webapp_generate_script(
    url: str,
    actions: list[str] | None = None,
    headless: bool = True,
    wait_strategy: str = "networkidle",
) -> str:
    """Generate a Playwright test script for the given URL and actions."""
    try:
        inp = GenerateScriptInput(
            url=url,
            actions=actions or [],
            headless=headless,
            wait_strategy=wait_strategy,
        )

        header = _generate_playwright_header(inp.headless)
        footer = _generate_playwright_footer()

        body_lines = [
            f"            # Navigate to target URL",
            f"            page.goto('{inp.url}')",
            f"            {_generate_wait_code(inp.wait_strategy)}",
            "",
        ]

        # Add action code
        for i, action in enumerate(inp.actions):
            body_lines.append(f"            # Action {i + 1}: {action}")
            # Parse simple action syntax
            if action.startswith("click:"):
                selector = action[6:].strip()
                body_lines.append(f"            page.locator('{selector}').click()")
            elif action.startswith("fill:"):
                parts = action[5:].split("=", 1)
                if len(parts) == 2:
                    body_lines.append(
                        f"            page.locator('{parts[0].strip()}').fill('{parts[1].strip()}')"
                    )
            elif action.startswith("screenshot:"):
                path = action[11:].strip() or "/tmp/screenshot.png"
                body_lines.append(f"            page.screenshot(path='{path}')")
            elif action.startswith("wait:"):
                ms = action[5:].strip()
                body_lines.append(f"            page.wait_for_timeout({ms})")
            else:
                body_lines.append(f"            # TODO: Implement action: {action}")
            body_lines.append("")

        script = header + "\n".join(body_lines) + footer
        return json.dumps(
            {"script": script, "url": inp.url, "actions_count": len(inp.actions)}
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def webapp_generate_discovery(
    url: str,
    element_types: list[str] | None = None,
    screenshot_path: str | None = None,
) -> str:
    """Generate element discovery script to find buttons, links, and inputs."""
    try:
        inp = GenerateDiscoveryInput(
            url=url,
            element_types=element_types or ["button", "a", "input"],
            screenshot_path=screenshot_path,
        )

        header = _generate_playwright_header(True)
        footer = _generate_playwright_footer()

        body_lines = [
            f"            # Navigate and wait for dynamic content",
            f"            page.goto('{inp.url}')",
            f"            page.wait_for_load_state('networkidle')",
            "",
        ]

        if inp.screenshot_path:
            body_lines.extend(
                [
                    f"            # Capture screenshot for visual reference",
                    f"            page.screenshot(path='{inp.screenshot_path}', full_page=True)",
                    "",
                ]
            )

        body_lines.extend(
            [
                "            # Discover elements",
                "            elements = {}",
                "",
            ]
        )

        for elem_type in inp.element_types:
            body_lines.extend(
                [
                    f"            # Find all {elem_type} elements",
                    f"            {elem_type}s = page.locator('{elem_type}').all()",
                    f"            elements['{elem_type}'] = []",
                    f"            for el in {elem_type}s:",
                    f"                try:",
                    f"                    info = {{",
                    f"                        'text': el.text_content()[:100] if el.text_content() else '',",
                    f"                        'visible': el.is_visible(),",
                    f"                    }}",
                    f"                    for attr in ['id', 'class', 'name', 'type', 'href', 'data-testid']:",
                    f"                        val = el.get_attribute(attr)",
                    f"                        if val:",
                    f"                            info[attr] = val[:100]",
                    f"                    elements['{elem_type}'].append(info)",
                    f"                except:",
                    f"                    pass",
                    "",
                ]
            )

        body_lines.extend(
            [
                "            # Print discovered elements",
                "            import json",
                "            print(json.dumps(elements, indent=2))",
                "",
            ]
        )

        script = header + "\n".join(body_lines) + footer
        return json.dumps(
            {"script": script, "url": inp.url, "element_types": inp.element_types}
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def webapp_generate_screenshot(
    url: str,
    output_path: str = "/tmp/screenshot.png",
    full_page: bool = True,
    viewport_width: int = 1280,
    viewport_height: int = 720,
) -> str:
    """Generate script to capture browser screenshot."""
    try:
        inp = GenerateScreenshotInput(
            url=url,
            output_path=output_path,
            full_page=full_page,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
        )

        script = f'''"""Screenshot capture script generated by webapp_testing_mcp"""
from playwright.sync_api import sync_playwright

def capture_screenshot():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={{'width': {inp.viewport_width}, 'height': {inp.viewport_height}}}
        )
        page = context.new_page()

        try:
            page.goto('{inp.url}')
            page.wait_for_load_state('networkidle')

            page.screenshot(
                path='{inp.output_path}',
                full_page={inp.full_page}
            )
            print(f"Screenshot saved to {inp.output_path}")

        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    capture_screenshot()
'''
        return json.dumps({"script": script, "output_path": inp.output_path})
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def webapp_generate_form_test(
    url: str,
    fields: dict[str, str],
    submit_selector: str = "button[type=submit]",
    success_indicator: str | None = None,
) -> str:
    """Generate form testing script with field filling and submission."""
    try:
        inp = GenerateFormTestInput(
            url=url,
            fields=fields,
            submit_selector=submit_selector,
            success_indicator=success_indicator,
        )

        header = _generate_playwright_header(True)
        footer = _generate_playwright_footer()

        body_lines = [
            f"            # Navigate to form",
            f"            page.goto('{inp.url}')",
            f"            page.wait_for_load_state('networkidle')",
            "",
            "            # Fill form fields",
        ]

        for selector, value in inp.fields.items():
            body_lines.append(f"            page.locator('{selector}').fill('{value}')")

        body_lines.extend(
            [
                "",
                "            # Submit form",
                f"            page.locator('{inp.submit_selector}').click()",
                "",
                "            # Wait for response",
                "            page.wait_for_load_state('networkidle')",
                "",
            ]
        )

        if inp.success_indicator:
            body_lines.extend(
                [
                    "            # Verify success",
                    f"            expect(page.locator('{inp.success_indicator}')).to_be_visible()",
                    "            print('Form submission successful!')",
                ]
            )
        else:
            body_lines.extend(
                [
                    "            # TODO: Add success verification",
                    "            print('Form submitted - verify manually')",
                ]
            )

        script = header + "\n".join(body_lines) + footer
        return json.dumps({"script": script, "fields_count": len(inp.fields)})
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def webapp_generate_navigation(
    base_url: str,
    routes: list[str],
    check_elements: dict[str, str] | None = None,
) -> str:
    """Generate navigation testing script to verify multiple routes."""
    try:
        inp = GenerateNavigationInput(
            base_url=base_url, routes=routes, check_elements=check_elements or {}
        )

        header = _generate_playwright_header(True)
        footer = _generate_playwright_footer()

        body_lines = [
            f"            base_url = '{inp.base_url}'",
            "            results = []",
            "",
        ]

        for route in inp.routes:
            full_url = (
                f"{inp.base_url}{route}"
                if route.startswith("/")
                else f"{inp.base_url}/{route}"
            )
            element = inp.check_elements.get(route, "")

            body_lines.extend(
                [
                    f"            # Test route: {route}",
                    f"            try:",
                    f"                page.goto('{full_url}')",
                    f"                page.wait_for_load_state('networkidle')",
                    f"                status = 'loaded'",
                ]
            )

            if element:
                body_lines.extend(
                    [
                        f"                expect(page.locator('{element}')).to_be_visible()",
                        f"                status = 'verified'",
                    ]
                )

            body_lines.extend(
                [
                    f"                results.append({{'route': '{route}', 'status': status}})",
                    f"            except Exception as e:",
                    f"                results.append({{'route': '{route}', 'status': 'failed', 'error': str(e)}})",
                    "",
                ]
            )

        body_lines.extend(
            [
                "            # Print results",
                "            import json",
                "            print(json.dumps(results, indent=2))",
                "",
                "            # Summary",
                "            passed = sum(1 for r in results if r['status'] != 'failed')",
                "            print(f'\\nPassed: {passed}/{len(results)}')",
            ]
        )

        script = header + "\n".join(body_lines) + footer
        return json.dumps({"script": script, "routes_count": len(inp.routes)})
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def webapp_generate_assertions(
    url: str,
    assertions: list[dict],
) -> str:
    """Generate assertion testing script with various checks."""
    try:
        inp = GenerateAssertionsInput(url=url, assertions=assertions)

        header = _generate_playwright_header(True)
        footer = _generate_playwright_footer()

        body_lines = [
            f"            # Navigate to page",
            f"            page.goto('{inp.url}')",
            f"            page.wait_for_load_state('networkidle')",
            "",
            "            # Run assertions",
            "            passed = 0",
            "            failed = 0",
            "",
        ]

        for i, assertion in enumerate(inp.assertions):
            a_type = assertion["type"]
            selector = assertion.get("selector", "")
            expected = assertion.get("expected", "")

            body_lines.append(f"            # Assertion {i + 1}: {a_type}")
            body_lines.append("            try:")

            if a_type == "visible":
                body_lines.append(
                    f"                expect(page.locator('{selector}')).to_be_visible()"
                )
            elif a_type == "hidden":
                body_lines.append(
                    f"                expect(page.locator('{selector}')).to_be_hidden()"
                )
            elif a_type == "text_contains":
                body_lines.append(
                    f"                expect(page.locator('{selector}')).to_contain_text('{expected}')"
                )
            elif a_type == "text_equals":
                body_lines.append(
                    f"                expect(page.locator('{selector}')).to_have_text('{expected}')"
                )
            elif a_type == "count":
                body_lines.append(
                    f"                expect(page.locator('{selector}')).to_have_count({expected})"
                )
            elif a_type == "attribute":
                attr_name = assertion.get("attribute", "")
                body_lines.append(
                    f"                expect(page.locator('{selector}')).to_have_attribute('{attr_name}', '{expected}')"
                )
            elif a_type == "enabled":
                body_lines.append(
                    f"                expect(page.locator('{selector}')).to_be_enabled()"
                )
            elif a_type == "disabled":
                body_lines.append(
                    f"                expect(page.locator('{selector}')).to_be_disabled()"
                )

            body_lines.extend(
                [
                    "                passed += 1",
                    f"                print(f'[PASS] Assertion {i + 1}: {a_type}')",
                    "            except Exception as e:",
                    "                failed += 1",
                    f"                print(f'[FAIL] Assertion {i + 1}: {a_type} - {{e}}')",
                    "",
                ]
            )

        body_lines.extend(
            [
                "            print(f'\\nResults: {passed} passed, {failed} failed')",
                "            if failed > 0:",
                "                raise AssertionError(f'{failed} assertions failed')",
            ]
        )

        script = header + "\n".join(body_lines) + footer
        return json.dumps({"script": script, "assertions_count": len(inp.assertions)})
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def webapp_generate_server_cmd(
    servers: list[dict],
    test_script: str,
) -> str:
    """Generate with_server.py command for running tests with managed servers."""
    try:
        inp = GenerateServerCmdInput(servers=servers, test_script=test_script)

        # Build command
        cmd_parts = ["python scripts/with_server.py"]

        for server in inp.servers:
            cmd_parts.append(f'--server "{server["command"]}" --port {server["port"]}')

        cmd_parts.append(f"-- python {inp.test_script}")

        command = " \\\n  ".join(cmd_parts)

        # Also provide the Python equivalent
        python_usage = f'''"""Using with_server.py programmatically"""
import subprocess

# Command to run
cmd = {cmd_parts}

# Run as single command
subprocess.run(' '.join(cmd), shell=True)
'''

        return json.dumps(
            {
                "command": command,
                "servers_count": len(inp.servers),
                "python_usage": python_usage,
            }
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def webapp_detect_antipatterns(
    code: str,
) -> str:
    """Detect common testing antipatterns in Playwright code."""
    try:
        inp = DetectAntipatternsInput(code=code)

        findings = []
        for ap in ANTIPATTERNS:
            matches = re.findall(ap["pattern"], inp.code, re.IGNORECASE | re.MULTILINE)
            if matches:
                findings.append(
                    {
                        "issue": ap["issue"],
                        "fix": ap["fix"],
                        "occurrences": len(matches),
                    }
                )

        # Additional checks
        if "sync_playwright" not in inp.code and "async_playwright" not in inp.code:
            findings.append(
                {
                    "issue": "Missing Playwright import/context",
                    "fix": "Use 'with sync_playwright() as p:' context manager",
                    "occurrences": 1,
                }
            )

        if "browser.close()" not in inp.code and "context.close()" not in inp.code:
            findings.append(
                {
                    "issue": "Missing browser/context cleanup",
                    "fix": "Always close browser in finally block or use context manager",
                    "occurrences": 1,
                }
            )

        return json.dumps(
            {
                "findings": findings,
                "issues_found": len(findings),
                "code_lines": len(inp.code.split("\n")),
            }
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def webapp_suggest_selectors(
    html: str,
    target_element: str | None = None,
) -> str:
    """Suggest Playwright selectors for elements in HTML snippet."""
    try:
        inp = SuggestSelectorsInput(html=html, target_element=target_element)

        suggestions = []

        # Simple HTML parsing for common patterns
        # Find elements with data-testid
        testid_matches = re.findall(r'data-testid=["\']([^"\']+)["\']', inp.html)
        for tid in testid_matches:
            suggestions.append(
                {
                    "selector": f'[data-testid="{tid}"]',
                    "strategy": "data_testid",
                    "priority": 1,
                    "reason": "Preferred: explicit test ID",
                }
            )

        # Find elements with id
        id_matches = re.findall(r'\bid=["\']([^"\']+)["\']', inp.html)
        for eid in id_matches:
            suggestions.append(
                {
                    "selector": f"#{eid}",
                    "strategy": "id",
                    "priority": 2,
                    "reason": "Good: unique identifier",
                }
            )

        # Find buttons with text
        button_matches = re.findall(
            r"<button[^>]*>([^<]+)</button>", inp.html, re.IGNORECASE
        )
        for text in button_matches:
            text = text.strip()
            if text:
                suggestions.append(
                    {
                        "selector": f'role=button[name="{text}"]',
                        "strategy": "role",
                        "priority": 3,
                        "reason": "Accessible: ARIA role selector",
                    }
                )

        # Find links
        link_matches = re.findall(r"<a[^>]*>([^<]+)</a>", inp.html, re.IGNORECASE)
        for text in link_matches:
            text = text.strip()
            if text:
                suggestions.append(
                    {
                        "selector": f'role=link[name="{text}"]',
                        "strategy": "role",
                        "priority": 3,
                        "reason": "Accessible: ARIA role selector",
                    }
                )

        # Find inputs with placeholder
        placeholder_matches = re.findall(r'placeholder=["\']([^"\']+)["\']', inp.html)
        for ph in placeholder_matches:
            suggestions.append(
                {
                    "selector": f'[placeholder="{ph}"]',
                    "strategy": "placeholder",
                    "priority": 4,
                    "reason": "Good for form inputs",
                }
            )

        # General selector strategies reference
        strategies = [
            {"strategy": s, **SELECTOR_STRATEGIES[s]} for s in SELECTOR_STRATEGIES
        ]

        return json.dumps(
            {
                "suggestions": suggestions[:15],  # Limit results
                "strategies_reference": strategies,
                "target_element": inp.target_element,
            }
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def webapp_generate_scaffold(
    app_type: str,
    base_url: str = "http://localhost:3000",
    test_cases: list[str] | None = None,
    use_server_wrapper: bool = False,
) -> str:
    """Generate complete test scaffold for a web application."""
    try:
        inp = GenerateScaffoldInput(
            app_type=app_type,
            base_url=base_url,
            test_cases=test_cases or [],
            use_server_wrapper=use_server_wrapper,
        )

        # Config based on app type
        wait_strategy = "networkidle" if inp.app_type == "spa" else "domcontentloaded"

        scaffold = f'''"""
Web Application Test Suite
Generated by webapp_testing_mcp

App Type: {inp.app_type.upper()}
Base URL: {inp.base_url}
"""
from playwright.sync_api import sync_playwright, expect
import json

BASE_URL = "{inp.base_url}"

class TestSuite:
    """Test suite for {inp.app_type.upper()} application."""

    def __init__(self):
        self.results = []

    def setup(self):
        """Initialize browser and page."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

    def teardown(self):
        """Cleanup browser resources."""
        self.context.close()
        self.browser.close()
        self.playwright.stop()

    def navigate(self, path="/"):
        """Navigate to a path and wait for load."""
        url = f"{{BASE_URL}}{{path}}"
        self.page.goto(url)
        self.page.wait_for_load_state("{wait_strategy}")

    def run_test(self, name, test_fn):
        """Run a single test with error handling."""
        try:
            test_fn()
            self.results.append({{"name": name, "status": "passed"}})
            print(f"[PASS] {{name}}")
        except Exception as e:
            self.results.append({{"name": name, "status": "failed", "error": str(e)}})
            print(f"[FAIL] {{name}}: {{e}}")

    # =========================================================================
    # Test Cases
    # =========================================================================

    def test_homepage_loads(self):
        """Verify homepage loads successfully."""
        self.navigate("/")
        expect(self.page).to_have_title(/.+/)

    def test_navigation_works(self):
        """Verify basic navigation."""
        self.navigate("/")
        # TODO: Add navigation assertions
        pass
'''

        # Add custom test cases
        for i, tc in enumerate(inp.test_cases):
            method_name = re.sub(r"[^a-z0-9]+", "_", tc.lower()).strip("_")
            scaffold += f'''
    def test_{method_name}(self):
        """{tc}"""
        self.navigate("/")
        # TODO: Implement test for: {tc}
        pass
'''

        scaffold += '''
    def run_all(self):
        """Run all tests."""
        self.setup()
        try:
            self.run_test("Homepage loads", self.test_homepage_loads)
            self.run_test("Navigation works", self.test_navigation_works)
'''

        for tc in inp.test_cases:
            method_name = re.sub(r"[^a-z0-9]+", "_", tc.lower()).strip("_")
            scaffold += f'            self.run_test("{tc}", self.test_{method_name})\n'

        scaffold += """
            # Print summary
            passed = sum(1 for r in self.results if r["status"] == "passed")
            print(f"\\n{'='*50}")
            print(f"Results: {passed}/{len(self.results)} passed")
            print(json.dumps(self.results, indent=2))
        finally:
            self.teardown()


if __name__ == "__main__":
    suite = TestSuite()
    suite.run_all()
"""

        # Server wrapper command if needed
        server_cmd = None
        if inp.use_server_wrapper:
            server_cmd = f'python scripts/with_server.py --server "npm run dev" --port 3000 -- python test_suite.py'

        return json.dumps(
            {
                "scaffold": scaffold,
                "app_type": inp.app_type,
                "test_cases_count": len(inp.test_cases) + 2,  # +2 for default tests
                "server_command": server_cmd,
            }
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
