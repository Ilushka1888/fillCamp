'''
оплата только рублями (бонусы только начисляются);

оплата только бонусами;

оплата рубли + бонусы (MIXED);

недостаточно бонусов;

больше одного товара в корзине запрещено.
'''

from __future__ import annotations

from typing import Any, List

import pytest
from fastapi import HTTPException, status
from unittest.mock import AsyncMock, patch

from src.app.api.routes import shop_router
from src.app.models.balance_models import TransactionType
from src.app.models.shop_models import Order, Product
from src.app.models.user_models import User
from src.app.repositories.balance_repo import NotEnoughBalanceError
from src.app.schemas.miniapp_schemas import (
    CreateOrderRequest,
    OrderItemRequest,
    OrderResponse,
)


class FakeScalarResult:
    def __init__(self, seq: List[Any]) -> None:
        self._seq = seq

    def all(self) -> List[Any]:
        return list(self._seq)


class FakeResult:
    def __init__(self, seq: List[Any]) -> None:
        self._seq = seq

    def scalars(self) -> FakeScalarResult:
        return FakeScalarResult(self._seq)


class FakeSession:
    """Минимальная имитация AsyncSession для create_order."""

    def __init__(self, products: list[Product]) -> None:
        self._products = products
        self.added: list[Any] = []
        self.flushed = False
        self.committed = False

    async def execute(self, stmt: Any) -> FakeResult:  # type: ignore[override]
        # stmt нам не важен, возвращаем все продукты
        return FakeResult(self._products)

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flushed = True

    async def refresh(self, obj: Any) -> None:
        # эмулируем проставление id заказу
        if isinstance(obj, Order) and getattr(obj, "id", None) is None:
            obj.id = 1

    async def commit(self) -> None:
        self.committed = True


def make_user() -> User:
    return User(
        id=1,
        telegram_id=123456,
        full_name="Test User",
        phone="+79990000000",
    )


