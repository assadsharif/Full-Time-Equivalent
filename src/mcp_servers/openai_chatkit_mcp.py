"""
OpenAI ChatKit MCP Server — generates chat UI components, backend setup,
React integration, theming, error handling, and session management code.

Tools:
    chatkit_generate_provider    Generate ChatKitProvider setup
    chatkit_generate_hook        Generate useChatKit hook usage
    chatkit_generate_window      Generate ChatWindow component
    chatkit_generate_custom_ui   Generate custom chat UI component
    chatkit_generate_backend     Generate backend session endpoint
    chatkit_generate_theme       Generate theme configuration
    chatkit_generate_error_boundary  Generate error boundary component
    chatkit_detect_antipatterns  Detect common ChatKit anti-patterns
    chatkit_generate_scaffold    Generate complete chat scaffold
    chatkit_generate_streaming   Generate streaming configuration
"""

import json
import re
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("openai_chatkit_mcp")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_BACKEND_TYPES = ("openai-hosted", "self-hosted")
VALID_FRAMEWORKS = ("react", "vanilla")
VALID_LANGUAGES = ("typescript", "javascript", "python")

# ---------------------------------------------------------------------------
# Anti-patterns
# ---------------------------------------------------------------------------

ANTIPATTERNS: dict[str, dict] = {
    "exposed-api-key": {
        "description": "API key exposed to frontend/client code",
        "detection": "OPENAI_API_KEY in client-side code or not using environment variables",
        "impact": "API key theft, unauthorized usage, billing abuse",
        "fix": "Keep API key server-side only, return clientSecret from session endpoint",
        "severity": "critical",
    },
    "client-side-session": {
        "description": "Creating ChatKit sessions directly in client code",
        "detection": "ChatKit.sessions.create() called in React/browser code",
        "impact": "Exposes API key, security vulnerability",
        "fix": "Create sessions server-side, return only clientSecret to client",
        "severity": "critical",
    },
    "no-error-boundary": {
        "description": "ChatKit components not wrapped in error boundary",
        "detection": "ChatKitProvider/ChatWindow without try-catch or ErrorBoundary",
        "impact": "Unhandled errors crash entire app, poor UX",
        "fix": "Wrap ChatKit components in React ErrorBoundary or use error prop",
        "severity": "high",
    },
    "blocking-ui": {
        "description": "UI blocks during message sending without loading state",
        "detection": "sendMessage() without checking/displaying isLoading",
        "impact": "Poor UX, user confusion, potential double-sends",
        "fix": "Disable input/button when isLoading=true, show loading indicator",
        "severity": "medium",
    },
    "hardcoded-workflow-id": {
        "description": "Workflow ID hardcoded in source code",
        "detection": "workflow_id as string literal instead of env variable",
        "impact": "Difficult to change environments, security risk",
        "fix": "Use process.env.WORKFLOW_ID or environment configuration",
        "severity": "medium",
    },
    "no-streaming": {
        "description": "Streaming disabled for long responses",
        "detection": "streaming: false or missing streaming config",
        "impact": "User waits for entire response, poor UX for long outputs",
        "fix": "Enable streaming: config={{ streaming: true }}",
        "severity": "low",
    },
    "missing-loading-state": {
        "description": "No visual feedback during message processing",
        "detection": "isLoading not used in component render",
        "impact": "User unsure if message was sent, may retry",
        "fix": "Show spinner/skeleton when isLoading is true",
        "severity": "medium",
    },
}

# ---------------------------------------------------------------------------
# Code templates
# ---------------------------------------------------------------------------

PROVIDER_TEMPLATE = """import {{ ChatKitProvider }} from '@openai/chatkit-react';

function App() {{
  return (
    <ChatKitProvider
      sessionEndpoint="{session_endpoint}"
      {config}
    >
      {{children}}
    </ChatKitProvider>
  );
}}

export default App;
"""

HOOK_TEMPLATE = """import {{ useChatKit }} from '@openai/chatkit-react';

function ChatComponent() {{
  const {{
    messages,       // Message[] - conversation history
    sendMessage,    // (text: string) => Promise<void>
    isLoading,      // boolean - processing state
    error,          // Error | null
    clearMessages,  // () => void - reset conversation
    retry,          // () => void - retry failed message
  }} = useChatKit();

{usage_example}

  return (
    // Your JSX here
  );
}}
"""

