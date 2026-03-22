"""
Оркестрация асинхронной загрузки: параллельные запросы к API и запись в SQLite.

Запись выполняется через aiosqlite; конкурентность HTTP ограничивается семафором.
"""

from __future__ import annotations

import asyncio
import logging
import ssl
from typing import Any, Final

import aiohttp
import aiosqlite
import certifi

from swapi_asyncio.config import (
    get_database_path,
    get_http_concurrency,
    get_http_timeout_total,
    get_swapi_base_url,
)
from swapi_asyncio.logging_config import log_debug
from swapi_asyncio.swapi_client import SwapiClient

# Запрос вставки/обновления одной строки (повторный запуск загрузчика идемпотентен).
UPSERT_CHARACTER_SQL: Final[str] = """
INSERT OR REPLACE INTO characters (
    id, birth_year, eye_color, gender, hair_color, homeworld, mass, name, skin_color
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
"""


async def _fetch_one(
    client: SwapiClient,
    uid: str,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    """Загружает одного персонажа под семафором (ограничение параллелизма)."""
    async with semaphore:
        return await client.fetch_person_row(uid)


async def load_all_characters(
    logger: logging.Logger,
    database_path: str | None = None,
) -> int:
    """
    Загружает всех персонажей из SWAPI в таблицу characters.

    Перед вызовом таблица должна существовать (скрипт миграции).

    Параметры:
        logger — настроенный логгер приложения.
        database_path — путь к SQLite; если None, берётся из конфигурации.

    Возвращает количество успешно записанных строк.
    """
    db_path: str = str(database_path or get_database_path())
    base_url: str = get_swapi_base_url()
    concurrency: int = get_http_concurrency()
    timeout_total: float = get_http_timeout_total()

    # total и sock_read выравниваем по одному лимиту: у SWAPI ответ иногда приходит с большой задержкой.
    timeout: aiohttp.ClientTimeout = aiohttp.ClientTimeout(
        total=timeout_total,
        connect=min(120.0, timeout_total),
        sock_connect=min(120.0, timeout_total),
        sock_read=timeout_total,
    )
    # Явный CA bundle (certifi) повышает совместимость с Python на macOS/Windows,
    # где системное хранилище сертификатов может быть не подключено к ssl по умолчанию.
    ssl_context: ssl.SSLContext = ssl.create_default_context(cafile=certifi.where())

    log_debug(
        logger,
        f"Старт загрузки: БД={db_path}, base_url={base_url}, concurrency={concurrency}",
        class_name="-",
        def_name="load_all_characters",
    )

    # Отдельная короткая сессия для индекса персонажей — один-два запроса.
    list_connector: aiohttp.TCPConnector = aiohttp.TCPConnector(
        limit=4,
        ssl=ssl_context,
        enable_cleanup_closed=True,
    )
    async with aiohttp.ClientSession(
        timeout=timeout, connector=list_connector
    ) as list_session:
        list_client: SwapiClient = SwapiClient(list_session, base_url, logger)
        uids: list[str] = await list_client.fetch_all_people_uids()

    rows: list[dict[str, Any]] = []
    # Чанки + новая сессия на каждый чанк: у длительных пулов keep-alive иногда «залипают» сокеты.
    chunk_size: int = max(concurrency * 3, 12)
    for offset in range(0, len(uids), chunk_size):
        chunk: list[str] = uids[offset : offset + chunk_size]
        chunk_connector: aiohttp.TCPConnector = aiohttp.TCPConnector(
            limit=max(4, concurrency * 2),
            ssl=ssl_context,
            enable_cleanup_closed=True,
            force_close=True,
        )
        async with aiohttp.ClientSession(
            timeout=timeout, connector=chunk_connector
        ) as session:
            client: SwapiClient = SwapiClient(session, base_url, logger)
            semaphore: asyncio.Semaphore = asyncio.Semaphore(concurrency)
            tasks: list[asyncio.Task[dict[str, Any]]] = [
                asyncio.create_task(_fetch_one(client, uid, semaphore))
                for uid in chunk
            ]
            chunk_rows: list[dict[str, Any]] = await asyncio.gather(*tasks)
        rows.extend(chunk_rows)
        logger.info(
            "Загружен фрагмент персонажей %s–%s из %s",
            offset + 1,
            offset + len(chunk),
            len(uids),
        )
        if offset + chunk_size < len(uids):
            await asyncio.sleep(0.5)

    # Запись в БД последовательно в одном соединении — проще и достаточно быстро для ~80 строк.
    async with aiosqlite.connect(db_path) as connection:
        await connection.execute("PRAGMA foreign_keys = ON;")
        for row in rows:
            await connection.execute(
                UPSERT_CHARACTER_SQL,
                (
                    row["id"],
                    row["birth_year"],
                    row["eye_color"],
                    row["gender"],
                    row["hair_color"],
                    row["homeworld"],
                    row["mass"],
                    row["name"],
                    row["skin_color"],
                ),
            )
        await connection.commit()

    log_debug(
        logger,
        f"Запись в БД завершена, строк: {len(rows)}",
        class_name="-",
        def_name="load_all_characters",
    )
    logger.info("Загружено персонажей: %s", len(rows))
    return len(rows)


def run_load_sync(logger: logging.Logger, database_path: str | None = None) -> int:
    """
    Синхронная обёртка над load_all_characters для вызова из CLI.

    Создаёт новый цикл событий asyncio и выполняет корутину до завершения.
    """
    return asyncio.run(load_all_characters(logger, database_path))
