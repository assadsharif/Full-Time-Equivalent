"""
Web Artifacts Builder MCP Server — toolkit for creating elaborate, multi-component
claude.ai HTML artifacts using React, Tailwind CSS, and shadcn/ui.

TOOLS:
    artifacts_generate_component     Generate shadcn/ui React component
    artifacts_generate_page          Generate full page component
    artifacts_generate_layout        Generate layout components
    artifacts_generate_state         Generate state management code
    artifacts_generate_form          Generate form with validation
    artifacts_generate_data_display  Generate data display components
    artifacts_generate_init_cmd      Generate init-artifact.sh command
    artifacts_generate_bundle_cmd    Generate bundle-artifact.sh command
    artifacts_detect_antipatterns    Detect "AI slop" design patterns
    artifacts_generate_scaffold      Generate complete artifact scaffold
"""

import json
import re
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("web_artifacts_mcp")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Available shadcn/ui components
SHADCN_COMPONENTS = [
    "accordion", "alert", "alert-dialog", "aspect-ratio", "avatar", "badge",
    "breadcrumb", "button", "calendar", "card", "carousel", "chart", "checkbox",
    "collapsible", "combobox", "command", "context-menu", "data-table", "date-picker",
    "dialog", "drawer", "dropdown-menu", "form", "hover-card", "input", "input-otp",
    "label", "menubar", "navigation-menu", "pagination", "popover", "progress",
    "radio-group", "resizable", "scroll-area", "select", "separator", "sheet",
    "sidebar", "skeleton", "slider", "sonner", "switch", "table", "tabs",
    "textarea", "toast", "toggle", "toggle-group", "tooltip",
]

# AI slop patterns to detect and avoid
AI_SLOP_PATTERNS = [
    {"pattern": r"bg-gradient-to-[rb].*purple", "issue": "Purple gradient background", "fix": "Use solid colors or subtle gradients with brand colors"},
    {"pattern": r"text-center.*mx-auto.*max-w", "issue": "Overly centered layout", "fix": "Use asymmetric layouts, left-aligned content, or grid layouts"},
    {"pattern": r"rounded-[23]xl", "issue": "Excessive border radius", "fix": "Use rounded-lg or rounded-md for subtlety"},
    {"pattern": r"font-\[?['\"]?Inter", "issue": "Default Inter font", "fix": "Use distinctive fonts like Space Grotesk, Outfit, or system fonts"},
    {"pattern": r"(#7c3aed|#8b5cf6|#a855f7)", "issue": "Default purple colors", "fix": "Choose unique brand colors"},
    {"pattern": r"shadow-2xl.*rounded-3xl", "issue": "Heavy shadows with large radius", "fix": "Use subtle shadows (shadow-sm, shadow-md)"},
    {"pattern": r"hover:scale-1[01][05]", "issue": "Exaggerated scale transforms", "fix": "Use subtle transforms (scale-[1.02]) or no scale"},
    {"pattern": r"animate-bounce|animate-pulse", "issue": "Overused animations", "fix": "Use custom, subtle animations or transitions"},
    {"pattern": r"flex.*items-center.*justify-center.*min-h-screen", "issue": "Centered fullscreen pattern", "fix": "Use diverse layouts with proper hierarchy"},
    {"pattern": r"(bg-white|bg-gray-50).*dark:bg-gray-900", "issue": "Generic light/dark theming", "fix": "Create distinctive color schemes"},
]

# Layout types
LAYOUT_TYPES = ["sidebar", "topnav", "dashboard", "split", "fullscreen", "grid", "masonry", "hero"]

# Form field types
FORM_FIELD_TYPES = ["text", "email", "password", "number", "tel", "url", "textarea", "select", "checkbox", "radio", "date", "file", "switch", "slider", "combobox"]

# Data display types
DATA_DISPLAY_TYPES = ["table", "cards", "list", "grid", "tree", "timeline", "kanban", "stats"]

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

_CFG = ConfigDict(str_strip_whitespace=True, extra="forbid")


