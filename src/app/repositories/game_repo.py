from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.balance_models import TransactionType
from src.app.models.game_models import GameStats
from src.app.models.user_models import User
from src.app.repositories.balance_repo import BalanceRepository


class GameRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.balance_service = BalanceRepository(db)

    async def _get_stats(self, user_id: int) -> GameStats:
        stmt = select(GameStats).where(GameStats.user_id == user_id)
        result = await self.db.execute(stmt)
        stats = result.scalar_one_or_none()
        if stats is None:
            stats = GameStats(user_id=user_id)
            self.db.add(stats)
            await self.db.flush()
            await self.db.refresh(stats)
        return stats

    async def register_click(self, user: User, reward_per_click: int = 1) -> GameStats:
        stats = await self._get_stats(user.id)

        today = date.today()
        if stats.clicks_today_date != today:
            stats.clicks_today_date = today
            stats.clicks_today = 0

        stats.total_clicks += 1
        stats.clicks_today += 1
        stats.last_click_at = datetime.utcnow()

        await self.balance_service.change_balance(
            user=user,
            delta=reward_per_click,
            tx_type=TransactionType.GAME_CLICK,
            description="Game click reward",
        )

        self.db.add(stats)
        await self.db.flush()
        await self.db.refresh(stats)
        return stats
