# src/app/services/loyalty_service.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.app.models.shop_models import Product


@dataclass(frozen=True)
class LoyaltyRule:
    # сколько можно СПИСАТЬ
    writeoff_percent: float | None = None   # 0.05 = 5% от цены
    writeoff_fixed: int | None = None       # фиксированное кол-во бонусов

    # сколько можно НАКОПИТЬ
    accrue_percent: float | None = None     # 0.05 = 5% от покупки
    accrue_fixed: int | None = None         # фикс кол-во бонусов


# 💾 хардкод по твоей таблице
LOYALTY_RULES: dict[str, LoyaltyRule] = {
    # ---- смены ----
    # рекомендую такие category в Product.category
    "camp_china": LoyaltyRule(writeoff_percent=0.03, accrue_fixed=5000),
    "camp_sochi": LoyaltyRule(writeoff_percent=0.05, accrue_percent=0.05),
    "camp_moscow_city": LoyaltyRule(writeoff_percent=0.10, accrue_percent=0.10),
    "camp_izumrud": LoyaltyRule(writeoff_percent=0.07, accrue_percent=0.05),
    "camp_rozendorf": LoyaltyRule(writeoff_percent=0.07, accrue_percent=0.05),
    "camp_turkey": LoyaltyRule(writeoff_percent=0.03, accrue_fixed=5000),

    # ---- доп. услуги ----
    # Мерч / Уроки / Фотосессии / Трансфер
    # можно списать 100%, накопить 0
    "merch": LoyaltyRule(writeoff_percent=1.0, accrue_fixed=0),
    "lessons": LoyaltyRule(writeoff_percent=1.0, accrue_fixed=0),
    "photosession": LoyaltyRule(writeoff_percent=1.0, accrue_fixed=0),
    "transfer": LoyaltyRule(writeoff_percent=1.0, accrue_fixed=0),
}


def get_loyalty_rule_for_product(product: Product) -> Optional[LoyaltyRule]:
    """Правило по category или по названию (fallback)."""
    cat = (product.category or "").lower()
    if cat in LOYALTY_RULES:
        return LOYALTY_RULES[cat]

    name = (product.name or "").lower()

    # подстраховка по русскому названию, если category не заполнена
    if "кита" in name:
        return LOYALTY_RULES["camp_china"]
    if "соч" in name:
        return LOYALTY_RULES["camp_sochi"]
    if "городск" in name and "москв" in name:
        return LOYALTY_RULES["camp_moscow_city"]
    if "изумруд" in name:
        return LOYALTY_RULES["camp_izumrud"]
    if "розенд" in name:
        return LOYALTY_RULES["camp_rozendorf"]
    if "турци" in name:
        return LOYALTY_RULES["camp_turkey"]
    if "мерч" in name:
        return LOYALTY_RULES["merch"]
    if "урок" in name:
        return LOYALTY_RULES["lessons"]
    if "фотосес" in name:
        return LOYALTY_RULES["photosession"]
    if "трансфер" in name:
        return LOYALTY_RULES["transfer"]

    return None


def calc_bonus_writeoff(
    rule: Optional[LoyaltyRule],
    base_amount: float,
    quantity: int,
) -> int:
    """Сколько бонусов разрешено СПИСАТЬ по товару."""
    if rule is None:
        return 0

    if rule.writeoff_fixed is not None:
        return max(int(rule.writeoff_fixed) * quantity, 0)

    if rule.writeoff_percent is not None and base_amount > 0:
        return max(int(base_amount * rule.writeoff_percent), 0)

    return 0


def calc_bonus_accrual(
    rule: Optional[LoyaltyRule],
    base_amount: float,
    quantity: int,
) -> int:
    """Сколько бонусов разрешено НАКОПИТЬ по покупке."""
    if rule is None:
        return 0

    if rule.accrue_fixed is not None:
        return max(int(rule.accrue_fixed) * quantity, 0)

    if rule.accrue_percent is not None and base_amount > 0:
        return max(int(base_amount * rule.accrue_percent), 0)

    return 0
