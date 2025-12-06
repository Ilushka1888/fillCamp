from __future__ import annotations

import json
from typing import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from src.app.schemas.amocrm_schemas import TransactionWebhook


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    from src.app.api.routes import amocrm_router

    app = FastAPI()
    app.include_router(amocrm_router.router)

    with TestClient(app) as client:
        yield client


@pytest.mark.api
@pytest.mark.amocrm
class TestAmoCRMWebhookEndpoint:
    def test_receive_transaction_webhook_success(
        self,
        test_client: TestClient,
        sample_transaction_webhook: dict,
    ) -> None:
        with patch(
            "src.app.api.routes.amocrm_router.AmoCRMService.handle_transaction_webhook",
            new_callable=AsyncMock,
        ) as mock_handler:
            mock_handler.return_value = None

            response = test_client.post(
                "/amocrm/webhooks/transaction",
                json=sample_transaction_webhook,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["message"] == "Webhook accepted for processing"

        mock_handler.assert_awaited_once()
        args, kwargs = mock_handler.call_args
        assert isinstance(args[0], TransactionWebhook)

    def test_receive_invalid_webhook_payload(self, test_client: TestClient) -> None:
        invalid_payload = {"invalid": "data"}

        response = test_client.post(
            "/amocrm/webhooks/transaction",
            json=invalid_payload,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "error"
        assert data["message"] == "Invalid webhook payload"

    def test_receive_invalid_json(self, test_client: TestClient) -> None:
        raw_body = "not-a-json"

        response = test_client.post(
            "/amocrm/webhooks/transaction",
            data=raw_body,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "error"
        assert data["message"].startswith("Invalid JSON:")
