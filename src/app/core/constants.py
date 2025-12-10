# src/app/core/constants.py
from __future__ import annotations

from zoneinfo import ZoneInfo

# Максимальная "энергия" (количество кликов) в день
MAX_DAILY_ENERGY: int = 1000

# Часовой пояс Москвы
MOSCOW_TZ = ZoneInfo("Europe/Moscow")
