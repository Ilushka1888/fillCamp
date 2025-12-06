from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.db.base import Base


class AmoTransactionStatus(str, Enum):
    NEW = "new"
    PROCESSED = "processed"
    ERROR = "error"


class AmoTransaction(Base):
    __tablename__ = "amo_transactions"

    __table_args__ = (
        UniqueConstraint(
            "amocrm_event_id",
            name="uq_amo_transactions_amocrm_event_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    amocrm_event_id: Mapped[str | None] = mapped_column(String(255), index=True)
    amocrm_lead_id: Mapped[int | None] = mapped_column(Integer, index=True)

    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), index=True
    )

    payload: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[AmoTransactionStatus] = mapped_column(
        SQLEnum(AmoTransactionStatus, name="amo_transaction_status"),
        nullable=False,
        default=AmoTransactionStatus.NEW,
    )
    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    order: Mapped["Order | None"] = relationship("Order")
