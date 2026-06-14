from __future__ import annotations

import json
from datetime import date

from dreamloop.analysis import StaticAnalyzer
from dreamloop.analysis import normalize_analysis
from dreamloop.core import DreamLoop


class LanguageAnalyzer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def analyze(self, content: str, language: str = "en") -> dict[str, object]:
        self.calls.append((content, language))
        if language == "zh":
            return {
                "emotional_tone": "平静",
                "symbols": ["月亮"],
                "themes": ["抵达"],
                "summary": "一场关于月光下抵达的梦。",
                "confidence": 0.91,
            }
        return {
            "emotional_tone": "calm",
            "symbols": ["moon"],
            "themes": ["arrival"],
            "summary": "A dream about arriving under moonlight.",
            "confidence": 0.9,
        }


class ReflectionAwareAnalyzer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, str]]] = []

    def analyze(
        self,
        content: str,
        language: str = "en",
        reflections: dict[str, str] | None = None,
    ) -> dict[str, object]:
        self.calls.append((content, language, dict(reflections or {})))
        return detailed_analysis_result(language)


def detailed_analysis_result(language: str = "en") -> dict[str, object]:
    if language == "zh":
        return {
            "analysis_version": 2,
            "emotional_tone": "焦虑但好奇",
            "symbols": ["蓝色的门", "海底"],
            "themes": ["边界", "探索"],
            "summary": "这个梦把海底的门和现实中的压力联系在一起。",
            "confidence": 0.88,
            "dream_details": ["海底出现蓝色的门", "你停在门前没有立刻打开"],
            "core_emotion": "焦虑中夹着想探索的冲动",
            "waking_feeling": "醒来后还有一点紧张",
            "important_elements": ["蓝色的门", "海底空间"],
            "real_life_links": ["最近在考虑是否换工作"],
            "personal_associations": ["门让我想到新的选择"],
            "possible_interpretations": [
                {
                    "title": "解释 1：你在靠近一个新选择",
                    "interpretation": "门像是一个机会，但海底让这个机会带着压力。",
                    "dream_evidence": "蓝色的门出现在海底，而不是安全的房间里。",
                    "real_life_connection": "这可能对应你最近对换工作的犹豫。",
                    "verification_question": "最近有没有一个选择既吸引你又让你不安？",
                },
                {
                    "title": "解释 2：你需要先处理情绪再行动",
                    "interpretation": "海水可能代表情绪环境，门代表下一步。",
                    "dream_evidence": "你停在门前，没有立刻打开。",
                    "real_life_connection": "现实里可能有些压力需要先被看见。",
                    "verification_question": "你是否正在推迟一个决定，因为状态还没准备好？",
                },
            ],
            "real_life_questions": ["我真正害怕的是失败，还是改变本身？"],
            "verification_prompts": ["把这个梦和最近一周最反复出现的压力放在一起看。"],
        }
    return {
        "analysis_version": 2,
        "emotional_tone": "anxious but curious",
        "symbols": ["blue door", "undersea room"],
        "themes": ["threshold", "exploration"],
        "summary": "The dream connects an undersea door with a pressured real-life decision.",
        "confidence": 0.88,
        "dream_details": ["a blue door appeared under the sea"],
        "core_emotion": "anxiety mixed with curiosity",
        "waking_feeling": "still tense after waking",
        "important_elements": ["blue door", "undersea space"],
        "real_life_links": ["thinking about changing jobs"],
        "personal_associations": ["the door feels like a new choice"],
        "possible_interpretations": [
            {
                "title": "Interpretation 1: You are near a new choice",
                "interpretation": "The door suggests an opportunity, while the sea gives it pressure.",
                "dream_evidence": "The blue door appears underwater rather than in a safe room.",
                "real_life_connection": "This may echo your current uncertainty about changing jobs.",
                "verification_question": "Is there a choice that attracts you and unsettles you?",
            },
            {
                "title": "Interpretation 2: Emotion may need attention first",
                "interpretation": "The sea may describe the emotional setting around the next step.",
                "dream_evidence": "You paused before the door instead of opening it.",
                "real_life_connection": "You may need to name the pressure before acting.",
                "verification_question": "Are you delaying a decision because you do not feel ready?",
            },
        ],
        "real_life_questions": ["Am I afraid of failing, or of change itself?"],
        "verification_prompts": ["Compare this dream with the pressure you felt most often this week."],
    }


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
    assert dream["reflections"] == {}


