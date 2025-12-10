# src/app/api/routes/shop_router.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.api.deps import get_current_user
from src.app.db.session import get_db
from src.app.models.balance_models import TransactionType
from src.app.models.shop_models import (
  Order,
  OrderItem,
  OrderStatus,
  PaymentMethod,
  Product,
)
from src.app.models.user_models import User
from src.app.schemas.miniapp_schemas import (
  CreateOrderRequest,
  OrderItemResponse,
  OrderResponse,
  ShopItemResponse,
)

from src.app.repositories.balance_repo import BalanceRepository, NotEnoughBalanceError
from src.app.services.amocrm_service import AmoCRMService
from src.app.api.routes.amocrm_router import get_amocrm_service
from src.app.services.loyalty_service import (
    get_loyalty_rule_for_product,
    calc_bonus_writeoff,
    calc_bonus_accrual,
)

router = APIRouter(prefix="/api/shop", tags=["Shop"])


@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
        payload: CreateOrderRequest,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
        amocrm_service: AmoCRMService = Depends(get_amocrm_service),
) -> OrderResponse:
  if not payload.items:
    raise HTTPException(status_code=400, detail="Cart is empty")


  product_ids = [i.item for i in payload.items]
  stmt_products = select(Product).where(
    Product.id.in_(product_ids),
    Product.is_active.is_(True),
  )
  result_products = await db.execute(stmt_products)
  products = {p.id: p for p in result_products.scalars().all()}

  # Нельзя заказывать больше одного тура за раз
  for order_item in payload.items:
    product = products.get(order_item.item)
    if product is None:
      continue
    if product.category == "tour" and order_item.quantity > 1:
      raise HTTPException(
        status_code=400,
        detail=f"Тур '{product.name}' нельзя заказывать в количестве больше 1",
      )

  missing = [pid for pid in product_ids if pid not in products]
  if missing:
    raise HTTPException(
      status_code=400,
      detail=f"Products not found or inactive: {missing}",
    )

  # тут уже гарантированно 1 товар
  cart_item = payload.items[0]
  product = products[cart_item.item_id]
  quantity = cart_item.quantity

  # базовая цена в рублях
  price_money = float(product.price_money) if product.price_money is not None else 0.0
  total_money_raw = price_money * quantity

  # если цена в рублях не задана, берём price_bonus как "номинал" бонусов
  base_for_bonus = total_money_raw
  if base_for_bonus == 0 and product.price_bonus:
    base_for_bonus = float(product.price_bonus) * quantity

  rule = get_loyalty_rule_for_product(product)

  balance_repo = BalanceRepository(db)

  # ---------- СПИСАНИЕ БОНУСОВ ----------
  bonus_to_spend = 0
  if payload.pay_with_bonus:
    if rule is None:
      # Правила не настроены, а клиент пытается платить бонусами
      raise HTTPException(
        status_code=400,
        detail="Для этого товара не настроены бонусные правила, оплата бонусами запрещена",
      )

    bonus_to_spend = calc_bonus_writeoff(rule, base_for_bonus, quantity)

    if bonus_to_spend > 0:
      try:
        await balance_repo.change_balance(
          user=user,
          delta=-bonus_to_spend,
          tx_type=TransactionType.SHOP_PURCHASE,
          description=f"Списание бонусов за покупку товара #{product.id}",
        )
      except NotEnoughBalanceError:
        raise HTTPException(
          status_code=400,
          detail="Not enough bonus balance",
        )

  # сколько рублей реально платим после учёта бонусов
  total_money_to_store: float | None = None
  if total_money_raw > 0:
    total_money_to_store = max(total_money_raw - bonus_to_spend, 0.0)

  total_bonus_to_store = bonus_to_spend

  # ---------- НАЧИСЛЕНИЕ БОНУСОВ ----------
  bonus_to_accrue = 0
  if rule is not None:
    bonus_to_accrue = calc_bonus_accrual(rule, base_for_bonus, quantity)

  if bonus_to_accrue > 0:
    await balance_repo.change_balance(
      user=user,
      delta=bonus_to_accrue,
      tx_type=TransactionType.SHOP_PURCHASE,
      description=f"Начисление бонусов за покупку товара #{product.id}",
    )

  # ---------- СПОСОБ ОПЛАТЫ ----------
  if (total_money_to_store or 0) > 0 and bonus_to_spend > 0:
    payment_method = PaymentMethod.MIXED
  elif (total_money_to_store or 0) > 0:
    payment_method = PaymentMethod.CARD_ONLY
  elif bonus_to_spend > 0:
    payment_method = PaymentMethod.BONUS_ONLY
  else:
    payment_method = PaymentMethod.CARD_ONLY  # fallback

  # ---------- СОЗДАНИЕ ЗАКАЗА ----------
  order = Order(
    user_id=user.id,
    status=OrderStatus.NEW,
    total_bonus=total_bonus_to_store,
    total_money=total_money_to_store,
    payment_method=payment_method,
    customer_name=user.full_name,
    customer_phone=user.phone,
  )
  db.add(order)
  await db.flush()
  await db.refresh(order)

  order_item = OrderItem(
    order_id=order.id,
    product_id=product.id,
    quantity=quantity,
    unit_price_bonus=product.price_bonus,
    unit_price_money=product.price_money,
  )
  db.add(order_item)

  await db.flush()
  await db.commit()

  try:
    await amocrm_service.send_order_to_amocrm(order)
  except Exception:
    pass

  return OrderResponse(
    id=order.id,
    items=[
      OrderItemResponse(item=cart_item.item, quantity=cart_item.quantity)
    ],
    total_bonus=total_bonus_to_store,
    total_money=total_money_to_store,
    status=order.status.value,
  )

