"""
Web Content Fetch MCP Server — fetches public web content via HTTP with
URL safety validation, content type detection, and structured responses.

Tools:
    fetch_url               General URL fetch with auto content-type detection
    fetch_html              Fetch HTML content with optional text extraction
    fetch_json              Fetch and parse JSON from API endpoints
    fetch_text              Fetch raw plain text content
    fetch_headers           HEAD request to retrieve response headers only
    fetch_extract_links     Fetch HTML page and extract all hyperlinks
    fetch_validate_url      Validate URL format, scheme, and safety
    fetch_check_availability Quick reachability check via HEAD request
"""

import json
import re
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urlparse

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("web_content_fetch_mcp")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
DEFAULT_TIMEOUT = 30.0
USER_AGENT = "MCP-WebContentFetch/1.0 (Model Context Protocol)"

PRIVATE_IP_PATTERNS = [
    re.compile(r"^127\."),
    re.compile(r"^10\."),
    re.compile(r"^172\.(1[6-9]|2\d|3[01])\."),
    re.compile(r"^192\.168\."),
    re.compile(r"^0\."),
    re.compile(r"^169\.254\."),
]

PRIVATE_HOSTNAMES = {"localhost", "0.0.0.0", "[::]", "[::1]"}

ALLOWED_SCHEMES = {"http", "https"}

# ---------------------------------------------------------------------------
# URL Safety Helpers
# ---------------------------------------------------------------------------


def _is_private_url(url: str) -> bool:
    """Check if a URL points to a private/internal address."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
    except Exception:
        return True

    hostname_lower = hostname.lower()

    if hostname_lower in PRIVATE_HOSTNAMES:
        return True

    for pattern in PRIVATE_IP_PATTERNS:
        if pattern.match(hostname_lower):
            return True

    return False


def _validate_url_safety(url: str) -> list[str]:
    """Validate URL for safety. Returns list of error strings (empty = safe)."""
    errors: list[str] = []

    try:
        parsed = urlparse(url)
    except Exception:
        return ["Invalid URL: could not parse"]

    # Scheme check
    if not parsed.scheme:
        errors.append("Missing URL scheme (must be http:// or https://)")
    elif parsed.scheme.lower() not in ALLOWED_SCHEMES:
        errors.append(
            f"Unsupported scheme '{parsed.scheme}' — only http:// and https:// allowed"
        )

    # Host check
    if not parsed.hostname:
        errors.append("Missing hostname in URL")
    elif _is_private_url(url):
        errors.append(
            f"Private/internal URL blocked: {parsed.hostname} is not publicly accessible"
        )

    return errors


def _check_url_or_error(url: str) -> str | None:
    """Return JSON error string if URL is unsafe, else None."""
    errors = _validate_url_safety(url)
    if errors:
        return json.dumps(
            {
                "status": "error",
                "message": f"URL blocked: {'; '.join(errors)}",
            }
        )
    return None


# ---------------------------------------------------------------------------
# HTTP Helpers (mockable)
# ---------------------------------------------------------------------------


async def _http_get(url: str, timeout: float = DEFAULT_TIMEOUT) -> httpx.Response:
    """Perform an async HTTP GET request."""
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        return await client.get(url)


async def _http_head(url: str, timeout: float = DEFAULT_TIMEOUT) -> httpx.Response:
    """Perform an async HTTP HEAD request."""
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        return await client.head(url)


# ---------------------------------------------------------------------------
# HTML text extraction (stdlib, no external deps)
# ---------------------------------------------------------------------------


class _TextExtractor(HTMLParser):
    """Simple HTML-to-text extractor using stdlib HTMLParser."""

    SKIP_TAGS = {"script", "style", "noscript", "head"}

    def __init__(self):
        super().__init__()
        self._text_parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs):
        if tag.lower() in self.SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str):
        if tag.lower() in self.SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str):
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self._text_parts.append(text)

    def get_text(self) -> str:
        return "\n".join(self._text_parts)


def _extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML using stdlib parser."""
    parser = _TextExtractor()
    parser.feed(html)
    return parser.get_text()


class _LinkExtractor(HTMLParser):
    """Extract all href links from HTML."""

    def __init__(self):
        super().__init__()
        self.links: list[dict] = []

    def handle_starttag(self, tag: str, attrs):
        if tag.lower() == "a":
            href = None
            text = ""
            for name, value in attrs:
                if name == "href" and value:
                    href = value
            if href:
                self.links.append({"href": href})


def _extract_links_from_html(html: str) -> list[dict]:
    """Extract all anchor href links from HTML."""
    parser = _LinkExtractor()
    parser.feed(html)
    return parser.links


# ---------------------------------------------------------------------------
# Error handler
# ---------------------------------------------------------------------------


