from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


WebhookEvent = Literal["add", "update", "delete", "status", "responsible"]


class WebhookTransaction(BaseModel):
    id: int
    customer_id: int
    price: int
    comment: Optional[str] = None
    created_at: int
    next_price: Optional[int] = None
    next_date: Optional[int] = None


class TransactionWebhook(BaseModel):
    account_id: int = Field(..., description="ID аккаунта AmoCRM")
    event: WebhookEvent = Field(..., description="Тип события в AmoCRM")
    transaction: WebhookTransaction = Field(..., description="Данные транзакции")

    class Config:
        extra = "ignore"


class StoredTransaction(BaseModel):
    id: int
    customer_id: int
    price: int
    comment: Optional[str] = None

    created_at: int
    completed_at: Optional[int] = None

    next_price: Optional[int] = None
    next_date: Optional[int] = None

    webhook_received_at: datetime
    account_id: int
    event_type: str

    @classmethod
    def from_webhook(cls, webhook: "TransactionWebhook") -> "StoredTransaction":
        tx = webhook.transaction

        return cls(
            id=tx.id,
            customer_id=tx.customer_id,
            price=tx.price,
            comment=tx.comment,
            created_at=tx.created_at,
            completed_at=None,
            next_price=tx.next_price,
            next_date=tx.next_date,
            webhook_received_at=datetime.now(),
            account_id=webhook.account_id,
            event_type=webhook.event,
        )


class WebhookResponse(BaseModel):
    status: str = "ok"
    message: str = "Webhook processed successfully"
