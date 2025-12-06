from __future__ import annotations

from datetime import datetime, timedelta

from aiogram import Bot
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.broadcast_models import Broadcast, BroadcastStatus
from src.app.models.user_models import User
from src.app.core.logger import get_logger

logger = get_logger(__name__)


class BroadcastService:
    def __init__(self, db: AsyncSession, bot: Bot) -> None:
        self.db = db
        self.bot = bot

    async def send_due_broadcasts(self, now: datetime | None = None) -> None:
        if now is None:
            now = datetime.utcnow()

        stmt = (
            select(Broadcast)
            .where(Broadcast.status == BroadcastStatus.SCHEDULED)
            .where(Broadcast.scheduled_at <= now)
            .order_by(Broadcast.scheduled_at)
        )
        result = await self.db.execute(stmt)
        broadcasts: list[Broadcast] = list(result.scalars())

        if not broadcasts:
            return

        users_stmt = select(User).where(User.is_subscribed.is_(True))
        users_result = await self.db.execute(users_stmt)
        users: list[User] = list(users_result.scalars())

        for broadcast in broadcasts:
            for user in users:
                try:
                    await self.bot.send_message(
                        chat_id=user.telegram_id,
                        text=broadcast.text,
                    )
                except Exception as send_err:
                    logger.info(
                        f"Ошибка отправки рассылки {broadcast.id} пользователю {user.telegram_id}: {send_err}"
                    )

            broadcast.status = BroadcastStatus.SENT
            self.db.add(broadcast)

        await self.db.flush()

    async def send_inactive_reminders(
        self,
        inactive_days: int = 3,
        limit_per_run: int = 1000,
    ) -> None:
        now = datetime.utcnow()
        threshold = now - timedelta(days=inactive_days)

        stmt = (
            select(User)
            .where(User.is_subscribed.is_(True))
            .where(User.last_app_interaction_at.is_not(None))
            .where(User.last_app_interaction_at < threshold)
            .order_by(User.last_app_interaction_at)
            .limit(limit_per_run)
        )

        result = await self.db.execute(stmt)
        inactive_users: list[User] = list(result.scalars())

        if not inactive_users:
            return

        for user in inactive_users:
            try:
                await self.bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        "Мы давно не видели вас в лагере! "
                        "Загляните в Mini App и продолжите копить бонусы 🙂"
                    ),
                )
            except Exception as send_err:
                print(
                    f"Ошибка отправки напоминания пользователю {user.telegram_id}: {send_err}"
                )

            user.last_bot_interaction_at = now
            self.db.add(user)

        await self.db.flush()
