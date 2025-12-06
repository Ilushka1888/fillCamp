from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.services.amocrm_client import AmoCRMClient
from src.app.core.logger import get_logger
from src.app.db.session import get_db
from src.app.models import User
from src.app.models.shop_models import (
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    Product,
)
from src.app.schemas.amocrm_schemas import TransactionWebhook, WebhookResponse
from src.app.services.amocrm_service import AmoCRMService

logger = get_logger(__name__)

router = APIRouter(
    prefix="/amocrm",
    tags=["AmoCRM"],
)


def get_amocrm_service(db: AsyncSession = Depends(get_db)) -> AmoCRMService:
    return AmoCRMService(db)


def _get_amocrm_oauth_config() -> tuple[str, str, str, str]:
    subdomain = os.getenv("CAMPBOT_AMOCRM_SUBDOMAIN", "").strip()
    client_id = os.getenv("CAMPBOT_AMOCRM_CLIENT_ID", "").strip()
    client_secret = os.getenv("CAMPBOT_AMOCRM_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv("CAMPBOT_AMOCRM_REDIRECT_URI", "").strip()

    if not subdomain or not client_id or not client_secret or not redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "AmoCRM OAuth не сконфигурирован. "
                "Проверь CAMPBOT_AMOCRM_SUBDOMAIN, CAMPBOT_AMOCRM_CLIENT_ID, "
                "CAMPBOT_AMOCRM_CLIENT_SECRET и CAMPBOT_AMOCRM_REDIRECT_URI в .env."
            ),
        )

    base_url = f"https://{subdomain}.amocrm.ru"
    return base_url, client_id, client_secret, redirect_uri


@router.get("/oauth/start")
async def amocrm_oauth_start():
    client = AmoCRMClient()
    url = client.build_authorization_url()
    return {"auth_url": url}


@router.get("/oauth/callback")
async def amocrm_oauth_callback(code: str | None = None):
    if not code:
        raise HTTPException(400, "Missing code")

    client = AmoCRMClient()
    token = await client.exchange_code_for_tokens(code)
    return {
        "access_token": token.access_token,
        "refresh_token": token.refresh_token,
        "expires_at": token.expires_at.isoformat(),
    }


@router.post("/webhooks/transaction", response_model=WebhookResponse)
async def receive_transaction_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    service: AmoCRMService = Depends(get_amocrm_service),
) -> WebhookResponse:
    raw_body: bytes | None = None

    try:
        raw_body = await request.body()
        body_str = raw_body.decode("utf-8")
        logger.debug("Получен вебхук AmoCRM: %s", body_str)

        payload: dict[str, Any] = json.loads(body_str)
        webhook = TransactionWebhook.model_validate(payload)

    except ValidationError as e:
        logger.error("Ошибка валидации вебхука AmoCRM: %s", e)
        return WebhookResponse(
            status="error",
            message="Invalid webhook payload",
        )
    except json.JSONDecodeError as e:
        logger.error("Ошибка при разборе JSON: %s", e)
        if raw_body is not None:
            logger.error("Проблемное тело: %s", raw_body[:1000])
        return WebhookResponse(
            status="error",
            message=f"Invalid JSON: {str(e)}",
        )
    except Exception as e:
        logger.error(
            "Неожиданная ошибка при разборе вебхука AmoCRM: %s",
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse transaction webhook",
        )

    try:
        background_tasks.add_task(service.handle_transaction_webhook, webhook)
        return WebhookResponse(
            status="ok",
            message="Webhook accepted for processing",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ошибка при обработке вебхука транзакции: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process transaction webhook",
        )


