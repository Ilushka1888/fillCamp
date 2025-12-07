from __future__ import annotations

import logging
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

BASE_DIR = Path(__file__).resolve().parents[1]  # корень проекта
SRC_DIR = BASE_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _get_alembic_config() -> AlembicConfig:
    """
    Загружаем конфиг Alembic из src/alembic.ini
    """
    ini_path = SRC_DIR / "alembic.ini"
    if not ini_path.exists():
        raise RuntimeError(f"alembic.ini not found at {ini_path}")

    cfg = AlembicConfig(str(ini_path))
    return cfg


def run_migrations() -> None:
    cfg = _get_alembic_config()
    log.info("Running Alembic migrations using %s", cfg.config_file_name)
    command.upgrade(cfg, "head")
    log.info("Alembic upgrade to head completed")


def main() -> None:
    try:
        run_migrations()
    except Exception as exc:  # noqa: BLE001
        log.exception("Error while running migrations: %s", exc)
        raise


if __name__ == "__main__":
    main()
