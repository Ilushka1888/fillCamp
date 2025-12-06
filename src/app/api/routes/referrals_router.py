# src/app/api/routes/referrals_router.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.app.api.deps import get_current_user
from src.app.core.config import config
from src.app.db.session import get_db
from src.app.models.balance_models import BalanceTransaction, TransactionType
from src.app.models.referral_models import Referral
from src.app.models.user_models import User
from src.app.schemas.miniapp_schemas import (
  InvitedUserInfo,
  ReferralInfoResponse,
)

router = APIRouter(prefix="/api/referrals", tags=["Referrals"])


def build_referral_link(user: User) -> str:
  # тут можно использовать username бота из настроек, если есть
  # чтобы не ломать существующий config, делаем простую заглушку
  bot_username = "your_bot_username"  # TODO: заменить на реальный username бота
  return f"https://t.me/{bot_username}?start={user.telegram_id}"


@router.get("/me", response_model=ReferralInfoResponse)
async def get_my_referrals(
  db: AsyncSession = Depends(get_db),
  user: User = Depends(get_current_user),
) -> ReferralInfoResponse:
  # все рефералы
  stmt = (
    select(Referral)
    .options(joinedload(Referral.invited))
    .where(Referral.inviter_user_id == user.id)
  )
  result = await db.execute(stmt)
  referrals = result.scalars().all()

  invited_users: list[InvitedUserInfo] = []
  for ref in referrals:
    invited = ref.invited
    if not invited:
      continue
    full_name = (
      invited.full_name
      or " ".join(filter(None, [invited.first_name, invited.last_name]))
      or "Без имени"
    )
    invited_users.append(
      InvitedUserInfo(full_name=full_name, tg_id=invited.telegram_id)
    )

  invited_count = len(invited_users)

  # сколько бонусов дано за рефералку
  stmt_bonus = select(
    func.coalesce(func.sum(BalanceTransaction.delta), 0)
  ).where(
    BalanceTransaction.user_id == user.id,
    BalanceTransaction.type == TransactionType.REFERRAL,
    BalanceTransaction.delta > 0,
  )
  result_bonus = await db.execute(stmt_bonus)
  bonus_earned = int(result_bonus.scalar_one() or 0)

  return ReferralInfoResponse(
    referral_link=build_referral_link(user),
    invited_count=invited_count,
    bonus_earned=bonus_earned,
    invited_users=invited_users,
  )
