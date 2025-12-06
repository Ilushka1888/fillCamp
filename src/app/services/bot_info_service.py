from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.user_models import User
from src.app.models.game_models import GameStats
from src.app.models.shop_models import Order
from src.app.repositories.balance_repo import BalanceRepository

# from src.app.repositories.game_repo import GameService


class BotInfoService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._balance_repo = BalanceRepository(db)
        # self._game_service = GameService(db)

    async def get_balance_amount(self, user: User) -> int:
        balance = await self._balance_repo.get_balance(user=user)
        return balance.amount

    async def get_game_stats(self, user: User) -> Optional[GameStats]:
        stmt = select(GameStats).where(GameStats.user_id == user.id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_recent_orders(
        self,
        user: User,
        limit: int = 5,
    ) -> List[Order]:
        stmt = (
            select(Order)
            .where(Order.user_id == user.id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars())