@router.post("/orders/{order_id}/send", response_model=WebhookResponse)
async def send_order_to_amocrm_endpoint(
    order_id: int,
    service: AmoCRMService = Depends(get_amocrm_service),
) -> WebhookResponse:
    order = await service.db.get(Order, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    await service.send_order_to_amocrm(order)
    await service.db.refresh(order)

    return WebhookResponse(
        status="ok",
        message=f"Order {order.id} sent to AmoCRM, lead_id={order.amocrm_lead_id}",
    )


@router.post("/test-order/send", response_model=WebhookResponse)
async def create_test_order_and_send(
    service: AmoCRMService = Depends(get_amocrm_service),
) -> WebhookResponse:
    db = service.db

    result = await db.execute(select(Product).limit(1))
    product = result.scalar_one_or_none()
    if product is None:
        product = Product(
            name="Тестовый товар",
            description="Тестовый товар для AmoCRM",
            image_url=None,
            price_bonus=100,
            price_money=150.00,
            category="test",
            is_active=True,
        )
        db.add(product)
        await db.flush()
        await db.refresh(product)

    user_id = 6

    order = Order(
        user_id=user_id,
        status=OrderStatus.NEW,
        total_bonus=0,
        total_money=product.price_money,
        payment_method=PaymentMethod.CARD_ONLY,
        customer_name="Тестовый Пользователь",
        customer_phone="+79990000000",
        amocrm_lead_id=None,
    )
    db.add(order)
    await db.flush()
    await db.refresh(order)

    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=1,
        unit_price_bonus=product.price_bonus,
        unit_price_money=product.price_money,
    )
    db.add(item)
    await db.flush()
    await db.refresh(order)

    await service.send_order_to_amocrm(order)
    await db.refresh(order)

    return WebhookResponse(
        status="ok",
        message=f"Test order {order.id} sent to AmoCRM, lead_id={order.amocrm_lead_id}",
    )


@router.post("/test-flow/user-6/full", response_model=dict[str, Any])
async def run_full_test_flow_for_user_6(
    service: AmoCRMService = Depends(get_amocrm_service),
) -> dict[str, Any]:
    db: AsyncSession = service.db

    result = await db.execute(select(User).where(User.id == 6))
    user: User | None = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь с id=6 не найден в БД",
        )

    result = await db.execute(select(Product).limit(1))
    product: Product | None = result.scalar_one_or_none()
    if product is None:
        product = Product(
            name="Тестовый товар для AmoCRM",
            description="Автоматически созданный тестовый товар для тестового флоу AmoCRM",
            image_url=None,
            price_bonus=0,
            price_money=150.00,
            category="test",
            is_active=True,
        )
        db.add(product)
        await db.flush()
        await db.refresh(product)

    customer_name = (
        getattr(user, "first_name", None)
        or getattr(user, "full_name", None)
        or "Тестовый Пользователь"
    )
    customer_phone = getattr(user, "phone", "+79990000000")

    order = Order(
        user_id=user.id,
        status=OrderStatus.NEW,
        total_bonus=0,
        total_money=product.price_money,
        payment_method=PaymentMethod.CARD_ONLY,
        customer_name=customer_name,
        customer_phone=customer_phone,
        amocrm_lead_id=None,
    )
    db.add(order)
    await db.flush()
    await db.refresh(order)

    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=1,
        unit_price_bonus=product.price_bonus,
        unit_price_money=product.price_money,
    )
    db.add(item)
    await db.flush()
    await db.refresh(order)

    await service.send_order_to_amocrm(order)
    await db.refresh(order)

    if not order.amocrm_lead_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AmoCRM lead_id не установился на заказе. Проверь send_order_to_amocrm.",
        )

    now = int(time.time())
    webhook_dict = {
        "account_id": 12345678,
        "event": "add",
        "transaction": {
            "id": now,
            "customer_id": order.amocrm_lead_id,
            "price": int(order.total_money or 0),
            "comment": f"Тестовая оплата локального заказа {order.id}",
            "created_at": now,
            "next_price": 0,
            "next_date": None,
        },
    }

    webhook = TransactionWebhook.model_validate(webhook_dict)
    webhook_result: WebhookResponse = await service.handle_transaction_webhook(webhook)
    await db.refresh(order)

    logger.info(
        "Полный тестовый флоу для user_id=%s, order_id=%s: status=%s, lead_id=%s",
        user.id,
        order.id,
        order.status,
        order.amocrm_lead_id,
    )

    return {
        "webhook_result": webhook_result.model_dump(),
        "order": {
            "id": order.id,
            "status": str(order.status),
            "total_money": (
                float(order.total_money) if order.total_money is not None else 0
            ),
            "amocrm_lead_id": order.amocrm_lead_id,
        },
        "product": {
            "id": product.id,
            "name": product.name,
            "price_money": float(product.price_money),
        },
        "user": {
            "id": user.id,
            "name": customer_name,
            "phone": customer_phone,
        },
    }
