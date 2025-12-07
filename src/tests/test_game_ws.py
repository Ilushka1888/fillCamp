from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, WebSocketDisconnect, status
from fastapi.testclient import TestClient

from src.app.api.routes import game_router
from src.app.api.deps import get_current_user
from src.app.db.session import get_db
from src.app.models.user_models import User, UserRole
from src.app.schemas.miniapp_schemas import GameClickResponse


class DummyDB:
    """Простейший объект вместо AsyncSession для зависимостей get_db."""
    pass


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    app.include_router(game_router.router)

    # подменяем get_db, чтобы не дергать настоящую БД
    dummy_db = DummyDB()

    def override_get_db() -> DummyDB:
        return dummy_db

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.mark.api
@pytest.mark.game
class TestGameWebSocket:
    def test_ws_rejects_without_telegram_id(self, client: TestClient) -> None:
        """
        Если не передан X-Telegram-Id — соединение закрывается с 4401.
        """
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect("/api/game/ws") as ws:  # noqa: F841
                pass

        assert exc.value.code == 4401

    def test_ws_rejects_non_child_role(self, client: TestClient) -> None:
        """
        Пользователь с ролью != CHILD — соединение закрывается с 4403.
        """
        non_child_user = User(
            id=1,
            telegram_id=123,
            full_name="Parent User",
            phone="+79990000000",
            role=UserRole.PARENT,
        )

        with patch("src.app.api.routes.game_router.UserRepository") as MockUserRepo:
            user_repo_instance = MockUserRepo.return_value
            user_repo_instance.get_by_telegram_id = AsyncMock(
                return_value=non_child_user
            )
            user_repo_instance.touch_app_activity = AsyncMock()

            with pytest.raises(WebSocketDisconnect) as exc:
                with client.websocket_connect(
                    "/api/game/ws",
                    headers={"X-Telegram-Id": "123"},
                ) as ws:  # noqa: F841
                    pass

        assert exc.value.code == 4403

    def test_ws_click_flow_for_child(self, client: TestClient) -> None:
        """
        Для ребёнка:
        - соединение устанавливается,
        - при сообщении {"type": "click"} вызывается _process_click,
        - клиент получает event="click" с корректными данными.
        """
        child_user = User(
            id=42,
            telegram_id=555,
            full_name="Child User",
            phone="+79990000001",
            role=UserRole.CHILD,
        )

        fake_response = GameClickResponse(
            new_bonus_balance=10,
            game_progress=3,
        )

        with patch("src.app.api.routes.game_router.UserRepository") as MockUserRepo, patch(
            "src.app.api.routes.game_router._process_click",
            new_callable=AsyncMock,
        ) as mock_process_click:
            user_repo_instance = MockUserRepo.return_value
            user_repo_instance.get_by_telegram_id = AsyncMock(
                return_value=child_user
            )
            user_repo_instance.touch_app_activity = AsyncMock()

            mock_process_click.return_value = fake_response

            with client.websocket_connect(
                "/api/game/ws",
                headers={"X-Telegram-Id": "555"},
            ) as ws:
                ws.send_json({"type": "click"})
                data = ws.receive_json()

        assert data["event"] == "click"
        assert data["new_bonus_balance"] == 10
        assert data["game_progress"] == 3

        assert mock_process_click.await_count == 1
        args, kwargs = mock_process_click.call_args
        # args[0] — db, args[1] — user
        assert isinstance(args[1], User)
        assert args[1].id == child_user.id
        assert args[1].role == UserRole.CHILD

    def test_ws_unsupported_message_type(self, client: TestClient) -> None:
        """
        Если отправить сообщение с другим type, сервер должен вернуть event="error".
        """
        child_user = User(
            id=99,
            telegram_id=777,
            full_name="Child User",
            phone="+79990000002",
            role=UserRole.CHILD,
        )

        with patch("src.app.api.routes.game_router.UserRepository") as MockUserRepo, patch(
            "src.app.api.routes.game_router._process_click",
            new_callable=AsyncMock,
        ) as mock_process_click:
            user_repo_instance = MockUserRepo.return_value
            user_repo_instance.get_by_telegram_id = AsyncMock(
                return_value=child_user
            )
            user_repo_instance.touch_app_activity = AsyncMock()

            mock_process_click.return_value = GameClickResponse(
                new_bonus_balance=100,
                game_progress=50,
            )

            with client.websocket_connect(
                "/api/game/ws",
                headers={"X-Telegram-Id": "777"},
            ) as ws:
                ws.send_json({"type": "unknown"})
                data = ws.receive_json()

        assert data["event"] == "error"
        assert "Unsupported message type" in data["detail"]
        mock_process_click.assert_not_awaited()


@pytest.mark.api
@pytest.mark.game
class TestGameHttpClick:
    def test_http_click_uses_process_click(self, app: FastAPI, client: TestClient) -> None:
        """
        /api/game/click должен вызывать _process_click и возвращать его результат.
        """
        child_user = User(
            id=50,
            telegram_id=999,
            full_name="Child User",
            phone="+79990000003",
            role=UserRole.CHILD,
        )

        async def override_get_current_user() -> User:
            return child_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        fake_response = GameClickResponse(
            new_bonus_balance=123,
            game_progress=7,
        )

        with patch(
            "src.app.api.routes.game_router._process_click",
            new_callable=AsyncMock,
        ) as mock_process_click:
            mock_process_click.return_value = fake_response

            resp = client.post("/api/game/click")

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["new_bonus_balance"] == 123
        assert data["game_progress"] == 7

        mock_process_click.assert_awaited_once()
        args, kwargs = mock_process_click.call_args
        assert isinstance(args[1], User)
        assert args[1].id == child_user.id
