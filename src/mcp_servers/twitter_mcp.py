"""
Twitter/X MCP Server — exposes Twitter API tools via FastMCP (stdio transport).

Tools:
    twitter_post_tweet          Post a new tweet
    twitter_post_thread         Post a thread of tweets
    twitter_get_timeline        Get user's timeline
    twitter_get_mentions        Get mentions and replies
    twitter_search_tweets       Search for tweets by keyword
    twitter_get_trends          Get trending topics
    twitter_like_tweet          Like a tweet
    twitter_retweet             Retweet a tweet
    twitter_reply_to_tweet      Reply to a tweet
    twitter_get_analytics       Get tweet analytics
    twitter_generate_summary    Generate summary from timeline/mentions

Requires:
    - Twitter API v2 credentials (OAuth 2.0)
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

mcp = FastMCP("twitter_mcp")

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
    Load Twitter API credentials from environment or keyring.

    Expected environment variables:
    - TWITTER_BEARER_TOKEN: Twitter API v2 Bearer Token
    - TWITTER_API_KEY: Twitter API Key
    - TWITTER_API_SECRET: Twitter API Secret
    - TWITTER_ACCESS_TOKEN: User Access Token
    - TWITTER_ACCESS_SECRET: User Access Token Secret

    Returns:
        Dictionary with credentials or error
    """
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_secret = os.getenv("TWITTER_ACCESS_SECRET")

    if not bearer_token or not access_token:
        return {
            "error": "Twitter API credentials not configured",
            "setup": "Set TWITTER_BEARER_TOKEN, TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, and TWITTER_ACCESS_SECRET environment variables",
        }

    return {
        "bearer_token": bearer_token,
        "api_key": api_key,
        "api_secret": api_secret,
        "access_token": access_token,
        "access_secret": access_secret,
    }


# ---------------------------------------------------------------------------
# Pydantic Input Models
# ---------------------------------------------------------------------------


class TwitterPostTweetInput(BaseModel):
    """Input for twitter_post_tweet."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    text: str = Field(
        ..., min_length=1, max_length=280, description="Tweet text (max 280 characters)"
    )
    media_path: Optional[str] = Field(
        None, description="Optional path to image/video file"
    )
    reply_to_tweet_id: Optional[str] = Field(
        None, description="Tweet ID to reply to (creates a reply)"
    )
    quote_tweet_id: Optional[str] = Field(
        None, description="Tweet ID to quote (creates a quote tweet)"
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        return _check_dangerous_content(v)


class TwitterPostThreadInput(BaseModel):
    """Input for twitter_post_thread."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    tweets: list[str] = Field(
        ...,
        min_length=2,
        max_length=25,
        description="List of tweet texts (2-25 tweets, each max 280 chars)",
    )

    @field_validator("tweets")
    @classmethod
    def validate_tweets(cls, v: list[str]) -> list[str]:
        for tweet in v:
            if len(tweet) > 280:
                raise ValueError(f"Tweet exceeds 280 characters: {tweet[:50]}...")
            _check_dangerous_content(tweet)
        return v


class TwitterGetTimelineInput(BaseModel):
    """Input for twitter_get_timeline."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    max_results: int = Field(
        default=10, ge=5, le=100, description="Number of tweets to retrieve (5-100)"
    )
    exclude_replies: bool = Field(
        default=False, description="Exclude replies from timeline"
    )
    exclude_retweets: bool = Field(
        default=False, description="Exclude retweets from timeline"
    )


class TwitterGetMentionsInput(BaseModel):
    """Input for twitter_get_mentions."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    max_results: int = Field(
        default=10, ge=5, le=100, description="Number of mentions to retrieve (5-100)"
    )
    since_hours: Optional[int] = Field(
        None,
        ge=1,
        le=168,
        description="Get mentions from last N hours (max 168 = 1 week)",
    )


class TwitterSearchTweetsInput(BaseModel):
    """Input for twitter_search_tweets."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Search query (supports Twitter search operators)",
    )
    max_results: int = Field(
        default=10, ge=10, le=100, description="Number of results (10-100)"
    )
    sort_order: Literal["recency", "relevancy"] = Field(
        default="recency", description="Sort order for results"
    )


class TwitterGetTrendsInput(BaseModel):
    """Input for twitter_get_trends."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    woeid: int = Field(
        default=1, description="Where On Earth ID (1=Worldwide, 23424977=USA)"
    )


class TwitterLikeTweetInput(BaseModel):
    """Input for twitter_like_tweet."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    tweet_id: str = Field(..., min_length=1, description="Tweet ID to like")


class TwitterRetweetInput(BaseModel):
    """Input for twitter_retweet."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    tweet_id: str = Field(..., min_length=1, description="Tweet ID to retweet")


