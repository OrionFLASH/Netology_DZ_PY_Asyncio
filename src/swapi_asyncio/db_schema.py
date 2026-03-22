"""
Определение схемы таблицы для хранения полей персонажа по условию задания.

Поля соответствуют выгрузке из SWAPI (properties): id — uid персонажа.
"""

from __future__ import annotations

# SQL для создания таблицы персонажей (SQLite).
# id — числовой идентификатор персонажа в SWAPI (uid).
CREATE_CHARACTERS_TABLE_SQL: str = """
CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY,
    birth_year TEXT,
    eye_color TEXT,
    gender TEXT,
    hair_color TEXT,
    homeworld TEXT,
    mass TEXT,
    name TEXT,
    skin_color TEXT
);
"""
