# src/app/api/routes/news_router.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.session import get_db
from src.app.models.news_models import News
from src.app.schemas.miniapp_schemas import NewsItem

router = APIRouter(prefix="/api/news", tags=["News"])


@router.get("", response_model=list[NewsItem])
async def get_news(
  db: AsyncSession = Depends(get_db),
  limit: int = 50,
  offset: int = 0,
) -> list[NewsItem]:
  stmt = (
    select(News)
    .where(News.is_published.is_(True))
    .order_by(News.published_at.desc(), News.id.desc())
    .offset(offset)
    .limit(limit)
  )
  result = await db.execute(stmt)
  rows = result.scalars().all()
  return [NewsItem.model_validate(row, from_attributes=True) for row in rows]
