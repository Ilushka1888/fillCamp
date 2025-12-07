# src/app/api/deps.py
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.session import get_db
from src.app.models.user_models import User, UserRole
from src.app.repositories.user_repo import UserRepository
from src.app.services.referral_service import ReferralService


async def get_current_user(
  request: Request,
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

  # --- пробуем достать реферальный код из заголовка ---
  referral_code = request.headers.get("X-Referral-Code")

  if user is None:
    # по умолчанию — родитель
    role = UserRole.PARENT
    referrer_id: int | None = None

    # если пришёл реферальный код — пробуем найти пригласившего
    if referral_code:
      ref_service = ReferralService(db)
      referrer = await ref_service.get_user_by_referral(referral_code)
      if referrer:
        role = UserRole.CHILD
        referrer_id = referrer.id

    # создаём пользователя ОДИН раз, сразу с нужной ролью и referrer_id
    user = User(
      telegram_id=telegram_id,
      role=role,
      referrer_id=referrer_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

  # считаем взаимодействие c Mini App
  await user_repo.touch_app_activity(user)
  await db.commit()

  return user