WINDOW_TEMPLATE = """import {{ ChatWindow }} from '@openai/chatkit-react';

function Chat() {{
  return (
    <ChatWindow
      {props}
    />
  );
}}

export default Chat;
"""

CUSTOM_UI_TEMPLATE = """import {{ useState, FormEvent }} from 'react';
import {{ useChatKit }} from '@openai/chatkit-react';

function CustomChat() {{
  const {{ messages, sendMessage, isLoading, error, retry }} = useChatKit();
  const [input, setInput] = useState('');

  const handleSubmit = async (e: FormEvent) => {{
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    await sendMessage(input);
    setInput('');
  }};

  return (
    <div className="{container_class}">
      {{/* Error display */}}
      {{error && (
        <div role="alert" className="error">
          <p>Error: {{error.message}}</p>
          <button onClick={{retry}}>Retry</button>
        </div>
      )}}

      {{/* Messages */}}
      <div className="{messages_class}">
        {{messages.map(msg => (
          <div key={{msg.id}} className={{`message ${{msg.role}}`}}>
            {{msg.content}}
          </div>
        ))}}
        {{isLoading && <div className="loading">Thinking...</div>}}
      </div>

      {{/* Input form */}}
      <form onSubmit={{handleSubmit}} className="{form_class}">
        <input
          value={{input}}
          onChange={{e => setInput(e.target.value)}}
          placeholder="{placeholder}"
          disabled={{isLoading}}
        />
        <button type="submit" disabled={{isLoading || !input.trim()}}>
          {{isLoading ? 'Sending...' : 'Send'}}
        </button>
      </form>
    </div>
  );
}}

export default CustomChat;
"""

BACKEND_OPENAI_HOSTED_TEMPLATE = """import {{ ChatKit }} from '@openai/chatkit';

const chatkit = new ChatKit({{
  apiKey: process.env.OPENAI_API_KEY!,
}});

// POST /api/session
export async function createSession(req: Request, res: Response) {{
  try {{
    const session = await chatkit.sessions.create({{
      workflow_id: process.env.WORKFLOW_ID!,
    }});

    // IMPORTANT: Only return clientSecret, never the full API key
    res.json({{
      clientSecret: session.client_secret,
      sessionId: session.id,
    }});
  }} catch (error) {{
    console.error('Session creation failed:', error);
    res.status(500).json({{ error: 'Failed to create session' }});
  }}
}}
"""

BACKEND_SELF_HOSTED_TEMPLATE = """from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai_chatkit import ChatKitServer
import os

app = FastAPI()
chatkit = ChatKitServer(api_key=os.environ["OPENAI_API_KEY"])

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        result = await chatkit.process(
            message=request.message,
            session_id=request.session_id,
        )
        return ChatResponse(
            response=result.content,
            session_id=result.session_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/session")
async def create_session():
    session = await chatkit.create_session()
    return {{"clientSecret": session.client_secret, "sessionId": session.id}}
"""

THEME_TEMPLATE = """const theme = {{
  primaryColor: '{primary_color}',
  backgroundColor: '{background_color}',
  textColor: '{text_color}',
  fontFamily: '{font_family}',
  borderRadius: '{border_radius}',
  messageBubble: {{
    user: {{
      backgroundColor: '{user_bubble_bg}',
      textColor: '{user_bubble_text}',
    }},
    assistant: {{
      backgroundColor: '{assistant_bubble_bg}',
      textColor: '{assistant_bubble_text}',
    }},
  }},
}};

<ChatWindow theme={{theme}} />
"""

