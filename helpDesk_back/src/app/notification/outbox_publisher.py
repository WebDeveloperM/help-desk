"""Outbox dispatcher: publish notification outbox rows to RabbitMQ with at-least-once behavior."""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

import aio_pika
from aio_pika import DeliveryMode, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.database import get_session_factory
from app.notification.repositories import SQLAlchemyNotificationRepository

logger = logging.getLogger(__name__)


class _RabbitMqOutboxPublisher:
    """
    Long-lived RabbitMQ publisher for the outbox dispatcher.

    Owns one robust connection + channel + exchange across many batches.
    Topology (exchange, queue, binding) is declared once on first use.
    `connect_robust` handles transport-level reconnection; `ensure_ready`
    transparently re-opens if the connection has been explicitly closed.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractRobustChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None
        self._lock = asyncio.Lock()

    def _is_ready(self) -> bool:
        return (
            self._exchange is not None
            and self._connection is not None
            and not self._connection.is_closed
        )

    async def ensure_ready(self) -> None:
        """Open connection and declare topology on first use; reopen if closed."""
        if self._is_ready():
            return
        async with self._lock:
            if self._is_ready():
                return
            await self._open()

    async def _open(self) -> None:
        await self._close_quietly()
        connection = await aio_pika.connect_robust(self.settings.rabbitmq_url)
        try:
            channel = await connection.channel(publisher_confirms=True)
            exchange = await channel.declare_exchange(
                self.settings.rabbitmq_exchange,
                aio_pika.ExchangeType.TOPIC,
                durable=True,
            )
            queue = await channel.declare_queue(
                self.settings.rabbitmq_queue,
                durable=True,
            )
            await queue.bind(exchange, routing_key=self.settings.rabbitmq_queue)
        except Exception:
            await connection.close()
            raise
        self._connection = connection
        self._channel = channel
        self._exchange = exchange

    async def publish(
        self, routing_key: str, body: bytes, timeout: float = 5.0
    ) -> None:
        await self.ensure_ready()
        assert self._exchange is not None  # ensure_ready guarantees this
        await self._exchange.publish(
            Message(body=body, delivery_mode=DeliveryMode.PERSISTENT),
            routing_key=routing_key,
            timeout=timeout,
        )

    async def close(self) -> None:
        async with self._lock:
            await self._close_quietly()

    async def _close_quietly(self) -> None:
        connection = self._connection
        self._connection = None
        self._channel = None
        self._exchange = None
        if connection is None or connection.is_closed:
            return
        try:
            await connection.close()
        except Exception as e:
            logger.warning("Outbox: error closing RabbitMQ connection: %s", e)


def next_retry_at(attempts: int, max_attempts: int) -> datetime | None:
    """Exponential backoff: 2^attempts seconds from now, or None if max attempts reached."""
    if attempts >= max_attempts:
        return None
    delay_seconds = min(2**attempts, 300)
    return datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)


async def _record_publish_failure(
    repo: SQLAlchemyNotificationRepository,
    row,
    attempts: int,
    max_attempts: int,
    error: str,
) -> None:
    """
    Record a publish failure: schedule a retry, or dead-letter when the budget
    is exhausted. Logs at ERROR for dead-letters so ops can surface them.
    """
    retry_at = next_retry_at(attempts, max_attempts)
    if retry_at is None:
        logger.error(
            "Outbox row %s exhausted retries (attempts=%d, max=%d): %s",
            row.id,
            attempts,
            max_attempts,
            error,
        )
        await repo.mark_outbox_dead_letter(
            row.id,
            attempts=attempts,
            last_error=error,
        )
        return
    await repo.mark_outbox_failed(
        row.id,
        attempts=attempts,
        next_retry_at=retry_at,
        last_error=error,
    )


async def process_outbox_batch(
    settings: Settings,
    session: AsyncSession,
    publisher: _RabbitMqOutboxPublisher,
) -> int:
    """
    Fetch pending outbox rows, publish each to RabbitMQ, update DB (sent or failed).

    The caller owns `publisher` and commits/rolls back the session. The publisher
    is shared across batches so we don't re-handshake AMQP every interval.

    Returns:
        Number of rows processed.
    """
    if not settings.rabbitmq_url:
        return 0
    repo = SQLAlchemyNotificationRepository(session)
    rows = await repo.get_pending_outbox(limit=settings.outbox_batch_size)
    if not rows:
        return 0
    try:
        await publisher.ensure_ready()
    except Exception as e:
        logger.warning("Outbox: RabbitMQ ensure_ready failed: %s", e)
        for row in rows:
            attempts = row.attempts + 1
            await _record_publish_failure(
                repo,
                row,
                attempts=attempts,
                max_attempts=settings.outbox_max_attempts,
                error=str(e),
            )
        return len(rows)

    now = datetime.now(timezone.utc)
    processed = 0
    for row in rows:
        try:
            body = json.dumps(row.payload_json).encode("utf-8")
            await publisher.publish(row.routing_key, body, timeout=5.0)
            await repo.mark_outbox_sent(row.id, published_at=now)
            processed += 1
        except Exception as e:
            attempts = row.attempts + 1
            await _record_publish_failure(
                repo,
                row,
                attempts=attempts,
                max_attempts=settings.outbox_max_attempts,
                error=str(e)[:500],
            )
    return processed


async def run_outbox_dispatcher(settings: Settings) -> None:
    """
    Background task: every outbox_interval_seconds, process a batch of outbox rows.

    Runs until cancelled. Owns one `_RabbitMqOutboxPublisher` for the whole
    lifetime so AMQP setup happens once instead of per batch. Uses the same
    session factory as the app (init_database must have been called).
    """
    if not settings.rabbitmq_url:
        logger.info("Outbox dispatcher disabled: RABBITMQ_URL not set")
        return
    factory = get_session_factory()
    publisher = _RabbitMqOutboxPublisher(settings)
    try:
        while True:
            try:
                async with factory() as session:
                    try:
                        await process_outbox_batch(settings, session, publisher)
                        await session.commit()
                    except Exception as e:
                        logger.warning("Outbox batch error: %s", e)
                        await session.rollback()
            except asyncio.CancelledError:
                logger.info("Outbox dispatcher stopped")
                raise
            except Exception as e:
                logger.warning("Outbox dispatcher session error: %s", e)
            await asyncio.sleep(settings.outbox_interval_seconds)
    finally:
        await publisher.close()
