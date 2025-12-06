from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.core.logger import get_logger
from src.app.models.amocrm_models import AmoTransactionStatus
from src.app.models.shop_models import Order, OrderItem, Product
from src.app.repositories.amo_transaction_repo import AmoTransactionRepository
from src.app.repositories.order_repo import OrderRepository
from src.app.schemas.amocrm_schemas import (
    StoredTransaction,
    TransactionWebhook,
    WebhookResponse,
)
from src.app.services.amocrm_client import AmoCRMClient

logger = get_logger(__name__)


class AmoCRMService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.tx_repo = AmoTransactionRepository(db)
        self.order_repo = OrderRepository(db)
        self.client = AmoCRMClient()

    async def handle_transaction_webhook(
        self,
        webhook: TransactionWebhook,
    ) -> WebhookResponse:
        stored: StoredTransaction = StoredTransaction.from_webhook(webhook)
        payload = stored.model_dump()

        amocrm_event_id = f"{stored.event_type}:{stored.id}"
        amocrm_lead_id = stored.customer_id

        order = await self.order_repo.get_last_unpaid_by_amocrm_lead_id(
            stored.customer_id
        )
        order_id = order.id if order else None  # type: ignore[union-attr]

        tx = await self.tx_repo.create_from_payload(
            payload=payload,
            amocrm_event_id=amocrm_event_id,
            amocrm_lead_id=amocrm_lead_id,
            order_id=order_id,
        )

        if tx.status == AmoTransactionStatus.PROCESSED:
            return WebhookResponse(
                status="ok",
                message="Transaction already processed",
            )

        try:
            await self._process_transaction(stored, order)
            await self.tx_repo.mark_processed(tx)
            return WebhookResponse(
                status="ok",
                message="Stored transaction processed",
            )
        except Exception as e:
            logger.exception("AmoCRM transaction processing error")
            await self.tx_repo.mark_error(tx, str(e))
            return WebhookResponse(
                status="error",
                message="Failed to process transaction",
            )

    async def _process_transaction(
        self,
        stored: StoredTransaction,
        order: Order | None,
    ) -> None:
        if not order:
            logger.info(
                "AmoCRM transaction without local order: customer_id=%s, tx_id=%s",
                stored.customer_id,
                stored.id,
            )
            return

        if stored.event_type in ("add", "update"):
            amount = float(stored.price)
            await self.order_repo.mark_paid(order, amount=amount)

    async def send_order_to_amocrm(self, order: Order) -> None:
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
            .where(Order.id == order.id)
        )
        order_db = result.scalar_one_or_none()
        if order_db is None:
            logger.error(
                "Order %s not found in DB when sending to AmoCRM",
                order.id,
            )
            return

        order = order_db

        phone = order.customer_phone
        full_name = order.customer_name

        total_money = float(order.total_money) if order.total_money is not None else 0
        total_bonus = order.total_bonus

        items_description_parts: list[str] = []
        for item in order.items:
            product_name = getattr(item.product, "name", f"ID {item.product_id}")
            items_description_parts.append(f"{product_name} x {item.quantity}")
        items_description = "; ".join(items_description_parts)

        lead_custom_fields: list[dict] = [
            {
                "field_name": "Local order ID",
                "values": [{"value": order.id}],
            },
            {
                "field_name": "Order items",
                "values": [{"value": items_description}],
            },
            {
                "field_name": "Bonus spent",
                "values": [{"value": total_bonus}],
            },
        ]

        contact_custom_fields: list[dict] = []

        lead_name = f"Заказ #{order.id}"
        if full_name:
            lead_name += f" от {full_name}"

        lead_id: int | None = None

        try:
            lead_id = await self.client.create_lead_with_contact(
                name=lead_name,
                price=int(total_money),
                phone=phone,
                lead_custom_fields=lead_custom_fields,
                contact_custom_fields=contact_custom_fields,
                tags=["MiniApp", "Лагерь"],
            )
        except Exception:
            logger.exception("Failed to send order %s to AmoCRM", order.id)
            return

        if lead_id is not None:
            order.amocrm_lead_id = int(lead_id)
            await self.db.commit()
            await self.db.refresh(order)
            logger.info(
                "Order %s successfully sent to AmoCRM, lead_id=%s",
                order.id,
                lead_id,
            )
