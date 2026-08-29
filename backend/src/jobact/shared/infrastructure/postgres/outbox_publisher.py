"""Drains `platform.outbox` and publishes each unpublished row via a
`MessageBroker`.

This is infrastructure, not application logic -- it needs both direct
Postgres access (to select/stamp outbox rows) and a `MessageBroker`
together, so it lives here rather than split awkwardly across layers.
Task 2.3's worker entrypoint is what actually runs this in a loop; this
module only owns "drain once."

Each row is published, then immediately stamped with `published_at` in
its own small transaction -- if the process dies between the two, the
row is republished on the next drain (at-least-once delivery, matching
the outbox pattern's own guarantee; consumers are expected to be
idempotent, e.g. via `platform.inbox` in Task 2.3).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, update

from jobact.shared.application.ports import MessageBroker
from jobact.shared.infrastructure.postgres.engine import get_sessionmaker
from jobact.shared.infrastructure.postgres.tables import outbox_table

_BATCH_SIZE = 100


def stream_for_event(event_type: str, aggregate_type: str) -> str:
    if event_type == "TranscriptionDispatchRequested":
        return "outbox.Transcription"
    return f"outbox.{aggregate_type}"


async def publish_pending_outbox_events(broker: MessageBroker) -> int:
    """Publish every unpublished `platform.outbox` row, oldest first.

    Returns the number of rows published in this drain. Call repeatedly
    (Task 2.3's worker loop does this on an interval) -- a single call
    only drains what's queued right now, up to `_BATCH_SIZE`.
    """
    session_factory = get_sessionmaker()
    published = 0

    async with session_factory() as session:
        result = await session.execute(
            select(
                outbox_table.c.id,
                outbox_table.c.event_type,
                outbox_table.c.aggregate_type,
                outbox_table.c.aggregate_id,
                outbox_table.c.event_version,
                outbox_table.c.payload,
                outbox_table.c.occurred_at,
            )
            .where(outbox_table.c.published_at.is_(None))
            .order_by(outbox_table.c.occurred_at)
            .limit(_BATCH_SIZE)
        )
        rows = result.all()

    for row in rows:
        stream = stream_for_event(row.event_type, row.aggregate_type)
        message_payload = {
            "event_id": str(row.id),
            "event_type": row.event_type,
            "event_version": row.event_version,
            "aggregate_type": row.aggregate_type,
            "aggregate_id": str(row.aggregate_id),
            "occurred_at": row.occurred_at.isoformat(),
            "payload": row.payload,
        }
        await broker.publish(stream, message_payload)

        async with session_factory() as session, session.begin():
            await session.execute(
                update(outbox_table)
                .where(outbox_table.c.id == row.id)
                .values(published_at=datetime.now(UTC))
            )
        published += 1

    return published
