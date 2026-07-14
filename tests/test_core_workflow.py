from __future__ import annotations

import json
import sqlite3
from datetime import date

import pytest

from dreamloop.analysis import AnalysisIncomplete, AnalysisLanguageMismatch, StaticAnalyzer
from dreamloop.analysis import normalize_analysis
from dreamloop.analysis import REFLECTION_LABELS
from dreamloop.core import AnalysisUnavailableError, DreamLoop
from dreamloop.database import connect
from dreamloop.images import image_status, save_image_config, save_image_secret


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
    assert (tmp_path / ".dreamloop" / "exports").is_dir()
    assert (tmp_path / ".dreamloop" / "imports").is_dir()
    assert ".dreamloop/" in (tmp_path / ".gitignore").read_text(encoding="utf-8")


def test_database_context_closes_connection(tmp_path):
    with connect(tmp_path / "close-check.sqlite3") as db:
        db.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY)")

    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        db.execute("SELECT 1")


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


def test_analyze_pending_is_language_specific(tmp_path):
    loop = DreamLoop(tmp_path)
    dream_id = loop.add_dream("I crossed a moonlit station.")
    analyzer = LanguageAnalyzer()

    loop.analyze_dream(dream_id, analyzer, language="en")
    analyzed = loop.analyze_pending(analyzer, language="zh")

    assert analyzed == [dream_id]
    assert loop.get_dream(dream_id, language="zh")["analysis"]["summary"] == "一场关于月光下抵达的梦。"


def test_analyze_pending_does_not_hold_database_lock_during_provider_call(tmp_path):
    loop = DreamLoop(tmp_path)
    first_id = loop.add_dream("First pending dream.")
    second_id = loop.add_dream("Second pending dream.")

    class WritingAnalyzer:
        calls = 0

        def analyze(self, content: str, language: str = "en") -> dict[str, object]:
            self.calls += 1
            if self.calls == 2:
                loop.add_dream("Write performed during provider call.")
            return {
                "emotional_tone": "calm",
                "symbols": [],
                "themes": [],
                "summary": "A complete English analysis returned during the provider call.",
                "confidence": 1,
            }

    assert loop.analyze_pending(WritingAnalyzer()) == [first_id, second_id]


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


def test_custom_analyzer_language_mismatch_is_not_retried_or_persisted(tmp_path):
    loop = DreamLoop(tmp_path)
    dream_id = loop.add_dream("I found a bright doorway.")

    class CountingAnalyzer:
        calls = 0

        def analyze(self, content: str, language: str = "en") -> dict[str, object]:
            self.calls += 1
            return {"summary": "这个结果完全使用中文，因此不能被标记成英文分析保存。"}

    analyzer = CountingAnalyzer()

    with pytest.raises(AnalysisLanguageMismatch):
        loop.analyze_dream(dream_id, analyzer, language="en")

    assert analyzer.calls == 1
    assert loop.get_dream(dream_id, language="en")["analysis"] is None


@pytest.mark.parametrize(
    ("analysis_payload", "error_type"),
    [
        ({"summary": "这个结果使用中文，却试图保存成英文分析。"}, AnalysisLanguageMismatch),
        ({"summary": "too short"}, AnalysisIncomplete),
    ],
)
def test_invalid_analysis_rolls_back_dream_and_analysis_rows(tmp_path, analysis_payload, error_type):
    loop = DreamLoop(tmp_path)

    with pytest.raises(error_type):
        loop.add_dream_with_analysis(
            "I found a bright doorway.",
            analysis_payload,
            language="en",
        )

    assert loop.list_dreams() == []
    with loop._connect() as db:
        assert db.execute("SELECT COUNT(*) FROM dream_analyses").fetchone()[0] == 0


def test_unsupported_analysis_language_rolls_back_write(tmp_path):
    loop = DreamLoop(tmp_path)

    with pytest.raises(ValueError, match="Unsupported analysis language"):
        loop.add_dream_with_analysis(
            "I found a bright doorway.",
            {"summary": "This analysis is long enough to describe a present decision in clear English."},
            language="fr",
        )

    assert loop.list_dreams() == []


