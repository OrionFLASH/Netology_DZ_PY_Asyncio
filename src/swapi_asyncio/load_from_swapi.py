"""
Скрипт асинхронной выгрузки всех персонажей из SWAPI в базу данных SQLite.

Перед первым запуском выполните миграцию:
    python -m swapi_asyncio.migrate_db

Затем:
    python -m swapi_asyncio.load_from_swapi
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from swapi_asyncio.loader import run_load_sync
from swapi_asyncio.logging_config import setup_logging


def main() -> int:
    """Точка входа CLI: настраивает логи и запускает полную загрузку."""
    logger: logging.Logger
    info_path: Path
    debug_path: Path

    logger, info_path, debug_path = setup_logging()
    logger.info("Запуск загрузки персонажей из SWAPI")
    logger.info("Файлы логов: INFO=%s, DEBUG=%s", info_path, debug_path)

    try:
        count: int = run_load_sync(logger)
    except Exception as exc:  # noqa: BLE001 — верхний уровень CLI: логируем и выходим
        logger.exception("Ошибка при загрузке данных: %s", exc)
        return 1

    logger.info("Готово. Сохранено записей: %s", count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
