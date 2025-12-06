from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.models.broadcast_models import Broadcast, BroadcastStatus
from src.app.repositories.base import BaseRepository


class BroadcastRepository(BaseRepository[Broadcast]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Broadcast)

    def get_scheduled_due(self, now: datetime, limit: int = 50) -> list[Broadcast]:
        stmt = (
            select(Broadcast)
            .where(Broadcast.status == BroadcastStatus.SCHEDULED)
            .where(Broadcast.scheduled_at <= now)
            .order_by(Broadcast.scheduled_at)
            .limit(limit)
        )
        return list(self.db.scalars(stmt))