ERROR_BOUNDARY_TEMPLATE = """import {{ Component, ReactNode }} from 'react';

interface Props {{
  children: ReactNode;
  fallback?: ReactNode;
}}

interface State {{
  hasError: boolean;
  error: Error | null;
}}

class ChatErrorBoundary extends Component<Props, State> {{
  constructor(props: Props) {{
    super(props);
    this.state = {{ hasError: false, error: null }};
  }}

  static getDerivedStateFromError(error: Error): State {{
    return {{ hasError: true, error }};
  }}

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {{
    console.error('ChatKit error:', error, errorInfo);
  }}

  render() {{
    if (this.state.hasError) {{
      return this.props.fallback || (
        <div role="alert" className="chat-error">
          <h2>Chat Unavailable</h2>
          <p>{{this.state.error?.message || 'An error occurred'}}</p>
          <button onClick={{() => this.setState({{ hasError: false, error: null }})}}>
            Try Again
          </button>
        </div>
      );
    }}

    return this.props.children;
  }}
}}

export default ChatErrorBoundary;

// Usage:
// <ChatErrorBoundary>
//   <ChatKitProvider sessionEndpoint="/api/session">
//     <ChatWindow />
//   </ChatKitProvider>
// </ChatErrorBoundary>
"""

STREAMING_TEMPLATE = """<ChatKitProvider
  sessionEndpoint="/api/session"
  config={{{{
    streaming: true,
    streamingOptions: {{
      onToken: (token) => {{
        // Called for each token during streaming
        console.log('Token:', token);
      }},
      onComplete: (message) => {{
        // Called when message is complete
        console.log('Complete:', message);
      }},
      onError: (error) => {{
        // Called on streaming error
        console.error('Stream error:', error);
      }},
    }},
  }}}}
>
  <ChatWindow />
</ChatKitProvider>
"""

# ---------------------------------------------------------------------------
# Pydantic input models
# ---------------------------------------------------------------------------

_CFG = ConfigDict(str_strip_whitespace=True, extra="forbid")


class ProviderInput(BaseModel):
    model_config = _CFG
    session_endpoint: str = Field(
        default="/api/session", description="Backend session endpoint"
    )
    streaming: bool = Field(default=True, description="Enable streaming responses")
    debug: bool = Field(default=False, description="Enable debug mode")


class HookInput(BaseModel):
    model_config = _CFG
    include_example: bool = Field(default=True, description="Include usage example")


class WindowInput(BaseModel):
    model_config = _CFG
    show_tool_calls: bool = Field(
        default=True, description="Display agent tool invocations"
    )
    show_timestamps: bool = Field(default=False, description="Show message timestamps")
    placeholder: str = Field(
        default="Ask anything...", description="Input placeholder text"
    )
    streaming: bool = Field(default=True, description="Enable streaming")


class CustomUIInput(BaseModel):
    model_config = _CFG
    container_class: str = Field(
        default="chat-container", description="Container CSS class"
    )
    messages_class: str = Field(
        default="messages", description="Messages container CSS class"
    )
    form_class: str = Field(default="chat-form", description="Form CSS class")
    placeholder: str = Field(
        default="Type a message...", description="Input placeholder"
    )


class BackendInput(BaseModel):
    model_config = _CFG
    backend_type: str = Field(
        default="openai-hosted", description="openai-hosted or self-hosted"
    )
    language: str = Field(
        default="typescript", description="typescript, javascript, or python"
    )

    @field_validator("backend_type")
    @classmethod
    def _check_backend(cls, v: str) -> str:
        if v not in VALID_BACKEND_TYPES:
            raise ValueError(f"backend_type must be one of {VALID_BACKEND_TYPES}")
        return v

    @field_validator("language")
    @classmethod
    def _check_lang(cls, v: str) -> str:
        if v not in VALID_LANGUAGES:
            raise ValueError(f"language must be one of {VALID_LANGUAGES}")
        return v


class ThemeInput(BaseModel):
    model_config = _CFG
    primary_color: str = Field(default="#1877f2", description="Primary accent color")
    background_color: str = Field(default="#ffffff", description="Background color")
    text_color: str = Field(default="#1c1e21", description="Text color")
    font_family: str = Field(default="Inter, sans-serif", description="Font family")
    border_radius: str = Field(default="8px", description="Border radius")
    user_bubble_bg: str = Field(
        default="#1877f2", description="User message background"
    )
    user_bubble_text: str = Field(
        default="#ffffff", description="User message text color"
    )
    assistant_bubble_bg: str = Field(
        default="#f0f2f5", description="Assistant message background"
    )
    assistant_bubble_text: str = Field(
        default="#1c1e21", description="Assistant message text color"
    )


