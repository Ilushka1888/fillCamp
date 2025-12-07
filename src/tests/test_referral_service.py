from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.app.models.user_models import User
from src.app.services.referral_service import ReferralService


class DummyDB:
    def __init__(self) -> None:
        self.commits = 0
        self.refreshed: list[User] = []

    def add(self, obj: object) -> None:
        # в реальном AsyncSession add синхронный
        pass

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, obj: User) -> None:
        self.refreshed.append(obj)


@pytest.mark.anyio
@pytest.mark.unit
@pytest.mark.referral
class TestReferralService:
    async def test_generate_referral_code_sets_code_and_commits(self) -> None:
        """
        Первый вызов generate_referral_code:
        - выставляет user.referral_code
        - вызывает commit и refresh
        """
        db = DummyDB()
        user = User(
            id=1,
            telegram_id=123456,
            full_name="Parent User",
            phone="+79990000000",
        )

        service = ReferralService(db)  # type: ignore[arg-type]

        # не хотим трогать настоящую БД, мокаем проверку уникальности
        with patch.object(
            service,
            "_code_exists",
            new=AsyncMock(return_value=False),
        ):
            code = await service.generate_referral_code(user)

        assert code.startswith("ref_")
        assert user.referral_code == code
        assert db.commits == 1
        assert db.refreshed == [user]

    async def test_generate_referral_code_overwrites_old_code(self) -> None:
        """
        Повторный вызов должен перезаписать старый код.
        """
        db = DummyDB()
        user = User(
            id=2,
            telegram_id=999999,
            full_name="Another User",
            phone="+79990000001",
            referral_code="ref_old",  # старый код
        )

        service = ReferralService(db)  # type: ignore[arg-type]

        with patch.object(
            service,
            "_code_exists",
            new=AsyncMock(return_value=False),
        ):
            code1 = await service.generate_referral_code(user)
            code2 = await service.generate_referral_code(user)

        assert code1.startswith("ref_")
        assert code2.startswith("ref_")
        # коды могут совпасть теоретически, но с token_hex это крайне маловероятно.
        # главное — что последнее значение сохранено в user.referral_code
        assert user.referral_code == code2
        assert db.commits == 2
        assert db.refreshed == [user, user]
