from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from src.app.db.session import AsyncSessionLocal
from src.app.models.user_models import User
from src.app.services.telegram_user_service import TelegramUserService
from src.app.services.bot_info_service import BotInfoService
from src.app.core.logger import get_logger

logger = get_logger(__name__)


def register_handlers(dp: Dispatcher, bot: Bot) -> None:
    @dp.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        async with AsyncSessionLocal() as db:
            user_service = TelegramUserService(db)
            user: User = await user_service.get_or_create_from_telegram(
                message.from_user
            )
            await db.commit()

        await message.answer(
            "Привет! Это бот лагеря.\n\n"
            "Через Mini App ты можешь копить бонусы, играть и тратить их в магазине.\n"
            "Если ты ещё не заходил(а) в приложение, открой меню Telegram и выбери Mini App лагеря."
        )

    @dp.message(Command("help"))
    async def cmd_help(message: Message) -> None:
        await message.answer(
            "/start — зарегистрироваться в системе и подписаться на уведомления\n"
            "/unsubscribe — отписаться от рассылки\n"
            "/balance — посмотреть текущий бонусный баланс\n"
            "/orders — посмотреть последние заказы\n"
            "/stats — посмотреть прогресс в игре\n\n"
            "Остальные уведомления приходят автоматически: акции лагеря, напоминания и т.д."
        )

    @dp.message(Command("unsubscribe"))
    async def cmd_unsubscribe(message: Message) -> None:
        async with AsyncSessionLocal() as db:
            user_service = TelegramUserService(db)
            user = await user_service.get_or_create_from_telegram(message.from_user)
            await user_service.unsubscribe(user)
            await db.commit()

        await message.answer(
            "Вы отписались от рассылок. Чтобы снова подписаться — используйте /start."
        )

    @dp.message(Command("balance"))
    async def cmd_balance(message: Message) -> None:
        async with AsyncSessionLocal() as db:
            user_service = TelegramUserService(db)
            user: User = await user_service.get_or_create_from_telegram(
                message.from_user
            )

            info_service = BotInfoService(db)
            amount = await info_service.get_balance_amount(user)
            await db.commit()

        await message.answer(f"Ваш текущий бонусный баланс: <b>{amount}</b> бонусов.")

    @dp.message(Command("orders"))
    async def cmd_orders(message: Message) -> None:
        async with AsyncSessionLocal() as db:
            user_service = TelegramUserService(db)
            user: User = await user_service.get_or_create_from_telegram(
                message.from_user
            )

            info_service = BotInfoService(db)
            orders = await info_service.get_recent_orders(user, limit=5)
            await db.commit()

        if not orders:
            await message.answer("У вас пока нет заказов в магазине лагеря.")
            return

        lines: list[str] = ["Ваши последние заказы:"]
        for order in orders:
            status = getattr(order, "status", None)
            total_bonus = getattr(order, "total_bonus", None)
            created_at = getattr(order, "created_at", None)

            status_str = str(status.value) if hasattr(status, "value") else str(status)
            created_str = (
                created_at.strftime("%d.%m.%Y %H:%M") if created_at is not None else "—"
            )

            line = (
                f"• #{order.id} | {status_str} | {total_bonus} бонусов | {created_str}"
            )
            lines.append(line)

        await message.answer("\n".join(lines))

    @dp.message(Command("stats"))
    async def cmd_stats(message: Message) -> None:
        async with AsyncSessionLocal() as db:
            user_service = TelegramUserService(db)
            user: User = await user_service.get_or_create_from_telegram(
                message.from_user
            )

            info_service = BotInfoService(db)
            stats = await info_service.get_game_stats(user)
            await db.commit()

        if stats is None:
            await message.answer(
                "У вас пока нет статистики по игре.\n"
                "Зайдите в Mini App и сделайте первые клики, чтобы начать копить бонусы."
            )
            return

        total_clicks = getattr(stats, "total_clicks", 0)
        clicks_today = getattr(stats, "clicks_today", 0)
        last_click_at = getattr(stats, "last_click_at", None)

        last_click_str = (
            last_click_at.strftime("%d.%m.%Y %H:%M")
            if last_click_at is not None
            else "—"
        )

        text = (
            "<b>Ваш прогресс в игре</b>\n\n"
            f"Всего кликов: <b>{total_clicks}</b>\n"
            f"Кликов сегодня: <b>{clicks_today}</b>\n"
            f"Последний клик: <b>{last_click_str}</b>"
        )

        await message.answer(text)

    @dp.message()
    async def any_message(message: Message) -> None:
        async with AsyncSessionLocal() as db:
            user_service = TelegramUserService(db)
            user = await user_service.get_or_create_from_telegram(message.from_user)
            await user_service.touch_bot_interaction(user)
            await db.commit()
