# src/app/schemas/miniapp_schemas.py
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NewsItem(BaseModel):
  id: int
  title: str
  text: str
  image_url: str | None = None
  created_at: datetime

  model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(BaseModel):
  id: int
  tg_id: int
  full_name: str
  username: str | None = None
  avatar_url: str | None = None
  role: Literal["child", "parent"]
  linked_parent_tg_id: int | None = None
  linked_child_tg_id: int | None = None
  bonus_balance: int = 0


class InvitedUserInfo(BaseModel):
  full_name: str
  tg_id: int


class ReferralInfoResponse(BaseModel):
  referral_link: str
  invited_count: int
  bonus_earned: int
  invited_users: list[InvitedUserInfo]


class ShopItemResponse(BaseModel):
  id: int
  name: str
  description: str | None = None
  image_url: str | None = None
  price_bonus: int
  price_money: float | None = None
  category: str | None = None

  model_config = ConfigDict(from_attributes=True)


class OrderItemRequest(BaseModel):
  item_id: int = Field(gt=0)
  quantity: int = Field(gt=0)


class CreateOrderRequest(BaseModel):
  items: list[OrderItemRequest]
  pay_with_bonus: bool = True


class OrderItemResponse(BaseModel):
  item_id: int
  quantity: int


class OrderResponse(BaseModel):
  id: int
  items: list[OrderItemResponse]
  total_bonus: int
  total_money: float | None
  status: str


class GameClickResponse(BaseModel):
  new_bonus_balance: int
  current_energy: int


class UserInfoResponse(BaseModel):
  telegram_id: int
  first_name: str | None = None
  last_name: str | None = None
  username: str | None = None
  created_at: datetime
  updated_at: datetime
