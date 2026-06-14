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

from .analysis import (
    Analyzer,
    build_analyzer,
    clean_reflections,
    is_meaningful_term,
    normalize_analysis,
    normalize_report_payload,
    normalize_text_list,
)
from .images import ImageGenerator, build_image_generator, image_status

FEEDBACK_RATINGS = {"resonates", "not_accurate", "unsure"}


class DreamLoop:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or Path.cwd())
        self.data_dir = self.root / ".dreamloop"
        self.db_path = self.data_dir / "dreamloop.sqlite3"
        self.images_dir = self.data_dir / "assets" / "images"

    def init(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        for name in ("chroma", "exports", "imports"):
            (self.data_dir / name).mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_gitignore()
        self._migrate()

    def add_dream(
        self,
        content: str,
        tags: list[str] | None = None,
        mood: str | None = None,
        dreamed_on: date | None = None,
        reflections: dict[str, Any] | None = None,
    ) -> int:
        self.init()
        if not content.strip():
            raise ValueError("Dream content cannot be empty.")
        dreamed_on = dreamed_on or date.today()
        with self._connect() as db:
            cursor = db.execute(
                """
                INSERT INTO dreams (
                    content, created_at, dreamed_on, manual_mood, tags_json, reflection_json, analysis_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    content.strip(),
                    datetime.now().isoformat(timespec="seconds"),
                    dreamed_on.isoformat(),
                    mood,
                    json.dumps(tags or [], ensure_ascii=False),
                    json.dumps(clean_reflections(reflections), ensure_ascii=False),
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
        reflections: dict[str, Any] | None = None,
    ) -> int:
        self.init()
        if not content.strip():
            raise ValueError("Dream content cannot be empty.")
        dreamed_on = dreamed_on or date.today()
        with self._connect() as db:
            cursor = db.execute(
                """
                INSERT INTO dreams (
                    content, created_at, dreamed_on, manual_mood, tags_json, reflection_json, analysis_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    content.strip(),
                    datetime.now().isoformat(timespec="seconds"),
                    dreamed_on.isoformat(),
                    None,
                    "[]",
                    json.dumps(clean_reflections(reflections), ensure_ascii=False),
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
            image = db.execute(
                """
                SELECT * FROM dream_images
                WHERE dream_id = ? AND language = ?
                ORDER BY CASE WHEN status = 'complete' THEN 0 ELSE 1 END, id DESC
                LIMIT 1
                """,
                (dream_id, normalize_language(language)),
            ).fetchone()
        if analysis:
            raw_report = parse_json_any(analysis["raw_json"])
            report = normalize_report_payload(raw_report) if isinstance(raw_report, dict) else {}
            dream["analysis"] = {
                "language": analysis["language"],
                "emotional_tone": analysis["emotional_tone"],
                "symbols": normalize_text_list(json.loads(analysis["symbols_json"])),
                "themes": normalize_text_list(json.loads(analysis["themes_json"])),
                "summary": analysis["summary"],
                "confidence": analysis["confidence"],
                "report": report,
                "raw_json": json.dumps(report, ensure_ascii=False),
            }
        else:
            dream["analysis"] = None
        dream["image"] = image_from_row(image) if image else None
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
                self._write_analysis(db, int(row["id"]), row["content"], analyzer, language, row["reflection_json"])
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
            self._write_analysis(db, dream_id, row["content"], analyzer, language, row["reflection_json"])
        return dream_id

    def delete_dream(self, dream_id: int) -> bool:
        self.init()
        with self._connect() as db:
            db.execute("DELETE FROM user_feedback WHERE dream_id = ?", (dream_id,))
            db.execute("DELETE FROM dream_images WHERE dream_id = ?", (dream_id,))
            db.execute("DELETE FROM dream_analyses WHERE dream_id = ?", (dream_id,))
            cursor = db.execute("DELETE FROM dreams WHERE id = ?", (dream_id,))
            return cursor.rowcount > 0

    def add_feedback(
        self,
        dream_id: int,
        *,
        language: str = "en",
        interpretation_index: int = 0,
        rating: str,
        reason: str = "",
    ) -> int:
        self.init()
        rating = rating.strip()
        if rating not in FEEDBACK_RATINGS:
            raise ValueError(f"Unsupported feedback rating: {rating}")
        with self._connect() as db:
            dream = db.execute("SELECT id FROM dreams WHERE id = ?", (dream_id,)).fetchone()
            if dream is None:
                raise KeyError(f"Dream {dream_id} was not found.")
            cursor = db.execute(
                """
                INSERT INTO user_feedback (
                    dream_id, analysis_language, interpretation_index, rating, reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    dream_id,
                    normalize_language(language),
                    interpretation_index,
                    rating,
                    reason.strip(),
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            return int(cursor.lastrowid)

    def feedback_for_dream(self, dream_id: int, *, language: str = "en") -> list[dict[str, Any]]:
        self.init()
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT * FROM user_feedback
                WHERE dream_id = ? AND analysis_language = ?
                ORDER BY created_at DESC, id DESC
                """,
                (dream_id, normalize_language(language)),
            ).fetchall()
        return [dict(row) for row in rows]

    def feedback_summary(self, *, language: str = "en") -> dict[str, list[dict[str, Any]]]:
        self.init()
        rating_counts: Counter[str] = Counter()
        resonant_themes: Counter[str] = Counter()
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM user_feedback WHERE analysis_language = ?",
                (normalize_language(language),),
            ).fetchall()
        for row in rows:
            rating_counts[row["rating"]] += 1
            if row["rating"] != "resonates":
                continue
            try:
                dream = self.get_dream(int(row["dream_id"]), language=language)
            except KeyError:
                continue
            analysis = dream.get("analysis") or {}
            resonant_themes.update(analysis.get("themes", []))
        return {
            "ratings": counter_items(rating_counts),
            "resonant_themes": counter_items(resonant_themes),
        }

    def seed_demo(self) -> list[int]:
        samples = demo_samples()
        created: list[int] = []
        for sample in samples:
            dream_id = self.add_dream_with_analysis(
                sample["content"],
                sample["analysis"],
                language="en",
                reflections=sample.get("reflections", {}),
            )
            self.generate_visual_memory(dream_id, language="en")
            created.append(dream_id)
        return created

    def generate_visual_memory(self, dream_id: int, *, language: str = "en") -> dict[str, Any]:
        dream = self.get_dream(dream_id, language=language)
        analysis = dream.get("analysis") or {}
        symbols = normalize_text_list(analysis.get("symbols"))
        themes = normalize_text_list(analysis.get("themes"))
        title = str(analysis.get("summary") or dream["content"]).strip()
        if len(title) > 90:
            title = title[:87].rstrip() + "..."
        palette = visual_palette(dream_id)
        prompt_parts = [
            "Local visual memory card for a dream.",
            f"Dream: {dream['content']}",
        ]
        if symbols:
            prompt_parts.append(f"Symbols: {', '.join(symbols[:5])}")
        if themes:
            prompt_parts.append(f"Themes: {', '.join(themes[:5])}")
        visual = {
            "kind": "local_card",
            "title": title,
            "prompt": " ".join(prompt_parts),
            "symbols": symbols[:5],
            "themes": themes[:5],
            "accent_1": palette[0],
            "accent_2": palette[1],
            "accent_3": palette[2],
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        with self._connect() as db:
            db.execute(
                "UPDATE dreams SET visual_json = ? WHERE id = ?",
                (json.dumps(visual, ensure_ascii=False), dream_id),
            )
        return visual

    def generate_dream_image(
        self,
        dream_id: int,
        *,
        language: str = "en",
        generator: ImageGenerator | None = None,
    ) -> dict[str, Any]:
        self.init()
        dream = self.get_dream(dream_id, language=language)
        prompt = build_dream_image_prompt(dream)
        status = image_status(self.root)
        generator = generator or build_image_generator(self.root)
        provider = getattr(generator, "provider", status.provider) if generator else status.provider
        model = getattr(generator, "model", status.model) if generator else status.model
        created_at = datetime.now().isoformat(timespec="seconds")
        if generator is None:
            error = status.warning or "Image provider is not ready."
            with self._connect() as db:
                image_id = self._store_image_record(
                    db,
                    dream_id,
                    language=language,
                    provider=provider,
                    model=model or "",
                    prompt=prompt,
                    image_path="",
                    status="error",
                    error=error,
                    created_at=created_at,
                )
            raise RuntimeError(f"{error} (image record #{image_id})")
        try:
            image_bytes = generator.generate(prompt)
        except Exception as exc:
            with self._connect() as db:
                self._store_image_record(
                    db,
                    dream_id,
                    language=language,
                    provider=provider,
                    model=model or "",
                    prompt=prompt,
                    image_path="",
                    status="error",
                    error=str(exc),
                    created_at=created_at,
                )
            raise
        filename = f"dream-{dream_id}-{normalize_language(language)}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}.png"
        image_path = self.images_dir / filename
        image_path.write_bytes(image_bytes)
        relative_path = f"assets/images/{filename}"
        with self._connect() as db:
            image_id = self._store_image_record(
                db,
                dream_id,
                language=language,
                provider=provider,
                model=model or "",
                prompt=prompt,
                image_path=relative_path,
                status="complete",
                error="",
                created_at=created_at,
            )
            row = db.execute("SELECT * FROM dream_images WHERE id = ?", (image_id,)).fetchone()
        return image_from_row(row)

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
        reflection_json: str | None = None,
    ) -> None:
        reflections = parse_json_object(reflection_json)
        normalized = normalize_analysis(call_analyzer(analyzer, content, normalize_language(language), reflections))
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

    def _store_image_record(
        self,
        db: sqlite3.Connection,
        dream_id: int,
        *,
        language: str,
        provider: str,
        model: str,
        prompt: str,
        image_path: str,
        status: str,
        error: str,
        created_at: str,
    ) -> int:
        cursor = db.execute(
            """
            INSERT INTO dream_images (
                dream_id, language, provider, model, prompt, image_path, status, error, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dream_id,
                normalize_language(language),
                provider,
                model,
                prompt,
                image_path,
                status,
                error,
                created_at,
            ),
        )
        return int(cursor.lastrowid)

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
            self._migrate_dreams_table(db)
            self._migrate_analysis_table(db)

    def _migrate_dreams_table(self, db: sqlite3.Connection) -> None:
        columns = db.execute("PRAGMA table_info(dreams)").fetchall()
        column_names = {column["name"] for column in columns}
        if "reflection_json" not in column_names:
            db.execute("ALTER TABLE dreams ADD COLUMN reflection_json TEXT NOT NULL DEFAULT '{}'")
        if "visual_json" not in column_names:
            db.execute("ALTER TABLE dreams ADD COLUMN visual_json TEXT NOT NULL DEFAULT '{}'")

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
        dream["reflections"] = parse_json_object(dream.pop("reflection_json", "{}"))
        visual_memory = parse_json_any(dream.pop("visual_json", "{}"))
        dream["visual_memory"] = (
            normalize_visual_memory(visual_memory) if isinstance(visual_memory, dict) and visual_memory else None
        )
        return dream


def value_at(payload: dict[str, Any], key: str, index: int) -> Any:
    values = payload.get(key, [])
    return values[index] if index < len(values) else None


def normalize_language(language: str | None) -> str:
    return language if language in {"en", "zh"} else "en"


def visual_palette(seed: int) -> tuple[str, str, str]:
    palettes = (
        ("#69f0d7", "#8e63ff", "#ff6ba8"),
        ("#78d7ff", "#a68cff", "#ffe27a"),
        ("#88f0a6", "#5cc8ff", "#f58bd1"),
        ("#f7c66b", "#8d7aff", "#5de2d0"),
    )
    return palettes[seed % len(palettes)]


def normalize_visual_memory(payload: dict[str, Any]) -> dict[str, Any]:
    visual = dict(payload)
    symbols = normalize_text_list(visual.get("symbols"))
    themes = normalize_text_list(visual.get("themes"))
    title_values = normalize_text_list(visual.get("title"))
    title = title_values[0] if title_values else (symbols[0] if symbols else "Local visual memory")
    prompt = str(visual.get("prompt") or "").strip()
    if '"name"' in prompt or '"meaning"' in prompt or "{'name'" in prompt or "{'meaning'" in prompt:
        prompt_parts = ["Local visual memory card."]
        if symbols:
            prompt_parts.append(f"Symbols: {', '.join(symbols[:5])}.")
        if themes:
            prompt_parts.append(f"Themes: {', '.join(themes[:5])}.")
        prompt = " ".join(prompt_parts)
    visual["kind"] = str(visual.get("kind") or "local_card")
    visual["title"] = title
    visual["prompt"] = prompt
    visual["symbols"] = symbols[:5]
    visual["themes"] = themes[:5]
    visual.setdefault("accent_1", "#69f0d7")
    visual.setdefault("accent_2", "#8e63ff")
    visual.setdefault("accent_3", "#ff6ba8")
    return visual


def image_from_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    image = dict(row)
    image["image_url"] = image_url(image.get("image_path", ""))
    return image


def image_url(image_path: str) -> str:
    if not image_path:
        return ""
    if image_path.startswith("assets/"):
        return f"/dreamloop-assets/{image_path.removeprefix('assets/')}"
    return f"/dreamloop-assets/{image_path.lstrip('/')}"


def build_dream_image_prompt(dream: dict[str, Any]) -> str:
    analysis = dream.get("analysis") or {}
    report = analysis.get("report") or {}
    parts = [
        "Create a cinematic, dreamlike illustration based on this dream.",
        f"Dream text: {dream.get('content', '')}",
    ]
    if analysis.get("summary"):
        parts.append(f"Interpretive summary: {analysis['summary']}")
    if analysis.get("emotional_tone"):
        parts.append(f"Core emotion: {analysis['emotional_tone']}")
    symbols = normalize_text_list(analysis.get("symbols"))
    if symbols:
        parts.append(f"Important people, objects, and scenes: {', '.join(symbols[:6])}")
    details = normalize_text_list(report.get("dream_details"))
    if details:
        parts.append(f"Concrete dream details to preserve: {', '.join(details[:4])}")
    parts.append("Avoid text, logos, UI, gore, and literal JSON. Keep it atmospheric but specific.")
    return " ".join(part for part in parts if part.strip())


def demo_samples() -> list[dict[str, Any]]:
    return [
        {
            "content": "I kept walking through a quiet subway station, but every exit led back to the same platform.",
            "reflections": {
                "strongest_emotion": "uneasy curiosity",
                "real_life_context": "I have been comparing several life options.",
            },
            "analysis": {
                "analysis_version": 2,
                "emotional_tone": "uneasy but curious",
                "symbols": ["subway station", "repeating platform", "exit"],
                "themes": ["transition", "uncertainty"],
                "summary": "A transition dream where every route returns to the same unresolved question.",
                "confidence": 0.82,
                "dream_details": [
                    "The station feels quiet rather than dangerous.",
                    "Every exit leads back to the same platform.",
                ],
                "core_emotion": "A mix of curiosity and low-grade frustration.",
                "real_life_links": ["You may be circling a decision without finding a satisfying next step."],
                "possible_interpretations": [
                    {
                        "title": "A decision loop",
                        "interpretation": "The repeating platform may reflect revisiting the same choice from different angles.",
                        "dream_evidence": "Each exit returns to the same place.",
                        "real_life_connection": "This can map to a decision that has no perfect option yet.",
                        "verification_question": "Which real choice keeps bringing you back to the same concern?",
                    }
                ],
                "real_life_questions": ["What decision feels circular rather than impossible?"],
                "verification_prompts": ["Write down the choices you keep comparing and what each one costs."],
            },
        },
        {
            "content": "A blue door appeared under the sea. I could breathe, but I waited before opening it.",
            "reflections": {
                "strongest_emotion": "wonder",
                "personal_association": "A new project that feels exciting and heavy.",
            },
            "analysis": {
                "analysis_version": 2,
                "emotional_tone": "wonder with caution",
                "symbols": ["blue door", "sea", "waiting"],
                "themes": ["threshold", "exploration"],
                "summary": "A threshold dream about a possible opening that still asks for emotional readiness.",
                "confidence": 0.84,
                "dream_details": ["The door is under the sea.", "You can breathe, but you do not rush."],
                "core_emotion": "Interest held back by caution.",
                "real_life_links": ["A promising opportunity may feel real but not fully safe yet."],
                "possible_interpretations": [
                    {
                        "title": "Approaching an opportunity carefully",
                        "interpretation": "The blue door may mark a new option, while the sea adds emotional depth.",
                        "dream_evidence": "You can breathe, yet you wait.",
                        "real_life_connection": "This may echo a project or relationship that needs pacing.",
                        "verification_question": "Where are you interested but not ready to commit?",
                    }
                ],
                "real_life_questions": ["What opening needs patience rather than force?"],
                "verification_prompts": ["Notice whether excitement or fear is leading the delay."],
            },
        },
        {
            "content": "I found an old library where the books rearranged themselves whenever I touched the shelves.",
            "reflections": {
                "strongest_emotion": "fascinated",
                "waking_feeling": "I wanted to remember the layout.",
            },
            "analysis": {
                "analysis_version": 2,
                "emotional_tone": "fascinated and slightly overwhelmed",
                "symbols": ["old library", "moving shelves", "rearranging books"],
                "themes": ["memory", "knowledge", "change"],
                "summary": "A knowledge dream where memory keeps reorganizing itself as you interact with it.",
                "confidence": 0.8,
                "dream_details": ["Books rearrange when touched.", "The library feels old and alive."],
                "core_emotion": "The pleasure of discovery mixed with too much information.",
                "real_life_links": ["You may be reorganizing how you understand a topic or period of life."],
                "possible_interpretations": [
                    {
                        "title": "A changing knowledge map",
                        "interpretation": "The library may reflect a personal knowledge system that evolves as you use it.",
                        "dream_evidence": "The books move only when you touch the shelves.",
                        "real_life_connection": "This may map to learning, writing, or rebuilding your notes.",
                        "verification_question": "What knowledge area changes shape whenever you engage with it?",
                    }
                ],
                "real_life_questions": ["What system are you trying to reorganize without losing yourself in it?"],
                "verification_prompts": ["Pick one area of knowledge and name the pattern that keeps shifting."],
            },
        },
    ]


def parse_json_object(text: str | None) -> dict[str, str]:
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return clean_reflections(payload if isinstance(payload, dict) else {})


def parse_json_any(text: str | None) -> Any:
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def call_analyzer(
    analyzer: Analyzer,
    content: str,
    language: str,
    reflections: dict[str, str],
) -> dict[str, Any]:
    import inspect

    parameters = inspect.signature(analyzer.analyze).parameters
    if "reflections" in parameters:
        return analyzer.analyze(content, language=language, reflections=reflections)
    return analyzer.analyze(content, language=language)


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
    filtered = Counter({name: count for name, count in counter.items() if is_meaningful_term(name)})
    return [
        {"name": name, "count": count}
        for name, count in sorted(
            filtered.items(), key=lambda item: (-item[1], -secondary[item[0]], item[0])
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
