"""
Meta Social MCP Server — exposes Facebook & Instagram tools via FastMCP (stdio transport).

Tools:
    meta_facebook_post          Post to Facebook page or profile
    meta_facebook_get_feed      Get recent Facebook posts
    meta_facebook_get_insights  Get page/post insights
    meta_instagram_post         Post to Instagram (photo/video/story)
    meta_instagram_get_feed     Get Instagram feed posts
    meta_instagram_get_insights Get Instagram account insights
    meta_facebook_schedule_post Schedule future Facebook post
    meta_instagram_schedule_post Schedule future Instagram post
    meta_generate_summary       Generate summary from social media activity

Requires:
    - Facebook/Instagram Graph API credentials (OAuth 2.0)
    - Stored in OS keyring or environment variables
"""

import json
import os
from datetime import datetime, timedelta
from typing import Literal, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("meta_social_mcp")

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
    Load Meta API credentials from environment or keyring.

    Expected environment variables:
    - META_ACCESS_TOKEN: Facebook/Instagram Graph API access token
    - META_PAGE_ID: Facebook Page ID
    - META_INSTAGRAM_ACCOUNT_ID: Instagram Business Account ID

    Returns:
        Dictionary with credentials or error
    """
    access_token = os.getenv("META_ACCESS_TOKEN")
    page_id = os.getenv("META_PAGE_ID")
    instagram_id = os.getenv("META_INSTAGRAM_ACCOUNT_ID")

    if not access_token:
        return {
            "error": "Meta API credentials not configured",
            "setup": "Set META_ACCESS_TOKEN, META_PAGE_ID, and META_INSTAGRAM_ACCOUNT_ID environment variables",
        }

    return {
        "access_token": access_token,
        "page_id": page_id or "NOT_SET",
        "instagram_id": instagram_id or "NOT_SET",
    }


# ---------------------------------------------------------------------------
# Pydantic Input Models
# ---------------------------------------------------------------------------


class MetaFacebookPostInput(BaseModel):
    """Input for meta_facebook_post."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    message: str = Field(
        ..., min_length=1, max_length=63206, description="Post message content"
    )
    link_url: Optional[str] = Field(None, description="Optional link to attach")
    image_path: Optional[str] = Field(None, description="Optional path to image file")
    video_path: Optional[str] = Field(None, description="Optional path to video file")
    published: bool = Field(
        default=True, description="Publish immediately (True) or save as draft (False)"
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        return _check_dangerous_content(v)


class MetaFacebookGetFeedInput(BaseModel):
    """Input for meta_facebook_get_feed."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    limit: int = Field(
        default=25, ge=1, le=100, description="Number of posts to retrieve (1-100)"
    )
    since: Optional[str] = Field(
        None, description="Get posts since this date (ISO format: YYYY-MM-DD)"
    )


class MetaFacebookGetInsightsInput(BaseModel):
    """Input for meta_facebook_get_insights."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    post_id: Optional[str] = Field(
        None, description="Specific post ID (omit for page-level insights)"
    )
    metrics: list[str] = Field(
        default=["page_impressions", "page_engaged_users", "page_post_engagements"],
        description="Metrics to retrieve",
    )
    period: Literal["day", "week", "days_28"] = Field(
        default="day", description="Time period for insights"
    )


class MetaInstagramPostInput(BaseModel):
    """Input for meta_instagram_post."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    caption: str = Field(..., min_length=1, max_length=2200, description="Post caption")
    image_path: Optional[str] = Field(None, description="Path to image file")
    video_path: Optional[str] = Field(None, description="Path to video file")
    media_type: Literal["IMAGE", "VIDEO", "CAROUSEL_ALBUM", "STORIES"] = Field(
        default="IMAGE", description="Type of media post"
    )
    location_id: Optional[str] = Field(None, description="Optional location ID")
    user_tags: Optional[list[dict]] = Field(
        None, description="Optional user tags [{username: str, x: float, y: float}]"
    )

    @field_validator("caption")
    @classmethod
    def validate_caption(cls, v: str) -> str:
        return _check_dangerous_content(v)


class MetaInstagramGetFeedInput(BaseModel):
    """Input for meta_instagram_get_feed."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    limit: int = Field(
        default=25, ge=1, le=100, description="Number of posts to retrieve (1-100)"
    )


