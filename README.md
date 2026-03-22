# Учебный проект: асинхронная выгрузка персонажей Star Wars (SWAPI)

Репозиторий реализует домашнее задание к лекции «Asyncio» ([формулировка в `Docs/2.2-asyncio-README.md`](Docs/2.2-asyncio-README.md), исходные материалы Нетологии — в каталоге `Docs/`, включая файл `Docs/contacts.db` из [репозитория заданий](https://github.com/netology-code/py-homeworks-web/tree/new/2.2-asyncio)).

В проекте **одна** тема: асинхронные запросы к [SWAPI](https://swapi.tech/) и запись всех персонажей в SQLite. Отдельные подкаталоги под несколько несвязанных заданий не используются.

> Примечание: в вашем шаблоне описан Django‑проект с HTML; **данное задание Нетологии по ссылке выше — про asyncio и БД**, без веб‑интерфейса. Текущая реализация соответствует официальной формулировке 2.2-asyncio.

## Структура каталогов

| Путь | Назначение |
|------|------------|
| `src/swapi_asyncio/` | Основной код: конфигурация, логирование, миграция, HTTP‑клиент, загрузчик |
| `src/Tests/` | Автотесты (`unittest`) |
| `Docs/` | Текст задания и исходные файлы из репозитория Нетологии |
| `data/` | Рабочий каталог для файла SQLite (создаётся при миграции; в репозитории не хранится готовый `.db`) |
| `log/` | Файлы логов (создаются при запуске скриптов; не коммитятся) |

## Техническое задание (кратко)

1. Асинхронно получить из API данные по **всем** персонажам.
2. Сохранить в БД поля: `id`, `birth_year`, `eye_color`, `gender`, `hair_color`, `homeworld`, `mass`, `name`, `skin_color`.
3. Предоставить **скрипт миграции** БД и **скрипт загрузки** данных.

## Соответствие заданию (контрольный список)

| Требование | Реализация |
|------------|------------|
| Все персонажи из API | Индекс `/people` с пагинацией; число уникальных `uid` сверяется с полем `total_records` ответа SWAPI |
| Поля записи | Таблица `characters` и словарь строки — ровно перечисленные в ДЗ поля (`id` = `uid`) |
| Асинхронная выгрузка из API | `aiohttp`, параллельные карточки с семафором, чанки и отдельные сессии |
| Асинхронная загрузка в БД | `aiosqlite`, пакет `executemany` + `commit` в одной транзакции |
| Скрипт миграции | `python -m swapi_asyncio.migrate_db` |
| Скрипт загрузки | `python -m swapi_asyncio.load_from_swapi` |
| Контроль полноты после HTTP | Если число загруженных карточек не совпало с числом `uid` в индексе — `RuntimeError` |

Проверка на рабочей среде (март 2026): после загрузки `SELECT COUNT(*) FROM characters` возвращает **82** — как `total_records` в SWAPI (значение может измениться при обновлении API).

## Описание решения

- **База данных:** SQLite, файл по умолчанию `./data/characters.db` (переопределяется переменной `DATABASE_PATH` в `.env`).
- **Миграция:** синхронный модуль `sqlite3` выполняет `CREATE TABLE IF NOT EXISTS` для таблицы `characters` (см. `src/swapi_asyncio/db_schema.py`, запуск — `python -m swapi_asyncio.migrate_db`).
- **Загрузка:** `aiohttp` параллельно запрашивает список персонажей и карточки `/people/{uid}`; параллелизм ограничен семафором (`HTTP_CONCURRENCY`). Для устойчивости к нестабильному публичному API: повторные попытки при сетевых ошибках для списка и карточек (`SwapiClient`), увеличенные таймауты чтения, пакетная загрузка чанками с **отдельной HTTP‑сессией на каждый чанк** и пакет `certifi` для проверки TLS. Запись в БД — `aiosqlite`, **`executemany`** с `INSERT OR REPLACE` для идемпотентности повторных запусков; перед записью проверяется `len(карточек) == len(uid из индекса)`.
- **Логи:** каталог `log/`, имена файлов вида `INFO_swapi_ГГГГММДД_ЧЧ.log` и `DEBUG_swapi_ГГГГММДД_ЧЧ.log`; для уровня DEBUG строки имеют формат с полями `[class: … | def: …]` (см. `src/swapi_asyncio/logging_config.py`).

## Переменные окружения

Копируйте `.env.example` в `.env` и при необходимости измените значения.

| Переменная | Назначение | Пример |
|------------|------------|--------|
| `DATABASE_PATH` | Путь к файлу SQLite | `./data/characters.db` |
| `SWAPI_BASE_URL` | Базовый URL API | `https://www.swapi.tech/api` |
| `HTTP_CONCURRENCY` | Одновременных запросов за деталями персонажа | `6` |
| `HTTP_TIMEOUT_TOTAL` | Таймаут одного запроса (total и sock_read, сек) | `600` |

## Установка и запуск

```bash
cd /path/to/Netology_DZ_PY_Asyncio
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
cp .env.example .env
```

1. **Миграция БД**

```bash
python -m swapi_asyncio.migrate_db
```

2. **Загрузка всех персонажей из API** (нужен доступ в интернет)

```bash
python -m swapi_asyncio.load_from_swapi
```

3. **Проверка содержимого БД** (пример)

```bash
sqlite3 data/characters.db "SELECT COUNT(*) FROM characters;"
sqlite3 data/characters.db "SELECT id, name, gender FROM characters ORDER BY id LIMIT 5;"
```

Ожидается **82** строки (актуально для SWAPI на момент проверки; число может измениться, если API обновят).

Полная загрузка с публичного API может занять **несколько минут и более** (зависит от нагрузки на swapi.tech). При ошибках таймаута уменьшите `HTTP_CONCURRENCY` в `.env` (например, до `3–4`) и при необходимости увеличьте `HTTP_TIMEOUT_TOTAL`.

## Тестирование

```bash
source .venv/bin/activate
PYTHONPATH=src python -m unittest discover -s src/Tests -p "test_*.py"
```

Автотест проверяет только создание схемы БД без сетевых вызовов. Ручная проверка загрузки: выполнить миграцию и скрипт загрузки, затем запросы `sqlite3` выше.

## Переменные и функции (справочник)

### Модуль `swapi_asyncio.config`

| Имя | Назначение |
|-----|------------|
| `get_database_path()` | Абсолютный путь к SQLite из `DATABASE_PATH` |
| `get_swapi_base_url()` | Базовый URL SWAPI |
| `get_http_concurrency()` | Лимит параллельных HTTP‑запросов |
| `get_http_timeout_total()` | Таймаут одного запроса aiohttp (`total` / `sock_read`) |
| `get_project_root()` | Корень репозитория |

**Пример:** `path = get_database_path()` — путь для `migrate_db` и загрузчика.

### Модуль `swapi_asyncio.logging_config`

| Имя | Назначение |
|-----|------------|
| `setup_logging()` | Настраивает логгер `swapi_asyncio`, файлы INFO/DEBUG и консоль |
| `log_debug(logger, message, class_name=..., def_name=...)` | Запись в DEBUG с требуемой разметкой class/def |

### Модуль `swapi_asyncio.db_schema`

| Имя | Назначение |
|-----|------------|
| `CREATE_CHARACTERS_TABLE_SQL` | Текст DDL таблицы `characters` |

### Модуль `swapi_asyncio.migrate_db`

| Имя | Назначение |
|-----|------------|
| `apply_migration(database_path)` | Создаёт каталоги и применяет DDL к файлу БД |
| `main()` | CLI миграции |

### Модуль `swapi_asyncio.swapi_client`

| Имя | Назначение |
|-----|------------|
| `SwapiClient` | Класс клиента SWAPI |
| `fetch_all_people_uids()` | Асинхронно собирает уникальные `uid` из пагинации `/people`, сверяет с `total_records` |
| `fetch_person_row(uid)` | Асинхронно возвращает словарь полей для одной записи БД |

### Модуль `swapi_asyncio.loader`

| Имя | Назначение |
|-----|------------|
| `load_all_characters(logger, database_path=None)` | Полная асинхронная загрузка в БД (`executemany`); возвращает число записей |
| `run_load_sync(logger, database_path=None)` | Обёртка `asyncio.run` для CLI |

### Модуль `swapi_asyncio.load_from_swapi`

| Имя | Назначение |
|-----|------------|
| `main()` | CLI загрузки |

## История версий

| Версия | Изменения |
|--------|-----------|
| 0.1.0 | Первоначальная реализация: миграция SQLite, асинхронный загрузчик SWAPI, логирование, документация, тест DDL, материалы в `Docs/`. |
| 0.1.1 | Устойчивость к медленному SWAPI: `certifi`, таймауты, повторы запросов, чанки и отдельные сессии; фильтр только DEBUG в отладочном логе. |
| 0.1.2 | Проверка полноты: `total_records` vs уникальные `uid`, контроль числа карточек перед записью; пакетная запись `executemany`; повторы для запроса списка `/people`. |

## Git и удалённый репозиторий

Ветка отслеживает `origin`; после изменений выполняйте коммит и `git push`. Сообщения коммитов формулируйте по сути изменений.
