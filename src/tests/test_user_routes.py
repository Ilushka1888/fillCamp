from __future__ import annotations

from datetime import datetime
from typing import Generator

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient


@pytest.fixture
def app() -> FastAPI:
    from src.app.api.routes import user_router

    app = FastAPI()
    app.include_router(user_router.router)
    return app


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(app) as client:
        yield client


class DummyUser:
    def __init__(
        self,
        telegram_id: int,
        first_name: str | None,
        last_name: str | None,
        username: str | None,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self.telegram_id = telegram_id
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.created_at = created_at
        self.updated_at = updated_at


@pytest.mark.api
@pytest.mark.user
def test_get_user_info_returns_current_user_data(client: TestClient) -> None:
    from src.app.api import deps

    # подсовываем фейкового пользователя, вместо настоящего из БД
    dummy_user = DummyUser(
        telegram_id=123456789,
        first_name="Ivan",
        last_name="Ivanov",
        username="ivan_i",
        created_at=datetime(2025, 1, 1, 12, 0, 0),
        updated_at=datetime(2025, 1, 2, 13, 30, 0),
    )

    async def override_get_current_user() -> DummyUser:
        return dummy_user

    # переопределяем зависимость get_current_user на время теста
    client.app.dependency_overrides[deps.get_current_user] = override_get_current_user

    response = client.get(
        "/api/user",
        headers={"X-Telegram-Id": str(dummy_user.telegram_id)},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["telegram_id"] == dummy_user.telegram_id
    assert data["first_name"] == dummy_user.first_name
    assert data["last_name"] == dummy_user.last_name
    assert data["username"] == dummy_user.username
    assert data["created_at"] == dummy_user.created_at.isoformat()
    assert data["updated_at"] == dummy_user.updated_at.isoformat()