class TwitterReplyInput(BaseModel):
    """Input for twitter_reply_to_tweet."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    tweet_id: str = Field(..., min_length=1, description="Tweet ID to reply to")
    reply_text: str = Field(
        ..., min_length=1, max_length=280, description="Reply text (max 280 characters)"
    )

    @field_validator("reply_text")
    @classmethod
    def validate_reply_text(cls, v: str) -> str:
        return _check_dangerous_content(v)


class TwitterGetAnalyticsInput(BaseModel):
    """Input for twitter_get_analytics."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    tweet_id: str = Field(
        ..., min_length=1, description="Tweet ID to get analytics for"
    )


class TwitterGenerateSummaryInput(BaseModel):
    """Input for twitter_generate_summary."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    include_timeline: bool = Field(default=True, description="Include timeline summary")
    include_mentions: bool = Field(default=True, description="Include mentions summary")
    days: int = Field(
        default=7, ge=1, le=7, description="Number of days to summarize (1-7)"
    )


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def twitter_post_tweet(input: TwitterPostTweetInput) -> dict:
    """
    Post a new tweet.

    Creates a tweet with optional media attachment. Can be a reply or quote tweet.
    Requires HITL approval before actual posting.

    Returns:
        Tweet status and preview
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
        "tweet_preview": {
            "text": input.text,
            "media_path": input.media_path,
            "reply_to_tweet_id": input.reply_to_tweet_id,
            "quote_tweet_id": input.quote_tweet_id,
            "character_count": len(input.text),
        },
        "approval_required": True,
        "message": "Tweet queued for approval. Move to /Approved to publish.",
        "mock_mode": True,
        "note": "TODO: Implement actual Twitter API v2 integration",
    }


@mcp.tool()
def twitter_post_thread(input: TwitterPostThreadInput) -> dict:
    """
    Post a thread of tweets.

    Creates a thread by posting multiple tweets in sequence, each replying
    to the previous one. Requires HITL approval before actual posting.

    Returns:
        Thread status and preview
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
        "thread_preview": {
            "tweets": [
                {"index": i + 1, "text": tweet, "character_count": len(tweet)}
                for i, tweet in enumerate(input.tweets)
            ],
            "total_tweets": len(input.tweets),
        },
        "approval_required": True,
        "message": f"Thread of {len(input.tweets)} tweets queued for approval.",
        "mock_mode": True,
        "note": "TODO: Implement actual Twitter API v2 integration",
    }


@mcp.tool()
def twitter_get_timeline(input: TwitterGetTimelineInput) -> dict:
    """
    Get user's timeline tweets.

    Retrieves recent tweets from the authenticated user's timeline
    for content analysis and summarization.

    Returns:
        List of timeline tweets with engagement metrics
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    mock_tweets = [
        {
            "tweet_id": f"tweet_{i}",
            "text": f"Sample timeline tweet {i}",
            "author": f"@user{i}",
            "created_at": (datetime.now() - timedelta(hours=i * 6)).isoformat(),
            "likes": 10 * i,
            "retweets": 2 * i,
            "replies": i,
            "is_retweet": False,
        }
        for i in range(1, min(input.max_results, 10) + 1)
    ]

    return {
        "success": True,
        "tweets": mock_tweets,
        "count": len(mock_tweets),
        "filters": {
            "exclude_replies": input.exclude_replies,
            "exclude_retweets": input.exclude_retweets,
        },
        "mock_mode": True,
        "note": "TODO: Implement actual Twitter API v2 integration",
    }


@mcp.tool()
def twitter_get_mentions(input: TwitterGetMentionsInput) -> dict:
    """
    Get mentions and replies.

    Retrieves tweets that mention the authenticated user.
    Useful for monitoring engagement and responding to interactions.

    Returns:
        List of mentions with author and content
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    mock_mentions = [
        {
            "tweet_id": f"mention_{i}",
            "text": f"Sample mention tweet {i} @you",
            "author": f"@mentioner{i}",
            "created_at": (datetime.now() - timedelta(hours=i * 2)).isoformat(),
            "likes": 5 * i,
            "is_reply": i % 2 == 0,
        }
        for i in range(1, min(input.max_results, 10) + 1)
    ]

    return {
        "success": True,
        "mentions": mock_mentions,
        "count": len(mock_mentions),
        "since_hours": input.since_hours,
        "mock_mode": True,
        "note": "TODO: Implement actual Twitter API v2 integration",
    }


@mcp.tool()
def twitter_search_tweets(input: TwitterSearchTweetsInput) -> dict:
    """
    Search for tweets by keyword.

    Searches recent tweets matching the query. Supports Twitter search
    operators for advanced filtering.

    Returns:
        List of matching tweets
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    mock_results = [
        {
            "tweet_id": f"search_{i}",
            "text": f"Sample tweet matching '{input.query}' - result {i}",
            "author": f"@author{i}",
            "created_at": (datetime.now() - timedelta(hours=i)).isoformat(),
            "likes": 8 * i,
            "retweets": i,
        }
        for i in range(1, min(input.max_results, 10) + 1)
    ]

    return {
        "success": True,
        "tweets": mock_results,
        "count": len(mock_results),
        "query": input.query,
        "sort_order": input.sort_order,
        "mock_mode": True,
        "note": "TODO: Implement actual Twitter API v2 integration",
    }


