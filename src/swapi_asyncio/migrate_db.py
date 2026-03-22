"""
Скрипт миграции базы данных: создаёт файл SQLite и таблицу characters.

Запуск из корня репозитория (после установки зависимостей и PYTHONPATH):
    pip install -e .
    python -m swapi_asyncio.migrate_db

Миграция выполняется синхронно через стандартный sqlite3 (однократное DDL).
"""

from __future__ import annotations

import logging
import sqlite3
import sys
from pathlib import Path

from swapi_asyncio.config import get_database_path
from swapi_asyncio.db_schema import CREATE_CHARACTERS_TABLE_SQL
from swapi_asyncio.logging_config import setup_logging


def apply_migration(database_path: Path) -> None:
    """
    Создаёт родительские каталоги при необходимости и применяет DDL к указанному файлу.

    Повторный вызов безопасен: используется CREATE TABLE IF NOT EXISTS.

    Параметры:
        database_path — путь к файлу .db SQLite.
    """
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection: sqlite3.Connection = sqlite3.connect(str(database_path))
    try:
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.executescript(CREATE_CHARACTERS_TABLE_SQL)
        connection.commit()
    finally:
        connection.close()


def main() -> int:
    """Точка входа CLI: пишет логи и создаёт схему по пути из конфигурации."""
    logger: logging.Logger
    info_path: Path
    debug_path: Path
    logger, info_path, debug_path = setup_logging()
    db_path: Path = get_database_path()

    logger.info("Запуск миграции БД: путь к файлу %s", db_path)
    logger.info("Файлы логов: INFO=%s, DEBUG=%s", info_path, debug_path)

    apply_migration(db_path)
    logger.info("Миграция успешно применена.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
