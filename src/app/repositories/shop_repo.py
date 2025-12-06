from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.models.shop_models import Order, OrderItem, OrderStatus, Product
from src.app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Product)

    def get_active(self, limit: int = 100, offset: int = 0) -> list[Product]:
        stmt = (
            select(Product)
            .where(Product.is_active.is_(True))
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(stmt))


class OrderRepository(BaseRepository[Order]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Order)

    def get_for_user(
        self, user_id: int, limit: int = 50, offset: int = 0
    ) -> list[Order]:
        stmt = (
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def get_by_amocrm_lead_id(self, lead_id: int) -> Order | None:
        stmt = select(Order).where(Order.amocrm_lead_id == lead_id)
        return self.db.scalar(stmt)

    def update_status(self, order: Order, status: OrderStatus) -> Order:
        order.status = status
        self.db.add(order)
        self.db.flush()
        self.db.refresh(order)
        return order


class OrderItemRepository(BaseRepository[OrderItem]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, OrderItem)

    def get_for_order(self, order_id: int) -> list[OrderItem]:
        stmt = select(OrderItem).where(OrderItem.order_id == order_id)
        return list(self.db.scalars(stmt))
