"""Worker process entrypoint.

Runs two things concurrently, both against the real Postgres/Redis
this process is configured for:

1. The outbox publisher (`publish_pending_outbox_events`, Task 2.2) on
   an interval -- drains `platform.outbox` and pushes committed events
   onto their Redis Streams.
2. A stream consumer that reads those events back, dedupes via
   `platform.inbox` (keyed by the domain event's own `event_id` from
   the payload, NOT the Redis stream entry id -- the entry id is a
   delivery-mechanism artifact, not a stable domain identifier),
   dispatches to a handler registry by `event_type`, and acks.

No concrete event handlers exist yet in this milestone -- the registry
is intentionally empty. An event with no registered handler is
acked and inbox-recorded like any other (there's nothing wrong with an
event nobody currently listens for; consumers are added later without
touching this loop).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError

from jobact.shared.application.ports import Message, MessageBroker
from jobact.shared.infrastructure.postgres.engine import get_sessionmaker
from jobact.shared.infrastructure.postgres.outbox_publisher import (
    publish_pending_outbox_events,
)
from jobact.shared.infrastructure.postgres.tables import inbox_table
from jobact.shared.infrastructure.redis.client import get_redis_client
from jobact.shared.infrastructure.redis.streams import RedisStreamsBroker
from jobact.workflows.visual_audit.dispatcher import process_visual_audit_event

_PUBLISH_INTERVAL_SECONDS = 2.0
_CONSUMER_GROUP = "worker"
_CONSUMER_NAME = "worker-1"
_MAX_ATTEMPTS = 5
_RETRY_BASE_DELAY_SECONDS = 1.0

# event_type -> handler. Empty for now -- nothing in this milestone
# consumes outbox events yet.
HANDLER_REGISTRY: dict[str, Callable[[dict], Awaitable[None]]] = {
    "VisualAuditRequested": process_visual_audit_event,
}


async def _already_processed(event_id: UUID) -> bool:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        result = await session.execute(
            select(inbox_table.c.message_id).where(
                inbox_table.c.message_id == event_id
            )
        )
        return result.first() is not None


async def _record_processed(event_id: UUID) -> None:
    session_factory = get_sessionmaker()
    async with session_factory() as session, session.begin():
        try:
            await session.execute(
                insert(inbox_table).values(
                    message_id=event_id,
                    consumer=_CONSUMER_GROUP,
                    processed_at=datetime.now(UTC),
                )
            )
        except IntegrityError:
            # Already recorded by a concurrent delivery -- fine, the
            # point (dedup) already holds.
            pass


async def _dispatch(message: Message) -> None:
    event_id = UUID(message.payload["event_id"])

    if await _already_processed(event_id):
        await message.ack()
        return

    handler = HANDLER_REGISTRY.get(message.payload.get("event_type", ""))

    attempt = 0
    while True:
        try:
            if handler is not None:
                await handler(message.payload)
            break
        except Exception:  # noqa: BLE001 - retry boundary for all event-handler failures
            attempt += 1
            if attempt >= _MAX_ATTEMPTS:
                # Exhausted retries -- do not ack, do not record as
                # processed. The message stays pending in the consumer
                # group for manual investigation/replay; crashing the
                # whole worker over one bad event would be worse.
                return
            await asyncio.sleep(_RETRY_BASE_DELAY_SECONDS * (2**attempt))

    await _record_processed(event_id)
    await message.ack()


async def _run_publisher_loop(broker: MessageBroker) -> None:
    while True:
        await publish_pending_outbox_events(broker)
        await asyncio.sleep(_PUBLISH_INTERVAL_SECONDS)


async def _run_consumer_loop(broker: RedisStreamsBroker, stream: str) -> None:
    async for message in broker.consume(stream, _CONSUMER_GROUP, _CONSUMER_NAME):
        await _dispatch(message)


async def main() -> None:
    broker = RedisStreamsBroker(get_redis_client())
    # Streams are named "outbox.<aggregate_type>" (see outbox_publisher.py).
    # No consumer loop is started per-stream here yet since no aggregate
    # type has a registered handler in this milestone -- the publisher
    # loop alone is enough to keep platform.outbox draining. A later
    # milestone that adds a real handler also adds its stream's consumer
    # loop to this gather() call.
    await asyncio.gather(
        _run_publisher_loop(broker),
        _run_consumer_loop(broker, "outbox.VisualAuditAttempt"),
    )


if __name__ == "__main__":
    asyncio.run(main())