@mcp.tool()
def twitter_get_trends(input: TwitterGetTrendsInput) -> dict:
    """
    Get trending topics.

    Retrieves current trending topics for specified location.
    Useful for content inspiration and trend monitoring.

    Returns:
        List of trending topics with volumes
    """
    creds = _load_credentials()
    if "error" in creds:
        return {
            "success": False,
            "error": creds["error"],
            "setup_instructions": creds["setup"],
        }

    mock_trends = [
        {
            "name": f"#TrendingTopic{i}",
            "tweet_volume": 10000 * (11 - i),
            "url": f"https://twitter.com/search?q=%23TrendingTopic{i}",
        }
        for i in range(1, 11)
    ]

    return {
        "success": True,
        "trends": mock_trends,
        "woeid": input.woeid,
        "location": "Worldwide" if input.woeid == 1 else f"WOEID-{input.woeid}",
        "as_of": datetime.now().isoformat(),
        "mock_mode": True,
        "note": "TODO: Implement actual Twitter API v2 integration",
    }


@mcp.tool()
def twitter_like_tweet(input: TwitterLikeTweetInput) -> dict:
    """
    Like a tweet.

    Adds a like to the specified tweet. Requires HITL approval.

    Returns:
        Like action status
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
        "action": {"type": "like", "tweet_id": input.tweet_id},
        "approval_required": True,
        "message": "Like action queued for approval.",
        "mock_mode": True,
        "note": "TODO: Implement actual Twitter API v2 integration",
    }


@mcp.tool()
def twitter_retweet(input: TwitterRetweetInput) -> dict:
    """
    Retweet a tweet.

    Retweets the specified tweet to your timeline. Requires HITL approval.

    Returns:
        Retweet action status
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
        "action": {"type": "retweet", "tweet_id": input.tweet_id},
        "approval_required": True,
        "message": "Retweet action queued for approval.",
        "mock_mode": True,
        "note": "TODO: Implement actual Twitter API v2 integration",
    }


@mcp.tool()
def twitter_reply_to_tweet(input: TwitterReplyInput) -> dict:
    """
    Reply to a tweet.

    Posts a reply to the specified tweet. Requires HITL approval.

    Returns:
        Reply status and preview
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
        "reply_preview": {
            "tweet_id": input.tweet_id,
            "reply_text": input.reply_text,
            "character_count": len(input.reply_text),
        },
        "approval_required": True,
        "message": "Reply queued for approval. Move to /Approved to post.",
        "mock_mode": True,
        "note": "TODO: Implement actual Twitter API v2 integration",
    }


@mcp.tool()
def twitter_get_analytics(input: TwitterGetAnalyticsInput) -> dict:
    """
    Get tweet analytics.

    Retrieves engagement metrics for a specific tweet.
    Useful for measuring content performance.

    Returns:
        Analytics with impressions, engagement, and clicks
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
        "tweet_id": input.tweet_id,
        "analytics": {
            "impressions": 3456,
            "engagements": 234,
            "engagement_rate": 0.0677,
            "likes": 145,
            "retweets": 34,
            "replies": 23,
            "profile_clicks": 45,
            "url_clicks": 67,
            "detail_expands": 89,
        },
        "mock_mode": True,
        "note": "TODO: Implement actual Twitter API v2 integration",
    }


@mcp.tool()
def twitter_generate_summary(input: TwitterGenerateSummaryInput) -> dict:
    """
    Generate summary from Twitter activity.

    Aggregates timeline and mentions to create an activity summary
    for CEO briefing or reporting.

    Returns:
        Summary with tweet counts, engagement metrics, and highlights
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

    if input.include_timeline:
        summary["timeline"] = {
            "tweets_posted": 12,
            "total_impressions": 25000,
            "total_engagements": 1200,
            "new_followers": 35,
            "top_tweet": {
                "text": "Sample top-performing tweet",
                "impressions": 8500,
                "engagements": 450,
            },
        }

    if input.include_mentions:
        summary["mentions"] = {
            "total_mentions": 45,
            "replies_given": 15,
            "engagement_opportunities": 30,
            "top_mention": {
                "author": "@topmentioner",
                "text": "Great content!",
                "engagement": 23,
            },
        }

    return {
        "success": True,
        "summary": summary,
        "mock_mode": True,
        "note": "TODO: Implement actual Twitter API v2 integration",
    }


# ---------------------------------------------------------------------------
# Server Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
