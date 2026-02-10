"""
LinkedIn MCP Server — exposes LinkedIn automation tools via FastMCP (stdio transport).

Tools:
    linkedin_post               Post content to LinkedIn
    linkedin_get_profile        Get profile information
    linkedin_get_feed          Get recent posts from feed
    linkedin_share_article      Share an article with commentary
    linkedin_send_message       Send a direct message (requires connection)
    linkedin_search_people      Search for people by criteria
    linkedin_list_connections   List user's connections
    linkedin_get_analytics      Get post analytics (views, likes, comments)

Requires:
    - LinkedIn API credentials (OAuth 2.0)
    - Stored in OS keyring or environment variables
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("linkedin_mcp")

# ---------------------------------------------------------------------------
# Security & Configuration
# ---------------------------------------------------------------------------


def _check_dangerous_content(text: str) -> str:
    """Basic content safety check."""
    dangerous_patterns = ["</script>", "<script", "javascript:", "onerror="]
    text_lower = text.lower()
    for pattern in dangerous_patterns:
        if pattern in text_lower:
            raise ValueError(f"Potentially dangerous content detected: {pattern}")
    return text


def _load_credentials() -> dict[str, str]:
    """
    Load LinkedIn credentials from environment or keyring.

    Expected environment variables:
    - LINKEDIN_ACCESS_TOKEN: OAuth 2.0 access token
    - LINKEDIN_USER_ID: LinkedIn user/organization ID

    Returns:
        Dictionary with access_token and user_id
    """
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    user_id = os.getenv("LINKEDIN_USER_ID")

    if not access_token or not user_id:
        return {
            "error": "LinkedIn credentials not configured",
            "setup": "Set LINKEDIN_ACCESS_TOKEN and LINKEDIN_USER_ID environment variables",
        }

    return {"access_token": access_token, "user_id": user_id}


# ---------------------------------------------------------------------------
# Pydantic Input Models
# ---------------------------------------------------------------------------


class LinkedInPostInput(BaseModel):
    """Input for linkedin_post."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    content: str = Field(
        ...,
        min_length=1,
        max_length=3000,
        description="Post content (max 3000 characters)",
    )
    visibility: Literal["PUBLIC", "CONNECTIONS", "LOGGED_IN"] = Field(
        default="PUBLIC", description="Post visibility level"
    )
    link_url: Optional[str] = Field(None, description="Optional URL to attach to post")
    image_path: Optional[str] = Field(
        None, description="Optional path to image file to attach"
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        return _check_dangerous_content(v)


class LinkedInGetProfileInput(BaseModel):
    """Input for linkedin_get_profile."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    profile_id: Optional[str] = Field(
        None, description="LinkedIn profile ID (defaults to authenticated user)"
    )


class LinkedInGetFeedInput(BaseModel):
    """Input for linkedin_get_feed."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    count: int = Field(
        default=10, ge=1, le=50, description="Number of posts to retrieve (1-50)"
    )
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class LinkedInShareArticleInput(BaseModel):
    """Input for linkedin_share_article."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    article_url: str = Field(
        ..., min_length=1, description="URL of the article to share"
    )
    commentary: str = Field(
        ..., min_length=1, max_length=3000, description="Your commentary on the article"
    )
    visibility: Literal["PUBLIC", "CONNECTIONS", "LOGGED_IN"] = Field(
        default="PUBLIC", description="Post visibility level"
    )

    @field_validator("commentary")
    @classmethod
    def validate_commentary(cls, v: str) -> str:
        return _check_dangerous_content(v)


class LinkedInSendMessageInput(BaseModel):
    """Input for linkedin_send_message."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    recipient_id: str = Field(
        ..., min_length=1, description="LinkedIn ID of message recipient"
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="Message content (max 8000 characters)",
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        return _check_dangerous_content(v)


class LinkedInSearchPeopleInput(BaseModel):
    """Input for linkedin_search_people."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    keywords: str = Field(..., min_length=1, description="Search keywords")
    filters: Optional[dict[str, str]] = Field(
        None, description="Optional filters (title, company, location, etc.)"
    )
    count: int = Field(default=10, ge=1, le=50, description="Number of results (1-50)")


class LinkedInListConnectionsInput(BaseModel):
    """Input for linkedin_list_connections."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    count: int = Field(
        default=50, ge=1, le=500, description="Number of connections to retrieve"
    )
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class LinkedInGetAnalyticsInput(BaseModel):
    """Input for linkedin_get_analytics."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    post_id: str = Field(..., min_length=1, description="LinkedIn post ID or URN")


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def linkedin_post(input: LinkedInPostInput) -> dict:
    """
    Post content to LinkedIn.

    This tool creates a new post on the authenticated user's LinkedIn profile.
    Supports text, links, and images. Requires HITL approval for actual posting.

    Returns:
        Dictionary with post_id, status, and preview_url
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    # In production, this would call LinkedIn API
    # For now, return mock response with approval requirement

    return {
        "success": True,
        "status": "pending_approval",
        "post_preview": {
            "content": input.content,
            "visibility": input.visibility,
            "link_url": input.link_url,
            "image_path": input.image_path,
            "author": creds["user_id"],
        },
        "approval_required": True,
        "message": "Post queued for approval. Move to /Approved to publish.",
        "mock_mode": True,
        "note": "TODO: Implement actual LinkedIn API integration with OAuth 2.0",
    }


@mcp.tool()
def linkedin_get_profile(input: LinkedInGetProfileInput) -> dict:
    """
    Get LinkedIn profile information.

    Retrieves profile details for the specified user or authenticated user.

    Returns:
        Dictionary with profile information
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    profile_id = input.profile_id or creds["user_id"]

    return {
        "success": True,
        "profile": {
            "id": profile_id,
            "name": "[Profile Name]",
            "headline": "[Professional Headline]",
            "location": "[Location]",
            "connections": 500,
            "followers": 1000,
        },
        "mock_mode": True,
        "note": "TODO: Implement actual LinkedIn API integration",
    }


@mcp.tool()
def linkedin_get_feed(input: LinkedInGetFeedInput) -> dict:
    """
    Get recent posts from LinkedIn feed.

    Retrieves posts from the user's LinkedIn feed for content aggregation
    and summarization.

    Returns:
        List of feed posts with content, author, and engagement metrics
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    return {
        "success": True,
        "posts": [
            {
                "id": f"post_{i}",
                "author": f"Author {i}",
                "content": f"Sample post content {i}",
                "likes": 10 * i,
                "comments": 2 * i,
                "timestamp": datetime.now().isoformat(),
            }
            for i in range(1, input.count + 1)
        ],
        "count": input.count,
        "offset": input.offset,
        "mock_mode": True,
        "note": "TODO: Implement actual LinkedIn API integration",
    }


@mcp.tool()
def linkedin_share_article(input: LinkedInShareArticleInput) -> dict:
    """
    Share an article on LinkedIn with commentary.

    Creates a post sharing an external article with your commentary.
    Requires HITL approval for actual posting.

    Returns:
        Dictionary with share status and preview
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    return {
        "success": True,
        "status": "pending_approval",
        "share_preview": {
            "article_url": input.article_url,
            "commentary": input.commentary,
            "visibility": input.visibility,
            "author": creds["user_id"],
        },
        "approval_required": True,
        "message": "Article share queued for approval. Move to /Approved to publish.",
        "mock_mode": True,
        "note": "TODO: Implement actual LinkedIn API integration",
    }


@mcp.tool()
def linkedin_send_message(input: LinkedInSendMessageInput) -> dict:
    """
    Send a direct message on LinkedIn.

    Sends a private message to a LinkedIn connection. Requires HITL approval
    for actual sending.

    Returns:
        Dictionary with message status
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    return {
        "success": True,
        "status": "pending_approval",
        "message_preview": {
            "recipient_id": input.recipient_id,
            "message": input.message,
            "sender": creds["user_id"],
        },
        "approval_required": True,
        "message": "Message queued for approval. Move to /Approved to send.",
        "mock_mode": True,
        "note": "TODO: Implement actual LinkedIn API integration",
    }


@mcp.tool()
def linkedin_search_people(input: LinkedInSearchPeopleInput) -> dict:
    """
    Search for people on LinkedIn.

    Searches LinkedIn for people matching keywords and filters.
    Useful for finding potential connections or prospects.

    Returns:
        List of search results with profile summaries
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    return {
        "success": True,
        "results": [
            {
                "id": f"person_{i}",
                "name": f"Person {i}",
                "headline": f"Professional headline {i}",
                "location": "Location",
                "is_connection": False,
            }
            for i in range(1, input.count + 1)
        ],
        "query": input.keywords,
        "filters": input.filters,
        "count": input.count,
        "mock_mode": True,
        "note": "TODO: Implement actual LinkedIn API integration",
    }


@mcp.tool()
def linkedin_list_connections(input: LinkedInListConnectionsInput) -> dict:
    """
    List user's LinkedIn connections.

    Retrieves the authenticated user's LinkedIn connections for
    network analysis and relationship management.

    Returns:
        List of connections with profile information
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    return {
        "success": True,
        "connections": [
            {
                "id": f"connection_{i}",
                "name": f"Connection {i}",
                "headline": f"Professional at Company {i}",
                "connected_at": datetime.now().isoformat(),
            }
            for i in range(1, min(input.count, 10) + 1)
        ],
        "count": input.count,
        "offset": input.offset,
        "total_connections": 500,
        "mock_mode": True,
        "note": "TODO: Implement actual LinkedIn API integration",
    }


@mcp.tool()
def linkedin_get_analytics(input: LinkedInGetAnalyticsInput) -> dict:
    """
    Get analytics for a LinkedIn post.

    Retrieves engagement metrics (views, likes, comments, shares) for
    a specific post. Useful for measuring content performance.

    Returns:
        Dictionary with detailed engagement metrics
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    return {
        "success": True,
        "post_id": input.post_id,
        "analytics": {
            "impressions": 1234,
            "unique_viewers": 987,
            "likes": 45,
            "comments": 12,
            "shares": 8,
            "click_through_rate": 0.023,
            "engagement_rate": 0.067,
        },
        "time_period": "all_time",
        "mock_mode": True,
        "note": "TODO: Implement actual LinkedIn API integration",
    }


# ---------------------------------------------------------------------------
# Server Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
