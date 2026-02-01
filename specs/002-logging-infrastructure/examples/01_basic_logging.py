"""
Example 1: Basic Logging

Demonstrates:
- Initializing the logging system
- Basic log levels
- Context and tags
- Graceful shutdown
"""

import asyncio
from src.logging import init_logging, get_logger


async def main():
    # Initialize logging system
    logger = init_logging(log_dir="./Logs", level="INFO")
    await logger.start_async_writer()

    # Get logger for current module
    logger = get_logger(__name__)

    # Basic logging at different levels
    logger.debug("This is a debug message")  # Won't show (level=INFO)
    logger.info("Application started successfully")
    logger.warning("This is a warning message")

    # Logging with structured context
    logger.info(
        "User logged in",
        context={
            "user_id": "user-123",
            "ip_address": "192.168.1.1",
            "session_id": "sess-abc"
        }
    )

    # Logging with tags
    logger.info(
        "File uploaded",
        tags=["file", "upload", "success"],
        context={"filename": "document.pdf", "size_bytes": 1024000}
    )

    # Error logging
    try:
        result = 1 / 0
    except ZeroDivisionError as e:
        logger.error(
            "Division error occurred",
            exception=e,
            context={"numerator": 1, "denominator": 0}
        )

    # Critical error
    logger.critical(
        "System instability detected",
        context={"memory_usage": 95, "cpu_usage": 98}
    )

    # Graceful shutdown
    print("Flushing logs...")
    await logger.stop_async_writer()
    print("Logs flushed successfully")


if __name__ == "__main__":
    asyncio.run(main())
