# src/app/api/deps.py
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.session import get_db
from src.app.models.user_models import User, UserRole
from src.app.repositories.user_repo import UserRepository


async def get_current_user(
  db: AsyncSession = Depends(get_db),
  telegram_id: int | None = Header(default=None, alias="X-Telegram-Id"),
) -> User:
  """
  Простейшая аутентификация по Telegram ID из заголовка X-Telegram-Id.
  В бою сюда можно прикрутить валидацию initData.
  """
  if telegram_id is None:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="X-Telegram-Id header is required",
    )

  user_repo = UserRepository(db)
  user = await user_repo.get_by_telegram_id(telegram_id)

  if user is None:
    # минимальное создание пользователя
    user = User(
      telegram_id=telegram_id,
      role=UserRole.PARENT,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

  # считаем взаимодействие c Mini App
  await user_repo.touch_app_activity(user)
  await db.commit()

  return user
