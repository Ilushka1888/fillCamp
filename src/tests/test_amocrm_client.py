from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.app.services.amocrm_client import AmoCRMClient, AmoCRMToken


@pytest.mark.anyio
@pytest.mark.unit
@pytest.mark.amocrm
class TestAmoCRMClient:
    async def test_create_lead_with_contact_success(self):
        # create_lead_with_contact ожидает, что .json() вернёт список с лидами
        mock_response_data = [
            {
                "id": 123,
            }
        ]

        with patch("src.app.services.amocrm_client.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            # Клиент — это AsyncMock, а не контекстный менеджер
            mock_client.return_value = mock_instance

            mock_http_response = AsyncMock(spec=httpx.Response)
            mock_http_response.status_code = 200
            mock_http_response.json.return_value = mock_response_data
            mock_http_response.raise_for_status = MagicMock()

            mock_instance.post.return_value = mock_http_response

            client = AmoCRMClient()
            client.base_url = "https://test.amocrm.ru"

            # Мокаем валидный токен, чтобы не лезть в файловое хранилище
            valid_token = AmoCRMToken(
                access_token="test_token",
                refresh_token="refresh_token",
                token_type="Bearer",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )

            with patch.object(
                AmoCRMClient,
                "get_valid_token",
                new=AsyncMock(return_value=valid_token),
            ) as mock_get_token:
                result = await client.create_lead_with_contact(
                    name="Заказ #1",
                    price=15000,
                    phone="+79990000000",
                    lead_custom_fields=[
                        {
                            "field_name": "Local order ID",
                            "values": [{"value": 1}],
                        }
                    ],
                    contact_custom_fields=None,
                    tags=["MiniApp"],
                )

            # Теперь метод возвращает id лида, а не весь JSON
            assert result == 123

            # Проверяем, что токен запрошен
            mock_get_token.assert_awaited_once()

            # Проверяем, что запрос к /leads/complex ушёл ровно один раз
            mock_instance.post.assert_awaited_once()
            post_args, post_kwargs = mock_instance.post.call_args
            assert post_args[0] == "/leads/complex"
            assert "json" in post_kwargs

            # Проверяем, как создали AsyncClient
            _, client_kwargs = mock_client.call_args
            assert client_kwargs["base_url"] == "https://test.amocrm.ru/api/v4"
            headers = client_kwargs["headers"]
            assert headers["Authorization"] == "Bearer test_token"
            assert headers["Content-Type"] == "application/json"

    async def test_create_lead_with_contact_http_error(self):
        with patch("src.app.services.amocrm_client.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            # То же самое: клиент = AsyncMock
            mock_client.return_value = mock_instance

            mock_http_response = AsyncMock(spec=httpx.Response)
            mock_http_response.status_code = 400
            http_error = httpx.HTTPStatusError(
                "Bad Request",
                request=MagicMock(),
                response=mock_http_response,
            )
            mock_http_response.raise_for_status = MagicMock(side_effect=http_error)
            mock_instance.post.return_value = mock_http_response

            client = AmoCRMClient()
            client.base_url = "https://test.amocrm.ru"

            valid_token = AmoCRMToken(
                access_token="test_token",
                refresh_token="refresh_token",
                token_type="Bearer",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )

            with patch.object(
                AmoCRMClient,
                "get_valid_token",
                new=AsyncMock(return_value=valid_token),
            ):
                with pytest.raises(httpx.HTTPStatusError):
                    await client.create_lead_with_contact(
                        name="Заказ #1",
                        price=15000,
                        phone="+79990000000",
                        lead_custom_fields=None,
                        contact_custom_fields=None,
                        tags=None,
                    )

            # Убедимся, что вызов к API был
            mock_instance.post.assert_awaited_once()
            # И что клиент корректно закрывается (aclose тоже awaitable)
            mock_instance.aclose.assert_awaited_once()
