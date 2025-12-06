from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.db.base import Base


class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    inviter_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invited_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    reward_given: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reward_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    inviter: Mapped["User"] = relationship(
        "User",
        foreign_keys=[inviter_user_id],
        back_populates="referrals_given",
    )
    invited: Mapped["User"] = relationship(
        "User",
        foreign_keys=[invited_user_id],
        back_populates="referrals_received",
    )
