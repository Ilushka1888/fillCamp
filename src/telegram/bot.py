from __future__ import annotations

import asyncio
import os

from aiogram import Bot, Dispatcher

from src.app.core.config import config
from src.app.core.logger import get_logger
from aiogram.client.default import DefaultBotProperties
from src.app.db.session import AsyncSessionLocal
from src.app.services.broadcast_service import BroadcastService
from src.telegram.handlers import register_handlers

logger = get_logger(__name__)


def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    env_token = os.environ.get("CAMPBOT_TELEGRAM_BOT_TOKEN", "")
    token = env_token or config.telegram_bot_token

    logger.info(f"TELEGRAM TOKEN FROM ENV: {repr(env_token)}")
    logger.info(f"TELEGRAM TOKEN FROM SETTINGS: {repr(config.telegram_bot_token)}")

    if not token:
        raise RuntimeError("TG_BOT_TOKEN не задан в настройках")

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher()

    register_handlers(dp, bot)

    return bot, dp


async def scheduler_loop(bot: Bot) -> None:
    broadcasts_interval_sec = 60
    inactive_interval_sec = 3600
    inactive_days = 3

    next_inactive_tick = 0
    tick = 0

    while True:
        tick += 1

        async with AsyncSessionLocal() as db:
            service = BroadcastService(db, bot)
            await service.send_due_broadcasts()
            await db.commit()

        if tick >= next_inactive_tick:
            async with AsyncSessionLocal() as db:
                service = BroadcastService(db, bot)
                await service.send_inactive_reminders(inactive_days=inactive_days)
                await db.commit()
            next_inactive_tick = tick + (
                inactive_interval_sec // broadcasts_interval_sec
            )

        await asyncio.sleep(broadcasts_interval_sec)


async def start_bot(bot: Bot, dp: Dispatcher) -> None:
    asyncio.create_task(scheduler_loop(bot))

    logger.info("Запуск Telegram-бота лагеря...")
    await dp.start_polling(bot)
