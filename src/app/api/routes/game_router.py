# src/app/api/routes/game_router.py
from __future__ import annotations

from datetime import date, datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.api.deps import get_current_user
from src.app.db.session import get_db
from src.app.models.balance_models import TransactionType
from src.app.models.game_models import GameStats
from src.app.models.user_models import User, UserRole
from src.app.repositories.balance_repo import BalanceRepository
from src.app.repositories.user_repo import UserRepository
from src.app.schemas.miniapp_schemas import GameClickResponse

router = APIRouter(prefix="/api/game", tags=["Game"])


async def _process_click(db: AsyncSession, user: User) -> GameClickResponse:
    """
    Общая логика обработки клика:
    - доступ только для role=child
    - обновление статистики
    - начисление бонуса
    """

    if user.role != UserRole.CHILD:
        # HTTP-ручка поймает эту ошибку, а в WS мы проверяем отдельно
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Игра доступна только для ребенка",
        )

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

    # награда за клик — 1 бонус
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


# ---------- HTTP-ручка (как была, но через общий обработчик) ----------


@router.post("/click", response_model=GameClickResponse)
async def game_click(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GameClickResponse:
    return await _process_click(db, user)


# ---------- WebSocket-игра ----------


@router.websocket("/ws")
async def game_ws(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Протокол:
    - клиент подключается к ws://.../api/game/ws с заголовком X-Telegram-Id
    - сервер валидирует пользователя, проверяет role=child
    - клиент шлёт: {"type": "click"}
    - сервер отвечает: {
          "event": "click",
          "new_bonus_balance": <int>,
          "game_progress": <int>
      }
    """

    # принимаем соединение
    await websocket.accept()

    # --- простая "аутентификация" по X-Telegram-Id, как в get_current_user ---
    telegram_id_header = (
        websocket.headers.get("x-telegram-id")
        or websocket.headers.get("X-Telegram-Id")
    )
    if telegram_id_header is None:
        # не передан телеграм-айди
        await websocket.close(code=4401)  # 4401 — Unauthorized
        return

    try:
        telegram_id = int(telegram_id_header)
    except ValueError:
        await websocket.close(code=4401)
        return

    user_repo = UserRepository(db)
    user = await user_repo.get_by_telegram_id(telegram_id)

    if user is None:
        # минимальное создание пользователя, дефолт — ребенок
        user = User(
            telegram_id=telegram_id,
            role=UserRole.CHILD,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

    # трекаем активность mini-app
    await user_repo.touch_app_activity(user)
    await db.commit()

    # --- доступ только для детей ---
    if user.role != UserRole.CHILD:
        await websocket.close(code=4403)  # 4403 — Forbidden
        return

    # --- игровой цикл ---
    try:
        while True:
            message = await websocket.receive_json()

            if message.get("type") != "click":
                await websocket.send_json(
                    {"event": "error", "detail": "Unsupported message type"}
                )
                continue

            # та же логика, что и в HTTP-ручке
            try:
                result = await _process_click(db, user)
            except HTTPException as exc:
                # на всякий случай, если роль поменялась
                await websocket.send_json(
                    {
                        "event": "error",
                        "detail": exc.detail,
                    }
                )
                if exc.status_code == status.HTTP_403_FORBIDDEN:
                    await websocket.close(code=4403)
                    return
                continue

            await websocket.send_json(
                {
                    "event": "click",
                    "new_bonus_balance": result.new_bonus_balance,
                    "game_progress": result.game_progress,
                }
            )

    except WebSocketDisconnect:
        # просто выходим из функции
        return