def test_add_dream_stores_optional_reflections(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()

    dream_id = loop.add_dream(
        "I found a blue door under the sea.",
        reflections={
            "strongest_emotion": "curiosity with fear",
            "waking_feeling": "tense",
            "real_life_context": "I am considering a job change.",
        },
    )

    dream = loop.get_dream(dream_id)
    assert dream["reflections"] == {
        "strongest_emotion": "curiosity with fear",
        "waking_feeling": "tense",
        "real_life_context": "I am considering a job change.",
    }


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


def test_analyze_dream_writes_only_requested_dream(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()
    first_id = loop.add_dream("I was walking through a quiet library.")
    second_id = loop.add_dream("A black river crossed the train station.")

    analyzed = loop.analyze_dream(
        second_id,
        StaticAnalyzer(
            {
                "emotional_tone": "uneasy",
                "symbols": ["river", "station"],
                "themes": ["transition"],
                "summary": "A transition dream marked by a dark river.",
                "confidence": 0.76,
            }
        ),
    )

    assert analyzed == second_id
    assert loop.get_dream(first_id)["analysis_status"] == "pending"
    second = loop.get_dream(second_id)
    assert second["analysis_status"] == "analyzed"
    assert second["analysis"]["symbols"] == ["river", "station"]


def test_normalize_analysis_keeps_report_strings_as_single_items():
    normalized = normalize_analysis(
        {
            "analysis_version": 2,
            "emotional_tone": "anxious",
            "symbols": "??",
            "themes": ["transition"],
            "summary": "A long interpretation.",
            "confidence": 0.7,
            "dream_details": "A crowded subway station turned into an unfamiliar neighborhood.",
            "real_life_links": "You may be navigating several housing or commute options.",
            "real_life_questions": "Which choice feels unreliable in real life?",
            "verification_prompts": "Check whether this matches your recent decisions.",
        }
    )

    assert normalized["report"]["dream_details"] == [
        "A crowded subway station turned into an unfamiliar neighborhood."
    ]
    assert normalized["report"]["real_life_links"] == [
        "You may be navigating several housing or commute options."
    ]
    assert normalized["report"]["real_life_questions"] == ["Which choice feels unreliable in real life?"]
    assert normalized["symbols"] == []


def test_analyze_dream_passes_reflections_and_preserves_detailed_report(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()
    dream_id = loop.add_dream(
        "我在海底看到一扇蓝色的门。",
        reflections={
            "strongest_emotion": "害怕又好奇",
            "waking_feeling": "醒来后很紧张",
            "real_life_context": "最近在考虑是否换工作",
            "personal_association": "门让我想到新的选择",
        },
    )
    analyzer = ReflectionAwareAnalyzer()

    analyzed = loop.analyze_dream(dream_id, analyzer, language="zh")

    dream = loop.get_dream(analyzed, language="zh")
    raw = json.loads(dream["analysis"]["raw_json"])
    assert analyzer.calls == [
        (
            "我在海底看到一扇蓝色的门。",
            "zh",
            {
                "strongest_emotion": "害怕又好奇",
                "waking_feeling": "醒来后很紧张",
                "real_life_context": "最近在考虑是否换工作",
                "personal_association": "门让我想到新的选择",
            },
        )
    ]
    assert raw["analysis_version"] == 2
    assert len(raw["possible_interpretations"]) == 2
    assert raw["real_life_questions"] == ["我真正害怕的是失败，还是改变本身？"]


def test_analyze_dream_stores_separate_language_results(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()
    dream_id = loop.add_dream("The moon was above the harbor.")
    analyzer = LanguageAnalyzer()

    loop.analyze_dream(dream_id, analyzer, language="en")
    loop.analyze_dream(dream_id, analyzer, language="zh")

    english = loop.get_dream(dream_id, language="en")
    chinese = loop.get_dream(dream_id, language="zh")
    assert analyzer.calls == [
        ("The moon was above the harbor.", "en"),
        ("The moon was above the harbor.", "zh"),
    ]
    assert english["analysis"]["summary"] == "A dream about arriving under moonlight."
    assert chinese["analysis"]["summary"] == "一场关于月光下抵达的梦。"
    assert chinese["analysis"]["symbols"] == ["月亮"]


def test_add_dream_with_analysis_saves_selected_language(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()

    dream_id = loop.add_dream_with_analysis(
        "我打开了一扇发光的门。",
        {
            "emotional_tone": "好奇",
            "symbols": ["门"],
            "themes": ["发现"],
            "summary": "一场关于发现隐藏之门的梦。",
            "confidence": 0.86,
        },
        language="zh",
    )

    chinese = loop.get_dream(dream_id, language="zh")
    english = loop.get_dream(dream_id, language="en")
    assert chinese["analysis_status"] == "analyzed"
    assert chinese["analysis"]["summary"] == "一场关于发现隐藏之门的梦。"
    assert english["analysis"] is None


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


def test_trends_filter_placeholder_terms_and_delete_dream(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()
    first_id = loop.add_dream("A crowded subway station became an unfamiliar district.")
    second_id = loop.add_dream("I walked through a library.")
    loop.analyze_dream(
        first_id,
        StaticAnalyzer(
            {
                "emotional_tone": "anxious",
                "symbols": ["??", "subway station"],
                "themes": ["????", "transition"],
                "summary": "A transition dream.",
                "confidence": 0.7,
            }
        ),
    )

    trends = loop.trends()

    assert trends["symbols"] == [{"name": "subway station", "count": 1}]
    assert trends["themes"] == [{"name": "transition", "count": 1}]
    assert loop.delete_dream(second_id) is True
    assert loop.delete_dream(9999) is False
    assert [dream["id"] for dream in loop.list_dreams()] == [first_id]


def test_structured_symbol_objects_are_displayed_as_terms(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()
    dream_id = loop.add_dream_with_analysis(
        "I was lost in a subway station with a broken map.",
        {
            "emotional_tone": "anxious",
            "symbols": [
                {"name": "subway station", "meaning": "A confusing transition point."},
                {"name": "broken map", "meaning": "Planning tools failing."},
            ],
            "themes": [{"name": "lost direction", "meaning": "Unclear next step."}],
            "summary": "A dream about finding direction under pressure.",
            "confidence": 0.74,
            "dream_details": [{"name": "subway station", "meaning": "You cannot find the exit."}],
        },
    )

    dream = loop.get_dream(dream_id)
    trends = loop.trends()
    raw = json.loads(dream["analysis"]["raw_json"])

    assert dream["analysis"]["symbols"] == ["subway station", "broken map"]
    assert dream["analysis"]["themes"] == ["lost direction"]
    assert raw["symbols"] == ["subway station", "broken map"]
    assert "subway station: You cannot find the exit." in raw["dream_details"]
    assert {"name": "subway station", "count": 1} in trends["symbols"]
    assert {"name": "broken map", "count": 1} in trends["symbols"]
    assert all('"name"' not in item["name"] and "meaning" not in item["name"] for item in trends["symbols"])


def test_legacy_json_string_terms_and_visual_memory_are_sanitized(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()
    dream_id = loop.add_dream_with_analysis(
        "I was trapped in a station.",
        {
            "emotional_tone": "stuck",
            "symbols": ["station"],
            "themes": ["transition"],
            "summary": "A stuck transition dream.",
            "confidence": 0.7,
        },
    )
    legacy_symbol = json.dumps({"name": "station", "meaning": "A transfer point."}, ensure_ascii=False)
    legacy_theme = json.dumps({"name": "blocked transition", "meaning": "No clear route."}, ensure_ascii=False)
    legacy_visual = {
        "kind": "local_card",
        "title": legacy_symbol,
        "prompt": f"Local visual memory card. Symbols: {legacy_symbol}",
        "symbols": [legacy_symbol],
        "themes": [legacy_theme],
        "accent_1": "#69f0d7",
        "accent_2": "#8e63ff",
        "accent_3": "#ff6ba8",
    }
    with loop._connect() as db:
        db.execute(
            "UPDATE dream_analyses SET symbols_json = ?, themes_json = ? WHERE dream_id = ? AND language = 'en'",
            (json.dumps([legacy_symbol]), json.dumps([legacy_theme]), dream_id),
        )
        db.execute("UPDATE dreams SET visual_json = ? WHERE id = ?", (json.dumps(legacy_visual), dream_id))

    dream = loop.get_dream(dream_id)
    trends = loop.trends()
    visual = dream["visual_memory"]

    assert dream["analysis"]["symbols"] == ["station"]
    assert dream["analysis"]["themes"] == ["blocked transition"]
    assert trends["symbols"] == [{"name": "station", "count": 1}]
    assert visual["title"] == "station"
    assert visual["symbols"] == ["station"]
    assert visual["themes"] == ["blocked transition"]
    assert '"name"' not in visual["prompt"]
    assert "meaning" not in visual["prompt"]


def test_generate_visual_memory_creates_local_card_without_external_api(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()
    dream_id = loop.add_dream_with_analysis(
        "I found a blue door under the sea.",
        {
            "emotional_tone": "curious",
            "symbols": ["blue door", "sea"],
            "themes": ["threshold"],
            "summary": "A threshold dream under water.",
            "confidence": 0.8,
        },
        language="en",
    )

    visual = loop.generate_visual_memory(dream_id, language="en")
    dream = loop.get_dream(dream_id, language="en")

    assert visual["kind"] == "local_card"
    assert visual["title"] == "A threshold dream under water."
    assert "blue door" in visual["prompt"]
    assert "sea" in visual["symbols"]
    assert dream["visual_memory"] == visual


def test_generate_visual_memory_raises_for_missing_dream(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()

    try:
        loop.generate_visual_memory(999)
    except KeyError as exc:
        assert "999" in str(exc)
    else:
        raise AssertionError("Expected missing dream to raise KeyError")


def test_feedback_lifecycle_and_resonance_summary(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()
    dream_id = loop.add_dream_with_analysis(
        "I was lost in a station.",
        {
            "analysis_version": 2,
            "emotional_tone": "anxious",
            "symbols": ["station"],
            "themes": ["transition", "uncertainty"],
            "summary": "A dream about uncertainty.",
            "confidence": 0.8,
            "possible_interpretations": [
                {
                    "title": "Choosing a route",
                    "interpretation": "You may be comparing several imperfect options.",
                    "dream_evidence": "The station had too many exits.",
                    "real_life_connection": "This may mirror a current decision.",
                    "verification_question": "Which choice feels overloaded?",
                }
            ],
        },
        language="en",
    )

    feedback_id = loop.add_feedback(
        dream_id,
        language="en",
        interpretation_index=0,
        rating="resonates",
        reason="This matches my week.",
    )
    feedback = loop.feedback_for_dream(dream_id, language="en")
    summary = loop.feedback_summary(language="en")

    assert feedback_id > 0
    assert feedback[0]["rating"] == "resonates"
    assert feedback[0]["reason"] == "This matches my week."
    assert summary["ratings"][0] == {"name": "resonates", "count": 1}
    assert {"name": "transition", "count": 1} in summary["resonant_themes"]
    assert {"name": "uncertainty", "count": 1} in summary["resonant_themes"]

    try:
        loop.add_feedback(dream_id, language="en", interpretation_index=0, rating="too_mystical")
    except ValueError as exc:
        assert "rating" in str(exc)
    else:
        raise AssertionError("Expected invalid feedback rating to fail")

    assert loop.delete_dream(dream_id) is True
    assert loop.feedback_for_dream(dream_id, language="en") == []


def test_seed_demo_adds_complete_local_sample_without_deleting_existing_data(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()
    existing = loop.add_dream("Do not remove this dream.")

    created = loop.seed_demo()
    dreams = loop.list_dreams()
    visual_count = sum(1 for dream in dreams if dream.get("visual_memory"))

    assert len(created) == 3
    assert existing in [dream["id"] for dream in dreams]
    assert len(dreams) == 4
    assert visual_count >= 1
    assert all(loop.get_dream(dream_id, language="en")["analysis"] for dream_id in created)