def test_detail_fallback_prefers_valid_other_language_over_mislabeled_requested_row(tmp_path):
    loop = DreamLoop(tmp_path)
    dream_id = loop.add_dream_with_analysis(
        "I found a bright doorway.",
        {"summary": "This English analysis connects the doorway with a current choice and uncertainty."},
        language="en",
    )
    loop.analyze_dream(
        dream_id,
        StaticAnalyzer({"summary": "这份中文分析把发光的门与现实中的选择和犹豫联系起来。"}),
        language="zh",
    )
    bad_english = normalize_analysis({"summary": "这条记录虽然标记为英文，但实际内容明显全部使用中文。"})
    with loop._connect() as db:
        db.execute(
            """
            UPDATE dream_analyses
            SET emotional_tone = ?, symbols_json = ?, themes_json = ?, summary = ?, raw_json = ?
            WHERE dream_id = ? AND language = 'en'
            """,
            (
                bad_english["emotional_tone"],
                json.dumps(bad_english["symbols"], ensure_ascii=False),
                json.dumps(bad_english["themes"], ensure_ascii=False),
                bad_english["summary"],
                bad_english["raw_json"],
                dream_id,
            ),
        )

    exact = loop.get_dream(dream_id, language="en")
    detail = loop.get_dream(dream_id, language="en", allow_analysis_fallback=True)

    assert exact["analysis"] is None
    assert exact["analysis_language_mismatch"] is True
    assert detail["analysis"]["language"] == "zh"
    assert detail["displayed_analysis_language"] == "zh"
    assert detail["analysis_is_fallback"] is True
    assert detail["analysis_actions_enabled"] is True


def test_mismatch_only_detail_disables_analysis_bound_actions(tmp_path):
    loop = DreamLoop(tmp_path)
    dream_id = loop.add_dream("I found a bright doorway.")
    bad_english = normalize_analysis({"summary": "这条记录虽然标记为英文，但实际内容明显全部使用中文。"})
    with loop._connect() as db:
        db.execute(
            """
            INSERT INTO dream_analyses (
                dream_id, language, emotional_tone, symbols_json, themes_json, summary, confidence, raw_json
            ) VALUES (?, 'en', ?, ?, ?, ?, ?, ?)
            """,
            (
                dream_id,
                bad_english["emotional_tone"],
                json.dumps(bad_english["symbols"], ensure_ascii=False),
                json.dumps(bad_english["themes"], ensure_ascii=False),
                bad_english["summary"],
                bad_english["confidence"],
                bad_english["raw_json"],
            ),
        )

    detail = loop.get_dream(dream_id, language="en", allow_analysis_fallback=True)

    assert detail["analysis"]["language_mismatch"] is True
    assert detail["analysis_language_mismatch"] is True
    assert detail["analysis_actions_enabled"] is False
    with pytest.raises(AnalysisUnavailableError):
        loop.add_feedback(dream_id, language="en", rating="resonates")

    visual = loop.generate_visual_memory(dream_id, language="en")
    assert visual["title"] == "I found a bright doorway."
    assert visual["symbols"] == []
    assert loop.trends(language="en")["themes"] == []

    with loop._connect() as db:
        db.execute(
            """
            INSERT INTO user_feedback (
                dream_id, analysis_language, interpretation_index, rating, reason, created_at
            ) VALUES (?, 'en', 0, 'resonates', '', '2026-07-14T00:00:00')
            """,
            (dream_id,),
        )
    assert loop.feedback_summary(language="en") == {"ratings": [], "resonant_themes": []}


def test_stored_analysis_validates_display_columns_when_raw_report_is_stale(tmp_path):
    loop = DreamLoop(tmp_path)
    dream_id = loop.add_dream_with_analysis(
        "I found a bright doorway.",
        {"summary": "This English analysis connects the doorway with a present decision and uncertainty."},
        language="en",
    )
    with loop._connect() as db:
        db.execute(
            """
            UPDATE dream_analyses
            SET emotional_tone = ?, symbols_json = ?, themes_json = ?, summary = ?
            WHERE dream_id = ? AND language = 'en'
            """,
            (
                "犹豫而期待",
                json.dumps(["发光的门"], ensure_ascii=False),
                json.dumps(["现实选择"], ensure_ascii=False),
                "这份中文摘要已经替换了显示列，但旧的英文原始报告仍然留在数据库中。",
                dream_id,
            ),
        )

    exact = loop.get_dream(dream_id, language="en")
    listed = loop.list_dreams_with_analysis(language="en")[0]

    assert exact["analysis"] is None
    assert exact["invalid_analysis"]["detected_language"] == "zh"
    assert exact["analysis_language_mismatch"] is True
    assert listed["analysis"] is None
    assert loop.trends(language="en")["themes"] == []


