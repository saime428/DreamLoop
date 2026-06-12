from __future__ import annotations

import json
import sqlite3
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import urlopen

from .analysis import Analyzer, build_analyzer, normalize_analysis


class DreamLoop:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or Path.cwd())
        self.data_dir = self.root / ".dreamloop"
        self.db_path = self.data_dir / "dreamloop.sqlite3"

    def init(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        for name in ("chroma", "exports", "imports"):
            (self.data_dir / name).mkdir(parents=True, exist_ok=True)
        self._ensure_gitignore()
        self._migrate()

    def add_dream(
        self,
        content: str,
        tags: list[str] | None = None,
        mood: str | None = None,
        dreamed_on: date | None = None,
    ) -> int:
        self.init()
        if not content.strip():
            raise ValueError("Dream content cannot be empty.")
        dreamed_on = dreamed_on or date.today()
        with self._connect() as db:
            cursor = db.execute(
                """
                INSERT INTO dreams (
                    content, created_at, dreamed_on, manual_mood, tags_json, analysis_status
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    content.strip(),
                    datetime.now().isoformat(timespec="seconds"),
                    dreamed_on.isoformat(),
                    mood,
                    json.dumps(tags or [], ensure_ascii=False),
                    "pending",
                ),
            )
            return int(cursor.lastrowid)

    def add_dream_with_analysis(
        self,
        content: str,
        analysis: dict[str, Any],
        *,
        language: str = "en",
        dreamed_on: date | None = None,
    ) -> int:
        self.init()
        if not content.strip():
            raise ValueError("Dream content cannot be empty.")
        dreamed_on = dreamed_on or date.today()
        with self._connect() as db:
            cursor = db.execute(
                """
                INSERT INTO dreams (
                    content, created_at, dreamed_on, manual_mood, tags_json, analysis_status
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    content.strip(),
                    datetime.now().isoformat(timespec="seconds"),
                    dreamed_on.isoformat(),
                    None,
                    "[]",
                    "analyzed",
                ),
            )
            dream_id = int(cursor.lastrowid)
            self._store_analysis(db, dream_id, normalize_analysis(analysis), language)
            return dream_id

    def list_dreams(self) -> list[dict[str, Any]]:
        self.init()
        with self._connect() as db:
            rows = db.execute("SELECT * FROM dreams ORDER BY dreamed_on DESC, id DESC").fetchall()
        return [self._dream_from_row(row) for row in rows]

    def get_dream(self, dream_id: int, language: str = "en") -> dict[str, Any]:
        self.init()
        with self._connect() as db:
            row = db.execute("SELECT * FROM dreams WHERE id = ?", (dream_id,)).fetchone()
            if row is None:
                raise KeyError(f"Dream {dream_id} was not found.")
            dream = self._dream_from_row(row)
            analysis = db.execute(
                "SELECT * FROM dream_analyses WHERE dream_id = ? AND language = ?",
                (dream_id, normalize_language(language)),
            ).fetchone()
        if analysis:
            dream["analysis"] = {
                "language": analysis["language"],
                "emotional_tone": analysis["emotional_tone"],
                "symbols": json.loads(analysis["symbols_json"]),
                "themes": json.loads(analysis["themes_json"]),
                "summary": analysis["summary"],
                "confidence": analysis["confidence"],
                "raw_json": analysis["raw_json"],
            }
        else:
            dream["analysis"] = None
        return dream

    def analyze_pending(
        self,
        analyzer: Analyzer | None = None,
        limit: int | None = None,
        *,
        language: str = "en",
    ) -> list[int]:
        self.init()
        if analyzer is None:
            analyzer = build_analyzer(self.root)
            if analyzer is None:
                return []

        sql = "SELECT * FROM dreams WHERE analysis_status = 'pending' ORDER BY id"
        params: tuple[Any, ...] = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (limit,)

        analyzed: list[int] = []
        with self._connect() as db:
            rows = db.execute(sql, params).fetchall()
            for row in rows:
                self._write_analysis(db, int(row["id"]), row["content"], analyzer, language)
                analyzed.append(int(row["id"]))
        return analyzed

    def analyze_dream(self, dream_id: int, analyzer: Analyzer | None = None, *, language: str = "en") -> int:
        self.init()
        if analyzer is None:
            analyzer = build_analyzer(self.root)
            if analyzer is None:
                raise RuntimeError("AI provider is not ready.")

        with self._connect() as db:
            row = db.execute("SELECT * FROM dreams WHERE id = ?", (dream_id,)).fetchone()
            if row is None:
                raise KeyError(f"Dream {dream_id} was not found.")
            self._write_analysis(db, dream_id, row["content"], analyzer, language)
        return dream_id

    def import_ics(self, path: str | Path) -> int:
        self.init()
        events = parse_ics(Path(path).read_text(encoding="utf-8"))
        with self._connect() as db:
            for event in events:
                db.execute(
                    """
                    INSERT INTO calendar_events (uid, starts_on, ends_on, summary, raw_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        event.get("uid"),
                        event["starts_on"],
                        event.get("ends_on"),
                        event.get("summary", ""),
                        json.dumps(event, ensure_ascii=False),
                    ),
                )
        return len(events)

    def sync_weather(
        self,
        lat: float,
        lon: float,
        *,
        fetcher: Callable[..., dict[str, Any]] | None = None,
    ) -> int:
        self.init()
        payload = fetcher(lat, lon) if fetcher else fetch_open_meteo(lat, lon)
        daily = payload.get("daily", {})
        times = daily.get("time", [])
        with self._connect() as db:
            for index, day in enumerate(times):
                db.execute(
                    """
                    INSERT INTO weather_daily (
                        weather_date, lat, lon, temperature_2m_max, temperature_2m_min,
                        precipitation_sum, weather_code, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(weather_date) DO UPDATE SET
                        lat = excluded.lat,
                        lon = excluded.lon,
                        temperature_2m_max = excluded.temperature_2m_max,
                        temperature_2m_min = excluded.temperature_2m_min,
                        precipitation_sum = excluded.precipitation_sum,
                        weather_code = excluded.weather_code,
                        raw_json = excluded.raw_json
                    """,
                    (
                        day,
                        lat,
                        lon,
                        value_at(daily, "temperature_2m_max", index),
                        value_at(daily, "temperature_2m_min", index),
                        value_at(daily, "precipitation_sum", index),
                        value_at(daily, "weather_code", index),
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )
        return len(times)

    def heatmap(self) -> list[dict[str, Any]]:
        self.init()
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT dreamed_on, manual_mood, COUNT(*) AS count
                FROM dreams
                GROUP BY dreamed_on, manual_mood
                ORDER BY dreamed_on
                """
            ).fetchall()
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            bucket = grouped.setdefault(row["dreamed_on"], {"date": row["dreamed_on"], "count": 0, "moods": {}})
            bucket["count"] += row["count"]
            mood = row["manual_mood"] or "unknown"
            bucket["moods"][mood] = row["count"]
        return list(grouped.values())

    def day_context(self, day: date) -> dict[str, Any]:
        self.init()
        day_text = day.isoformat()
        with self._connect() as db:
            events = db.execute(
                "SELECT * FROM calendar_events WHERE starts_on = ? ORDER BY id", (day_text,)
            ).fetchall()
            weather = db.execute(
                "SELECT * FROM weather_daily WHERE weather_date = ?", (day_text,)
            ).fetchone()
        return {
            "events": [dict(event) for event in events],
            "weather": dict(weather) if weather else None,
        }

    def similar_dreams(self, dream_id: int, limit: int = 5) -> list[dict[str, Any]]:
        target = self.get_dream(dream_id)
        matches: list[dict[str, Any]] = []
        for dream in self.list_dreams():
            if dream["id"] == dream_id:
                continue
            score = dream_similarity(target, dream)
            if score > 0:
                dream["score"] = round(score, 3)
                matches.append(dream)
        return sorted(matches, key=lambda item: item["score"], reverse=True)[:limit]

    def trends(self, language: str = "en") -> dict[str, list[dict[str, Any]]]:
        self.init()
        tags: Counter[str] = Counter()
        symbols: Counter[str] = Counter()
        themes: Counter[str] = Counter()
        for dream in self.list_dreams():
            tags.update(dream["tags"])
            analysis = self.get_dream(dream["id"], language=language)["analysis"]
            if analysis:
                symbols.update(analysis["symbols"])
                themes.update(analysis["themes"])
        return {
            "tags": counter_items(tags),
            "symbols": counter_items(symbols, secondary=tags),
            "themes": counter_items(themes),
        }

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        return db

    def _write_analysis(
        self,
        db: sqlite3.Connection,
        dream_id: int,
        content: str,
        analyzer: Analyzer,
        language: str,
    ) -> None:
        normalized = normalize_analysis(analyzer.analyze(content, language=normalize_language(language)))
        self._store_analysis(db, dream_id, normalized, language)

    def _store_analysis(
        self,
        db: sqlite3.Connection,
        dream_id: int,
        normalized: dict[str, Any],
        language: str,
    ) -> None:
        language = normalize_language(language)
        db.execute(
            """
            INSERT INTO dream_analyses (
                dream_id, language, emotional_tone, symbols_json, themes_json, summary,
                confidence, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(dream_id, language) DO UPDATE SET
                emotional_tone = excluded.emotional_tone,
                symbols_json = excluded.symbols_json,
                themes_json = excluded.themes_json,
                summary = excluded.summary,
                confidence = excluded.confidence,
                raw_json = excluded.raw_json
            """,
            (
                dream_id,
                language,
                normalized["emotional_tone"],
                json.dumps(normalized["symbols"], ensure_ascii=False),
                json.dumps(normalized["themes"], ensure_ascii=False),
                normalized["summary"],
                normalized["confidence"],
                normalized["raw_json"],
            ),
        )
        db.execute("UPDATE dreams SET analysis_status = 'analyzed' WHERE id = ?", (dream_id,))

    def _migrate(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS dreams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    dreamed_on TEXT NOT NULL,
                    manual_mood TEXT,
                    tags_json TEXT NOT NULL DEFAULT '[]',
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
                """
            )
            self._migrate_analysis_table(db)

    def _migrate_analysis_table(self, db: sqlite3.Connection) -> None:
        columns = db.execute("PRAGMA table_info(dream_analyses)").fetchall()
        if not columns:
            self._create_analysis_table(db)
            return

        column_names = {column["name"] for column in columns}
        pk_columns = [
            column["name"]
            for column in sorted((column for column in columns if column["pk"]), key=lambda item: item["pk"])
        ]
        if "language" in column_names and pk_columns == ["dream_id", "language"]:
            return

        db.execute("ALTER TABLE dream_analyses RENAME TO dream_analyses_old")
        self._create_analysis_table(db)
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

    @staticmethod
    def _create_analysis_table(db: sqlite3.Connection) -> None:
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

    def _ensure_gitignore(self) -> None:
        gitignore = self.root / ".gitignore"
        existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
        if ".dreamloop/" not in existing.splitlines():
            prefix = "" if not existing or existing.endswith("\n") else "\n"
            gitignore.write_text(existing + prefix + ".dreamloop/\n", encoding="utf-8")

    @staticmethod
    def _dream_from_row(row: sqlite3.Row) -> dict[str, Any]:
        dream = dict(row)
        dream["tags"] = json.loads(dream.pop("tags_json"))
        return dream


def value_at(payload: dict[str, Any], key: str, index: int) -> Any:
    values = payload.get(key, [])
    return values[index] if index < len(values) else None


def normalize_language(language: str | None) -> str:
    return language if language in {"en", "zh"} else "en"


def dream_terms(dream: dict[str, Any]) -> set[str]:
    stopwords = {"the", "was", "were", "and", "with", "through", "around"}
    terms = set(dream.get("tags", []))
    terms.update(
        term
        for term in re.findall(r"[a-zA-Z]{3,}", dream.get("content", "").lower())
        if term not in stopwords
    )
    analysis = dream.get("analysis")
    if analysis:
        terms.update(analysis.get("symbols", []))
        terms.update(analysis.get("themes", []))
    return {term.lower() for term in terms}


def dream_similarity(target: dict[str, Any], candidate: dict[str, Any]) -> float:
    target_tags = {tag.lower() for tag in target.get("tags", [])}
    candidate_tags = {tag.lower() for tag in candidate.get("tags", [])}
    target_all = dream_terms(target)
    candidate_all = dream_terms(candidate)
    target_text = dream_terms({"content": target.get("content", ""), "tags": []})
    candidate_text = dream_terms({"content": candidate.get("content", ""), "tags": []})

    weighted_overlap = (
        3 * len(target_tags & candidate_tags)
        + 2 * len(target_text & candidate_text)
        + len(target_all & candidate_all)
    )
    weighted_size = (
        3 * len(target_tags | candidate_tags)
        + 2 * len(target_text | candidate_text)
        + len(target_all | candidate_all)
    )
    return weighted_overlap / weighted_size if weighted_size else 0.0


def counter_items(counter: Counter[str], secondary: Counter[str] | None = None) -> list[dict[str, Any]]:
    secondary = secondary or Counter()
    return [
        {"name": name, "count": count}
        for name, count in sorted(
            counter.items(), key=lambda item: (-item[1], -secondary[item[0]], item[0])
        )
    ]


def fetch_open_meteo(lat: float, lon: float) -> dict[str, Any]:
    query = urlencode(
        {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
            "timezone": "auto",
            "past_days": 30,
            "forecast_days": 1,
        }
    )
    with urlopen(f"https://api.open-meteo.com/v1/forecast?{query}", timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_ics(text: str) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT" and current is not None:
            if "starts_on" in current:
                events.append(current)
            current = None
        elif current is not None and ":" in line:
            key, value = line.split(":", 1)
            upper_key = key.upper()
            if upper_key == "UID":
                current["uid"] = value
            elif upper_key.startswith("DTSTART"):
                current["starts_on"] = parse_ics_date(value)
            elif upper_key.startswith("DTEND"):
                current["ends_on"] = parse_ics_date(value)
            elif upper_key == "SUMMARY":
                current["summary"] = value.replace("\\,", ",")
    return events


def parse_ics_date(value: str) -> str:
    if "T" in value:
        return date.fromisoformat(value[:8]).isoformat()
    return date.fromisoformat(f"{value[:4]}-{value[4:6]}-{value[6:8]}").isoformat()