class MetaInstagramGetInsightsInput(BaseModel):
    """Input for meta_instagram_get_insights."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    post_id: Optional[str] = Field(
        None, description="Specific post ID (omit for account-level insights)"
    )
    metrics: list[str] = Field(
        default=["impressions", "reach", "engagement"],
        description="Metrics to retrieve",
    )
    period: Literal["day", "week", "days_28", "lifetime"] = Field(
        default="day", description="Time period for insights"
    )


class MetaSchedulePostInput(BaseModel):
    """Input for meta_facebook_schedule_post and meta_instagram_schedule_post."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    message: str = Field(..., min_length=1, description="Post content")
    scheduled_time: str = Field(
        ..., description="Scheduled publish time (ISO format with timezone)"
    )
    media_path: Optional[str] = Field(None, description="Optional media file path")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        return _check_dangerous_content(v)


class MetaGenerateSummaryInput(BaseModel):
    """Input for meta_generate_summary."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    platform: Literal["facebook", "instagram", "both"] = Field(
        default="both", description="Which platform(s) to summarize"
    )
    days: int = Field(
        default=7, ge=1, le=90, description="Number of days to include in summary"
    )


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def meta_facebook_post(input: MetaFacebookPostInput) -> dict:
    """
    Post content to Facebook page or profile.

    Creates a Facebook post with optional media. Requires HITL approval
    before actual posting.

    Returns:
        Post status and preview
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
        "post_preview": {
            "message": input.message,
            "link_url": input.link_url,
            "image_path": input.image_path,
            "video_path": input.video_path,
            "published": input.published,
            "page_id": creds["page_id"],
        },
        "approval_required": True,
        "message": "Facebook post queued for approval. Move to /Approved to publish.",
        "mock_mode": True,
        "note": "TODO: Implement actual Facebook Graph API integration",
    }


@mcp.tool()
def meta_facebook_get_feed(input: MetaFacebookGetFeedInput) -> dict:
    """
    Get recent Facebook posts from page.

    Retrieves recent posts for content analysis and summarization.

    Returns:
        List of Facebook posts with engagement metrics
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    mock_posts = [
        {
            "post_id": f"FB-{i}",
            "message": f"Sample Facebook post {i}",
            "created_time": (datetime.now() - timedelta(days=i)).isoformat(),
            "likes": 10 * i,
            "comments": 2 * i,
            "shares": i,
            "reach": 100 * i,
        }
        for i in range(1, min(input.limit, 10) + 1)
    ]

    return {
        "success": True,
        "posts": mock_posts,
        "count": len(mock_posts),
        "page_id": creds["page_id"],
        "mock_mode": True,
        "note": "TODO: Implement actual Facebook Graph API integration",
    }


@mcp.tool()
def meta_facebook_get_insights(input: MetaFacebookGetInsightsInput) -> dict:
    """
    Get Facebook page or post insights.

    Retrieves analytics and engagement metrics for performance tracking.

    Returns:
        Insights data with impressions, reach, and engagement
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    if input.post_id:
        insights = {
            "post_id": input.post_id,
            "impressions": 1234,
            "reach": 987,
            "engagement": 156,
            "likes": 89,
            "comments": 34,
            "shares": 23,
            "clicks": 45,
        }
    else:
        insights = {
            "page_impressions": 15000,
            "page_engaged_users": 1200,
            "page_post_engagements": 850,
            "page_fans": 5000,
            "page_fan_adds": 50,
            "page_fan_removes": 10,
        }

    return {
        "success": True,
        "insights": insights,
        "period": input.period,
        "metrics": input.metrics,
        "mock_mode": True,
        "note": "TODO: Implement actual Facebook Graph API integration",
    }


