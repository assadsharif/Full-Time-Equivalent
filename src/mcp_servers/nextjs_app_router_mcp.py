"""
Next.js App Router MCP Server.

Provides 8 tools for generating Next.js App Router code:
- nextjs_scaffold_app: Scaffold app directory structure
- nextjs_generate_page: Generate page components
- nextjs_generate_layout: Generate layout components
- nextjs_generate_server_action: Generate server actions
- nextjs_generate_api_client: Generate API client
- nextjs_generate_loading_error: Generate loading/error states
- nextjs_validate_structure: Validate app structure
- nextjs_diagnose_issues: Diagnose common Next.js issues

Based on: .claude/skills/nextjs-app-router/
"""

import json
import re
from enum import Enum
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator


# =============================================================================
# MCP Server Instance
# =============================================================================

mcp = FastMCP("nextjs_app_router_mcp")


# =============================================================================
# Enums
# =============================================================================


class ComponentType(str, Enum):
    """Component type for Next.js."""

    SERVER = "server"
    CLIENT = "client"


class FetchCacheOption(str, Enum):
    """Fetch cache options."""

    NO_STORE = "no-store"
    FORCE_CACHE = "force-cache"
    DEFAULT = "default"


# =============================================================================
# Input Models
# =============================================================================


class ScaffoldAppInput(BaseModel):
    """Input for scaffolding a Next.js app."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    app_name: str = Field(..., min_length=1, description="Application name")
    features: list[str] = Field(default_factory=list, description="Feature routes to create")
    typescript: bool = Field(default=True, description="Use TypeScript")
    tailwind: bool = Field(default=True, description="Include Tailwind CSS")

    @field_validator("app_name")
    @classmethod
    def validate_app_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("App name is required")
        return v


class GeneratePageInput(BaseModel):
    """Input for generating a page component."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    route: str = Field(..., min_length=1, description="Route path (e.g., /todos, /todos/[id])")
    component_type: ComponentType = Field(default=ComponentType.SERVER, description="Server or client component")
    api_endpoint: Optional[str] = Field(default=None, description="API endpoint for data fetching")
    cache_option: FetchCacheOption = Field(default=FetchCacheOption.NO_STORE, description="Fetch cache option")

    @field_validator("route")
    @classmethod
    def validate_route(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Route is required")
        return v


class GenerateLayoutInput(BaseModel):
    """Input for generating a layout component."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    route: str = Field(..., min_length=1, description="Route path for the layout")
    title: Optional[str] = Field(default=None, description="Page title for metadata")
    description: Optional[str] = Field(default=None, description="Page description for metadata")


class GenerateServerActionInput(BaseModel):
    """Input for generating a server action."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    action_name: str = Field(..., min_length=1, description="Action function name")
    api_endpoint: str = Field(..., min_length=1, description="Backend API endpoint")
    method: str = Field(default="POST", description="HTTP method")
    revalidate_path: Optional[str] = Field(default=None, description="Path to revalidate after action")
    redirect_to: Optional[str] = Field(default=None, description="Path to redirect after action")

    @field_validator("action_name")
    @classmethod
    def validate_action_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Action name is required")
        return v


class GenerateApiClientInput(BaseModel):
    """Input for generating an API client."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    resource_name: str = Field(..., min_length=1, description="Resource name (e.g., todos)")
    base_url: str = Field(..., min_length=1, description="Base URL for API")
    endpoints: list[str] = Field(
        default_factory=lambda: ["list", "get", "create", "update", "delete"],
        description="Endpoints to generate",
    )
    use_env_var: bool = Field(default=True, description="Use environment variable for base URL")


class GenerateLoadingErrorInput(BaseModel):
    """Input for generating loading and error states."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    route: str = Field(..., min_length=1, description="Route path")
    include_not_found: bool = Field(default=False, description="Include not-found.tsx")
    loading_message: str = Field(default="Loading...", description="Loading message")


class ValidateStructureInput(BaseModel):
    """Input for validating app structure."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    files: list[str] = Field(..., min_length=1, description="List of file paths in the app")

    @field_validator("files")
    @classmethod
    def validate_files(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("Files list is required")
        return v


class DiagnoseIssuesInput(BaseModel):
    """Input for diagnosing Next.js issues."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    error_message: str = Field(..., min_length=1, description="Error message to diagnose")
    code_snippet: Optional[str] = Field(default=None, description="Related code snippet")


# =============================================================================
# Helper Functions
# =============================================================================


def _to_pascal_case(s: str) -> str:
    """Convert route to PascalCase component name."""
    # Remove leading slash and brackets
    s = s.lstrip("/")
    s = re.sub(r"\[(\w+)\]", r"\1", s)
    # Split and capitalize
    parts = re.split(r"[-_/]", s)
    return "".join(word.capitalize() for word in parts if word) or "Home"


def _route_to_path(route: str) -> str:
    """Convert route to file path."""
    if route == "/":
        return "app"
    return f"app{route}"


def _is_dynamic_route(route: str) -> bool:
    """Check if route has dynamic segments."""
    return "[" in route and "]" in route


def _extract_params(route: str) -> list[str]:
    """Extract dynamic parameters from route."""
    return re.findall(r"\[(\w+)\]", route)


# =============================================================================
# MCP Tools
# =============================================================================


@mcp.tool()
async def nextjs_scaffold_app(
    app_name: str,
    features: list[str] = None,
    typescript: bool = True,
    tailwind: bool = True,
) -> str:
    """
    Scaffold a Next.js App Router application structure.

    Args:
        app_name: Application name
        features: Feature routes to create
        typescript: Use TypeScript
        tailwind: Include Tailwind CSS

    Returns:
        JSON with file structure and setup instructions
    """
    features = features or []
    _input = ScaffoldAppInput(
        app_name=app_name,
        features=features,
        typescript=typescript,
        tailwind=tailwind,
    )

    ext = "tsx" if typescript else "jsx"
    ts_ext = "ts" if typescript else "js"

    files = {
        f"app/layout.{ext}": _generate_root_layout_code(app_name, typescript),
        f"app/page.{ext}": _generate_home_page_code(typescript),
        f"app/loading.{ext}": _generate_loading_code(),
        f"app/error.{ext}": _generate_error_code(),
        f"app/not-found.{ext}": _generate_not_found_code(),
        f"lib/api.{ts_ext}": _generate_api_lib_code(typescript),
        ".env.local": "NEXT_PUBLIC_API_URL=http://localhost:8000\nAPI_URL=http://localhost:8000",
    }

    # Add feature routes
    for feature in features:
        feature_path = feature.lstrip("/")
        files[f"app/{feature_path}/page.{ext}"] = _generate_feature_page_code(feature, typescript)
        files[f"app/{feature_path}/loading.{ext}"] = _generate_loading_code(feature)

    # Add types file if TypeScript
    if typescript:
        files["types/index.ts"] = _generate_types_code(features)

    return json.dumps({
        "success": True,
        "app_name": app_name,
        "files": list(files.keys()),
        "file_contents": files,
        "setup_commands": [
            f"npx create-next-app@latest {app_name} --typescript --tailwind --app",
            f"cd {app_name}",
            "npm run dev",
        ],
    })


def _generate_root_layout_code(app_name: str, typescript: bool) -> str:
    """Generate root layout code."""
    type_annotation = ": { children: React.ReactNode }" if typescript else ""
    return f'''import type {{ Metadata }} from 'next'
import './globals.css'

export const metadata: Metadata = {{
  title: '{app_name}',
  description: 'A Next.js application',
}}

export default function RootLayout({{
  children,
}}{type_annotation}) {{
  return (
    <html lang="en">
      <body>{{children}}</body>
    </html>
  )
}}
'''


def _generate_home_page_code(typescript: bool) -> str:
    """Generate home page code."""
    return '''export default function HomePage() {
  return (
    <main className="min-h-screen p-8">
      <h1 className="text-4xl font-bold">Welcome</h1>
      <p className="mt-4">Your Next.js application is ready.</p>
    </main>
  )
}
'''


def _generate_loading_code(feature: str = None) -> str:
    """Generate loading component code."""
    message = f"Loading {feature}..." if feature else "Loading..."
    return f'''export default function Loading() {{
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
      <span className="ml-2">{message}</span>
    </div>
  )
}}
'''


def _generate_error_code() -> str:
    """Generate error component code."""
    return '''"use client"

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h2 className="text-2xl font-bold text-red-600">Something went wrong!</h2>
      <p className="mt-2 text-gray-600">{error.message}</p>
      <button
        onClick={reset}
        className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
      >
        Try again
      </button>
    </div>
  )
}
'''


def _generate_not_found_code() -> str:
    """Generate not-found component code."""
    return '''import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h2 className="text-2xl font-bold">Not Found</h2>
      <p className="mt-2 text-gray-600">Could not find the requested resource.</p>
      <Link href="/" className="mt-4 text-blue-500 hover:underline">
        Return Home
      </Link>
    </div>
  )
}
'''


def _generate_api_lib_code(typescript: bool) -> str:
    """Generate API library code."""
    return '''const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`)
  }

  return res.json()
}
'''


def _generate_feature_page_code(feature: str, typescript: bool) -> str:
    """Generate feature page code."""
    component_name = _to_pascal_case(feature)
    return f'''import {{ fetchApi }} from '@/lib/api'

export default async function {component_name}Page() {{
  // const data = await fetchApi('/api/{feature}')

  return (
    <main className="min-h-screen p-8">
      <h1 className="text-2xl font-bold">{component_name}</h1>
      {{/* Add your content here */}}
    </main>
  )
}}
'''


def _generate_types_code(features: list[str]) -> str:
    """Generate TypeScript types."""
    return '''// Add your types here

export interface ApiResponse<T> {
  data: T
  error?: string
}
'''


@mcp.tool()
async def nextjs_generate_page(
    route: str,
    component_type: str = "server",
    api_endpoint: Optional[str] = None,
    cache_option: str = "no-store",
) -> str:
    """
    Generate a Next.js page component.

    Args:
        route: Route path (e.g., /todos, /todos/[id])
        component_type: server or client
        api_endpoint: API endpoint for data fetching
        cache_option: Fetch cache option

    Returns:
        JSON with generated page code
    """
    _input = GeneratePageInput(
        route=route,
        component_type=ComponentType(component_type),
        api_endpoint=api_endpoint,
        cache_option=FetchCacheOption(cache_option),
    )

    component_name = _to_pascal_case(route)
    is_dynamic = _is_dynamic_route(route)
    params = _extract_params(route)
    file_path = f"{_route_to_path(route)}/page.tsx"

    if component_type == "client":
        code = _generate_client_page(component_name, route)
    else:
        code = _generate_server_page(component_name, route, api_endpoint, cache_option, is_dynamic, params)

    return json.dumps({
        "success": True,
        "code": code,
        "file_path": file_path,
        "component_type": component_type,
        "is_dynamic": is_dynamic,
        "params": params,
    })


def _generate_server_page(
    component_name: str,
    route: str,
    api_endpoint: Optional[str],
    cache_option: str,
    is_dynamic: bool,
    params: list[str],
) -> str:
    """Generate server component page."""
    params_type = ""
    params_destructure = ""
    if is_dynamic and params:
        params_type = f"{{ params }}: {{ params: {{ {', '.join(f'{p}: string' for p in params)} }} }}"
        params_destructure = f"  const {{ {', '.join(params)} }} = params\n"

    fetch_code = ""
    if api_endpoint:
        fetch_code = f'''
  const res = await fetch('{api_endpoint}', {{
    cache: '{cache_option}'
  }})
  const data = await res.json()
'''

    return f'''export default async function {component_name}Page({params_type}) {{
{params_destructure}{fetch_code}
  return (
    <main className="min-h-screen p-8">
      <h1 className="text-2xl font-bold">{component_name}</h1>
      {{/* Add your content here */}}
    </main>
  )
}}
'''


def _generate_client_page(component_name: str, route: str) -> str:
    """Generate client component page."""
    return f'''"use client"

import {{ useState, useEffect }} from 'react'

export default function {component_name}Page() {{
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {{
    // Fetch data here
    setLoading(false)
  }}, [])

  if (loading) return <div>Loading...</div>

  return (
    <main className="min-h-screen p-8">
      <h1 className="text-2xl font-bold">{component_name}</h1>
      {{/* Add your interactive content here */}}
    </main>
  )
}}
'''


@mcp.tool()
async def nextjs_generate_layout(
    route: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
) -> str:
    """
    Generate a Next.js layout component.

    Args:
        route: Route path for the layout
        title: Page title for metadata
        description: Page description for metadata

    Returns:
        JSON with generated layout code
    """
    _input = GenerateLayoutInput(route=route, title=title, description=description)

    is_root = route == "/"
    file_path = f"{_route_to_path(route)}/layout.tsx"

    if is_root:
        code = _generate_root_layout(title or "My App", description)
    else:
        code = _generate_nested_layout(route, title, description)

    return json.dumps({
        "success": True,
        "code": code,
        "file_path": file_path,
        "is_root": is_root,
    })


def _generate_root_layout(title: str, description: Optional[str]) -> str:
    """Generate root layout with html/body."""
    desc_line = f"\n  description: '{description}'," if description else ""
    return f'''import type {{ Metadata }} from 'next'
import './globals.css'

export const metadata: Metadata = {{
  title: '{title}',{desc_line}
}}

export default function RootLayout({{
  children,
}}: {{
  children: React.ReactNode
}}) {{
  return (
    <html lang="en">
      <body>{{children}}</body>
    </html>
  )
}}
'''


def _generate_nested_layout(route: str, title: Optional[str], description: Optional[str]) -> str:
    """Generate nested layout without html/body."""
    component_name = _to_pascal_case(route)
    metadata_block = ""
    if title:
        desc_line = f"\n  description: '{description}'," if description else ""
        metadata_block = f'''
export const metadata: Metadata = {{
  title: '{title}',{desc_line}
}}
'''

    return f'''import type {{ Metadata }} from 'next'
{metadata_block}
export default function {component_name}Layout({{
  children,
}}: {{
  children: React.ReactNode
}}) {{
  return (
    <section>
      {{/* Add navigation or shared UI here */}}
      {{children}}
    </section>
  )
}}
'''


@mcp.tool()
async def nextjs_generate_server_action(
    action_name: str,
    api_endpoint: str,
    method: str = "POST",
    revalidate_path: Optional[str] = None,
    redirect_to: Optional[str] = None,
) -> str:
    """
    Generate a Next.js server action.

    Args:
        action_name: Action function name
        api_endpoint: Backend API endpoint
        method: HTTP method
        revalidate_path: Path to revalidate after action
        redirect_to: Path to redirect after action

    Returns:
        JSON with generated server action code
    """
    _input = GenerateServerActionInput(
        action_name=action_name,
        api_endpoint=api_endpoint,
        method=method,
        revalidate_path=revalidate_path,
        redirect_to=redirect_to,
    )

    imports = ["'use server'", ""]
    if revalidate_path:
        imports.append("import { revalidatePath } from 'next/cache'")
    if redirect_to:
        imports.append("import { redirect } from 'next/navigation'")

    post_actions = []
    if revalidate_path:
        post_actions.append(f"  revalidatePath('{revalidate_path}')")
    if redirect_to:
        post_actions.append(f"  redirect('{redirect_to}')")

    post_action_code = "\n" + "\n".join(post_actions) if post_actions else ""

    code = f'''{chr(10).join(imports)}

export async function {action_name}(formData: FormData) {{
  const API_BASE = process.env.API_URL || 'http://localhost:8000'

  // Extract form data
  const data = Object.fromEntries(formData.entries())

  const res = await fetch(`${{API_BASE}}{api_endpoint}`, {{
    method: '{method}',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify(data),
  }})

  if (!res.ok) {{
    throw new Error('Failed to {action_name}')
  }}
{post_action_code}
  return res.json()
}}
'''

    return json.dumps({
        "success": True,
        "code": code,
        "action_name": action_name,
        "method": method,
        "revalidate_path": revalidate_path,
        "redirect_to": redirect_to,
    })


@mcp.tool()
async def nextjs_generate_api_client(
    resource_name: str,
    base_url: str,
    endpoints: list[str] = None,
    use_env_var: bool = True,
) -> str:
    """
    Generate an API client for a resource.

    Args:
        resource_name: Resource name (e.g., todos)
        base_url: Base URL for API
        endpoints: Endpoints to generate
        use_env_var: Use environment variable for base URL

    Returns:
        JSON with generated API client code
    """
    endpoints = endpoints or ["list", "get", "create", "update", "delete"]
    _input = GenerateApiClientInput(
        resource_name=resource_name,
        base_url=base_url,
        endpoints=endpoints,
        use_env_var=use_env_var,
    )

    base_url_code = "process.env.NEXT_PUBLIC_API_URL || " if use_env_var else ""
    resource_pascal = resource_name.capitalize()

    methods = []

    if "list" in endpoints:
        methods.append(f'''  list: async (): Promise<{resource_pascal}[]> => {{
    const res = await fetch(`${{API_BASE}}/api/{resource_name}`)
    if (!res.ok) throw new Error('Failed to fetch {resource_name}')
    return res.json()
  }}''')

    if "get" in endpoints:
        methods.append(f'''  get: async (id: number): Promise<{resource_pascal}> => {{
    const res = await fetch(`${{API_BASE}}/api/{resource_name}/${{id}}`)
    if (!res.ok) throw new Error('Failed to fetch {resource_name}')
    return res.json()
  }}''')

    if "create" in endpoints:
        methods.append(f'''  create: async (data: {resource_pascal}Create): Promise<{resource_pascal}> => {{
    const res = await fetch(`${{API_BASE}}/api/{resource_name}`, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(data),
    }})
    if (!res.ok) throw new Error('Failed to create {resource_name}')
    return res.json()
  }}''')

    if "update" in endpoints:
        methods.append(f'''  update: async (id: number, data: {resource_pascal}Update): Promise<{resource_pascal}> => {{
    const res = await fetch(`${{API_BASE}}/api/{resource_name}/${{id}}`, {{
      method: 'PUT',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(data),
    }})
    if (!res.ok) throw new Error('Failed to update {resource_name}')
    return res.json()
  }}''')

    if "delete" in endpoints:
        methods.append(f'''  delete: async (id: number): Promise<void> => {{
    const res = await fetch(`${{API_BASE}}/api/{resource_name}/${{id}}`, {{
      method: 'DELETE',
    }})
    if (!res.ok) throw new Error('Failed to delete {resource_name}')
  }}''')

    methods_joined = ",\n".join(methods)

    code = f'''const API_BASE = {base_url_code}'{base_url}'

// Types - define these in types/{resource_name}.ts
interface {resource_pascal} {{
  id: number
  // Add fields
}}

interface {resource_pascal}Create {{
  // Add create fields
}}

interface {resource_pascal}Update {{
  // Add update fields
}}

export const {resource_name}Api = {{
{methods_joined}
}}
'''

    return json.dumps({
        "success": True,
        "code": code,
        "resource_name": resource_name,
        "endpoints": endpoints,
        "file_path": f"lib/{resource_name}-api.ts",
    })


@mcp.tool()
async def nextjs_generate_loading_error(
    route: str,
    include_not_found: bool = False,
    loading_message: str = "Loading...",
) -> str:
    """
    Generate loading and error state components.

    Args:
        route: Route path
        include_not_found: Include not-found.tsx
        loading_message: Loading message

    Returns:
        JSON with generated component code
    """
    _input = GenerateLoadingErrorInput(
        route=route,
        include_not_found=include_not_found,
        loading_message=loading_message,
    )

    base_path = _route_to_path(route)
    component_name = _to_pascal_case(route)

    loading_code = f'''export default function Loading() {{
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
      <span className="ml-2">{loading_message}</span>
    </div>
  )
}}
'''

    error_code = f'''"use client"

export default function Error({{
  error,
  reset,
}}: {{
  error: Error & {{ digest?: string }}
  reset: () => void
}}) {{
  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h2 className="text-2xl font-bold text-red-600">Failed to load {component_name}</h2>
      <p className="mt-2 text-gray-600">{{error.message}}</p>
      <button
        onClick={{reset}}
        className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
      >
        Try again
      </button>
    </div>
  )
}}
'''

    result = {
        "success": True,
        "loading_code": loading_code,
        "loading_path": f"{base_path}/loading.tsx",
        "error_code": error_code,
        "error_path": f"{base_path}/error.tsx",
    }

    if include_not_found:
        not_found_code = f'''import Link from 'next/link'

export default function NotFound() {{
  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h2 className="text-2xl font-bold">{component_name} Not Found</h2>
      <p className="mt-2 text-gray-600">Could not find the requested resource.</p>
      <Link href="{route}" className="mt-4 text-blue-500 hover:underline">
        Return to {component_name}
      </Link>
    </div>
  )
}}
'''
        result["not_found_code"] = not_found_code
        result["not_found_path"] = f"{base_path}/not-found.tsx"

    return json.dumps(result)


@mcp.tool()
async def nextjs_validate_structure(files: list[str]) -> str:
    """
    Validate Next.js app structure.

    Args:
        files: List of file paths in the app

    Returns:
        JSON with validation results
    """
    _input = ValidateStructureInput(files=files)

    issues: list[str] = []
    warnings: list[str] = []

    # Check for required files
    has_root_layout = any("app/layout" in f for f in files)
    has_root_page = any("app/page" in f for f in files)
    has_loading = any("loading" in f for f in files)
    has_error = any("error" in f for f in files)

    if not has_root_layout:
        issues.append("Missing app/layout.tsx - root layout is required")

    if not has_root_page:
        issues.append("Missing app/page.tsx - root page is required")

    if not has_loading:
        warnings.append("Consider adding loading.tsx for better UX")

    if not has_error:
        warnings.append("Consider adding error.tsx for error handling")

    # Check for common patterns
    has_lib = any("lib/" in f for f in files)
    if not has_lib:
        warnings.append("Consider adding lib/ directory for shared utilities")

    valid = len(issues) == 0

    return json.dumps({
        "valid": valid,
        "issues": issues,
        "warnings": warnings,
        "files_checked": len(files),
        "checks_performed": [
            "root_layout_check",
            "root_page_check",
            "loading_state_check",
            "error_boundary_check",
            "lib_directory_check",
        ],
    })


@mcp.tool()
async def nextjs_diagnose_issues(
    error_message: str,
    code_snippet: Optional[str] = None,
) -> str:
    """
    Diagnose common Next.js issues.

    Args:
        error_message: Error message to diagnose
        code_snippet: Related code snippet

    Returns:
        JSON with diagnosis and suggestions
    """
    _input = DiagnoseIssuesInput(error_message=error_message, code_snippet=code_snippet)

    error_lower = error_message.lower()

    diagnosis = ""
    suggestions: list[str] = []

    # useState/useEffect in server component
    if "usestate" in error_lower or "useeffect" in error_lower:
        if "client" in error_lower or "server" in error_lower:
            diagnosis = "React hooks (useState, useEffect) can only be used in Client Components"
            suggestions = [
                "Add 'use client' directive at the top of the file",
                "Move interactive logic to a separate client component",
                "Consider using server actions for form handling instead",
            ]

    # Hydration mismatch
    elif "hydration" in error_lower:
        diagnosis = "Hydration mismatch - server and client HTML don't match"
        suggestions = [
            "Ensure consistent rendering between server and client",
            "Avoid using browser-only APIs (window, document) in initial render",
            "Use useEffect for browser-only code",
            "Check for time-dependent values (Date.now(), Math.random())",
        ]

    # Async in client component
    elif "async" in error_lower and "client" in error_lower:
        diagnosis = "Async/await cannot be used directly in Client Components"
        suggestions = [
            "Move data fetching to a Server Component",
            "Use useEffect with fetch for client-side data fetching",
            "Consider using SWR or React Query for client-side fetching",
        ]

    # Module not found
    elif "module not found" in error_lower or "cannot find module" in error_lower:
        diagnosis = "Module import error - package or file not found"
        suggestions = [
            "Check if the package is installed (npm install <package>)",
            "Verify import path is correct",
            "Use @ alias for app-relative imports",
            "Check tsconfig.json paths configuration",
        ]

    # Dynamic server usage
    elif "dynamic server" in error_lower:
        diagnosis = "Dynamic server usage in static generation context"
        suggestions = [
            "Add export const dynamic = 'force-dynamic' to the page",
            "Use generateStaticParams for static generation with dynamic routes",
            "Check for usage of cookies(), headers(), or searchParams",
        ]

    # Generic/Unknown
    else:
        diagnosis = "Next.js error detected"
        suggestions = [
            "Check the full stack trace for more details",
            "Verify the component is in the correct directory",
            "Review Next.js App Router documentation",
            "Check for TypeScript type errors",
        ]

    return json.dumps({
        "success": True,
        "diagnosis": diagnosis,
        "suggestions": suggestions,
        "error_type": error_message.split(":")[0] if ":" in error_message else "Unknown",
    })


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    mcp.run(transport="stdio")
