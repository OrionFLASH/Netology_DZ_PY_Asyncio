"""
Настройка логирования: отдельные файлы INFO и DEBUG в каталоге log/.

Имена файлов: Уровень_логирования_(тема)_годмесяцдень_час.log
Строки DEBUG приводятся к требуемому формату с полями class и def.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Final

from swapi_asyncio.config import get_project_root

_LOG_TOPIC: Final[str] = "swapi"


class DebugLevelOnlyFilter(logging.Filter):
    """Пропускает только записи уровня DEBUG в файл отладочного лога."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno == logging.DEBUG


class SwapiDebugFormatter(logging.Formatter):
    """
    Форматтер для файла DEBUG: фиксированная структура строки с class/def.

    Если в записи не переданы class_name и def_name через extra, подставляются
    прочерк и имя функции из LogRecord (funcName).
    """

    def format(self, record: logging.LogRecord) -> str:
        class_name: str = getattr(record, "class_name", "-")
        def_name: str = getattr(record, "def_name", record.funcName)
        timestamp: str = self.formatTime(record, self.datefmt)
        message: str = record.getMessage()
        return f"{timestamp} - [DEBUG] - {message} [class: {class_name} | def: {def_name}]"


def _log_dir() -> Path:
    """Каталог для файлов логов (создаётся при необходимости)."""
    directory: Path = get_project_root() / "log"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _build_log_filename(level_name: str, topic: str) -> Path:
    """Формирует путь к файлу лога по шаблону задания."""
    now: datetime = datetime.now()
    stamp: str = now.strftime("%Y%m%d_%H")
    return _log_dir() / f"{level_name}_{topic}_{stamp}.log"


def setup_logging() -> tuple[logging.Logger, Path, Path]:
    """
    Настраивает корневой логгер приложения и возвращает пути к файлам логов.

    Возвращает кортеж (логгер, путь_info, путь_debug).
    """
    logger: logging.Logger = logging.getLogger("swapi_asyncio")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    info_path: Path = _build_log_filename("INFO", _LOG_TOPIC)
    debug_path: Path = _build_log_filename("DEBUG", _LOG_TOPIC)

    info_handler: logging.FileHandler = logging.FileHandler(
        info_path, encoding="utf-8"
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(
        logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s")
    )

    debug_handler: logging.FileHandler = logging.FileHandler(
        debug_path, encoding="utf-8"
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.addFilter(DebugLevelOnlyFilter())
    debug_handler.setFormatter(
        SwapiDebugFormatter(datefmt="%Y-%m-%d %H:%M:%S")
    )

    console: logging.StreamHandler = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(
        logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s")
    )

    logger.addHandler(info_handler)
    logger.addHandler(debug_handler)
    logger.addHandler(console)

    return logger, info_path, debug_path


def log_debug(
    logger: logging.Logger,
    message: str,
    *,
    class_name: str = "-",
    def_name: str | None = None,
) -> None:
    """
    Пишет сообщение уровня DEBUG с явными class_name и def_name в extra.

    Если def_name не задан, используется имя вызывающей функции (один уровень вверх).
    """
    import inspect

    resolved_def: str
    if def_name is not None:
        resolved_def = def_name
    else:
        frame = inspect.currentframe()
        try:
            caller = frame.f_back if frame is not None else None
            resolved_def = (
                caller.f_code.co_name if caller is not None else "unknown"
            )
        finally:
            del frame

    logger.debug(
        message,
        extra={"class_name": class_name, "def_name": resolved_def},
    )
