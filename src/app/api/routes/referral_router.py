from fastapi import APIRouter, Depends
from src.app.api.deps import get_current_user, get_db
from src.app.models.user_models import User
from src.app.services.referral_service import ReferralService

router = APIRouter(prefix="/api/referral", tags=["Referral"])


@router.post("/generate")
async def generate_referral_link(
    user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    service = ReferralService(db)
    code = await service.generate_referral_code(user)

    # ссылка на твой mini-app
    link = f"https://t.me/{'your_bot_name'}/app?ref={code}"

    return {
        "referral_code": code,
        "referral_link": link
    }
