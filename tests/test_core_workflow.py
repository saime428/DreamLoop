from __future__ import annotations

import json
from datetime import date

from dreamloop.analysis import StaticAnalyzer
from dreamloop.core import DreamLoop


def test_init_creates_local_store_and_gitignore(tmp_path):
    loop = DreamLoop(tmp_path)

    loop.init()

    assert (tmp_path / ".dreamloop").is_dir()
    assert (tmp_path / ".dreamloop" / "dreamloop.sqlite3").exists()
    assert (tmp_path / ".dreamloop" / "chroma").is_dir()
    assert (tmp_path / ".dreamloop" / "exports").is_dir()
    assert (tmp_path / ".dreamloop" / "imports").is_dir()
    assert ".dreamloop/" in (tmp_path / ".gitignore").read_text(encoding="utf-8")


def test_add_dream_is_fast_local_and_pending(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()

    dream_id = loop.add_dream(
        "I was flying above a dark ocean.",
        tags=["water", "flying"],
        mood="anxious",
        dreamed_on=date(2026, 6, 12),
    )

    dream = loop.get_dream(dream_id)
    assert dream["content"] == "I was flying above a dark ocean."
    assert dream["tags"] == ["water", "flying"]
    assert dream["manual_mood"] == "anxious"
    assert dream["analysis_status"] == "pending"


def test_analyze_pending_writes_structured_result(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()
    dream_id = loop.add_dream("I was chased through a flooded city.")

    analyzed = loop.analyze_pending(
        StaticAnalyzer(
            {
                "emotional_tone": "anxious",
                "symbols": ["water", "chase"],
                "themes": ["escape"],
                "summary": "A tense dream about escaping through water.",
                "confidence": 0.82,
            }
        )
    )

    assert analyzed == [dream_id]
    dream = loop.get_dream(dream_id)
    assert dream["analysis_status"] == "analyzed"
    assert dream["analysis"]["emotional_tone"] == "anxious"
    assert dream["analysis"]["symbols"] == ["water", "chase"]
    assert json.loads(dream["analysis"]["raw_json"])["themes"] == ["escape"]


def test_import_ics_and_weather_feed_heatmap_context(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()
    loop.add_dream("A calm walk after the storm.", mood="calm", dreamed_on=date(2026, 6, 10))

    ics = tmp_path / "calendar.ics"
    ics.write_text(
        "\n".join(
            [
                "BEGIN:VCALENDAR",
                "BEGIN:VEVENT",
                "UID:1",
                "DTSTART;VALUE=DATE:20260610",
                "SUMMARY:Therapy session",
                "END:VEVENT",
                "END:VCALENDAR",
            ]
        ),
        encoding="utf-8",
    )

    imported = loop.import_ics(ics)
    weather = loop.sync_weather(
        31.2304,
        121.4737,
        fetcher=lambda *_args, **_kwargs: {
            "daily": {
                "time": ["2026-06-10"],
                "temperature_2m_max": [27.1],
                "temperature_2m_min": [19.8],
                "precipitation_sum": [4.2],
                "weather_code": [61],
            }
        },
    )

    heatmap = loop.heatmap()
    context = loop.day_context(date(2026, 6, 10))

    assert imported == 1
    assert weather == 1
    assert heatmap[0]["date"] == "2026-06-10"
    assert heatmap[0]["count"] == 1
    assert heatmap[0]["moods"] == {"calm": 1}
    assert context["events"][0]["summary"] == "Therapy session"
    assert context["weather"]["precipitation_sum"] == 4.2


def test_pattern_tracking_finds_similar_dreams_and_symbol_trends(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()
    first = loop.add_dream("I was swimming through a city of water.", tags=["water"])
    second = loop.add_dream("The water rose around the buildings.", tags=["water"])
    loop.add_dream("I was giving a speech on a mountain.", tags=["speech"])
    loop.analyze_pending(
        StaticAnalyzer(
            {
                "emotional_tone": "uneasy",
                "symbols": ["water", "city"],
                "themes": ["overwhelm"],
                "summary": "Recurring water in an urban space.",
                "confidence": 0.7,
            }
        )
    )

    similar = loop.similar_dreams(first)
    trends = loop.trends()

    assert similar[0]["id"] == second
    assert similar[0]["score"] > 0
    assert trends["symbols"][0] == {"name": "water", "count": 3}
