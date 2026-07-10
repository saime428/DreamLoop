from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    db = sqlite3.connect(db_path)
    try:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        with db:
            yield db
    finally:
        db.close()


def migrate(db_path: Path) -> None:
    with connect(db_path) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS dreams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                dreamed_on TEXT NOT NULL,
                manual_mood TEXT,
                tags_json TEXT NOT NULL DEFAULT '[]',
                reflection_json TEXT NOT NULL DEFAULT '{}',
                visual_json TEXT NOT NULL DEFAULT '{}',
                analysis_status TEXT NOT NULL DEFAULT 'pending'
            );

            CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid TEXT,
                starts_on TEXT NOT NULL,
                ends_on TEXT,
                summary TEXT NOT NULL DEFAULT '',
                raw_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS weather_daily (
                weather_date TEXT PRIMARY KEY,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                temperature_2m_max REAL,
                temperature_2m_min REAL,
                precipitation_sum REAL,
                weather_code INTEGER,
                raw_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dream_id INTEGER NOT NULL REFERENCES dreams(id) ON DELETE CASCADE,
                analysis_language TEXT NOT NULL DEFAULT 'en',
                interpretation_index INTEGER NOT NULL DEFAULT 0,
                rating TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS dream_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dream_id INTEGER NOT NULL REFERENCES dreams(id) ON DELETE CASCADE,
                language TEXT NOT NULL DEFAULT 'en',
                provider TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT '',
                prompt TEXT NOT NULL,
                image_path TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                error TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            """
        )
        migrate_dreams_table(db)
        migrate_analysis_table(db)


def migrate_dreams_table(db: sqlite3.Connection) -> None:
    columns = db.execute("PRAGMA table_info(dreams)").fetchall()
    column_names = {column["name"] for column in columns}
    if "reflection_json" not in column_names:
        db.execute("ALTER TABLE dreams ADD COLUMN reflection_json TEXT NOT NULL DEFAULT '{}'")
    if "visual_json" not in column_names:
        db.execute("ALTER TABLE dreams ADD COLUMN visual_json TEXT NOT NULL DEFAULT '{}'")


def migrate_analysis_table(db: sqlite3.Connection) -> None:
    columns = db.execute("PRAGMA table_info(dream_analyses)").fetchall()
    if not columns:
        create_analysis_table(db)
        return

    column_names = {column["name"] for column in columns}
    pk_columns = [
        column["name"]
        for column in sorted((column for column in columns if column["pk"]), key=lambda item: item["pk"])
    ]
    if "language" in column_names and pk_columns == ["dream_id", "language"]:
        return

    db.execute("ALTER TABLE dream_analyses RENAME TO dream_analyses_old")
    create_analysis_table(db)
    required = {
        "dream_id",
        "emotional_tone",
        "symbols_json",
        "themes_json",
        "summary",
        "confidence",
        "raw_json",
    }
    if required.issubset(column_names):
        language_expression = "language" if "language" in column_names else "'en'"
        db.execute(
            f"""
            INSERT OR REPLACE INTO dream_analyses (
                dream_id, language, emotional_tone, symbols_json, themes_json, summary,
                confidence, raw_json
            )
            SELECT
                dream_id,
                COALESCE(NULLIF({language_expression}, ''), 'en'),
                emotional_tone,
                symbols_json,
                themes_json,
                summary,
                confidence,
                raw_json
            FROM dream_analyses_old
            """
        )
    db.execute("DROP TABLE dream_analyses_old")


def create_analysis_table(db: sqlite3.Connection) -> None:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS dream_analyses (
            dream_id INTEGER NOT NULL REFERENCES dreams(id) ON DELETE CASCADE,
            language TEXT NOT NULL DEFAULT 'en',
            emotional_tone TEXT NOT NULL,
            symbols_json TEXT NOT NULL DEFAULT '[]',
            themes_json TEXT NOT NULL DEFAULT '[]',
            summary TEXT NOT NULL DEFAULT '',
            confidence REAL NOT NULL DEFAULT 0,
            raw_json TEXT NOT NULL,
            PRIMARY KEY (dream_id, language)
        )
        """
    )
