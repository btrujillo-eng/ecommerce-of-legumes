import logging
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.persistence.models import OutboxEvent

logger = logging.getLogger(__name__)


class OutboxRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def enqueue(self, *, event_key: str, event_type: str, payload: dict[str, Any]) -> bool:
        async with self.session_factory() as session:
            session.add(OutboxEvent(
                event_key=event_key,
                event_type=event_type,
                payload=payload,
                status="pending",
                attempts=0,
            ))
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                logger.info("Outbox event already queued: %s", event_key)
                return False
        return True
