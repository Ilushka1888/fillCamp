from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.shop_models import (
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
)


class OrderRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, order_id: int) -> Order | None:
        return await self.db.get(Order, order_id)

    async def create_order(
        self,
        *,
        user_id: int,
        customer_name: str | None,
        customer_phone: str | None,
        amocrm_lead_id: int | None,
        items_data: Iterable[dict[str, Any]],
        payment_method: PaymentMethod,
        total_bonus: int = 0,
        total_money: float | None = None,
    ) -> Order:
        order = Order(
            user_id=user_id,
            status=OrderStatus.NEW,
            payment_method=payment_method,
            customer_name=customer_name,
            customer_phone=customer_phone,
            amocrm_lead_id=amocrm_lead_id,
            total_bonus=0,
            total_money=0,
        )

        bonus_sum = 0
        money_sum: float = 0

        for item_data in items_data:
            quantity = int(item_data.get("quantity", 1))
            unit_price_bonus = int(item_data.get("unit_price_bonus", 0))
            unit_price_money = item_data.get("unit_price_money")

            bonus_sum += unit_price_bonus * quantity
            if unit_price_money is not None:
                money_sum += float(unit_price_money) * quantity

            order_item = OrderItem(
                product_id=item_data["product_id"],
                quantity=quantity,
                unit_price_bonus=unit_price_bonus,
                unit_price_money=unit_price_money,
            )
            order.items.append(order_item)

        order.total_bonus = total_bonus if total_bonus else bonus_sum
        order.total_money = (
            total_money if total_money is not None else money_sum or None
        )

        self.db.add(order)
        await self.db.flush()
        await self.db.refresh(order)
        return order

    async def get_last_unpaid_by_amocrm_lead_id(
        self,
        amocrm_lead_id: int,
    ) -> Order | None:
        stmt = (
            select(Order)
            .where(
                Order.amocrm_lead_id == amocrm_lead_id,
                Order.status.in_([OrderStatus.NEW, OrderStatus.PENDING_PAYMENT]),
            )
            .order_by(Order.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_paid(self, order: Order, amount: float | None = None) -> Order:
        if amount is not None and order.total_money is None:
            order.total_money = amount
        order.status = OrderStatus.PAID
        self.db.add(order)
        await self.db.flush()
        await self.db.refresh(order)
        return order
