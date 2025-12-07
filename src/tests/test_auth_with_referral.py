from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from starlette.requests import Request

from src.app.api import deps
from src.app.models.user_models import User, UserRole


class DummyDB:
    """
    Минимальный фейк AsyncSession, достаточный для get_current_user.
    """

    def __init__(self) -> None:
        self.added: list[Any] = []
        self.commits = 0
        self.refreshed: list[Any] = []

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, obj: Any) -> None:
        # эмулируем, что объект уже в БД и имеет id
        if isinstance(obj, User) and getattr(obj, "id", None) is None:
            obj.id = 100  # любой фиктивный id
        self.refreshed.append(obj)


def make_scope(
    telegram_id: int | None,
    referral_code: str | None = None,
) -> dict[str, Any]:
    headers: list[tuple[bytes, bytes]] = []
    if telegram_id is not None:
        headers.append((b"x-telegram-id", str(telegram_id).encode()))
    if referral_code is not None:
        headers.append((b"x-referral-code", referral_code.encode()))

    return {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers,
    }


@pytest.mark.anyio
@pytest.mark.unit
@pytest.mark.referral
class TestGetCurrentUserWithReferral:
    async def test_new_user_without_referral_becomes_parent(self) -> None:
        """
        Если пользователя нет и X-Referral-Code не передан:
        - создаётся новый пользователь
        - role = PARENT
        - referrer_id = None
        """
        db = DummyDB()
        scope = make_scope(telegram_id=123456)
        request = Request(scope)

        with patch.object(
            deps, "UserRepository"
        ) as MockUserRepo, patch.object(
            deps, "ReferralService"
        ) as MockRefService:
            user_repo_instance = MockUserRepo.return_value
            # пользователя ещё нет
            user_repo_instance.get_by_telegram_id = AsyncMock(return_value=None)
            user_repo_instance.touch_app_activity = AsyncMock()

            ref_service_instance = MockRefService.return_value
            ref_service_instance.get_user_by_referral = AsyncMock()

            user = await deps.get_current_user(
                request=request,
                db=db,  # type: ignore[arg-type]
                telegram_id=123456,
            )

        assert isinstance(user, User)
        assert user.telegram_id == 123456
        assert user.role == UserRole.PARENT
        # поле referrer_id может быть None, если ты его добавил в модель
        assert getattr(user, "referrer_id", None) is None

        # ReferralService вообще не должен вызываться, т.к. X-Referral-Code нет
        ref_service_instance.get_user_by_referral.assert_not_awaited()

        # Пользователь был создан и activity протрогали
        user_repo_instance.get_by_telegram_id.assert_awaited_once()
        user_repo_instance.touch_app_activity.assert_awaited_once_with(user)
        # commit вызывается: один раз после создания юзера, один раз после touch_app_activity
        assert db.commits == 2

    async def test_new_user_with_valid_referral_becomes_child(self) -> None:
        """
        Если пользователя нет и X-Referral-Code указывает на реального пригласившего:
        - создаётся новый пользователь
        - role = CHILD
        - referrer_id = referrer.id
        """
        db = DummyDB()
        scope = make_scope(telegram_id=222222, referral_code="ref_abc123")
        request = Request(scope)

        referrer = User(
            id=10,
            telegram_id=999999,
            full_name="Referrer User",
            phone="+79990000000",
            role=UserRole.PARENT,
        )

        with patch.object(
            deps, "UserRepository"
        ) as MockUserRepo, patch.object(
            deps, "ReferralService"
        ) as MockRefService:
            user_repo_instance = MockUserRepo.return_value
            user_repo_instance.get_by_telegram_id = AsyncMock(return_value=None)
            user_repo_instance.touch_app_activity = AsyncMock()

            ref_service_instance = MockRefService.return_value
            ref_service_instance.get_user_by_referral = AsyncMock(
                return_value=referrer
            )

            user = await deps.get_current_user(
                request=request,
                db=db,  # type: ignore[arg-type]
                telegram_id=222222,
            )

        assert isinstance(user, User)
        assert user.telegram_id == 222222
        assert user.role == UserRole.CHILD
        assert getattr(user, "referrer_id", None) == referrer.id

        ref_service_instance.get_user_by_referral.assert_awaited_once_with(
            "ref_abc123"
        )
        user_repo_instance.touch_app_activity.assert_awaited_once_with(user)
        assert db.commits == 2

    async def test_existing_user_ignores_referral_code(self) -> None:
        """
        Если пользователь уже существует:
        - X-Referral-Code игнорируется
        - роль и referrer_id не меняются
        """
        db = DummyDB()
        scope = make_scope(telegram_id=333333, referral_code="ref_should_be_ignored")
        request = Request(scope)

        existing_user = User(
            id=20,
            telegram_id=333333,
            full_name="Existing User",
            phone="+79990000003",
            role=UserRole.PARENT,
        )

        with patch.object(
            deps, "UserRepository"
        ) as MockUserRepo, patch.object(
            deps, "ReferralService"
        ) as MockRefService:
            user_repo_instance = MockUserRepo.return_value
            user_repo_instance.get_by_telegram_id = AsyncMock(
                return_value=existing_user
            )
            user_repo_instance.touch_app_activity = AsyncMock()

            ref_service_instance = MockRefService.return_value
            ref_service_instance.get_user_by_referral = AsyncMock()

            user = await deps.get_current_user(
                request=request,
                db=db,  # type: ignore[arg-type]
                telegram_id=333333,
            )

        # Вернулся тот же юзер, без изменений роли
        assert user is existing_user
        assert user.role == UserRole.PARENT
        assert getattr(user, "referrer_id", None) is None

        # ReferralService не должен вызываться
        ref_service_instance.get_user_by_referral.assert_not_awaited()
        user_repo_instance.touch_app_activity.assert_awaited_once_with(existing_user)
        assert db.commits == 1  # только commit после touch_app_activity