class DetectAntipatternsInput(BaseModel):
    model_config = _CFG
    code: str = Field(..., min_length=10, description="Code to analyze")
    include_fixes: bool = Field(default=True, description="Include fix recommendations")


class ScaffoldInput(BaseModel):
    model_config = _CFG
    backend_type: str = Field(default="openai-hosted", description="Backend type")
    include_custom_ui: bool = Field(
        default=False, description="Include custom UI instead of ChatWindow"
    )
    include_theme: bool = Field(default=True, description="Include theme configuration")
    include_error_boundary: bool = Field(
        default=True, description="Include error boundary"
    )
    streaming: bool = Field(default=True, description="Enable streaming")

    @field_validator("backend_type")
    @classmethod
    def _check_backend(cls, v: str) -> str:
        if v not in VALID_BACKEND_TYPES:
            raise ValueError(f"backend_type must be one of {VALID_BACKEND_TYPES}")
        return v


class StreamingInput(BaseModel):
    model_config = _CFG
    on_token: bool = Field(default=True, description="Include onToken callback")
    on_complete: bool = Field(default=True, description="Include onComplete callback")
    on_error: bool = Field(default=True, description="Include onError callback")


# ---------------------------------------------------------------------------
# Pure generator functions
# ---------------------------------------------------------------------------


def _gen_provider(inp: ProviderInput) -> str:
    """Generate ChatKitProvider setup."""
    config_parts = []
    if inp.streaming:
        config_parts.append("streaming: true")
    if inp.debug:
        config_parts.append("debug: true")

    config_str = ""
    if config_parts:
        config_str = f"config={{{{ {', '.join(config_parts)} }}}}"

    return PROVIDER_TEMPLATE.format(
        session_endpoint=inp.session_endpoint,
        config=config_str,
    )


def _gen_hook(inp: HookInput) -> str:
    """Generate useChatKit hook usage."""
    example = ""
    if inp.include_example:
        example = """  // Example: Send message on form submit
  const handleSubmit = async (text: string) => {
    if (isLoading) return;
    try {
      await sendMessage(text);
    } catch (err) {
      console.error('Send failed:', err);
    }
  };"""

    return HOOK_TEMPLATE.format(usage_example=example)


def _gen_window(inp: WindowInput) -> str:
    """Generate ChatWindow component."""
    props = []
    if inp.show_tool_calls:
        props.append("showToolCalls={true}")
    if inp.show_timestamps:
        props.append("showTimestamps={true}")
    if inp.streaming:
        props.append("streaming={true}")
    props.append(f'placeholder="{inp.placeholder}"')

    return WINDOW_TEMPLATE.format(props="\n      ".join(props))


def _gen_custom_ui(inp: CustomUIInput) -> str:
    """Generate custom chat UI component."""
    return CUSTOM_UI_TEMPLATE.format(
        container_class=inp.container_class,
        messages_class=inp.messages_class,
        form_class=inp.form_class,
        placeholder=inp.placeholder,
    )


def _gen_backend(inp: BackendInput) -> str:
    """Generate backend session endpoint."""
    if inp.backend_type == "self-hosted" or inp.language == "python":
        return BACKEND_SELF_HOSTED_TEMPLATE

    return BACKEND_OPENAI_HOSTED_TEMPLATE


def _gen_theme(inp: ThemeInput) -> str:
    """Generate theme configuration."""
    return THEME_TEMPLATE.format(
        primary_color=inp.primary_color,
        background_color=inp.background_color,
        text_color=inp.text_color,
        font_family=inp.font_family,
        border_radius=inp.border_radius,
        user_bubble_bg=inp.user_bubble_bg,
        user_bubble_text=inp.user_bubble_text,
        assistant_bubble_bg=inp.assistant_bubble_bg,
        assistant_bubble_text=inp.assistant_bubble_text,
    )


def _gen_error_boundary() -> str:
    """Generate error boundary component."""
    return ERROR_BOUNDARY_TEMPLATE


