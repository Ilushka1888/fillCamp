from __future__ import annotations

import pytest

from src.app.models.shop_models import Product
from src.app.services.loyalty_service import (
    calc_bonus_accrual,
    calc_bonus_writeoff,
    get_loyalty_rule_for_product,
)


@pytest.mark.unit
@pytest.mark.loyalty
class TestLoyaltyService:
    def test_get_rule_by_category(self) -> None:
        """
        camp_sochi:
        - можно списать 5% от стоимости
        - можно накопить 5% от стоимости
        """
        product = Product(
            name="Смена в Сочи",
            price_bonus=0,
            price_money=100_000,
            category="camp_sochi",
        )

        rule = get_loyalty_rule_for_product(product)
        assert rule is not None
        assert rule.writeoff_percent == pytest.approx(0.05)
        assert rule.accrue_percent == pytest.approx(0.05)

        writeoff = calc_bonus_writeoff(rule, base_amount=100_000, quantity=1)
        accrue = calc_bonus_accrual(rule, base_amount=100_000, quantity=1)

        assert writeoff == 5_000
        assert accrue == 5_000

    def test_get_rule_by_name_fallback(self) -> None:
        """
        category не задана, маппинг идёт по названию "Смены в Китае"
        """
        product = Product(
            name="Смены в Китае",
            price_bonus=0,
            price_money=200_000,
            category=None,
        )

        rule = get_loyalty_rule_for_product(product)
        assert rule is not None
        # из таблицы: 3% списать, 5000 накопить
        assert rule.writeoff_percent == pytest.approx(0.03)
        assert rule.accrue_fixed == 5_000

        writeoff = calc_bonus_writeoff(rule, base_amount=200_000, quantity=1)
        accrue = calc_bonus_accrual(rule, base_amount=200_000, quantity=1)

        assert writeoff == 6_000  # 3% от 200 000
        assert accrue == 5_000

    def test_merch_allows_full_writeoff_no_accrual(self) -> None:
        """
        merch:
        - можно списать 100% стоимости
        - накопить 0
        """
        product = Product(
            name="Футболка мерч",
            price_bonus=0,
            price_money=3_000,
            category="merch",
        )

        rule = get_loyalty_rule_for_product(product)
        assert rule is not None
        assert rule.writeoff_percent == pytest.approx(1.0)
        assert rule.accrue_fixed == 0

        writeoff = calc_bonus_writeoff(rule, base_amount=3_000, quantity=1)
        accrue = calc_bonus_accrual(rule, base_amount=3_000, quantity=1)

        assert writeoff == 3_000
        assert accrue == 0

    def test_unknown_product_has_no_rule(self) -> None:
        """
        Если нет правила — ни списать, ни накопить нельзя.
        """
        product = Product(
            name="Неизвестный товар",
            price_bonus=0,
            price_money=1_000,
            category="unknown_category",
        )

        rule = get_loyalty_rule_for_product(product)
        assert rule is None

        writeoff = calc_bonus_writeoff(rule, base_amount=1_000, quantity=1)
        accrue = calc_bonus_accrual(rule, base_amount=1_000, quantity=1)

        assert writeoff == 0
        assert accrue == 0
