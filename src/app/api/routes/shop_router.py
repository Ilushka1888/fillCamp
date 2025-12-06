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
from src.app.repositories.balance_repo import BalanceRepository, NotEnoughBalanceError
from src.app.schemas.miniapp_schemas import (
  CreateOrderRequest,
  OrderItemResponse,
  OrderResponse,
  ShopItemResponse,
)

router = APIRouter(prefix="/api/shop", tags=["Shop"])


@router.get("/items", response_model=list[ShopItemResponse])
async def get_items(
  db: AsyncSession = Depends(get_db),
) -> list[ShopItemResponse]:
  stmt = (
    select(Product)
    .where(Product.is_active.is_(True))
    .order_by(Product.name)
  )
  result = await db.execute(stmt)
  products = result.scalars().all()
  return [
    ShopItemResponse.model_validate(p, from_attributes=True)
    for p in products
  ]


@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
  payload: CreateOrderRequest,
  db: AsyncSession = Depends(get_db),
  user: User = Depends(get_current_user),
) -> OrderResponse:
  if not payload.items:
    raise HTTPException(status_code=400, detail="Cart is empty")

  product_ids = [i.item_id for i in payload.items]
  stmt_products = select(Product).where(
    Product.id.in_(product_ids),
    Product.is_active.is_(True),
  )
  result_products = await db.execute(stmt_products)
  products = {p.id: p for p in result_products.scalars().all()}

  missing = [pid for pid in product_ids if pid not in products]
  if missing:
    raise HTTPException(
      status_code=400,
      detail=f"Products not found or inactive: {missing}",
    )

  total_bonus = 0
  total_money = 0.0

  for item in payload.items:
    product = products[item.item_id]
    total_bonus += product.price_bonus * item.quantity
    if product.price_money is not None:
      total_money += float(product.price_money) * item.quantity

  balance_repo = BalanceRepository(db)

  payment_method: PaymentMethod
  total_bonus_to_store = 0
  total_money_to_store: float | None = None

  if payload.pay_with_bonus and total_bonus > 0:
    try:
      await balance_repo.change_balance(
        user=user,
        delta=-total_bonus,
        tx_type=TransactionType.SHOP_PURCHASE,
        description="Shop purchase",
      )
    except NotEnoughBalanceError:
      raise HTTPException(
        status_code=400,
        detail="Not enough bonus balance",
      )
    total_bonus_to_store = total_bonus

  if total_money > 0:
    if payload.pay_with_bonus and total_bonus > 0:
      payment_method = PaymentMethod.MIXED
    elif payload.pay_with_bonus:
      # бонусов нет, но флаг поставлен — считаем как карта
      payment_method = PaymentMethod.CARD_ONLY
    else:
      payment_method = PaymentMethod.CARD_ONLY
    total_money_to_store = total_money
  else:
    payment_method = PaymentMethod.BONUS_ONLY

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

  for item in payload.items:
    product = products[item.item_id]
    order_item = OrderItem(
      order_id=order.id,
      product_id=product.id,
      quantity=item.quantity,
      unit_price_bonus=product.price_bonus,
      unit_price_money=product.price_money,
    )
    db.add(order_item)

  await db.flush()
  await db.commit()

  return OrderResponse(
    id=order.id,
    items=[
      OrderItemResponse(item_id=i.item_id, quantity=i.quantity)
      for i in payload.items
    ],
    total_bonus=total_bonus_to_store,
    total_money=total_money_to_store,
    status=order.status.value,
  )