@mcp.tool()
def meta_instagram_post(input: MetaInstagramPostInput) -> dict:
    """
    Post content to Instagram.

    Creates an Instagram post (photo, video, carousel, or story).
    Requires HITL approval before actual posting.

    Returns:
        Post status and preview
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
        "post_preview": {
            "caption": input.caption,
            "image_path": input.image_path,
            "video_path": input.video_path,
            "media_type": input.media_type,
            "location_id": input.location_id,
            "user_tags": input.user_tags,
            "instagram_account_id": creds["instagram_id"],
        },
        "approval_required": True,
        "message": "Instagram post queued for approval. Move to /Approved to publish.",
        "mock_mode": True,
        "note": "TODO: Implement actual Instagram Graph API integration",
    }


@mcp.tool()
def meta_instagram_get_feed(input: MetaInstagramGetFeedInput) -> dict:
    """
    Get recent Instagram posts from account.

    Retrieves recent posts for content analysis and summarization.

    Returns:
        List of Instagram posts with engagement metrics
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    mock_posts = [
        {
            "post_id": f"IG-{i}",
            "caption": f"Sample Instagram post {i}",
            "media_type": "IMAGE" if i % 2 == 0 else "VIDEO",
            "timestamp": (datetime.now() - timedelta(days=i * 2)).isoformat(),
            "likes": 50 * i,
            "comments": 5 * i,
            "saved": 3 * i,
        }
        for i in range(1, min(input.limit, 10) + 1)
    ]

    return {
        "success": True,
        "posts": mock_posts,
        "count": len(mock_posts),
        "instagram_account_id": creds["instagram_id"],
        "mock_mode": True,
        "note": "TODO: Implement actual Instagram Graph API integration",
    }


@mcp.tool()
def meta_instagram_get_insights(input: MetaInstagramGetInsightsInput) -> dict:
    """
    Get Instagram account or post insights.

    Retrieves analytics and engagement metrics for performance tracking.

    Returns:
        Insights data with impressions, reach, and engagement
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    if input.post_id:
        insights = {
            "post_id": input.post_id,
            "impressions": 2345,
            "reach": 1876,
            "engagement": 234,
            "likes": 189,
            "comments": 45,
            "saved": 23,
            "shares": 12,
        }
    else:
        insights = {
            "impressions": 25000,
            "reach": 18000,
            "follower_count": 3500,
            "profile_views": 1200,
            "website_clicks": 150,
        }

    return {
        "success": True,
        "insights": insights,
        "period": input.period,
        "metrics": input.metrics,
        "mock_mode": True,
        "note": "TODO: Implement actual Instagram Graph API integration",
    }


@mcp.tool()
def meta_facebook_schedule_post(input: MetaSchedulePostInput) -> dict:
    """
    Schedule a future Facebook post.

    Creates a scheduled post to be published at specified time.
    Requires HITL approval.

    Returns:
        Scheduled post status and details
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
        "scheduled_post": {
            "message": input.message,
            "scheduled_time": input.scheduled_time,
            "media_path": input.media_path,
            "page_id": creds["page_id"],
        },
        "approval_required": True,
        "message": "Scheduled Facebook post queued for approval.",
        "mock_mode": True,
        "note": "TODO: Implement actual Facebook Graph API integration",
    }


@mcp.tool()
def meta_instagram_schedule_post(input: MetaSchedulePostInput) -> dict:
    """
    Schedule a future Instagram post.

    Creates a scheduled post to be published at specified time.
    Requires HITL approval.

    Returns:
        Scheduled post status and details
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
        "scheduled_post": {
            "message": input.message,
            "scheduled_time": input.scheduled_time,
            "media_path": input.media_path,
            "instagram_account_id": creds["instagram_id"],
        },
        "approval_required": True,
        "message": "Scheduled Instagram post queued for approval.",
        "mock_mode": True,
        "note": "TODO: Implement actual Instagram Graph API integration",
    }


@mcp.tool()
def meta_generate_summary(input: MetaGenerateSummaryInput) -> dict:
    """
    Generate summary from Facebook and/or Instagram activity.

    Aggregates recent posts and metrics to create an activity summary
    for CEO briefing or reporting.

    Returns:
        Summary with post counts, engagement metrics, and highlights
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    summary = {
        "period": f"Last {input.days} days",
        "generated_at": datetime.now().isoformat(),
    }

    if input.platform in ["facebook", "both"]:
        summary["facebook"] = {
            "posts_published": 15,
            "total_reach": 12000,
            "total_engagement": 850,
            "new_followers": 45,
            "top_post": {
                "message": "Sample top-performing post",
                "reach": 3500,
                "engagement": 245,
            },
        }

    if input.platform in ["instagram", "both"]:
        summary["instagram"] = {
            "posts_published": 10,
            "total_reach": 18000,
            "total_engagement": 1200,
            "new_followers": 120,
            "top_post": {
                "caption": "Sample top-performing Instagram post",
                "likes": 450,
                "comments": 89,
            },
        }

    return {
        "success": True,
        "summary": summary,
        "mock_mode": True,
        "note": "TODO: Implement actual Facebook/Instagram Graph API integration",
    }


# ---------------------------------------------------------------------------
# Server Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
