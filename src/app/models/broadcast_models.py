from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.db.base import Base


class BroadcastType(str, Enum):
    MANUAL = "manual"
    AUTO_INACTIVE = "auto_inactive"


class BroadcastStatus(str, Enum):
    SCHEDULED = "scheduled"
    SENT = "sent"
    CANCELED = "canceled"


class Broadcast(Base):
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    type: Mapped[BroadcastType] = mapped_column(
        SQLEnum(BroadcastType, name="broadcast_type"),
        nullable=False,
        default=BroadcastType.MANUAL,
    )

    text: Mapped[str] = mapped_column(Text, nullable=False)
    keyboard_json: Mapped[str | None] = mapped_column(Text)  # inline-кнопки в JSON

    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    status: Mapped[BroadcastStatus] = mapped_column(
        SQLEnum(BroadcastStatus, name="broadcast_status"),
        nullable=False,
        default=BroadcastStatus.SCHEDULED,
    )

    created_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    created_by_admin: Mapped["User | None"] = relationship(
        "User", back_populates="broadcasts_created"
    )
