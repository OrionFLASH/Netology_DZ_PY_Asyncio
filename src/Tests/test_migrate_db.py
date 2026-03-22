"""
Проверка, что миграция создаёт ожидаемую таблицу в пустом файле SQLite.
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from swapi_asyncio.migrate_db import apply_migration


class TestMigrateDb(unittest.TestCase):
    """Тесты DDL миграции без обращения к сети."""

    def test_creates_characters_table(self) -> None:
        """После apply_migration в БД должна существовать таблица characters с колонками задания."""
        with tempfile.TemporaryDirectory() as tmp:
            db_file: Path = Path(tmp) / "test.db"
            apply_migration(db_file)

            connection: sqlite3.Connection = sqlite3.connect(str(db_file))
            try:
                cursor: sqlite3.Cursor = connection.execute(
                    "PRAGMA table_info(characters);"
                )
                columns: list[tuple] = cursor.fetchall()
                names: set[str] = {row[1] for row in columns}
            finally:
                connection.close()

        expected: set[str] = {
            "id",
            "birth_year",
            "eye_color",
            "gender",
            "hair_color",
            "homeworld",
            "mass",
            "name",
            "skin_color",
        }
        self.assertTrue(expected.issubset(names))


if __name__ == "__main__":
    unittest.main()