def test_import_ics_and_weather_feed_heatmap_context(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()
    loop.add_dream("A calm walk after the storm.", mood="calm", dreamed_on=date(2026, 6, 10))

    ics = loop.data_dir / "imports" / "calendar.ics"
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
    reimported = loop.import_ics(ics)
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
    assert reimported == 1
    assert weather == 1
    assert heatmap[0]["date"] == "2026-06-10"
    assert heatmap[0]["count"] == 1
    assert heatmap[0]["moods"] == {"calm": 1}
    assert context["events"][0]["summary"] == "Therapy session"
    assert len(context["events"]) == 1
    assert context["weather"]["precipitation_sum"] == 4.2


def test_import_ics_rejects_path_outside_data_dir(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()
    outside_file = tmp_path / "outside.ics"
    outside_file.write_text(
        "\n".join(
            [
                "BEGIN:VCALENDAR",
                "BEGIN:VEVENT",
                "UID:x",
                "DTSTART;VALUE=DATE:20260610",
                "SUMMARY:Should not import",
                "END:VEVENT",
                "END:VCALENDAR",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="must be under"):
        loop.import_ics(outside_file)


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


def test_similar_dreams_supports_chinese_content(tmp_path):
    loop = DreamLoop(tmp_path)
    first = loop.add_dream("我在安静的车站等待最后一班列车。")
    second = loop.add_dream("我又回到同一个车站寻找那班列车。")
    loop.add_dream("我在海边看见一座白色灯塔。")

    similar = loop.similar_dreams(first, language="zh")

    assert similar[0]["id"] == second
    assert similar[0]["score"] > 0


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
    assert visual["accent_1"] == "#8ba87a"
    assert visual["accent_2"] == "#d4a574"
    assert visual["accent_3"] == "#c47a5a"


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
    assert visual["accent_1"] in {"#8ba87a", "#9a7b56", "#a67c6a", "#c47a5a"}
    assert visual["accent_2"] in {"#d4a574", "#e8c089", "#b89164", "#c49a6c"}
    assert visual["accent_3"] in {"#c47a5a", "#8ba87a", "#a67c6a", "#6f7f64"}
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


def test_list_dreams_with_analysis_matches_single_dream_loading(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()
    analyzed_id = loop.add_dream_with_analysis(
        "Water dream",
        {
            "emotional_tone": "calm",
            "symbols": ["water"],
            "themes": ["flow"],
            "summary": "A water dream.",
            "confidence": 0.8,
        },
        language="en",
    )
    pending_id = loop.add_dream("Pending dream")

    batch = {dream["id"]: dream for dream in loop.list_dreams_with_analysis(language="en")}

    assert batch[analyzed_id] == loop.get_dream(analyzed_id, language="en")
    assert batch[pending_id] == loop.get_dream(pending_id, language="en")
    assert batch[analyzed_id]["analysis"]["symbols"] == ["water"]
    assert batch[pending_id]["analysis"] is None


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


def test_seed_demo_supports_chinese_samples_with_full_reflections(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()

    created = loop.seed_demo(language="zh")

    assert len(created) == 5
    first = loop.get_dream(created[0], language="zh")
    assert first["analysis"]
    assert first["analysis"]["language"] == "zh"
    assert first["analysis"]["report"]["dream_details"]
    assert first["analysis"]["report"]["possible_interpretations"]
    assert all(first["reflections"].get(key) for key in REFLECTION_LABELS)
    assert loop.get_dream(created[0], language="en")["analysis"] is None


def test_symbol_graph_counts_symbol_cooccurrence(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()
    loop.add_dream_with_analysis(
        "A station filled with water.",
        {
            "emotional_tone": "uneasy",
            "symbols": ["station", "water"],
            "themes": ["transition"],
            "summary": "A transition dream.",
            "confidence": 0.8,
        },
    )
    loop.add_dream_with_analysis(
        "Water covered a bridge.",
        {
            "emotional_tone": "curious",
            "symbols": ["water", "bridge"],
            "themes": ["crossing"],
            "summary": "A crossing dream.",
            "confidence": 0.78,
        },
    )

    graph = loop.symbol_graph()

    assert graph["nodes"][0] == {"id": "water", "label": "water", "count": 2}
    assert {"id": "transition", "label": "transition", "count": 1} in graph["nodes"]
    assert {"source": "station", "target": "water", "weight": 1} in graph["edges"]
    assert {"source": "bridge", "target": "water", "weight": 1} in graph["edges"]
    assert {"source": "transition", "target": "water", "weight": 1} in graph["edges"]


class FakeImageGenerator:
    provider = "local_comfyui"
    model = "test-image-model"

    def generate(self, prompt: str) -> bytes:
        self.prompt = prompt
        return b"\x89PNG\r\n\x1a\nfake-dream-image"


class FailingImageGenerator:
    provider = "local_comfyui"
    model = "broken-model"

    def generate(self, prompt: str) -> bytes:
        raise RuntimeError("image backend failed")


def test_image_config_defaults_to_local_card_without_secret(tmp_path):
    status = image_status(tmp_path)

    assert status.provider == "local_card"
    assert status.ready is False
    assert "local visual cards" in (status.warning or "")


def test_local_comfyui_requires_workflow_before_ready(tmp_path):
    save_image_config(tmp_path, provider="local_comfyui", model="dream-model", base_url="http://127.0.0.1:8188")

    status = image_status(tmp_path)

    assert status.provider == "local_comfyui"
    assert status.mode == "local"
    assert status.ready is False
    assert "workflow" in (status.warning or "")


def test_save_image_config_preserves_ai_config_and_hides_secret(tmp_path):
    from dreamloop.analysis import load_ai_config, save_ai_config

    save_ai_config(tmp_path, provider="deepseek", model="deepseek-v4-flash")
    save_image_config(
        tmp_path,
        provider="cloud_openai_compatible",
        model="image-model",
        base_url="https://images.example/v1",
    )
    save_image_secret(tmp_path, "image-secret")

    ai = load_ai_config(tmp_path)
    status = image_status(tmp_path)

    assert ai["provider"] == "deepseek"
    assert status.provider == "cloud_openai_compatible"
    assert status.model == "image-model"
    assert status.base_url == "https://images.example/v1"
    assert status.ready is True
    assert "image-secret" not in repr(status)


def test_generate_dream_image_writes_file_and_database_record(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()
    save_image_config(tmp_path, provider="local_comfyui", model="dream-model", base_url="http://127.0.0.1:8188")
    dream_id = loop.add_dream_with_analysis(
        "I watched a silver train cross the night ocean.",
        {
            "emotional_tone": "awed",
            "symbols": ["silver train", "night ocean"],
            "themes": ["transition"],
            "summary": "A luminous transition over dark water.",
            "confidence": 0.8,
        },
        language="en",
    )
    generator = FakeImageGenerator()

    image = loop.generate_dream_image(dream_id, language="en", generator=generator)
    dream = loop.get_dream(dream_id, language="en")

    assert image["status"] == "complete"
    assert image["provider"] == "local_comfyui"
    assert image["image_path"].startswith("assets/images/")
    assert (tmp_path / ".dreamloop" / image["image_path"]).read_bytes().startswith(b"\x89PNG")
    assert "silver train" in image["prompt"]
    assert "night ocean" in generator.prompt
    assert dream["image"]["id"] == image["id"]


def test_delete_dream_removes_image_records(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()
    save_image_config(tmp_path, provider="local_comfyui", model="dream-model", base_url="http://127.0.0.1:8188")
    dream_id = loop.add_dream("A red tower grew from a lake.")
    image = loop.generate_dream_image(dream_id, generator=FakeImageGenerator())
    image_path = loop.data_dir / image["image_path"]

    assert loop.delete_dream(dream_id) is True
    with loop._connect() as db:
        rows = db.execute("SELECT * FROM dream_images WHERE dream_id = ?", (dream_id,)).fetchall()
    assert rows == []
    assert not image_path.exists()


def test_failed_image_retry_does_not_hide_existing_complete_image(tmp_path):
    loop = DreamLoop(tmp_path)
    loop.init()
    dream_id = loop.add_dream("A green bridge crossed the night sky.")
    first = loop.generate_dream_image(dream_id, generator=FakeImageGenerator())

    try:
        loop.generate_dream_image(dream_id, generator=FailingImageGenerator())
    except RuntimeError:
        pass

    dream = loop.get_dream(dream_id)
    with loop._connect() as db:
        errors = db.execute(
            "SELECT * FROM dream_images WHERE dream_id = ? AND status = 'error'",
            (dream_id,),
        ).fetchall()

    assert errors
    assert dream["image"]["id"] == first["id"]
    assert dream["image"]["status"] == "complete"
