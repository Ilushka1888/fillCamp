from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError
from urllib.parse import urlencode

from src.app.core.config import settings
from src.app.core.logger import get_logger

logger = get_logger(__name__)


class AmoCRMToken(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_at: datetime

    @classmethod
    def from_token_response(cls, data: dict[str, Any]) -> "AmoCRMToken":
        expires_in = int(data.get("expires_in", 3600))
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)

        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_at=expires_at,
        )


class AmoCRMTokenStorage:
    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            storage_root = (
                os.getenv("CAMPBOT_STORAGE_PATH")
                or getattr(settings, "storage_path", "./data")
                or "./data"
            )
            path = Path(storage_root) / "amocrm_token.json"

        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> AmoCRMToken | None:
        if not self.path.exists():
            return None
        try:
            raw = self.path.read_text(encoding="utf-8")
            data = json.loads(raw)
            return AmoCRMToken.model_validate(data)
        except Exception as e:
            logger.error("Failed to load AmoCRM token file: %s", e, exc_info=True)
            return None

    def save(self, token: AmoCRMToken) -> None:
        self.path.write_text(token.model_dump_json(), encoding="utf-8")
        logger.info(
            "AmoCRM access token saved to %s, expires_at=%s",
            self.path,
            token.expires_at.isoformat(),
        )


class AmoCRMClient:
    def __init__(self) -> None:
        base_url = ""

        try:
            base_url = settings.amocrm_base_url
        except Exception:
            base_url = ""

        if not base_url:
            subdomain = os.getenv("CAMPBOT_AMOCRM_SUBDOMAIN", "").strip()
            if subdomain:
                base_url = f"https://{subdomain}.amocrm.ru"

        if not base_url:
            base_url = "https://usmaxim.amocrm.ru"

        self.base_url = base_url.rstrip("/")

        env_client_id = os.getenv("CAMPBOT_AMOCRM_CLIENT_ID", "").strip()
        env_client_secret = os.getenv("CAMPBOT_AMOCRM_CLIENT_SECRET", "").strip()
        env_redirect_uri = os.getenv("CAMPBOT_AMOCRM_REDIRECT_URI", "").strip()

        self.client_id = getattr(settings, "amocrm_client_id", "") or env_client_id
        self.client_secret = (
            getattr(settings, "amocrm_client_secret", "") or env_client_secret
        )
        self.redirect_uri = (
            getattr(settings, "amocrm_redirect_uri", "") or env_redirect_uri
        )

        if not self.client_id or not self.client_secret or not self.redirect_uri:
            logger.warning(
                "AmoCRM OAuth не сконфигурирован полностью. "
                "client_id/secret/redirect_uri могут быть пустыми."
            )

        self.token_storage = AmoCRMTokenStorage()

    def build_authorization_url(self, state: str | None = None) -> str:
        if not self.client_id or not self.redirect_uri:
            raise RuntimeError(
                "AmoCRM OAuth не сконфигурирован. "
                "Проверь CAMPBOT_AMOCRM_CLIENT_ID и CAMPBOT_AMOCRM_REDIRECT_URI."
            )

        params: dict[str, str] = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
        }
        if state:
            params["state"] = state

        query = urlencode(params)
        return f"{self.base_url}/oauth2/authorize?{query}"

    async def exchange_code_for_tokens(self, code: str) -> AmoCRMToken:
        url = f"{self.base_url}/oauth2/access_token"

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        logger.info("AmoCRM: exchange_code_for_tokens payload: %s", payload)

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload)

            body_text = resp.text
            logger.error(
                "AmoCRM /oauth2/access_token response: status=%s, body=%s",
                resp.status_code,
                body_text,
            )

            resp.raise_for_status()
            data = resp.json()

        try:
            token = AmoCRMToken.from_token_response(data)
        except (KeyError, ValidationError) as e:
            logger.error("Failed to parse AmoCRM token response: %s, data=%s", e, data)
            raise

        self.token_storage.save(token)
        return token

    async def refresh_access_token(self, refresh_token: str) -> AmoCRMToken:
        if not self.client_id or not self.client_secret or not self.redirect_uri:
            raise RuntimeError(
                "AmoCRM OAuth не сконфигурирован. "
                "Проверь CAMPBOT_AMOCRM_CLIENT_ID, CAMPBOT_AMOCRM_CLIENT_SECRET "
                "и CAMPBOT_AMOCRM_REDIRECT_URI."
            )

        url = f"{self.base_url}/oauth2/access_token"

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "redirect_uri": self.redirect_uri,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        token = AmoCRMToken.from_token_response(data)
        self.token_storage.save(token)
        return token

    async def get_valid_token(self) -> AmoCRMToken:
        token = self.token_storage.load()
        now = datetime.now(timezone.utc)

        if token and token.expires_at > now:
            return token

        if token:
            logger.info("Refreshing expired AmoCRM access token...")
            return await self.refresh_access_token(token.refresh_token)

        raise RuntimeError(
            "AmoCRM access token is not configured. "
            "Сначала пройди OAuth: GET /api/v1/amocrm/oauth/start, "
            "затем /api/v1/amocrm/oauth/callback?code=... "
            "(callback должен вызывать exchange_code_for_tokens)."
        )

    async def _get_authorized_client(self) -> httpx.AsyncClient:
        token = await self.get_valid_token()
        headers = {
            "Authorization": f"{token.token_type} {token.access_token}",
            "Content-Type": "application/json",
        }
        return httpx.AsyncClient(
            base_url=f"{self.base_url}/api/v4",
            headers=headers,
            timeout=20.0,
        )

    async def create_lead_with_contact(
        self,
        name: str,
        price: int,
        phone: str | None,
        lead_custom_fields: list[dict] | None = None,
        contact_custom_fields: list[dict] | None = None,
        tags: list[str] | None = None,
    ) -> int | None:
        client = await self._get_authorized_client()
        try:
            contact_payload: dict[str, Any] = {}

            if phone:
                contact_payload["custom_fields_values"] = [
                    {
                        "field_code": "PHONE",
                        "values": [{"value": phone}],
                    }
                ]

            tags_payload = [{"name": t} for t in (tags or [])]

            lead_payload: dict[str, Any] = {
                "name": name,
                "price": price,
            }
            if tags_payload:
                lead_payload["tags"] = tags_payload

            payload = [
                {
                    **lead_payload,
                    "_embedded": {
                        "contacts": [contact_payload] if contact_payload else [],
                    },
                }
            ]

            resp = await client.post("/leads/complex", json=payload)

            if resp.status_code >= 400:
                logger.error(
                    "AmoCRM /leads/complex error: status=%s, body=%s",
                    resp.status_code,
                    resp.text,
                )

            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, list) and data:
                lead = data[0]
                lead_id = lead.get("id")
                logger.info("Created AmoCRM lead id=%s", lead_id)
                return int(lead_id) if lead_id is not None else None

            logger.error("Unexpected response from AmoCRM /leads/complex: %s", data)
            return None

        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error during AmoCRM lead creation: %s, response=%s",
                e,
                getattr(e.response, "text", None),
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error during AmoCRM lead creation: %s", e, exc_info=True
            )
            raise
        finally:
            await client.aclose()
