"""
Example 2: Trace Correlation

Demonstrates:
- Trace ID generation and binding
- Trace correlation across multiple operations
- Passing trace IDs to child operations
- Nested trace contexts
"""

import asyncio
from src.logging import init_logging, get_logger, new_trace_id


async def process_order(order_id: str, logger):
    """Process an order with trace correlation."""
    logger.info("Order received", context={"order_id": order_id, "status": "received"})

    # Simulate processing steps
    await validate_order(order_id, logger)
    await charge_payment(order_id, logger)
    await ship_order(order_id, logger)

    logger.info("Order completed", context={"order_id": order_id, "status": "completed"})


async def validate_order(order_id: str, logger):
    """Validate order (shares parent trace ID)."""
    logger.info("Validating order", context={"order_id": order_id})
    await asyncio.sleep(0.1)  # Simulate work
    logger.info("Order validated", context={"order_id": order_id})


async def charge_payment(order_id: str, logger):
    """Charge payment (shares parent trace ID)."""
    logger.info("Charging payment", context={"order_id": order_id})
    await asyncio.sleep(0.1)  # Simulate work
    logger.info("Payment charged", context={"order_id": order_id, "amount": 99.99})


async def ship_order(order_id: str, logger):
    """Ship order (shares parent trace ID)."""
    logger.info("Shipping order", context={"order_id": order_id})
    await asyncio.sleep(0.1)  # Simulate work
    logger.info("Order shipped", context={"order_id": order_id, "tracking": "TRK123"})


async def main():
    # Initialize logging
    logger = init_logging(log_dir="./Logs", level="INFO")
    await logger.start_async_writer()
    logger = get_logger(__name__)

    # Example 1: Auto-generated trace ID
    print("Example 1: Auto-generated trace ID")
    with logger.bind_trace_id() as trace_id:
        print(f"Trace ID: {trace_id}")
        await process_order("order-001", logger)

    # Example 2: Custom trace ID
    print("\nExample 2: Custom trace ID")
    custom_trace = "custom-trace-12345"
    with logger.bind_trace_id(custom_trace) as trace_id:
        print(f"Trace ID: {trace_id}")
        await process_order("order-002", logger)

    # Example 3: Multiple concurrent operations with different traces
    print("\nExample 3: Concurrent operations with different traces")
    async def order_with_trace(order_id: str):
        with logger.bind_trace_id() as trace_id:
            print(f"Order {order_id} - Trace: {trace_id}")
            await process_order(order_id, logger)

    await asyncio.gather(
        order_with_trace("order-003"),
        order_with_trace("order-004"),
        order_with_trace("order-005"),
    )

    # Example 4: Nested trace contexts
    print("\nExample 4: Nested trace contexts")
    with logger.bind_trace_id("outer-trace") as outer_trace:
        logger.info("Outer operation started")

        # Inner operation with its own trace
        with logger.bind_trace_id("inner-trace") as inner_trace:
            logger.info("Inner operation started")
            await asyncio.sleep(0.05)
            logger.info("Inner operation complete")

        # Back to outer trace
        logger.info("Outer operation complete")

    # Graceful shutdown
    await logger.stop_async_writer()
    print("\nAll operations logged. Check Logs/ directory.")
    print("Query by trace ID:")
    print("  fte logs query --trace-id <trace_id>")


if __name__ == "__main__":
    asyncio.run(main())
