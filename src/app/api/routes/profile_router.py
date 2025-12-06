# src/app/api/routes/profile_router.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.api.deps import get_current_user
from src.app.db.session import get_db
from src.app.models.balance_models import Balance
from src.app.models.game_models import GameStats
from src.app.models.user_models import User, UserRole
from src.app.repositories.balance_repo import BalanceRepository
from src.app.schemas.miniapp_schemas import UserProfileResponse

router = APIRouter(prefix="/api/profile", tags=["Profile"])


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
  db: AsyncSession = Depends(get_db),
  user: User = Depends(get_current_user),
) -> UserProfileResponse:
  # баланс
  balance_repo = BalanceRepository(db)
  bonus_balance = await balance_repo.get_balance(user)

  # прогресс игры
  stmt_stats = select(GameStats).where(GameStats.user_id == user.id)
  result_stats = await db.execute(stmt_stats)
  stats = result_stats.scalar_one_or_none()
  game_progress = stats.total_clicks if stats else 0

  # связи родитель/ребенок
  linked_parent_tg_id: int | None = None
  linked_child_tg_id: int | None = None

  if user.role == UserRole.CHILD and user.parent_id:
    parent = await db.get(User, user.parent_id)
    if parent:
      linked_parent_tg_id = parent.telegram_id

  if user.role == UserRole.PARENT:
    stmt_child = select(User).where(User.parent_id == user.id)
    res_child = await db.execute(stmt_child)
    child = res_child.scalar_one_or_none()
    if child:
      linked_child_tg_id = child.telegram_id

  full_name = (
    user.full_name
    or " ".join(filter(None, [user.first_name, user.last_name]))
    or "Без имени"
  )

  return UserProfileResponse(
    id=user.id,
    tg_id=user.telegram_id,
    full_name=full_name,
    username=user.username,
    avatar_url=user.photo_url,
    role="child" if user.role == UserRole.CHILD else "parent",
    linked_parent_tg_id=linked_parent_tg_id,
    linked_child_tg_id=linked_child_tg_id,
    bonus_balance=bonus_balance,
    game_progress=game_progress,
  )
