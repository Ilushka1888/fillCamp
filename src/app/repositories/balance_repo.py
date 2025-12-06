from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.balance_models import Balance, BalanceTransaction, TransactionType
from src.app.models.user_models import User


class NotEnoughBalanceError(Exception):
    pass


class BalanceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get_balance_row(self, user_id: int) -> Balance:
        stmt = select(Balance).where(Balance.user_id == user_id)
        result = await self.db.execute(stmt)
        balance = result.scalar_one_or_none()
        if balance is None:
            balance = Balance(user_id=user_id, amount=0)
            self.db.add(balance)
            await self.db.flush()
            await self.db.refresh(balance)
        return balance

    async def get_balance(self, user: User) -> int:
        balance = await self._get_balance_row(user.id)
        return balance.amount

    async def change_balance(
        self,
        user: User,
        delta: int,
        tx_type: TransactionType,
        description: str | None = None,
        allow_negative: bool = False,
    ) -> Balance:
        balance = await self._get_balance_row(user.id)

        new_amount = balance.amount + delta
        if new_amount < 0 and not allow_negative:
            raise NotEnoughBalanceError("Not enough balance")

        balance.amount = new_amount

        tx = BalanceTransaction(
            user_id=user.id,
            delta=delta,
            resulting_balance=new_amount,
            type=tx_type,
            description=description,
        )
        self.db.add(balance)
        self.db.add(tx)
        await self.db.flush()
        await self.db.refresh(balance)
        return balance
