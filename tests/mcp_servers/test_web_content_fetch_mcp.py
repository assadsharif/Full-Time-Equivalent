"""Tests for web_content_fetch_mcp — error-path-first, TDD-strict.

Tests cover all 8 MCP tools:
    1. fetch_url          — General content fetch
    2. fetch_html         — HTML fetch with text extraction
    3. fetch_json         — JSON API fetch
    4. fetch_text         — Plain text fetch
    5. fetch_headers      — HEAD request for headers
    6. fetch_extract_links — Extract hyperlinks from HTML
    7. fetch_validate_url  — URL validation (format, safety)
    8. fetch_check_availability — Quick reachability check
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_servers.web_content_fetch_mcp import (
    mcp,
    FetchUrlInput,
    FetchHtmlInput,
    FetchJsonInput,
    FetchTextInput,
    FetchHeadersInput,
    FetchExtractLinksInput,
    FetchValidateUrlInput,
    FetchCheckAvailabilityInput,
    _is_private_url,
    _validate_url_safety,
)


def _parse(raw: str) -> dict:
    return json.loads(raw)


# ===================================================================
# Section 1: Server Registration
# ===================================================================


class TestServerRegistration:
    """Verify FastMCP server metadata."""

    def test_server_name(self):
        assert mcp.name == "web_content_fetch_mcp"

    def test_tool_count(self):
        tools = mcp._tool_manager._tools
        assert len(tools) == 8, f"Expected 8 tools, got {len(tools)}: {list(tools.keys())}"

    def test_all_tool_names_present(self):
        tools = set(mcp._tool_manager._tools.keys())
        expected = {
            "fetch_url",
            "fetch_html",
            "fetch_json",
            "fetch_text",
            "fetch_headers",
            "fetch_extract_links",
            "fetch_validate_url",
            "fetch_check_availability",
        }
        assert tools == expected


# ===================================================================
# Section 2: Input Validation (error paths first)
# ===================================================================


class TestInputValidation:
    """Validate Pydantic input models reject bad data."""

    # --- FetchUrlInput ---

    def test_fetch_url_empty_rejected(self):
        with pytest.raises(Exception):
            FetchUrlInput(url="")

    def test_fetch_url_not_http_rejected(self):
        with pytest.raises(Exception):
            FetchUrlInput(url="ftp://files.example.com/data")

    def test_fetch_url_extra_fields_rejected(self):
        with pytest.raises(Exception):
            FetchUrlInput(url="https://example.com", unknown_field="bad")

    def test_fetch_url_valid_https(self):
        inp = FetchUrlInput(url="https://example.com")
        assert inp.url == "https://example.com"

    def test_fetch_url_valid_http(self):
        inp = FetchUrlInput(url="http://example.com")
        assert inp.url == "http://example.com"

    # --- FetchHtmlInput ---

    def test_fetch_html_empty_rejected(self):
        with pytest.raises(Exception):
            FetchHtmlInput(url="")

    def test_fetch_html_not_http_rejected(self):
        with pytest.raises(Exception):
            FetchHtmlInput(url="file:///etc/passwd")

    # --- FetchJsonInput ---

    def test_fetch_json_empty_rejected(self):
        with pytest.raises(Exception):
            FetchJsonInput(url="")

    # --- FetchTextInput ---

    def test_fetch_text_empty_rejected(self):
        with pytest.raises(Exception):
            FetchTextInput(url="")

    # --- FetchHeadersInput ---

    def test_fetch_headers_empty_rejected(self):
        with pytest.raises(Exception):
            FetchHeadersInput(url="")

    # --- FetchExtractLinksInput ---

    def test_extract_links_empty_rejected(self):
        with pytest.raises(Exception):
            FetchExtractLinksInput(url="")

    # --- FetchValidateUrlInput ---

    def test_validate_url_empty_rejected(self):
        with pytest.raises(Exception):
            FetchValidateUrlInput(url="")

    # --- FetchCheckAvailabilityInput ---

    def test_check_availability_empty_rejected(self):
        with pytest.raises(Exception):
            FetchCheckAvailabilityInput(url="")


# ===================================================================
# Section 3: URL Safety Validation
# ===================================================================


class TestUrlSafety:
    """Test private IP and unsafe URL blocking."""

    def test_localhost_is_private(self):
        assert _is_private_url("http://localhost/api") is True

    def test_127_0_0_1_is_private(self):
        assert _is_private_url("http://127.0.0.1/api") is True

    def test_10_x_is_private(self):
        assert _is_private_url("http://10.0.0.1/api") is True

    def test_192_168_is_private(self):
        assert _is_private_url("http://192.168.1.1/api") is True

    def test_172_16_is_private(self):
        assert _is_private_url("http://172.16.0.1/api") is True

    def test_0_0_0_0_is_private(self):
        assert _is_private_url("http://0.0.0.0/api") is True

    def test_public_url_not_private(self):
        assert _is_private_url("https://example.com") is False

    def test_file_scheme_rejected(self):
        errors = _validate_url_safety("file:///etc/passwd")
        assert len(errors) > 0

    def test_ftp_scheme_rejected(self):
        errors = _validate_url_safety("ftp://files.example.com")
        assert len(errors) > 0

    def test_private_ip_rejected(self):
        errors = _validate_url_safety("http://192.168.1.1/api")
        assert len(errors) > 0

    def test_public_https_valid(self):
        errors = _validate_url_safety("https://example.com")
        assert len(errors) == 0

    def test_missing_scheme_rejected(self):
        errors = _validate_url_safety("example.com")
        assert len(errors) > 0


# ===================================================================
# Section 4: fetch_url
# ===================================================================


def _mock_response(status_code=200, content=b"Hello World", headers=None):
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = content.decode("utf-8") if isinstance(content, bytes) else content
    resp.content = content if isinstance(content, bytes) else content.encode("utf-8")
    resp.headers = headers or {"content-type": "text/html; charset=utf-8"}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=MagicMock(), response=resp,
        )
    return resp


class TestFetchUrl:
    """Test general URL fetch tool."""

    @pytest.mark.asyncio
    async def test_fetch_url_success(self):
        mock_resp = _mock_response(content=b"<html>Hello</html>")
        with patch("mcp_servers.web_content_fetch_mcp._http_get", new_callable=AsyncMock, return_value=mock_resp):
            result = _parse(await mcp._tool_manager._tools["fetch_url"].run(
                {"url": "https://example.com"},
            ))
            assert result["status"] == "success"
            assert "content" in result
            assert result["status_code"] == 200

    @pytest.mark.asyncio
    async def test_fetch_url_private_ip_blocked(self):
        result = _parse(await mcp._tool_manager._tools["fetch_url"].run(
            {"url": "http://127.0.0.1/secret"},
        ))
        assert result["status"] == "error"
        assert "private" in result["message"].lower() or "blocked" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_fetch_url_http_error(self):
        mock_resp = _mock_response(status_code=404)
        with patch("mcp_servers.web_content_fetch_mcp._http_get", new_callable=AsyncMock, return_value=mock_resp):
            result = _parse(await mcp._tool_manager._tools["fetch_url"].run(
                {"url": "https://example.com/missing"},
            ))
            assert result["status"] == "error"
            assert "404" in result["message"]

    @pytest.mark.asyncio
    async def test_fetch_url_with_max_length(self):
        long_content = b"x" * 1000
        mock_resp = _mock_response(content=long_content)
        with patch("mcp_servers.web_content_fetch_mcp._http_get", new_callable=AsyncMock, return_value=mock_resp):
            result = _parse(await mcp._tool_manager._tools["fetch_url"].run(
                {"url": "https://example.com", "max_length": 100},
            ))
            assert result["status"] == "success"
            assert len(result["content"]) <= 100 or result.get("truncated", False)


# ===================================================================
# Section 5: fetch_html
# ===================================================================


class TestFetchHtml:
    """Test HTML fetch tool."""

    @pytest.mark.asyncio
    async def test_fetch_html_success(self):
        html = b"<html><body><h1>Title</h1><p>Content</p></body></html>"
        mock_resp = _mock_response(content=html, headers={"content-type": "text/html"})
        with patch("mcp_servers.web_content_fetch_mcp._http_get", new_callable=AsyncMock, return_value=mock_resp):
            result = _parse(await mcp._tool_manager._tools["fetch_html"].run(
                {"url": "https://example.com"},
            ))
            assert result["status"] == "success"
            assert "html" in result

    @pytest.mark.asyncio
    async def test_fetch_html_extract_text(self):
        html = b"<html><body><h1>Title</h1><p>Content</p></body></html>"
        mock_resp = _mock_response(content=html, headers={"content-type": "text/html"})
        with patch("mcp_servers.web_content_fetch_mcp._http_get", new_callable=AsyncMock, return_value=mock_resp):
            result = _parse(await mcp._tool_manager._tools["fetch_html"].run(
                {"url": "https://example.com", "extract_text": True},
            ))
            assert result["status"] == "success"
            assert "text" in result
            assert "Title" in result["text"]

    @pytest.mark.asyncio
    async def test_fetch_html_private_blocked(self):
        result = _parse(await mcp._tool_manager._tools["fetch_html"].run(
            {"url": "http://localhost:8080/admin"},
        ))
        assert result["status"] == "error"


# ===================================================================
# Section 6: fetch_json
# ===================================================================


class TestFetchJson:
    """Test JSON API fetch tool."""

    @pytest.mark.asyncio
    async def test_fetch_json_success(self):
        json_data = b'{"name": "test", "version": "1.0"}'
        mock_resp = _mock_response(content=json_data, headers={"content-type": "application/json"})
        mock_resp.json = MagicMock(return_value={"name": "test", "version": "1.0"})
        with patch("mcp_servers.web_content_fetch_mcp._http_get", new_callable=AsyncMock, return_value=mock_resp):
            result = _parse(await mcp._tool_manager._tools["fetch_json"].run(
                {"url": "https://api.example.com/data"},
            ))
            assert result["status"] == "success"
            assert "data" in result
            assert result["data"]["name"] == "test"

    @pytest.mark.asyncio
    async def test_fetch_json_invalid_json(self):
        mock_resp = _mock_response(content=b"not json")
        mock_resp.json = MagicMock(side_effect=json.JSONDecodeError("err", "doc", 0))
        with patch("mcp_servers.web_content_fetch_mcp._http_get", new_callable=AsyncMock, return_value=mock_resp):
            result = _parse(await mcp._tool_manager._tools["fetch_json"].run(
                {"url": "https://api.example.com/bad"},
            ))
            assert result["status"] == "error"
            assert "json" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_fetch_json_private_blocked(self):
        result = _parse(await mcp._tool_manager._tools["fetch_json"].run(
            {"url": "http://10.0.0.1/api/internal"},
        ))
        assert result["status"] == "error"


# ===================================================================
# Section 7: fetch_text
# ===================================================================


class TestFetchText:
    """Test plain text fetch tool."""

    @pytest.mark.asyncio
    async def test_fetch_text_success(self):
        mock_resp = _mock_response(content=b"Plain text content here", headers={"content-type": "text/plain"})
        with patch("mcp_servers.web_content_fetch_mcp._http_get", new_callable=AsyncMock, return_value=mock_resp):
            result = _parse(await mcp._tool_manager._tools["fetch_text"].run(
                {"url": "https://example.com/readme.txt"},
            ))
            assert result["status"] == "success"
            assert "content" in result
            assert "Plain text" in result["content"]

    @pytest.mark.asyncio
    async def test_fetch_text_private_blocked(self):
        result = _parse(await mcp._tool_manager._tools["fetch_text"].run(
            {"url": "http://192.168.0.1/config"},
        ))
        assert result["status"] == "error"


# ===================================================================
# Section 8: fetch_headers
# ===================================================================


class TestFetchHeaders:
    """Test HEAD request tool."""

    @pytest.mark.asyncio
    async def test_fetch_headers_success(self):
        mock_resp = _mock_response(
            headers={
                "content-type": "text/html",
                "content-length": "12345",
                "server": "nginx",
            },
        )
        with patch("mcp_servers.web_content_fetch_mcp._http_head", new_callable=AsyncMock, return_value=mock_resp):
            result = _parse(await mcp._tool_manager._tools["fetch_headers"].run(
                {"url": "https://example.com"},
            ))
            assert result["status"] == "success"
            assert "headers" in result
            assert result["headers"]["content-type"] == "text/html"

    @pytest.mark.asyncio
    async def test_fetch_headers_private_blocked(self):
        result = _parse(await mcp._tool_manager._tools["fetch_headers"].run(
            {"url": "http://localhost:3000"},
        ))
        assert result["status"] == "error"


# ===================================================================
# Section 9: fetch_extract_links
# ===================================================================


class TestFetchExtractLinks:
    """Test link extraction tool."""

    @pytest.mark.asyncio
    async def test_extract_links_success(self):
        html = (
            b'<html><body>'
            b'<a href="https://example.com/page1">Page 1</a>'
            b'<a href="/page2">Page 2</a>'
            b'<a href="https://other.com">Other</a>'
            b'</body></html>'
        )
        mock_resp = _mock_response(content=html, headers={"content-type": "text/html"})
        with patch("mcp_servers.web_content_fetch_mcp._http_get", new_callable=AsyncMock, return_value=mock_resp):
            result = _parse(await mcp._tool_manager._tools["fetch_extract_links"].run(
                {"url": "https://example.com"},
            ))
            assert result["status"] == "success"
            assert "links" in result
            assert len(result["links"]) >= 2

    @pytest.mark.asyncio
    async def test_extract_links_no_links(self):
        html = b"<html><body><p>No links here</p></body></html>"
        mock_resp = _mock_response(content=html, headers={"content-type": "text/html"})
        with patch("mcp_servers.web_content_fetch_mcp._http_get", new_callable=AsyncMock, return_value=mock_resp):
            result = _parse(await mcp._tool_manager._tools["fetch_extract_links"].run(
                {"url": "https://example.com"},
            ))
            assert result["status"] == "success"
            assert result["links"] == []

    @pytest.mark.asyncio
    async def test_extract_links_private_blocked(self):
        result = _parse(await mcp._tool_manager._tools["fetch_extract_links"].run(
            {"url": "http://172.16.0.1/admin"},
        ))
        assert result["status"] == "error"


# ===================================================================
# Section 10: fetch_validate_url
# ===================================================================


class TestFetchValidateUrl:
    """Test URL validation tool."""

    @pytest.mark.asyncio
    async def test_validate_public_https_valid(self):
        result = _parse(await mcp._tool_manager._tools["fetch_validate_url"].run(
            {"url": "https://example.com"},
        ))
        assert result["valid"] is True
        assert len(result.get("errors", [])) == 0

    @pytest.mark.asyncio
    async def test_validate_private_ip_invalid(self):
        result = _parse(await mcp._tool_manager._tools["fetch_validate_url"].run(
            {"url": "http://192.168.1.1/api"},
        ))
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_validate_file_scheme_invalid(self):
        result = _parse(await mcp._tool_manager._tools["fetch_validate_url"].run(
            {"url": "file:///etc/passwd"},
        ))
        assert result["valid"] is False

    @pytest.mark.asyncio
    async def test_validate_no_scheme_invalid(self):
        result = _parse(await mcp._tool_manager._tools["fetch_validate_url"].run(
            {"url": "example.com"},
        ))
        assert result["valid"] is False

    @pytest.mark.asyncio
    async def test_validate_localhost_invalid(self):
        result = _parse(await mcp._tool_manager._tools["fetch_validate_url"].run(
            {"url": "http://localhost:8000"},
        ))
        assert result["valid"] is False


# ===================================================================
# Section 11: fetch_check_availability
# ===================================================================


class TestFetchCheckAvailability:
    """Test URL availability check tool."""

    @pytest.mark.asyncio
    async def test_check_available(self):
        mock_resp = _mock_response(
            headers={"content-type": "text/html", "content-length": "5000"},
        )
        with patch("mcp_servers.web_content_fetch_mcp._http_head", new_callable=AsyncMock, return_value=mock_resp):
            result = _parse(await mcp._tool_manager._tools["fetch_check_availability"].run(
                {"url": "https://example.com"},
            ))
            assert result["status"] == "success"
            assert result["reachable"] is True
            assert result["status_code"] == 200

    @pytest.mark.asyncio
    async def test_check_unavailable(self):
        mock_resp = _mock_response(status_code=503)
        with patch("mcp_servers.web_content_fetch_mcp._http_head", new_callable=AsyncMock, return_value=mock_resp):
            result = _parse(await mcp._tool_manager._tools["fetch_check_availability"].run(
                {"url": "https://example.com"},
            ))
            assert result["status"] == "success"
            assert result["reachable"] is False

    @pytest.mark.asyncio
    async def test_check_private_blocked(self):
        result = _parse(await mcp._tool_manager._tools["fetch_check_availability"].run(
            {"url": "http://127.0.0.1:9999"},
        ))
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_check_timeout(self):
        with patch("mcp_servers.web_content_fetch_mcp._http_head", new_callable=AsyncMock, side_effect=httpx.TimeoutException("timeout")):
            result = _parse(await mcp._tool_manager._tools["fetch_check_availability"].run(
                {"url": "https://example.com"},
            ))
            assert result["status"] == "success"
            assert result["reachable"] is False
            assert "timeout" in result.get("message", "").lower()
