# src/app/api/routes/game_router.py
from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.api.deps import get_current_user
from src.app.db.session import get_db
from src.app.models.balance_models import TransactionType
from src.app.models.game_models import GameStats
from src.app.models.user_models import User
from src.app.repositories.balance_repo import BalanceRepository
from src.app.schemas.miniapp_schemas import GameClickResponse

router = APIRouter(prefix="/api/game", tags=["Game"])


@router.post("/click", response_model=GameClickResponse)
async def game_click(
  db: AsyncSession = Depends(get_db),
  user: User = Depends(get_current_user),
) -> GameClickResponse:
  # достаём/создаём статистику
  stmt = select(GameStats).where(GameStats.user_id == user.id)
  result = await db.execute(stmt)
  stats = result.scalar_one_or_none()
  if stats is None:
    stats = GameStats(user_id=user.id, total_clicks=0, clicks_today=0)
    db.add(stats)
    await db.flush()
    await db.refresh(stats)

  today = date.today()
  if stats.clicks_today_date != today:
    stats.clicks_today_date = today
    stats.clicks_today = 0

  stats.total_clicks += 1
  stats.clicks_today += 1
  stats.last_click_at = datetime.utcnow()

  # награда за клик — 1 бонус (можно сделать формулу посложнее)
  reward_per_click = 1

  balance_repo = BalanceRepository(db)
  await balance_repo.change_balance(
    user=user,
    delta=reward_per_click,
    tx_type=TransactionType.GAME_CLICK,
    description="Game click reward",
  )

  db.add(stats)
  await db.flush()
  await db.commit()

  new_balance = await balance_repo.get_balance(user)

  return GameClickResponse(
    new_bonus_balance=new_balance,
    game_progress=stats.total_clicks,
  )
