from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.amocrm_models import AmoTransaction, AmoTransactionStatus


class AmoTransactionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, id_: int) -> AmoTransaction | None:
        return await self.db.get(AmoTransaction, id_)

    async def get_by_event_id(self, event_id: str) -> AmoTransaction | None:
        stmt = select(AmoTransaction).where(AmoTransaction.amocrm_event_id == event_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_from_payload(
        self,
        payload: dict[str, Any],
        amocrm_event_id: str | None,
        amocrm_lead_id: int | None,
        order_id: int | None = None,
    ) -> AmoTransaction:
        if amocrm_event_id:
            existing = await self.get_by_event_id(amocrm_event_id)
            if existing:
                return existing

        tx = AmoTransaction(
            amocrm_event_id=amocrm_event_id,
            amocrm_lead_id=amocrm_lead_id,
            order_id=order_id,
            payload=jsonable_encoder(payload),
            status=AmoTransactionStatus.NEW,
        )
        self.db.add(tx)
        await self.db.flush()
        await self.db.refresh(tx)
        return tx

    async def mark_processed(self, tx: AmoTransaction) -> AmoTransaction:
        tx.status = AmoTransactionStatus.PROCESSED
        self.db.add(tx)
        await self.db.flush()
        await self.db.refresh(tx)
        return tx

    async def mark_error(self, tx: AmoTransaction, message: str) -> AmoTransaction:
        tx.status = AmoTransactionStatus.ERROR
        tx.error_message = message
        self.db.add(tx)
        await self.db.flush()
        await self.db.refresh(tx)
        return tx
