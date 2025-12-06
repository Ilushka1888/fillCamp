from __future__ import annotations

from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import selectinload

from src.app.db.base import Base
from src.app.models.shop_models import (
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    Product,
)
from src.app.services.amocrm_service import AmoCRMService


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)

    from src.app.models import shop_models  # noqa: F401
    from src.app.models import amocrm_models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.anyio
@pytest.mark.e2e
@pytest.mark.amocrm
async def test_send_order_to_amocrm_e2e(db_session: AsyncSession) -> None:
    product = Product(
        name="Тестовый товар",
        description="Описание",
        image_url=None,
        price_bonus=100,
        price_money=150.00,
        category="test",
        is_active=True,
    )
    db_session.add(product)
    await db_session.flush()

    order = Order(
        user_id=1,
        status=OrderStatus.NEW,
        total_bonus=200,
        total_money=300.00,
        payment_method=PaymentMethod.MIXED,
        customer_name="Иван Иванов",
        customer_phone="+79990000000",
        amocrm_lead_id=None,
    )

    order_item = OrderItem(
        product_id=product.id,
        quantity=2,
        unit_price_bonus=product.price_bonus,
        unit_price_money=product.price_money,
    )
    order_item.product = product
    order.items.append(order_item)

    db_session.add(order)
    await db_session.flush()
    order_id = order.id

    await db_session.commit()

    result = await db_session.execute(
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product),
        )
        .where(Order.id == order_id)
    )
    order_db = result.scalar_one()

    with patch("src.app.services.amocrm_service.AmoCRMClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client

        service = AmoCRMService(db_session)
        await service.send_order_to_amocrm(order_db)

        mock_client.create_lead_with_contact.assert_awaited_once()
        _, kwargs = mock_client.create_lead_with_contact.call_args

        expected_name = f"Заказ #{order_db.id} от {order_db.customer_name}"
        assert kwargs["name"] == expected_name

        assert kwargs["price"] == int(float(order_db.total_money))
        assert kwargs["phone"] == order_db.customer_phone

        lead_custom_fields = kwargs["lead_custom_fields"]
        assert any(
            f["field_name"] == "Local order ID"
            and f["values"][0]["value"] == order_db.id
            for f in lead_custom_fields
        )
        assert any(
            f["field_name"] == "Order items"
            and "Тестовый товар x 2" in f["values"][0]["value"]
            for f in lead_custom_fields
        )
        assert any(
            f["field_name"] == "Bonus spent"
            and f["values"][0]["value"] == order_db.total_bonus
            for f in lead_custom_fields
        )

        tags = kwargs["tags"]
        assert "MiniApp" in tags
        assert "Лагерь" in tags
