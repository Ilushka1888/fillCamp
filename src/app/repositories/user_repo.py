from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.user_models import User, UserRole


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.db.get(User, user_id)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_or_update_from_telegram(
        self,
        telegram_id: int,
        defaults: dict[str, Any],
    ) -> User:
        user = await self.get_by_telegram_id(telegram_id)

        if user:
            for field, value in defaults.items():
                if value is not None and hasattr(user, field):
                    setattr(user, field, value)
            user.last_bot_interaction_at = datetime.utcnow()
            self.db.add(user)
            await self.db.flush()
            await self.db.refresh(user)
            return user

        user = User(
            telegram_id=telegram_id,
            role=defaults.get("role", UserRole.CHILD),
            username=defaults.get("username"),
            first_name=defaults.get("first_name"),
            last_name=defaults.get("last_name"),
            full_name=defaults.get("full_name"),
            photo_url=defaults.get("photo_url"),
            phone=defaults.get("phone"),
            last_bot_interaction_at=datetime.utcnow(),
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def touch_app_activity(self, user: User) -> None:
        user.last_app_interaction_at = datetime.utcnow()
        self.db.add(user)
        await self.db.flush()