class GenerateComponentInput(BaseModel):
    model_config = _CFG
    component_name: str = Field(..., min_length=1, max_length=50, description="Component name (PascalCase)")
    component_type: str = Field(..., description="shadcn/ui component type to use")
    props: dict[str, str] = Field(default_factory=dict, description="Component props and their types")
    description: str = Field(default="", max_length=200, description="Component description")

    @field_validator("component_name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if not re.match(r"^[A-Z][a-zA-Z0-9]*$", v):
            raise ValueError("Component name must be PascalCase")
        return v

    @field_validator("component_type")
    @classmethod
    def _validate_type(cls, v: str) -> str:
        v = v.lower().replace("_", "-")
        if v not in SHADCN_COMPONENTS:
            raise ValueError(f"Unknown component: {v}. Available: {SHADCN_COMPONENTS[:10]}...")
        return v


class GeneratePageInput(BaseModel):
    model_config = _CFG
    page_name: str = Field(..., min_length=1, max_length=50, description="Page name")
    title: str = Field(..., min_length=1, max_length=100, description="Page title")
    sections: list[str] = Field(default_factory=list, description="Page sections")
    use_layout: Optional[str] = Field(default=None, description="Layout type to use")

    @field_validator("use_layout")
    @classmethod
    def _validate_layout(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.lower() not in LAYOUT_TYPES:
            raise ValueError(f"Unknown layout: {v}. Available: {LAYOUT_TYPES}")
        return v.lower() if v else None


class GenerateLayoutInput(BaseModel):
    model_config = _CFG
    layout_type: str = Field(..., description="Layout type")
    include_nav: bool = Field(default=True, description="Include navigation")
    include_footer: bool = Field(default=False, description="Include footer")
    responsive: bool = Field(default=True, description="Make responsive")

    @field_validator("layout_type")
    @classmethod
    def _validate_type(cls, v: str) -> str:
        v = v.lower()
        if v not in LAYOUT_TYPES:
            raise ValueError(f"Unknown layout: {v}. Available: {LAYOUT_TYPES}")
        return v


class GenerateStateInput(BaseModel):
    model_config = _CFG
    state_name: str = Field(..., min_length=1, max_length=50, description="State variable name")
    state_type: str = Field(..., description="TypeScript type for state")
    initial_value: str = Field(..., description="Initial value (JSON-compatible)")
    use_reducer: bool = Field(default=False, description="Use useReducer instead of useState")
    actions: list[str] = Field(default_factory=list, description="Actions for reducer")


class GenerateFormInput(BaseModel):
    model_config = _CFG
    form_name: str = Field(..., min_length=1, max_length=50, description="Form component name")
    fields: list[dict] = Field(..., min_length=1, description="Form fields [{name, type, label, required?, validation?}]")
    submit_action: str = Field(default="onSubmit", description="Submit handler name")
    use_react_hook_form: bool = Field(default=True, description="Use react-hook-form")

    @field_validator("fields")
    @classmethod
    def _validate_fields(cls, v: list[dict]) -> list[dict]:
        for f in v:
            if "name" not in f or "type" not in f:
                raise ValueError("Each field needs 'name' and 'type'")
            if f["type"] not in FORM_FIELD_TYPES:
                raise ValueError(f"Unknown field type: {f['type']}. Available: {FORM_FIELD_TYPES}")
        return v


class GenerateDataDisplayInput(BaseModel):
    model_config = _CFG
    display_type: str = Field(..., description="Display type")
    data_shape: dict[str, str] = Field(..., description="Data shape (field -> type)")
    component_name: str = Field(default="DataDisplay", description="Component name")
    include_actions: bool = Field(default=False, description="Include row/item actions")
    include_filtering: bool = Field(default=False, description="Include filtering")
    include_sorting: bool = Field(default=False, description="Include sorting")

    @field_validator("display_type")
    @classmethod
    def _validate_type(cls, v: str) -> str:
        v = v.lower()
        if v not in DATA_DISPLAY_TYPES:
            raise ValueError(f"Unknown display type: {v}. Available: {DATA_DISPLAY_TYPES}")
        return v


class GenerateInitCmdInput(BaseModel):
    model_config = _CFG
    project_name: str = Field(..., min_length=1, max_length=50, description="Project name")
    description: str = Field(default="", max_length=200, description="Project description")

    @field_validator("project_name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if not re.match(r"^[a-z][a-z0-9-]*$", v):
            raise ValueError("Project name must be lowercase with hyphens")
        return v


class GenerateBundleCmdInput(BaseModel):
    model_config = _CFG
    project_path: str = Field(default=".", description="Project path")
    output_name: str = Field(default="bundle.html", description="Output filename")

    @field_validator("project_path")
    @classmethod
    def _validate_path(cls, v: str) -> str:
        if ".." in v:
            raise ValueError("Path traversal not allowed")
        return v


class DetectAntipatternsInput(BaseModel):
    model_config = _CFG
    code: str = Field(..., min_length=10, max_length=50000, description="Code to analyze")


class GenerateScaffoldInput(BaseModel):
    model_config = _CFG
    artifact_type: str = Field(..., description="Artifact type: dashboard, landing, form, data-viz, app")
    title: str = Field(..., min_length=1, max_length=100, description="Artifact title")
    features: list[str] = Field(default_factory=list, description="Features to include")
    style: str = Field(default="modern", description="Style: modern, minimal, bold, elegant")

    @field_validator("artifact_type")
    @classmethod
    def _validate_type(cls, v: str) -> str:
        v = v.lower().replace("_", "-")
        valid = ["dashboard", "landing", "form", "data-viz", "app"]
        if v not in valid:
            raise ValueError(f"Unknown artifact type: {v}. Available: {valid}")
        return v


# ---------------------------------------------------------------------------
# Code generators
# ---------------------------------------------------------------------------


def _generate_imports(components: list[str], hooks: list[str] = None) -> str:
    """Generate import statements."""
    lines = ['import React from "react";']

    if hooks:
        lines[0] = f'import React, {{ {", ".join(hooks)} }} from "react";'

    for comp in components:
        pascal = comp.replace("-", " ").title().replace(" ", "")
        lines.append(f'import {{ {pascal} }} from "@/components/ui/{comp}";')

    return "\n".join(lines)


def _generate_typescript_interface(name: str, fields: dict[str, str]) -> str:
    """Generate TypeScript interface."""
    lines = [f"interface {name} {{"]
    for field, ftype in fields.items():
        lines.append(f"  {field}: {ftype};")
    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def artifacts_generate_component(
    component_name: str,
    component_type: str,
    props: dict[str, str] | None = None,
    description: str = "",
) -> str:
    """Generate a shadcn/ui React component with TypeScript."""
    try:
        inp = GenerateComponentInput(
            component_name=component_name,
            component_type=component_type,
            props=props or {},
            description=description,
        )

        # Generate props interface
        props_interface = ""
        props_str = ""
        if inp.props:
            props_interface = _generate_typescript_interface(f"{inp.component_name}Props", inp.props)
            props_str = f"{{ {', '.join(inp.props.keys())} }}: {inp.component_name}Props"

        # Component templates based on type
        templates = {
            "button": f'''<Button variant="default" size="default">
      Click me
    </Button>''',
            "card": f'''<Card>
      <CardHeader>
        <CardTitle>Title</CardTitle>
        <CardDescription>Description</CardDescription>
      </CardHeader>
      <CardContent>
        Content goes here
      </CardContent>
    </Card>''',
            "dialog": f'''<Dialog>
      <DialogTrigger asChild>
        <Button variant="outline">Open Dialog</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Title</DialogTitle>
          <DialogDescription>Description</DialogDescription>
        </DialogHeader>
        <div>Content</div>
      </DialogContent>
    </Dialog>''',
            "input": f'''<div className="space-y-2">
      <Label htmlFor="input">Label</Label>
      <Input id="input" placeholder="Enter value..." />
    </div>''',
            "select": f'''<Select>
      <SelectTrigger>
        <SelectValue placeholder="Select..." />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="1">Option 1</SelectItem>
        <SelectItem value="2">Option 2</SelectItem>
      </SelectContent>
    </Select>''',
        }

        template = templates.get(inp.component_type, f"<{inp.component_type.title()} />")

        code = f'''/**
 * {inp.component_name}
 * {inp.description or f"A {inp.component_type} component"}
 */
import React from "react";
import {{ {inp.component_type.title().replace("-", "")} }} from "@/components/ui/{inp.component_type}";

{props_interface}

export function {inp.component_name}({props_str or ""}) {{
  return (
    {template}
  );
}}
'''

        return json.dumps({
            "code": code,
            "component_name": inp.component_name,
            "component_type": inp.component_type,
            "imports": [inp.component_type],
        })
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def artifacts_generate_page(
    page_name: str,
    title: str,
    sections: list[str] | None = None,
    use_layout: str | None = None,
) -> str:
    """Generate a full page component with sections."""
    try:
        inp = GeneratePageInput(
            page_name=page_name,
            title=title,
            sections=sections or ["hero", "content", "footer"],
            use_layout=use_layout,
        )

        # Generate section components
        section_code = []
        for section in inp.sections:
            section_code.append(f'''        {{/* {section.title()} Section */}}
        <section className="py-12 px-4">
          <div className="max-w-6xl mx-auto">
            <h2 className="text-2xl font-bold mb-6">{section.title()}</h2>
            <p className="text-muted-foreground">
              {section.title()} content goes here
            </p>
          </div>
        </section>''')

        layout_wrapper_start = ""
        layout_wrapper_end = ""
        if inp.use_layout:
            layout_wrapper_start = f"<{inp.use_layout.title()}Layout>"
            layout_wrapper_end = f"</{inp.use_layout.title()}Layout>"

        code = f'''/**
 * {inp.page_name} Page
 */
import React from "react";

export function {inp.page_name}Page() {{
  return (
    {layout_wrapper_start}<div className="min-h-screen bg-background">
      {{/* Page Header */}}
      <header className="border-b">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold tracking-tight">{inp.title}</h1>
        </div>
      </header>

      {{/* Main Content */}}
      <main>
{chr(10).join(section_code)}
      </main>
    </div>{layout_wrapper_end}
  );
}}
'''

        return json.dumps({
            "code": code,
            "page_name": inp.page_name,
            "sections": inp.sections,
            "layout": inp.use_layout,
        })
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def artifacts_generate_layout(
    layout_type: str,
    include_nav: bool = True,
    include_footer: bool = False,
    responsive: bool = True,
) -> str:
    """Generate layout components (sidebar, topnav, dashboard, etc.)."""
    try:
        inp = GenerateLayoutInput(
            layout_type=layout_type,
            include_nav=include_nav,
            include_footer=include_footer,
            responsive=responsive,
        )

        # Define template content
        header_content = '<header className="h-14 border-b flex items-center px-4">\n          <button className="md:hidden">Menu</button>\n          <span className="ml-auto">User</span>\n        </header>'
        footer_content = '<footer className="border-t p-4 text-center text-sm text-muted-foreground">\n          Footer'

        layouts = {
            "sidebar": f'''export function SidebarLayout({{ children }}: {{ children: React.ReactNode }}) {{
  return (
    <div className="flex min-h-screen">
      {{/* Sidebar */}}
      <aside className="{"hidden md:flex" if inp.responsive else "flex"} w-64 flex-col border-r bg-muted/40">
        <div className="flex h-14 items-center border-b px-4">
          <span className="font-semibold">Logo</span>
        </div>
        <nav className="flex-1 p-4 space-y-2">
          <a href="#" className="block px-3 py-2 rounded-md hover:bg-accent">Dashboard</a>
          <a href="#" className="block px-3 py-2 rounded-md hover:bg-accent">Settings</a>
        </nav>
      </aside>

      {{/* Main Content */}}
      <div className="flex-1 flex flex-col">
        {header_content if inp.include_nav else ""}
        <main className="flex-1 p-6">
          {{children}}
        </main>
        {footer_content + "\n        </footer>" if inp.include_footer else ""}
      </div>
    </div>
  );
}}''',
            "topnav": f'''export function TopnavLayout({{ children }}: {{ children: React.ReactNode }}) {{
  return (
    <div className="min-h-screen flex flex-col">
      {f'''<header className="h-16 border-b">
        <nav className="max-w-7xl mx-auto px-4 h-full flex items-center justify-between">
          <span className="font-bold text-xl">Logo</span>
          <div className="{"hidden md:flex" if inp.responsive else "flex"} gap-6">
            <a href="#" className="hover:text-primary">Home</a>
            <a href="#" className="hover:text-primary">About</a>
            <a href="#" className="hover:text-primary">Contact</a>
          </div>
        </nav>
      </header>''' if inp.include_nav else ""}
      <main className="flex-1">
        {{children}}
      </main>
      {f'''<footer className="border-t py-8">
        <div className="max-w-7xl mx-auto px-4 text-center text-muted-foreground">
          Footer content
        </div>
      </footer>''' if inp.include_footer else ""}
    </div>
  );
}}''',
            "dashboard": f'''export function DashboardLayout({{ children }}: {{ children: React.ReactNode }}) {{
  return (
    <div className="min-h-screen bg-muted/40">
      {f'''<header className="sticky top-0 z-50 bg-background border-b">
        <div className="flex h-14 items-center px-4 gap-4">
          <span className="font-semibold">Dashboard</span>
          <div className="ml-auto flex items-center gap-4">
            <span>User</span>
          </div>
        </div>
      </header>''' if inp.include_nav else ""}
      <div className="flex">
        <aside className="{"hidden lg:block" if inp.responsive else "block"} w-64 border-r min-h-[calc(100vh-3.5rem)]">
          <nav className="p-4 space-y-2">
            <a href="#" className="flex items-center gap-2 px-3 py-2 rounded-md bg-accent">Overview</a>
            <a href="#" className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-accent">Analytics</a>
            <a href="#" className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-accent">Settings</a>
          </nav>
        </aside>
        <main className="flex-1 p-6">
          {{children}}
        </main>
      </div>
    </div>
  );
}}''',
            "split": f'''export function SplitLayout({{ left, right }}: {{ left: React.ReactNode; right: React.ReactNode }}) {{
  return (
    <div className="min-h-screen flex {"flex-col md:flex-row" if inp.responsive else "flex-row"}">
      <div className="{"w-full md:w-1/2" if inp.responsive else "w-1/2"} p-6 border-r">
        {{left}}
      </div>
      <div className="{"w-full md:w-1/2" if inp.responsive else "w-1/2"} p-6">
        {{right}}
      </div>
    </div>
  );
}}''',
        }

        code = f'''/**
 * {inp.layout_type.title()} Layout Component
 */
import React from "react";

{layouts.get(inp.layout_type, layouts["topnav"])}
'''

        return json.dumps({
            "code": code,
            "layout_type": inp.layout_type,
            "features": {
                "nav": inp.include_nav,
                "footer": inp.include_footer,
                "responsive": inp.responsive,
            },
        })
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def artifacts_generate_state(
    state_name: str,
    state_type: str,
    initial_value: str,
    use_reducer: bool = False,
    actions: list[str] | None = None,
) -> str:
    """Generate state management code with useState or useReducer."""
    try:
        inp = GenerateStateInput(
            state_name=state_name,
            state_type=state_type,
            initial_value=initial_value,
            use_reducer=use_reducer,
            actions=actions or [],
        )

        if inp.use_reducer and inp.actions:
            # Generate useReducer pattern
            action_types = " | ".join([f'{{ type: "{a}" }}' for a in inp.actions])

            code = f'''// State type
type {inp.state_name.title()}State = {inp.state_type};

// Action types
type {inp.state_name.title()}Action = {action_types};

// Reducer
function {inp.state_name}Reducer(
  state: {inp.state_name.title()}State,
  action: {inp.state_name.title()}Action
): {inp.state_name.title()}State {{
  switch (action.type) {{
{chr(10).join([f'    case "{a}":' + chr(10) + f'      // Handle {a}' + chr(10) + '      return state;' for a in inp.actions])}
    default:
      return state;
  }}
}}

// Initial state
const initial{inp.state_name.title()}: {inp.state_name.title()}State = {inp.initial_value};

// Usage in component
function Example() {{
  const [{inp.state_name}, dispatch] = useReducer(
    {inp.state_name}Reducer,
    initial{inp.state_name.title()}
  );

  return (
    <div>
      {{/* Use {inp.state_name} and dispatch */}}
    </div>
  );
}}
'''
        else:
            # Generate useState pattern
            setter = f"set{inp.state_name[0].upper()}{inp.state_name[1:]}"
            code = f'''// State type
type {inp.state_name.title()}State = {inp.state_type};

// Initial value
const initial{inp.state_name.title()}: {inp.state_name.title()}State = {inp.initial_value};

// Usage in component
function Example() {{
  const [{inp.state_name}, {setter}] = useState<{inp.state_name.title()}State>(
    initial{inp.state_name.title()}
  );

  // Update state
  const update{inp.state_name.title()} = (newValue: {inp.state_name.title()}State) => {{
    {setter}(newValue);
  }};

  return (
    <div>
      {{/* Use {inp.state_name} */}}
    </div>
  );
}}
'''

        return json.dumps({
            "code": code,
            "state_name": inp.state_name,
            "pattern": "useReducer" if inp.use_reducer else "useState",
            "hooks_needed": ["useReducer"] if inp.use_reducer else ["useState"],
        })
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def artifacts_generate_form(
    form_name: str,
    fields: list[dict],
    submit_action: str = "onSubmit",
    use_react_hook_form: bool = True,
) -> str:
    """Generate form component with validation using shadcn/ui and react-hook-form."""
    try:
        inp = GenerateFormInput(
            form_name=form_name,
            fields=fields,
            submit_action=submit_action,
            use_react_hook_form=use_react_hook_form,
        )

        # Generate form field components
        field_components = []
        for field in inp.fields:
            name = field["name"]
            ftype = field["type"]
            label = field.get("label", name.title())
            required = field.get("required", False)

            if ftype == "text" or ftype == "email" or ftype == "password":
                field_components.append(f'''          <FormField
            control={{form.control}}
            name="{name}"
            render={{({{ field }}) => (
              <FormItem>
                <FormLabel>{label}{" *" if required else ""}</FormLabel>
                <FormControl>
                  <Input type="{ftype}" placeholder="Enter {label.lower()}..." {{...field}} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}}
          />''')
            elif ftype == "textarea":
                field_components.append(f'''          <FormField
            control={{form.control}}
            name="{name}"
            render={{({{ field }}) => (
              <FormItem>
                <FormLabel>{label}</FormLabel>
                <FormControl>
                  <Textarea placeholder="Enter {label.lower()}..." {{...field}} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}}
          />''')
            elif ftype == "select":
                options = field.get("options", ["Option 1", "Option 2"])
                field_components.append(f'''          <FormField
            control={{form.control}}
            name="{name}"
            render={{({{ field }}) => (
              <FormItem>
                <FormLabel>{label}</FormLabel>
                <Select onValueChange={{field.onChange}} defaultValue={{field.value}}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select..." />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
{chr(10).join([f'                    <SelectItem value="{opt.lower().replace(" ", "-")}">{opt}</SelectItem>' for opt in options])}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}}
          />''')
            elif ftype == "checkbox":
                field_components.append(f'''          <FormField
            control={{form.control}}
            name="{name}"
            render={{({{ field }}) => (
              <FormItem className="flex items-center gap-2">
                <FormControl>
                  <Checkbox checked={{field.value}} onCheckedChange={{field.onChange}} />
                </FormControl>
                <FormLabel className="!mt-0">{label}</FormLabel>
              </FormItem>
            )}}
          />''')

        # Generate schema
        schema_fields = []
        for field in inp.fields:
            name = field["name"]
            ftype = field["type"]
            required = field.get("required", False)
            validation = field.get("validation", "")

            if ftype == "email":
                schema_fields.append(f'  {name}: z.string().email("Invalid email")')
            elif ftype in ("text", "password", "textarea"):
                schema_fields.append(f'  {name}: z.string(){".min(1)" if required else ""}')
            elif ftype == "checkbox":
                schema_fields.append(f'  {name}: z.boolean()')
            else:
                schema_fields.append(f'  {name}: z.string()')

        code = f'''/**
 * {inp.form_name} Form Component
 */
import React from "react";
import {{ useForm }} from "react-hook-form";
import {{ zodResolver }} from "@hookform/resolvers/zod";
import * as z from "zod";
import {{
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
}} from "@/components/ui/form";
import {{ Input }} from "@/components/ui/input";
import {{ Button }} from "@/components/ui/button";
import {{ Textarea }} from "@/components/ui/textarea";
import {{ Select, SelectContent, SelectItem, SelectTrigger, SelectValue }} from "@/components/ui/select";
import {{ Checkbox }} from "@/components/ui/checkbox";

// Form schema
const formSchema = z.object({{
{chr(10).join(schema_fields)},
}});

type FormValues = z.infer<typeof formSchema>;

interface {inp.form_name}Props {{
  {inp.submit_action}: (values: FormValues) => void;
}}

export function {inp.form_name}({{ {inp.submit_action} }}: {inp.form_name}Props) {{
  const form = useForm<FormValues>({{
    resolver: zodResolver(formSchema),
    defaultValues: {{
{chr(10).join([f'      {f["name"]}: "",' for f in inp.fields])}
    }},
  }});

  return (
    <Form {{...form}}>
      <form onSubmit={{form.handleSubmit({inp.submit_action})}} className="space-y-6">
{chr(10).join(field_components)}
        <Button type="submit">Submit</Button>
      </form>
    </Form>
  );
}}
'''

        return json.dumps({
            "code": code,
            "form_name": inp.form_name,
            "fields_count": len(inp.fields),
            "dependencies": ["react-hook-form", "@hookform/resolvers", "zod"],
        })
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def artifacts_generate_data_display(
    display_type: str,
    data_shape: dict[str, str],
    component_name: str = "DataDisplay",
    include_actions: bool = False,
    include_filtering: bool = False,
    include_sorting: bool = False,
) -> str:
    """Generate data display components (table, cards, list, etc.)."""
    try:
        inp = GenerateDataDisplayInput(
            display_type=display_type,
            data_shape=data_shape,
            component_name=component_name,
            include_actions=include_actions,
            include_filtering=include_filtering,
            include_sorting=include_sorting,
        )

        # Generate type interface
        interface = _generate_typescript_interface("DataItem", inp.data_shape)

        if inp.display_type == "table":
            columns = list(inp.data_shape.keys())
            code = f'''/**
 * {inp.component_name} - Table Display
 */
import React from "react";
import {{
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
}} from "@/components/ui/table";
{f'import {{ Button }} from "@/components/ui/button";' if inp.include_actions else ""}

{interface}

interface {inp.component_name}Props {{
  data: DataItem[];
  {f'onEdit?: (item: DataItem) => void;' if inp.include_actions else ""}
  {f'onDelete?: (item: DataItem) => void;' if inp.include_actions else ""}
}}

export function {inp.component_name}({{ data{", onEdit, onDelete" if inp.include_actions else ""} }}: {inp.component_name}Props) {{
  return (
    <Table>
      <TableHeader>
        <TableRow>
{chr(10).join([f'          <TableHead>{col.title()}</TableHead>' for col in columns])}
          {f'<TableHead>Actions</TableHead>' if inp.include_actions else ""}
        </TableRow>
      </TableHeader>
      <TableBody>
        {{data.map((item, index) => (
          <TableRow key={{index}}>
{chr(10).join([f'            <TableCell>{{item.{col}}}</TableCell>' for col in columns])}
            {f'''<TableCell>
              <Button variant="ghost" size="sm" onClick={{() => onEdit?.(item)}}>Edit</Button>
              <Button variant="ghost" size="sm" onClick={{() => onDelete?.(item)}}>Delete</Button>
            </TableCell>''' if inp.include_actions else ""}
          </TableRow>
        ))}}
      </TableBody>
    </Table>
  );
}}
'''
        elif inp.display_type == "cards":
            code = f'''/**
 * {inp.component_name} - Card Grid Display
 */
import React from "react";
import {{ Card, CardContent, CardHeader, CardTitle }} from "@/components/ui/card";

{interface}

interface {inp.component_name}Props {{
  data: DataItem[];
}}

export function {inp.component_name}({{ data }}: {inp.component_name}Props) {{
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {{data.map((item, index) => (
        <Card key={{index}}>
          <CardHeader>
            <CardTitle>{{item.{list(inp.data_shape.keys())[0]}}}</CardTitle>
          </CardHeader>
          <CardContent>
{chr(10).join([f'            <p><strong>{col.title()}:</strong> {{item.{col}}}</p>' for col in list(inp.data_shape.keys())[1:]])}
          </CardContent>
        </Card>
      ))}}
    </div>
  );
}}
'''
        else:
            # Default list display
            code = f'''/**
 * {inp.component_name} - List Display
 */
import React from "react";

{interface}

interface {inp.component_name}Props {{
  data: DataItem[];
}}

export function {inp.component_name}({{ data }}: {inp.component_name}Props) {{
  return (
    <ul className="space-y-4">
      {{data.map((item, index) => (
        <li key={{index}} className="p-4 border rounded-lg">
{chr(10).join([f'          <p><strong>{col.title()}:</strong> {{item.{col}}}</p>' for col in inp.data_shape.keys()])}
        </li>
      ))}}
    </ul>
  );
}}
'''

        return json.dumps({
            "code": code,
            "display_type": inp.display_type,
            "component_name": inp.component_name,
            "data_fields": list(inp.data_shape.keys()),
        })
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def artifacts_generate_init_cmd(
    project_name: str,
    description: str = "",
) -> str:
    """Generate init-artifact.sh command to create new artifact project."""
    try:
        inp = GenerateInitCmdInput(project_name=project_name, description=description)

        command = f"bash scripts/init-artifact.sh {inp.project_name}"

        instructions = f'''# Initialize New Artifact Project

## Command
```bash
{command}
cd {inp.project_name}
```

## What This Creates
- React + TypeScript project via Vite
- Tailwind CSS 3.4.1 with shadcn/ui theming
- Path aliases (@/) configured
- 40+ shadcn/ui components pre-installed
- Parcel bundling configuration

## Next Steps
1. Edit `src/App.tsx` to build your artifact
2. Run `npm run dev` to preview locally
3. Run `bash scripts/bundle-artifact.sh` when ready to bundle
'''

        return json.dumps({
            "command": command,
            "project_name": inp.project_name,
            "instructions": instructions,
        })
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def artifacts_generate_bundle_cmd(
    project_path: str = ".",
    output_name: str = "bundle.html",
) -> str:
    """Generate bundle-artifact.sh command to create single HTML file."""
    try:
        inp = GenerateBundleCmdInput(project_path=project_path, output_name=output_name)

        command = f"cd {inp.project_path} && bash ../scripts/bundle-artifact.sh"

        instructions = f'''# Bundle Artifact to Single HTML

## Command
```bash
{command}
```

## Output
Creates `{inp.output_name}` - a self-contained HTML file with:
- All JavaScript bundled and inlined
- All CSS bundled and inlined
- All dependencies resolved

## Requirements
- Project must have `index.html` in root
- Must have valid React app structure

## What the Script Does
1. Installs bundling dependencies (parcel, html-inline)
2. Creates .parcelrc config with path alias support
3. Builds with Parcel (no source maps)
4. Inlines all assets using html-inline
'''

        return json.dumps({
            "command": command,
            "output_file": inp.output_name,
            "instructions": instructions,
        })
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def artifacts_detect_antipatterns(
    code: str,
) -> str:
    """Detect 'AI slop' design antipatterns in React/Tailwind code."""
    try:
        inp = DetectAntipatternsInput(code=code)

        findings = []
        for ap in AI_SLOP_PATTERNS:
            matches = re.findall(ap["pattern"], inp.code, re.IGNORECASE)
            if matches:
                findings.append({
                    "issue": ap["issue"],
                    "fix": ap["fix"],
                    "occurrences": len(matches),
                    "examples": matches[:3],
                })

        # Score calculation
        total_issues = sum(f["occurrences"] for f in findings)
        score = max(0, 100 - (total_issues * 10))

        recommendations = []
        if total_issues > 0:
            recommendations = [
                "Replace purple gradients with brand-specific colors",
                "Use asymmetric layouts instead of centered everything",
                "Choose distinctive typography (Space Grotesk, Outfit, etc.)",
                "Use subtle shadows (shadow-sm) and border radius (rounded-md)",
                "Create custom, purposeful animations",
            ]

        return json.dumps({
            "findings": findings,
            "issues_count": len(findings),
            "total_occurrences": total_issues,
            "score": score,
            "recommendations": recommendations[:3] if findings else [],
        })
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def artifacts_generate_scaffold(
    artifact_type: str,
    title: str,
    features: list[str] | None = None,
    style: str = "modern",
) -> str:
    """Generate complete artifact scaffold with App.tsx and components."""
    try:
        inp = GenerateScaffoldInput(
            artifact_type=artifact_type,
            title=title,
            features=features or [],
            style=style,
        )

        # Style mappings
        style_classes = {
            "modern": "bg-slate-50 text-slate-900",
            "minimal": "bg-white text-gray-800",
            "bold": "bg-zinc-900 text-white",
            "elegant": "bg-stone-100 text-stone-800",
        }

        base_class = style_classes.get(inp.style, style_classes["modern"])

        # Generate based on artifact type
        if inp.artifact_type == "dashboard":
            scaffold = f'''/**
 * {inp.title} - Dashboard Artifact
 * Generated by web_artifacts_mcp
 */
import React, {{ useState }} from "react";
import {{ Card, CardContent, CardHeader, CardTitle }} from "@/components/ui/card";
import {{ Button }} from "@/components/ui/button";

export default function App() {{
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <div className="min-h-screen {base_class}">
      {{/* Header */}}
      <header className="border-b bg-background/95 backdrop-blur">
        <div className="flex h-14 items-center px-6">
          <h1 className="text-lg font-semibold">{inp.title}</h1>
        </div>
      </header>

      {{/* Main Content */}}
      <main className="p-6">
        {{/* Stats Cards */}}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
          {{["Users", "Revenue", "Orders", "Growth"].map((stat) => (
            <Card key={{stat}}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {{stat}}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">1,234</div>
              </CardContent>
            </Card>
          ))}}
        </div>

        {{/* Main Panel */}}
        <Card>
          <CardHeader>
            <CardTitle>Overview</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">
              Dashboard content goes here. Add charts, tables, or other components.
            </p>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}}
'''
        elif inp.artifact_type == "landing":
            scaffold = f'''/**
 * {inp.title} - Landing Page Artifact
 * Generated by web_artifacts_mcp
 */
import React from "react";
import {{ Button }} from "@/components/ui/button";

export default function App() {{
  return (
    <div className="min-h-screen {base_class}">
      {{/* Hero Section */}}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-6">
            {inp.title}
          </h1>
          <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
            A compelling description of your product or service goes here.
            Make it clear and persuasive.
          </p>
          <div className="flex gap-4 justify-center">
            <Button size="lg">Get Started</Button>
            <Button size="lg" variant="outline">Learn More</Button>
          </div>
        </div>
      </section>

      {{/* Features Section */}}
      <section className="py-16 px-6 bg-muted/50">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12">Features</h2>
          <div className="grid md:grid-cols-3 gap-8">
            {{["Fast", "Secure", "Scalable"].map((feature) => (
              <div key={{feature}} className="p-6 bg-background rounded-lg border">
                <h3 className="text-xl font-semibold mb-2">{{feature}}</h3>
                <p className="text-muted-foreground">
                  Description of the {{feature.toLowerCase()}} feature.
                </p>
              </div>
            ))}}
          </div>
        </div>
      </section>
    </div>
  );
}}
'''
        else:
            # Generic app scaffold
            scaffold = f'''/**
 * {inp.title} - App Artifact
 * Generated by web_artifacts_mcp
 */
import React, {{ useState }} from "react";
import {{ Button }} from "@/components/ui/button";
import {{ Card, CardContent, CardHeader, CardTitle }} from "@/components/ui/card";

export default function App() {{
  const [count, setCount] = useState(0);

  return (
    <div className="min-h-screen {base_class} p-6">
      <div className="max-w-2xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle>{inp.title}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-muted-foreground">
              Your artifact content goes here.
            </p>
            <div className="flex items-center gap-4">
              <Button onClick={{() => setCount(c => c + 1)}}>
                Count: {{count}}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}}
'''

        return json.dumps({
            "scaffold": scaffold,
            "artifact_type": inp.artifact_type,
            "title": inp.title,
            "style": inp.style,
            "recommended_components": ["Card", "Button", "Input", "Table"] if inp.artifact_type == "dashboard" else ["Button", "Card"],
        })
    except ValueError as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