def _detect_antipatterns(code: str, include_fixes: bool) -> list[dict]:
    """Detect anti-patterns in code."""
    findings = []

    # Check for exposed API key
    if (
        re.search(r'apiKey\s*[=:]\s*["\'][^"\']+["\']', code)
        and "process.env" not in code
    ):
        entry = {"pattern": "exposed-api-key", **ANTIPATTERNS["exposed-api-key"]}
        if not include_fixes:
            del entry["fix"]
        findings.append(entry)

    # Check for client-side session creation
    if re.search(r"chatkit\.sessions\.create", code, re.IGNORECASE) and (
        "useState" in code or "useEffect" in code
    ):
        entry = {
            "pattern": "client-side-session",
            **ANTIPATTERNS["client-side-session"],
        }
        if not include_fixes:
            del entry["fix"]
        findings.append(entry)

    # Check for missing error boundary
    if (
        "ChatKitProvider" in code
        and "ErrorBoundary" not in code
        and "error" not in code.lower()
    ):
        entry = {"pattern": "no-error-boundary", **ANTIPATTERNS["no-error-boundary"]}
        if not include_fixes:
            del entry["fix"]
        findings.append(entry)

    # Check for blocking UI
    if "sendMessage" in code and "isLoading" not in code:
        entry = {"pattern": "blocking-ui", **ANTIPATTERNS["blocking-ui"]}
        if not include_fixes:
            del entry["fix"]
        findings.append(entry)

    # Check for hardcoded workflow ID
    if re.search(r'workflow_id\s*[=:]\s*["\'][^"\']+["\']', code):
        entry = {
            "pattern": "hardcoded-workflow-id",
            **ANTIPATTERNS["hardcoded-workflow-id"],
        }
        if not include_fixes:
            del entry["fix"]
        findings.append(entry)

    # Check for missing loading state
    if "useChatKit" in code and "isLoading" not in code:
        entry = {
            "pattern": "missing-loading-state",
            **ANTIPATTERNS["missing-loading-state"],
        }
        if not include_fixes:
            del entry["fix"]
        findings.append(entry)

    return findings


def _gen_streaming(inp: StreamingInput) -> str:
    """Generate streaming configuration."""
    return STREAMING_TEMPLATE


def _gen_scaffold(inp: ScaffoldInput) -> dict:
    """Generate complete chat scaffold."""
    sections = {}

    # Backend
    backend_inp = BackendInput(
        backend_type=inp.backend_type,
        language="python" if inp.backend_type == "self-hosted" else "typescript",
    )
    sections["backend"] = _gen_backend(backend_inp)

    # Error boundary
    if inp.include_error_boundary:
        sections["error_boundary"] = _gen_error_boundary()

    # Theme
    if inp.include_theme:
        theme_inp = ThemeInput()
        sections["theme"] = _gen_theme(theme_inp)

    # Provider
    provider_inp = ProviderInput(streaming=inp.streaming)
    sections["provider"] = _gen_provider(provider_inp)

    # UI component
    if inp.include_custom_ui:
        custom_inp = CustomUIInput()
        sections["ui"] = _gen_custom_ui(custom_inp)
    else:
        window_inp = WindowInput(streaming=inp.streaming)
        sections["ui"] = _gen_window(window_inp)

    # App wrapper
    sections["app"] = """import ChatErrorBoundary from './ChatErrorBoundary';
import { ChatKitProvider } from '@openai/chatkit-react';
import Chat from './Chat';

function App() {
  return (
    <ChatErrorBoundary>
      <ChatKitProvider sessionEndpoint="/api/session" config={{ streaming: true }}>
        <Chat />
      </ChatKitProvider>
    </ChatErrorBoundary>
  );
}

export default App;
"""

    return sections


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def chatkit_generate_provider(
    session_endpoint: str = "/api/session",
    streaming: bool = True,
    debug: bool = False,
) -> str:
    """Generate ChatKitProvider setup code. Returns TypeScript/React code."""
    inp = ProviderInput(
        session_endpoint=session_endpoint, streaming=streaming, debug=debug
    )
    return json.dumps({"code": _gen_provider(inp)})


