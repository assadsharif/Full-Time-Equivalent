"""
Example 3: Context Binding

Demonstrates:
- Binding context to operation scope
- Nested context binding
- Context propagation through function calls
- Duration measurement
"""

import asyncio
from src.logging import init_logging, get_logger


async def process_task(task_id: str, logger):
    """Process a task with bound context."""
    # Bind task context for entire operation
    with logger.bind_context(task_id=task_id, operation="process_task"):
        logger.info("Task processing started")

        # All logs in this scope will include task_id and operation
        await validate_task(logger)
        await execute_task(logger)
        await finalize_task(logger)

        logger.info("Task processing complete")


async def validate_task(logger):
    """Validate task (inherits parent context)."""
    logger.info("Validating task")
    await asyncio.sleep(0.05)
    logger.info("Task validated")


async def execute_task(logger):
    """Execute task with additional context."""
    # Add nested context
    with logger.bind_context(phase="execution"):
        logger.info("Executing task")
        await asyncio.sleep(0.1)
        logger.info("Task executed", context={"result": "success"})


async def finalize_task(logger):
    """Finalize task (back to parent context)."""
    logger.info("Finalizing task")
    await asyncio.sleep(0.05)
    logger.info("Task finalized")


async def main():
    # Initialize logging
    logger = init_logging(log_dir="./Logs", level="INFO")
    await logger.start_async_writer()
    logger = get_logger(__name__)

    # Example 1: Simple context binding
    print("Example 1: Simple context binding")
    with logger.bind_context(user="alice", session="sess-123"):
        logger.info("User logged in")
        logger.info("Dashboard loaded")
        logger.info("User logged out")
    # All three logs include user and session context

    # Example 2: Context binding with task processing
    print("\nExample 2: Context binding with task processing")
    await process_task("task-001", logger)

    # Example 3: Duration measurement with context
    print("\nExample 3: Duration measurement with context")
    with logger.bind_context(database="postgres", table="users"):
        with logger.measure_duration("database_query", operation="SELECT"):
            await asyncio.sleep(0.15)  # Simulate query

        with logger.measure_duration("database_query", operation="INSERT"):
            await asyncio.sleep(0.08)  # Simulate insert

    # Example 4: Nested context
    print("\nExample 4: Nested context")
    with logger.bind_context(request_id="req-789", endpoint="/api/users"):
        logger.info("Request received")

        with logger.bind_context(user_id="user-456"):
            logger.info("User authenticated")
            logger.info("Processing user data")

        # Back to request-level context
        logger.info("Response sent")

    # Example 5: Combined trace ID and context
    print("\nExample 5: Combined trace ID and context")
    with logger.bind_trace_id() as trace_id:
        with logger.bind_context(workflow="order_fulfillment", step="initial"):
            logger.info("Workflow started")

            with logger.bind_context(step="validation"):
                logger.info("Validating order")

            with logger.bind_context(step="payment"):
                logger.info("Processing payment")

            with logger.bind_context(step="shipping"):
                logger.info("Arranging shipment")

            logger.info("Workflow complete")

    # Graceful shutdown
    await logger.stop_async_writer()
    print("\nAll operations logged. Check Logs/ directory.")


if __name__ == "__main__":
    asyncio.run(main())
