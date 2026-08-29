from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError

from jobact.shared.application.ports import Message
from jobact.shared.infrastructure.postgres.engine import get_sessionmaker
from jobact.shared.infrastructure.postgres.tables import inbox_table
from jobact.shared.infrastructure.redis.client import get_redis_client
from jobact.shared.infrastructure.redis.streams import RedisStreamsBroker
from jobact.workflows.report_fulfillment.transcription_dispatcher import (
    process_transcription_event,
)

_CONSUMER_GROUP = "stt-worker"
_CONSUMER_NAME = "stt-worker-1"
_MAX_ATTEMPTS = 3
_RETRY_BASE_DELAY_SECONDS = 1.0
_STREAM = "outbox.Transcription"

logger = logging.getLogger("jobact.apps.stt_worker")

HANDLER_REGISTRY: dict[str, Callable[[dict], Awaitable[None]]] = {
    "TranscriptionDispatchRequested": process_transcription_event,
}


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    for noisy_logger in ("httpcore", "httpx", "sqlalchemy.engine"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


async def _already_processed(event_id: UUID) -> bool:
    async with get_sessionmaker()() as session:
        result = await session.execute(
            select(inbox_table.c.message_id).where(
                inbox_table.c.message_id == event_id
            )
        )
        return result.first() is not None


async def _record_processed(event_id: UUID) -> None:
    async with get_sessionmaker()() as session, session.begin():
        try:
            await session.execute(
                insert(inbox_table).values(
                    message_id=event_id,
                    consumer=_CONSUMER_GROUP,
                    processed_at=datetime.now(UTC),
                )
            )
        except IntegrityError:
            pass


async def _dispatch(message: Message) -> None:
    event_id = UUID(message.payload["event_id"])
    event_type = message.payload.get("event_type", "")
    if await _already_processed(event_id):
        await message.ack()
        return
    handler = HANDLER_REGISTRY.get(event_type)
    if handler is None:
        await message.ack()
        return

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            await handler(message.payload)
            break
        except Exception as exc:  # noqa: BLE001 - worker retry boundary
            logger.warning(
                "stt_event_dispatch_failed event_id=%s event_type=%s attempt=%s "
                "error_type=%s",
                event_id,
                event_type,
                attempt,
                type(exc).__name__,
            )
            if attempt == _MAX_ATTEMPTS:
                return
            await asyncio.sleep(_RETRY_BASE_DELAY_SECONDS * (2**attempt))

    await _record_processed(event_id)
    await message.ack()


async def main() -> None:
    configure_logging()
    logger.info(
        "stt_worker_started consumer_group=%s consumer_name=%s",
        _CONSUMER_GROUP,
        _CONSUMER_NAME,
    )
    broker = RedisStreamsBroker(get_redis_client())
    async for message in broker.consume(_STREAM, _CONSUMER_GROUP, _CONSUMER_NAME):
        await _dispatch(message)


if __name__ == "__main__":
    asyncio.run(main())
