"""
Загрузка настроек из переменных окружения и файла .env.

Используется пакетом dotenv, чтобы путь к БД и параметры HTTP можно было
задавать без правки кода.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Загружаем переменные из .env в корне проекта (если файл существует).
_PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")


def _env_int(name: str, default: int) -> int:
    """Читает целое число из окружения; при ошибке парсинга возвращает default."""
    raw: str | None = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    """Читает число с плавающей точкой из окружения."""
    raw: str | None = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def get_database_path() -> Path:
    """
    Возвращает абсолютный путь к файлу SQLite.

    Переменная окружения: DATABASE_PATH (по умолчанию ./data/characters.db
    относительно корня репозитория).
    """
    raw: str | None = os.getenv("DATABASE_PATH")
    if raw is None or raw.strip() == "":
        return (_PROJECT_ROOT / "data" / "characters.db").resolve()
    path = Path(raw)
    if not path.is_absolute():
        path = (_PROJECT_ROOT / path).resolve()
    return path


def get_swapi_base_url() -> str:
    """Базовый URL API (без завершающего слэша)."""
    base: str = os.getenv("SWAPI_BASE_URL", "https://www.swapi.tech/api").rstrip("/")
    return base


def get_http_concurrency() -> int:
    """
    Максимальное число одновременных запросов к SWAPI при загрузке карточек.

    У публичного API бывают длительные ответы; умеренное значение снижает риск
    таймаутов и отказов при всплеске параллельных соединений.
    """
    return max(1, _env_int("HTTP_CONCURRENCY", 6))


def get_http_timeout_total() -> float:
    """
    Таймаут одного HTTP-запроса (total) в секундах.

    Для публичного SWAPI при параллельной загрузке десятков карточек увеличенное
    значение снижает риск обрыва по таймауту на медленных ответах.
    """
    return max(60.0, _env_float("HTTP_TIMEOUT_TOTAL", 600.0))


def get_project_root() -> Path:
    """Корень репозитория (родитель каталога src)."""
    return _PROJECT_ROOT
