"""
Асинхронный HTTP-клиент для SWAPI (swapi.tech): список персонажей и карточки.

Используется aiohttp; ограничение параллелизма задаётся семафором в вызывающем коде.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Final

import aiohttp

from swapi_asyncio.logging_config import log_debug

# Ключи полей внутри ответа API для одного персонажа.
_MESSAGE_OK: Final[str] = "ok"


class SwapiClient:
    """
    Клиент SWAPI: получение списка uid и детальных свойств персонажа.

    Атрибуты:
        _session — сессия aiohttp (внешняя, чтобы переиспользовать пул соединений).
        _base_url — базовый URL API без завершающего слэша.
        _logger — логгер пакета для диагностики.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        logger: logging.Logger,
    ) -> None:
        self._session: aiohttp.ClientSession = session
        self._base_url: str = base_url.rstrip("/")
        self._logger: logging.Logger = logger

    async def fetch_all_people_uids(self) -> list[str]:
        """
        Обходит постранично /people и собирает все uid персонажей.

        Сравнивает число уникальных uid с полем total_records ответа API (если оно есть),
        чтобы гарантировать полноту индекса до загрузки карточек.

        Возвращает отсортированный по возрастанию uid список строк.
        """
        uid_set: set[str] = set()
        expected_total: int | None = None
        # Стартуем с первой страницы; limit берём крупным, чтобы уменьшить число запросов.
        next_url: str | None = f"{self._base_url}/people?page=1&limit=100"

        while next_url is not None:
            log_debug(
                self._logger,
                f"Запрос списка персонажей: {next_url}",
                class_name=self.__class__.__name__,
                def_name="fetch_all_people_uids",
            )
            max_attempts: int = 4
            payload: dict[str, Any] | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    async with self._session.get(next_url) as response:
                        response.raise_for_status()
                        payload = await response.json()
                    break
                except (
                    aiohttp.ClientError,
                    asyncio.TimeoutError,
                    TimeoutError,
                ) as exc:
                    if attempt == max_attempts:
                        raise
                    delay_list: float = 1.5 * attempt
                    log_debug(
                        self._logger,
                        f"Ошибка списка персонажей: {exc!s}; пауза {delay_list} с",
                        class_name=self.__class__.__name__,
                        def_name="fetch_all_people_uids",
                    )
                    await asyncio.sleep(delay_list)

            if payload is None:
                raise RuntimeError("Пустой ответ при обходе списка персонажей")

            if payload.get("message") != _MESSAGE_OK:
                raise RuntimeError(f"SWAPI вернул ошибку списка: {payload}")

            if expected_total is None:
                tr_raw: Any = payload.get("total_records")
                if isinstance(tr_raw, int):
                    expected_total = tr_raw

            for item in payload.get("results", []):
                uid_raw: Any = item.get("uid")
                if uid_raw is not None:
                    uid_set.add(str(uid_raw))

            next_raw: Any = payload.get("next")
            next_url = str(next_raw) if next_raw else None

        uids: list[str] = sorted(uid_set, key=lambda x: int(x))

        if expected_total is not None and len(uids) != expected_total:
            raise RuntimeError(
                f"Несовпадение с SWAPI: total_records={expected_total}, "
                f"собрано уникальных uid={len(uids)}"
            )

        log_debug(
            self._logger,
            f"Всего найдено персонажей в индексе: {len(uids)}",
            class_name=self.__class__.__name__,
            def_name="fetch_all_people_uids",
        )
        return uids

    async def fetch_person_row(self, uid: str) -> dict[str, Any]:
        """
        Загружает карточку /people/{uid} и возвращает словарь полей для БД.

        Ключи словаря: id (int), birth_year, eye_color, gender, hair_color,
        homeworld, mass, name, skin_color — в соответствии с заданием.

        При кратковременных сбоях сети или таймаутах выполняется несколько попыток
        с паузой (публичный API не гарантирует стабильное время ответа).
        """
        url: str = f"{self._base_url}/people/{uid}"
        max_attempts: int = 4

        for attempt in range(1, max_attempts + 1):
            log_debug(
                self._logger,
                f"Запрос карточки персонажа uid={uid} (попытка {attempt}/{max_attempts})",
                class_name=self.__class__.__name__,
                def_name="fetch_person_row",
            )
            try:
                async with self._session.get(url) as response:
                    response.raise_for_status()
                    payload: dict[str, Any] = await response.json()
            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
                TimeoutError,
            ) as exc:
                if attempt == max_attempts:
                    raise
                delay: float = 1.5 * attempt
                log_debug(
                    self._logger,
                    f"Ошибка запроса uid={uid}: {exc!s}; пауза {delay} с",
                    class_name=self.__class__.__name__,
                    def_name="fetch_person_row",
                )
                await asyncio.sleep(delay)
                continue

            if payload.get("message") != _MESSAGE_OK:
                raise RuntimeError(f"SWAPI вернул ошибку для uid={uid}: {payload}")

            result: Any = payload.get("result")
            if not isinstance(result, dict):
                raise RuntimeError(f"Некорректный ответ API для uid={uid}")

            properties: Any = result.get("properties")
            if not isinstance(properties, dict):
                raise RuntimeError(f"Нет properties для uid={uid}")

            def _text(key: str) -> str | None:
                value: Any = properties.get(key)
                if value is None:
                    return None
                return str(value)

            row: dict[str, Any] = {
                "id": int(str(result.get("uid", uid))),
                "birth_year": _text("birth_year"),
                "eye_color": _text("eye_color"),
                "gender": _text("gender"),
                "hair_color": _text("hair_color"),
                "homeworld": _text("homeworld"),
                "mass": _text("mass"),
                "name": _text("name"),
                "skin_color": _text("skin_color"),
            }
            return row
