from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.db.base import Base


class UserRole(str, Enum):
    CHILD = "child"
    PARENT = "parent"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )

    username: Mapped[str | None] = mapped_column(String(255), index=True)
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(512))

    photo_url: Mapped[str | None] = mapped_column(Text)

    phone: Mapped[str | None] = mapped_column(String(32), index=True)

    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.PARENT,
    )

    # связь ребенок → родитель (для родителя null)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    parent: Mapped["User | None"] = relationship(
        "User",
        remote_side="User.id",
        back_populates="children",
    )
    children: Mapped[list["User"]] = relationship(
        "User",
        back_populates="parent",
        cascade="all,delete-orphan",
    )

    is_subscribed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    last_app_interaction_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    last_bot_interaction_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # relationships
    balance: Mapped["Balance | None"] = relationship(
        "Balance", uselist=False, back_populates="user"
    )
    transactions: Mapped[list["BalanceTransaction"]] = relationship(
        "BalanceTransaction", back_populates="user"
    )
    game_stats: Mapped["GameStats | None"] = relationship(
        "GameStats", uselist=False, back_populates="user"
    )
    referrals_given: Mapped[list["Referral"]] = relationship(
        "Referral",
        foreign_keys="Referral.inviter_user_id",
        back_populates="inviter",
    )
    referrals_received: Mapped[list["Referral"]] = relationship(
        "Referral",
        foreign_keys="Referral.invited_user_id",
        back_populates="invited",
    )
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user")
    broadcasts_created: Mapped[list["Broadcast"]] = relationship(
        "Broadcast",
        foreign_keys="Broadcast.created_by_admin_id",
        back_populates="created_by_admin",
    )
