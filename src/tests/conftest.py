from __future__ import annotations

import os
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient


os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("CAMPBOT_AMOCRM_SUBDOMAIN", "test")
os.environ.setdefault("CAMPBOT_TELEGRAM_BOT_TOKEN", "123456:TESTTOKEN")


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    from src.app.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    from src.app.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_transaction_webhook() -> dict:
    return {
        "account_id": 12345678,
        "event": "add",
        "entity": "customer_transaction",
        "created_at": 1704067200,
        "transaction": {
            "id": 999,
            "customer_id": 888,
            "price": 15000,
            "comment": "Оплата за путевку",
            "created_at": 1704067200,
            "next_price": None,
            "next_date": None,
        },
    }
