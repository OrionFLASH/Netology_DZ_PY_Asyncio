"""
Пакет асинхронной загрузки персонажей Star Wars из SWAPI в локальную базу SQLite.

Скрипты точки входа:
- python -m swapi_asyncio.migrate_db — создание схемы БД;
- python -m swapi_asyncio.load_from_swapi — выгрузка всех персонажей в БД.
"""
