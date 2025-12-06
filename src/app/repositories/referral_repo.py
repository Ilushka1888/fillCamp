from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.models.referral_models import Referral
from src.app.repositories.base import BaseRepository


class ReferralRepository(BaseRepository[Referral]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Referral)

    def get_by_invited_user_id(self, invited_user_id: int) -> Referral | None:
        stmt = select(Referral).where(Referral.invited_user_id == invited_user_id)
        return self.db.scalar(stmt)

    def get_for_inviter(self, inviter_user_id: int) -> list[Referral]:
        stmt = select(Referral).where(Referral.inviter_user_id == inviter_user_id)
        return list(self.db.scalars(stmt))
