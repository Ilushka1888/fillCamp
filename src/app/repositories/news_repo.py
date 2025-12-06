from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.models.news_models import News
from src.app.repositories.base import BaseRepository


class NewsRepository(BaseRepository[News]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, News)

    def get_published(self, limit: int = 50, offset: int = 0) -> list[News]:
        stmt = (
            select(News)
            .where(News.is_published.is_(True))
            .order_by(News.published_at.desc(), News.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(stmt))
