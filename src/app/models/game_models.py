from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.db.base import Base


class GameStats(Base):
    __tablename__ = "game_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    total_clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    last_click_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    clicks_today: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clicks_today_date: Mapped[date | None] = mapped_column(Date)

    user: Mapped["User"] = relationship("User", back_populates="game_stats")
