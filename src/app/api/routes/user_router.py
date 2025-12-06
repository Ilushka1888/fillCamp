# src/app/api/routes/user_router.py
from __future__ import annotations

from fastapi import APIRouter, Depends

from src.app.api.deps import get_current_user
from src.app.models.user_models import User
from src.app.schemas.miniapp_schemas import UserInfoResponse

router = APIRouter(prefix="/api/user", tags=["User"])


@router.get("", response_model=UserInfoResponse)
async def get_user_info(
    current_user: User = Depends(get_current_user),
) -> UserInfoResponse:

    return UserInfoResponse(
        telegram_id=current_user.telegram_id,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        username=current_user.username,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )
