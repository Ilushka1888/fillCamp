from __future__ import annotations

import logging
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path = [p for p in sys.path if p not in ("", str(BASE_DIR))]

from alembic import command
from alembic.config import Config as AlembicConfig


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _get_alembic_config() -> AlembicConfig:
    base_dir = Path(__file__).resolve().parents[1]
    alembic_ini = base_dir / "alembic.ini"

    if not alembic_ini.exists():
        raise RuntimeError(f"alembic.ini not found at {alembic_ini}")

    cfg = AlembicConfig(str(alembic_ini))
    return cfg


def run_migrations() -> None:
    cfg = _get_alembic_config()

    log.info("Running Alembic upgrade to head...")
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