def _handle_http_error(e: Exception) -> str:
    """Format HTTP errors into JSON error response."""
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        return json.dumps(
            {
                "status": "error",
                "message": f"HTTP {code} error fetching URL",
                "status_code": code,
            }
        )
    if isinstance(e, httpx.TimeoutException):
        return json.dumps(
            {
                "status": "error",
                "message": "Request timed out. The server did not respond within the timeout period.",
            }
        )
    if isinstance(e, httpx.ConnectError):
        return json.dumps(
            {
                "status": "error",
                "message": "Connection failed. The server may be unreachable or the hostname cannot be resolved.",
            }
        )
    return json.dumps(
        {
            "status": "error",
            "message": f"Unexpected error: {type(e).__name__}: {str(e)}",
        }
    )


# ---------------------------------------------------------------------------
# Pydantic Input Models
# ---------------------------------------------------------------------------


def _validate_http_url(v: str) -> str:
    """Validate that URL uses http or https scheme."""
    parsed = urlparse(v)
    if not parsed.scheme or parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise ValueError("URL must use http:// or https:// scheme")
    if not parsed.hostname:
        raise ValueError("URL must include a hostname")
    return v


class FetchUrlInput(BaseModel):
    """Input for fetch_url."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    url: str = Field(
        ..., min_length=1, description="URL to fetch (http:// or https://)"
    )
    max_length: Optional[int] = Field(
        None,
        ge=1,
        le=MAX_CONTENT_LENGTH,
        description="Max content length to return (truncates if exceeded)",
    )
    timeout: Optional[float] = Field(
        None,
        ge=1.0,
        le=120.0,
        description="Request timeout in seconds (default 30)",
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_http_url(v)


class FetchHtmlInput(BaseModel):
    """Input for fetch_html."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    url: str = Field(..., min_length=1, description="URL of HTML page to fetch")
    extract_text: bool = Field(False, description="Extract readable text from HTML")
    timeout: Optional[float] = Field(None, ge=1.0, le=120.0)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_http_url(v)


class FetchJsonInput(BaseModel):
    """Input for fetch_json."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    url: str = Field(..., min_length=1, description="URL of JSON API endpoint")
    timeout: Optional[float] = Field(None, ge=1.0, le=120.0)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_http_url(v)


class FetchTextInput(BaseModel):
    """Input for fetch_text."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    url: str = Field(..., min_length=1, description="URL of text content to fetch")
    max_length: Optional[int] = Field(None, ge=1, le=MAX_CONTENT_LENGTH)
    timeout: Optional[float] = Field(None, ge=1.0, le=120.0)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_http_url(v)


class FetchHeadersInput(BaseModel):
    """Input for fetch_headers."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    url: str = Field(..., min_length=1, description="URL to send HEAD request to")
    timeout: Optional[float] = Field(None, ge=1.0, le=120.0)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_http_url(v)


class FetchExtractLinksInput(BaseModel):
    """Input for fetch_extract_links."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    url: str = Field(
        ..., min_length=1, description="URL of HTML page to extract links from"
    )
    timeout: Optional[float] = Field(None, ge=1.0, le=120.0)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_http_url(v)


