from __future__ import annotations

from datetime import datetime

from aiogram.types import User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.app.models.user_models import User
from src.app.repositories.user_repo import UserRepository


class TelegramUserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)

    async def get_or_create_from_telegram(self, tg_user: TgUser) -> User:
        telegram_id = tg_user.id

        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.db.execute(stmt)
        user: User | None = result.scalar_one_or_none()

        full_name = " ".join(
            part for part in [tg_user.first_name, tg_user.last_name] if part
        ).strip()

        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                full_name=full_name or tg_user.full_name,
                is_subscribed=True,
                last_bot_interaction_at=datetime.utcnow(),
            )
            self.db.add(user)
            await self.db.flush()
            await self.db.refresh(user)
        else:
            user.username = tg_user.username
            user.first_name = tg_user.first_name
            user.last_name = tg_user.last_name
            user.full_name = full_name or user.full_name
            user.last_bot_interaction_at = datetime.utcnow()
            if not user.is_subscribed:
                user.is_subscribed = True
            self.db.add(user)
            await self.db.flush()
            await self.db.refresh(user)

        return user

    async def unsubscribe(self, user: User) -> None:
        user.is_subscribed = False
        user.last_bot_interaction_at = datetime.utcnow()
        self.db.add(user)
        await self.db.flush()

    async def touch_bot_interaction(self, user: User) -> None:
        user.last_bot_interaction_at = datetime.utcnow()
        self.db.add(user)
        await self.db.flush()