@mcp.tool()
async def chatkit_generate_hook(
    include_example: bool = True,
) -> str:
    """Generate useChatKit hook usage code. Returns TypeScript/React code."""
    inp = HookInput(include_example=include_example)
    return json.dumps({"code": _gen_hook(inp)})


@mcp.tool()
async def chatkit_generate_window(
    show_tool_calls: bool = True,
    show_timestamps: bool = False,
    placeholder: str = "Ask anything...",
    streaming: bool = True,
) -> str:
    """Generate ChatWindow component code. Returns TypeScript/React code."""
    inp = WindowInput(
        show_tool_calls=show_tool_calls,
        show_timestamps=show_timestamps,
        placeholder=placeholder,
        streaming=streaming,
    )
    return json.dumps({"code": _gen_window(inp)})


@mcp.tool()
async def chatkit_generate_custom_ui(
    container_class: str = "chat-container",
    messages_class: str = "messages",
    form_class: str = "chat-form",
    placeholder: str = "Type a message...",
) -> str:
    """Generate custom chat UI component. Returns TypeScript/React code."""
    inp = CustomUIInput(
        container_class=container_class,
        messages_class=messages_class,
        form_class=form_class,
        placeholder=placeholder,
    )
    return json.dumps({"code": _gen_custom_ui(inp)})


@mcp.tool()
async def chatkit_generate_backend(
    backend_type: str = "openai-hosted",
    language: str = "typescript",
) -> str:
    """Generate backend session endpoint code. Returns TypeScript or Python code."""
    inp = BackendInput(backend_type=backend_type, language=language)
    return json.dumps({"code": _gen_backend(inp), "language": inp.language})


@mcp.tool()
async def chatkit_generate_theme(
    primary_color: str = "#1877f2",
    background_color: str = "#ffffff",
    text_color: str = "#1c1e21",
    font_family: str = "Inter, sans-serif",
    border_radius: str = "8px",
    user_bubble_bg: str = "#1877f2",
    user_bubble_text: str = "#ffffff",
    assistant_bubble_bg: str = "#f0f2f5",
    assistant_bubble_text: str = "#1c1e21",
) -> str:
    """Generate theme configuration code. Returns TypeScript code."""
    inp = ThemeInput(
        primary_color=primary_color,
        background_color=background_color,
        text_color=text_color,
        font_family=font_family,
        border_radius=border_radius,
        user_bubble_bg=user_bubble_bg,
        user_bubble_text=user_bubble_text,
        assistant_bubble_bg=assistant_bubble_bg,
        assistant_bubble_text=assistant_bubble_text,
    )
    return json.dumps({"code": _gen_theme(inp)})


@mcp.tool()
async def chatkit_generate_error_boundary() -> str:
    """Generate error boundary component. Returns TypeScript/React code."""
    return json.dumps({"code": _gen_error_boundary()})


@mcp.tool()
async def chatkit_detect_antipatterns(
    code: str,
    include_fixes: bool = True,
) -> str:
    """Detect common ChatKit anti-patterns in code. Returns findings list."""
    inp = DetectAntipatternsInput(code=code, include_fixes=include_fixes)
    findings = _detect_antipatterns(inp.code, inp.include_fixes)
    return json.dumps({"findings": findings, "count": len(findings)})


@mcp.tool()
async def chatkit_generate_scaffold(
    backend_type: str = "openai-hosted",
    include_custom_ui: bool = False,
    include_theme: bool = True,
    include_error_boundary: bool = True,
    streaming: bool = True,
) -> str:
    """Generate complete chat scaffold with all components. Returns sections dict."""
    inp = ScaffoldInput(
        backend_type=backend_type,
        include_custom_ui=include_custom_ui,
        include_theme=include_theme,
        include_error_boundary=include_error_boundary,
        streaming=streaming,
    )
    sections = _gen_scaffold(inp)
    return json.dumps({"sections": sections})


@mcp.tool()
async def chatkit_generate_streaming(
    on_token: bool = True,
    on_complete: bool = True,
    on_error: bool = True,
) -> str:
    """Generate streaming configuration code. Returns TypeScript/React code."""
    inp = StreamingInput(on_token=on_token, on_complete=on_complete, on_error=on_error)
    return json.dumps({"code": _gen_streaming(inp)})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
