from __future__ import annotations

import json
import sqlite3
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from .analysis import (
    Analyzer,
    build_analyzer,
    clean_reflections,
    ensure_gitignore,
    is_meaningful_term,
    normalize_analysis,
    normalize_report_payload,
    normalize_text_list,
)
from .database import connect, migrate
from .demo_data import demo_samples, visual_palette
from .graph import build_symbol_graph
from .importers import fetch_open_meteo, parse_ics, value_at
from .images import ImageGenerator, build_image_generator, image_status
from .visuals import build_dream_image_prompt, image_from_row, normalize_visual_memory

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
        ensure_gitignore(self.root)
        migrate(self.db_path)

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
            rows = db.execute(
                "SELECT * FROM dreams ORDER BY dreamed_on DESC, id DESC"
            ).fetchall()
        return [self._dream_from_row(row) for row in rows]

    def list_dreams_with_analysis(self, language: str = "en") -> list[dict[str, Any]]:
        self.init()
        language = normalize_language(language)
        with self._connect() as db:
            dream_rows = db.execute(
                "SELECT * FROM dreams ORDER BY dreamed_on DESC, id DESC"
            ).fetchall()
            analysis_rows = db.execute(
                "SELECT * FROM dream_analyses WHERE language = ?", (language,)
            ).fetchall()
            image_rows = db.execute(
                """
                SELECT * FROM dream_images
                WHERE language = ?
                ORDER BY CASE WHEN status = 'complete' THEN 0 ELSE 1 END, id DESC
                """,
                (language,),
            ).fetchall()

        analyses = {int(row["dream_id"]): row for row in analysis_rows}
        images: dict[int, sqlite3.Row] = {}
        for row in image_rows:
            images.setdefault(int(row["dream_id"]), row)

        dreams = []
        for row in dream_rows:
            dream = self._dream_from_row(row)
            dream_id = int(dream["id"])
            dream["analysis"] = analysis_from_row(analyses.get(dream_id))
            dream["image"] = image_from_row(images.get(dream_id))
            dreams.append(dream)
        return dreams

    def get_dream(self, dream_id: int, language: str = "en") -> dict[str, Any]:
        self.init()
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM dreams WHERE id = ?", (dream_id,)
            ).fetchone()
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
        dream["analysis"] = analysis_from_row(analysis)
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
                self._write_analysis(
                    db,
                    int(row["id"]),
                    row["content"],
                    analyzer,
                    language,
                    row["reflection_json"],
                )
                analyzed.append(int(row["id"]))
        return analyzed

    def analyze_dream(
        self, dream_id: int, analyzer: Analyzer | None = None, *, language: str = "en"
    ) -> int:
        self.init()
        if analyzer is None:
            analyzer = build_analyzer(self.root)
            if analyzer is None:
                raise RuntimeError("AI provider is not ready.")

        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM dreams WHERE id = ?", (dream_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"Dream {dream_id} was not found.")
            self._write_analysis(
                db, dream_id, row["content"], analyzer, language, row["reflection_json"]
            )
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
            dream = db.execute(
                "SELECT id FROM dreams WHERE id = ?", (dream_id,)
            ).fetchone()
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

    def feedback_for_dream(
        self, dream_id: int, *, language: str = "en"
    ) -> list[dict[str, Any]]:
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

    def feedback_summary(
        self, *, language: str = "en"
    ) -> dict[str, list[dict[str, Any]]]:
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

    def seed_demo(self, language: str = "en") -> list[int]:
        language = normalize_language(language)
        samples = demo_samples(language)
        created: list[int] = []
        for sample in samples:
            dream_id = self.add_dream_with_analysis(
                sample["content"],
                sample["analysis"],
                language=language,
                reflections=sample.get("reflections", {}),
            )
            self.generate_visual_memory(dream_id, language=language)
            created.append(dream_id)
        return created

    def generate_visual_memory(
        self, dream_id: int, *, language: str = "en"
    ) -> dict[str, Any]:
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
        provider = (
            getattr(generator, "provider", status.provider)
            if generator
            else status.provider
        )
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
            row = db.execute(
                "SELECT * FROM dream_images WHERE id = ?", (image_id,)
            ).fetchone()
        return image_from_row(row)

    def import_ics(self, path: str | Path) -> int:
        self.init()
        resolved = Path(path).resolve()
        allowed = self.data_dir.resolve()
        if not resolved.is_relative_to(allowed):
            raise ValueError(f"Import path must be under {self.data_dir}")
        events = parse_ics(resolved.read_text(encoding="utf-8"))
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
            bucket = grouped.setdefault(
                row["dreamed_on"], {"date": row["dreamed_on"], "count": 0, "moods": {}}
            )
            bucket["count"] += row["count"]
            mood = row["manual_mood"] or "unknown"
            bucket["moods"][mood] = row["count"]
        return list(grouped.values())

    def day_context(self, day: date) -> dict[str, Any]:
        self.init()
        day_text = day.isoformat()
        with self._connect() as db:
            events = db.execute(
                "SELECT * FROM calendar_events WHERE starts_on = ? ORDER BY id",
                (day_text,),
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

    def trends_from_dreams(self, dreams: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        tags: Counter[str] = Counter()
        symbols: Counter[str] = Counter()
        themes: Counter[str] = Counter()
        for dream in dreams:
            tags.update(dream["tags"])
            analysis = dream.get("analysis")
            if analysis:
                symbols.update(analysis["symbols"])
                themes.update(analysis["themes"])
        return {
            "tags": counter_items(tags),
            "symbols": counter_items(symbols, secondary=tags),
            "themes": counter_items(themes),
        }

    def trends(self, language: str = "en") -> dict[str, list[dict[str, Any]]]:
        return self.trends_from_dreams(self.list_dreams_with_analysis(language=language))

    def symbol_graph_from_dreams(self, dreams: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        return build_symbol_graph(dreams)

    def symbol_graph(self, language: str = "en") -> dict[str, list[dict[str, Any]]]:
        return self.symbol_graph_from_dreams(self.list_dreams_with_analysis(language=language))

    def _connect(self) -> sqlite3.Connection:
        return connect(self.db_path)

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
        normalized = normalize_analysis(
            call_analyzer(analyzer, content, normalize_language(language), reflections)
        )
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
        db.execute(
            "UPDATE dreams SET analysis_status = 'analyzed' WHERE id = ?", (dream_id,)
        )

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

    @staticmethod
    def _dream_from_row(row: sqlite3.Row) -> dict[str, Any]:
        dream = dict(row)
        dream["tags"] = json.loads(dream.pop("tags_json"))
        dream["reflections"] = parse_json_object(dream.pop("reflection_json", "{}"))
        visual_memory = parse_json_any(dream.pop("visual_json", "{}"))
        dream["visual_memory"] = (
            normalize_visual_memory(visual_memory)
            if isinstance(visual_memory, dict) and visual_memory
            else None
        )
        return dream


def analysis_from_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    raw_report = parse_json_any(row["raw_json"])
    report = normalize_report_payload(raw_report) if isinstance(raw_report, dict) else {}
    return {
        "language": row["language"],
        "emotional_tone": row["emotional_tone"],
        "symbols": normalize_text_list(json.loads(row["symbols_json"])),
        "themes": normalize_text_list(json.loads(row["themes_json"])),
        "summary": row["summary"],
        "confidence": row["confidence"],
        "report": report,
        "raw_json": json.dumps(report, ensure_ascii=False),
    }


def normalize_language(language: str | None) -> str:
    return language if language in {"en", "zh"} else "en"


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


def counter_items(
    counter: Counter[str], secondary: Counter[str] | None = None
) -> list[dict[str, Any]]:
    secondary = secondary or Counter()
    filtered = Counter(
        {name: count for name, count in counter.items() if is_meaningful_term(name)}
    )
    return [
        {"name": name, "count": count}
        for name, count in sorted(
            filtered.items(), key=lambda item: (-item[1], -secondary[item[0]], item[0])
        )
    ]