@pytest.mark.anyio
@pytest.mark.unit
@pytest.mark.shop
class TestCreateOrderFlow:
    async def test_money_only_payment_accrues_bonuses_and_calls_amocrm(self) -> None:
        """
        Смена в Сочи, платим только рублями:
        - бонусы НЕ списываются
        - начисляется 5% бонусов от суммы
        - создаётся заказ и уходит в AmoCRM
        """
        product = Product(
            id=1,
            name="Смена в Сочи",
            price_bonus=0,
            price_money=100_000,
            category="camp_sochi",
        )
        db = FakeSession(products=[product])
        user = make_user()

        with patch("src.app.api.routes.shop_router.BalanceRepository") as MockBalanceRepo:
            balance_instance = MockBalanceRepo.return_value
            balance_instance.change_balance = AsyncMock()

            amocrm_service = AsyncMock()

            payload = CreateOrderRequest(
                items=[OrderItemRequest(item_id=1, quantity=1)],
                pay_with_bonus=False,
            )

            response: OrderResponse = await shop_router.create_order(
                payload=payload,
                db=db,  # type: ignore[arg-type]
                user=user,
                amocrm_service=amocrm_service,
            )

        # Ответ
        assert isinstance(response, OrderResponse)
        assert response.total_bonus == 0
        assert response.total_money == pytest.approx(100_000.0)

        # Одна транзакция на начисление бонусов
        balance_instance.change_balance.assert_awaited_once()
        call = balance_instance.change_balance.await_args_list[0]
        kwargs = call.kwargs
        assert kwargs["tx_type"] == TransactionType.SHOP_PURCHASE
        assert kwargs["delta"] == 5_000  # 5% от 100 000

        # Заказ ушёл в AmoCRM
        amocrm_service.send_order_to_amocrm.assert_awaited_once()
        order_arg = amocrm_service.send_order_to_amocrm.await_args_list[0].args[0]
        assert isinstance(order_arg, Order)
        assert order_arg.total_money == pytest.approx(100_000.0)
        assert order_arg.total_bonus == 0

    async def test_bonus_only_payment_merch(self) -> None:
        """
        Мерч, цена только в бонусах.
        - списываем 100% бонусами
        - ничего не начисляем
        """
        product = Product(
            id=2,
            name="Футболка мерч",
            price_bonus=3_000,
            price_money=None,
            category="merch",
        )
        db = FakeSession(products=[product])
        user = make_user()

        with patch("src.app.api.routes.shop_router.BalanceRepository") as MockBalanceRepo:
            balance_instance = MockBalanceRepo.return_value
            balance_instance.change_balance = AsyncMock()

            amocrm_service = AsyncMock()

            payload = CreateOrderRequest(
                items=[OrderItemRequest(item_id=2, quantity=1)],
                pay_with_bonus=True,
            )

            response: OrderResponse = await shop_router.create_order(
                payload=payload,
                db=db,  # type: ignore[arg-type]
                user=user,
                amocrm_service=amocrm_service,
            )

        # Полная стоимость оплачена бонусами, в деньгах 0
        assert response.total_money is None or response.total_money == 0
        assert response.total_bonus == 3_000

        # Одна операция списания, без начисления
        balance_instance.change_balance.assert_awaited_once()
        kwargs = balance_instance.change_balance.await_args_list[0].kwargs
        assert kwargs["delta"] == -3_000

        amocrm_service.send_order_to_amocrm.assert_awaited_once()

    async def test_mixed_payment_money_and_bonuses(self) -> None:
        """
        camp_sochi + pay_with_bonus=True:
        - 5% суммы списали бонусами
        - 5% начислили бонусами
        - остальное рублями
        """
        product = Product(
            id=3,
            name="Смена в Сочи",
            price_bonus=0,
            price_money=100_000,
            category="camp_sochi",
        )
        db = FakeSession(products=[product])
        user = make_user()

        with patch("src.app.api.routes.shop_router.BalanceRepository") as MockBalanceRepo:
            balance_instance = MockBalanceRepo.return_value
            balance_instance.change_balance = AsyncMock()

            amocrm_service = AsyncMock()

            payload = CreateOrderRequest(
                items=[OrderItemRequest(item_id=3, quantity=1)],
                pay_with_bonus=True,
            )

            response: OrderResponse = await shop_router.create_order(
                payload=payload,
                db=db,  # type: ignore[arg-type]
                user=user,
                amocrm_service=amocrm_service,
            )

        # 5% списали бонусами, остальное деньгами
        assert response.total_bonus == 5_000
        assert response.total_money == pytest.approx(95_000.0)

        # Две операции: списание и начисление
        assert balance_instance.change_balance.await_count == 2
        deltas = [call.kwargs["delta"] for call in balance_instance.change_balance.await_args_list]
        assert -5_000 in deltas
        assert 5_000 in deltas

        amocrm_service.send_order_to_amocrm.assert_awaited_once()

    async def test_not_enough_bonuses_raises_http_error(self) -> None:
        """
        При недостатке бонусов репозиторий кидает NotEnoughBalanceError,
        endpoint должен вернуть 400 и не дойти до AmoCRM.
        """
        product = Product(
            id=4,
            name="Футболка мерч",
            price_bonus=3_000,
            price_money=None,
            category="merch",
        )
        db = FakeSession(products=[product])
        user = make_user()

        with patch("src.app.api.routes.shop_router.BalanceRepository") as MockBalanceRepo:
            balance_instance = MockBalanceRepo.return_value

            async def _change_balance(*args: Any, **kwargs: Any) -> None:
                raise NotEnoughBalanceError("Not enough balance")

            balance_instance.change_balance = AsyncMock(side_effect=_change_balance)

            amocrm_service = AsyncMock()

            payload = CreateOrderRequest(
                items=[OrderItemRequest(item_id=4, quantity=1)],
                pay_with_bonus=True,
            )

            with pytest.raises(HTTPException) as exc:
                await shop_router.create_order(
                    payload=payload,
                    db=db,  # type: ignore[arg-type]
                    user=user,
                    amocrm_service=amocrm_service,
                )

        error = exc.value
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert "Not enough bonus balance" in error.detail

        # В AmoCRM заказ в этом случае не должен уходить
        amocrm_service.send_order_to_amocrm.assert_not_awaited()

    async def test_more_than_one_item_not_allowed(self) -> None:
        """
        В корзине может быть только один товар — проверяем 400 и отсутствие побочных эффектов.
        """
        product1 = Product(
            id=10,
            name="Смена в Сочи",
            price_bonus=0,
            price_money=100_000,
            category="camp_sochi",
        )
        product2 = Product(
            id=11,
            name="Футболка мерч",
            price_bonus=3_000,
            price_money=None,
            category="merch",
        )
        db = FakeSession(products=[product1, product2])
        user = make_user()

        with patch("src.app.api.routes.shop_router.BalanceRepository") as MockBalanceRepo:
            balance_instance = MockBalanceRepo.return_value
            balance_instance.change_balance = AsyncMock()

            amocrm_service = AsyncMock()

            payload = CreateOrderRequest(
                items=[
                    OrderItemRequest(item_id=10, quantity=1),
                    OrderItemRequest(item_id=11, quantity=1),
                ],
                pay_with_bonus=False,
            )

            with pytest.raises(HTTPException) as exc:
                await shop_router.create_order(
                    payload=payload,
                    db=db,  # type: ignore[arg-type]
                    user=user,
                    amocrm_service=amocrm_service,
                )

        error = exc.value
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert "одним товаром" in str(error.detail)

        balance_instance.change_balance.assert_not_awaited()
        amocrm_service.send_order_to_amocrm.assert_not_awaited()

