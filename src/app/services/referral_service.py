from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.user_models import User


class ReferralService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_referral_code(self, user: User) -> str:
        """
        Создаёт новый код и СРАЗУ перезаписывает старый (если был).
        """
        code = "ref_" + secrets.token_hex(4)

        # гарантируем уникальность
        while await self._code_exists(code):
            code = "ref_" + secrets.token_hex(4)

        user.referral_code = code
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return code

    async def _code_exists(self, code: str) -> bool:
        stmt = select(User).where(User.referral_code == code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_user_by_referral(self, code: str) -> User | None:
        stmt = select(User).where(User.referral_code == code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