class FetchValidateUrlInput(BaseModel):
    """Input for fetch_validate_url."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    url: str = Field(..., min_length=1, description="URL to validate")


class FetchCheckAvailabilityInput(BaseModel):
    """Input for fetch_check_availability."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    url: str = Field(..., min_length=1, description="URL to check availability of")
    timeout: Optional[float] = Field(None, ge=1.0, le=30.0)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_http_url(v)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def fetch_url(
    url: str,
    max_length: int | None = None,
    timeout: float | None = None,
) -> str:
    """Fetch content from a public URL with auto content-type detection.

    Returns JSON: {status, url, status_code, content_type, content, truncated?}
    Blocks private/internal URLs. Read-only GET request.
    """
    err = _check_url_or_error(url)
    if err:
        return err

    try:
        resp = await _http_get(url, timeout=timeout or DEFAULT_TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        return _handle_http_error(e)

    content = resp.text
    truncated = False
    if max_length and len(content) > max_length:
        content = content[:max_length]
        truncated = True

    return json.dumps(
        {
            "status": "success",
            "url": url,
            "status_code": resp.status_code,
            "content_type": resp.headers.get("content-type", "unknown"),
            "content": content,
            "truncated": truncated,
        }
    )


@mcp.tool()
async def fetch_html(
    url: str,
    extract_text: bool = False,
    timeout: float | None = None,
) -> str:
    """Fetch an HTML page. Optionally extract readable text.

    Returns JSON: {status, url, html, text? (if extract_text=True)}
    Blocks private/internal URLs.
    """
    err = _check_url_or_error(url)
    if err:
        return err

    try:
        resp = await _http_get(url, timeout=timeout or DEFAULT_TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        return _handle_http_error(e)

    result: dict = {
        "status": "success",
        "url": url,
        "status_code": resp.status_code,
        "html": resp.text,
    }

    if extract_text:
        result["text"] = _extract_text_from_html(resp.text)

    return json.dumps(result)


@mcp.tool()
async def fetch_json(
    url: str,
    timeout: float | None = None,
) -> str:
    """Fetch and parse JSON from an API endpoint.

    Returns JSON: {status, url, data}
    Blocks private/internal URLs. Returns error if response is not valid JSON.
    """
    err = _check_url_or_error(url)
    if err:
        return err

    try:
        resp = await _http_get(url, timeout=timeout or DEFAULT_TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        return _handle_http_error(e)

    try:
        data = resp.json()
    except (json.JSONDecodeError, Exception):
        return json.dumps(
            {
                "status": "error",
                "message": "Response is not valid JSON. Use fetch_url or fetch_text for non-JSON content.",
                "url": url,
            }
        )

    return json.dumps(
        {
            "status": "success",
            "url": url,
            "data": data,
        }
    )


@mcp.tool()
async def fetch_text(
    url: str,
    max_length: int | None = None,
    timeout: float | None = None,
) -> str:
    """Fetch raw text content from a URL.

    Returns JSON: {status, url, content, truncated?}
    Blocks private/internal URLs.
    """
    err = _check_url_or_error(url)
    if err:
        return err

    try:
        resp = await _http_get(url, timeout=timeout or DEFAULT_TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        return _handle_http_error(e)

    content = resp.text
    truncated = False
    if max_length and len(content) > max_length:
        content = content[:max_length]
        truncated = True

    return json.dumps(
        {
            "status": "success",
            "url": url,
            "content": content,
            "truncated": truncated,
        }
    )


@mcp.tool()
async def fetch_headers(
    url: str,
    timeout: float | None = None,
) -> str:
    """Fetch response headers via HEAD request (no body downloaded).

    Returns JSON: {status, url, status_code, headers}
    Blocks private/internal URLs.
    """
    err = _check_url_or_error(url)
    if err:
        return err

    try:
        resp = await _http_head(url, timeout=timeout or DEFAULT_TIMEOUT)
    except Exception as e:
        return _handle_http_error(e)

    return json.dumps(
        {
            "status": "success",
            "url": url,
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
        }
    )


@mcp.tool()
async def fetch_extract_links(
    url: str,
    timeout: float | None = None,
) -> str:
    """Fetch an HTML page and extract all hyperlinks.

    Returns JSON: {status, url, links}
    Each link has: {href}
    Blocks private/internal URLs.
    """
    err = _check_url_or_error(url)
    if err:
        return err

    try:
        resp = await _http_get(url, timeout=timeout or DEFAULT_TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        return _handle_http_error(e)

    links = _extract_links_from_html(resp.text)

    return json.dumps(
        {
            "status": "success",
            "url": url,
            "links": links,
            "count": len(links),
        }
    )


@mcp.tool()
async def fetch_validate_url(
    url: str,
) -> str:
    """Validate a URL for format, scheme, and safety (no private IPs).

    Returns JSON: {valid, url, scheme, hostname, errors}
    Does NOT make any HTTP request — purely validates the URL string.
    """
    errors = _validate_url_safety(url)
    parsed = urlparse(url)

    return json.dumps(
        {
            "valid": len(errors) == 0,
            "url": url,
            "scheme": parsed.scheme or None,
            "hostname": parsed.hostname or None,
            "errors": errors,
        }
    )


@mcp.tool()
async def fetch_check_availability(
    url: str,
    timeout: float | None = None,
) -> str:
    """Check if a URL is reachable via HEAD request.

    Returns JSON: {status, url, reachable, status_code?, content_type?, message?}
    Blocks private/internal URLs.
    """
    err = _check_url_or_error(url)
    if err:
        return err

    try:
        resp = await _http_head(url, timeout=timeout or 10.0)
    except httpx.TimeoutException:
        return json.dumps(
            {
                "status": "success",
                "url": url,
                "reachable": False,
                "message": "Timeout — server did not respond within the timeout period",
            }
        )
    except Exception as e:
        return json.dumps(
            {
                "status": "success",
                "url": url,
                "reachable": False,
                "message": f"Connection failed: {type(e).__name__}",
            }
        )

    reachable = resp.status_code < 400

    return json.dumps(
        {
            "status": "success",
            "url": url,
            "reachable": reachable,
            "status_code": resp.status_code,
            "content_type": resp.headers.get("content-type", "unknown"),
        }
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
