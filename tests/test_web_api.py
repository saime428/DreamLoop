from __future__ import annotations

import html
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dreamloop.analysis import StaticAnalyzer, load_ai_config, normalize_analysis
from dreamloop.images import save_image_config, save_image_secret
from dreamloop.web import create_app


class LanguageAwareAnalyzer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def analyze(self, content: str, language: str = "en") -> dict[str, object]:
        self.calls.append((content, language))
        if language == "zh":
            return {
                "emotional_tone": "好奇",
                "symbols": ["门"],
                "themes": ["发现"],
                "summary": "一场关于发现隐藏之门的梦。",
                "confidence": 0.86,
            }
        return {
            "emotional_tone": "curious",
            "symbols": ["door"],
            "themes": ["discovery"],
            "summary": "A dream about finding a hidden door.",
            "confidence": 0.84,
        }


class FakeImageGenerator:
    provider = "local_comfyui"
    model = "test-image-model"

    def generate(self, prompt: str) -> bytes:
        self.prompt = prompt
        return b"\x89PNG\r\n\x1a\nfake-web-image"


def test_web_rejects_cross_origin_writes_and_untrusted_hosts(tmp_path):
    app = create_app(tmp_path)
    analyzer = LanguageAwareAnalyzer()
    app.state.analyzer = analyzer
    client = TestClient(app)
    app.state.loop.add_dream("Private pending dream.")

    settings = client.post(
        "/settings/ai?lang=en",
        headers={"Origin": "https://attacker.example"},
        data={
            "provider": "custom",
            "model": "attacker-model",
            "base_url": "https://attacker.example/v1",
            "api_key": "",
        },
        follow_redirects=False,
    )
    analyze = client.post(
        "/api/analyze/pending?lang=en",
        headers={"Origin": "https://attacker.example"},
    )
    bad_host = client.get("/", headers={"Host": "attacker.example"})

    assert settings.status_code == 403
    assert analyze.status_code == 403
    assert bad_host.status_code == 400
    assert load_ai_config(tmp_path)["provider"] == "ollama"
    assert analyzer.calls == []


class DetailedReflectionAnalyzer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, str]]] = []

    def analyze(
        self,
        content: str,
        language: str = "en",
        reflections: dict[str, str] | None = None,
    ) -> dict[str, object]:
        self.calls.append((content, language, dict(reflections or {})))
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


class StructuredTermAnalyzer:
    def analyze(self, content: str, language: str = "en") -> dict[str, object]:
        return {
            "analysis_version": 2,
            "emotional_tone": "stuck",
            "symbols": [
                {"name": "subway station", "meaning": "A confusing transition point."},
                {"name": "broken map", "meaning": "Planning tools failing."},
            ],
            "themes": [{"name": "lost direction", "meaning": "Unclear next step."}],
            "summary": "A dream about trying to find a route.",
            "confidence": 0.75,
            "dream_details": [{"name": "subway station", "meaning": "You cannot find the exit."}],
            "real_life_links": [{"name": "commute planning", "meaning": "You may be choosing between routes."}],
            "possible_interpretations": [
                {
                    "title": "Pressure around choosing a route",
                    "interpretation": "The station and broken map point to uncertainty rather than a fixed omen.",
                    "dream_evidence": "You are in a station and the navigation is unreliable.",
                    "real_life_connection": "This may mirror a recent decision that has too many options.",
                    "verification_question": "Where are you currently choosing between several imperfect routes?",
                },
                {
                    "title": "Need for support",
                    "interpretation": "Ignored requests for help may reflect wanting clearer support.",
                    "dream_evidence": "People nearby do not answer you.",
                    "real_life_connection": "You may feel unsupported in a current task.",
                    "verification_question": "Who could you ask for a concrete next step?",
                },
            ],
            "real_life_questions": ["What real decision feels overloaded with routes?"],
            "verification_prompts": ["Compare the dream to one decision from this week."],
        }


def test_api_creates_lists_and_reads_dreams(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)

    created = client.post(
        "/api/dreams",
        json={"content": "I found a door in the sea.", "tags": ["water"], "manual_mood": "curious"},
    )
    assert created.status_code == 201
    dream_id = created.json()["id"]

    listed = client.get("/api/dreams")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == dream_id

    detail = client.get(f"/api/dreams/{dream_id}")
    assert detail.status_code == 200
    assert detail.json()["content"] == "I found a door in the sea."
    assert detail.json()["reflections"] == {}


def test_api_creates_dream_with_reflections(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)

    created = client.post(
        "/api/dreams",
        json={
            "content": "I found a door in the sea.",
            "reflections": {
                "strongest_emotion": "curiosity",
                "real_life_context": "I am thinking about changing jobs.",
            },
        },
    )

    assert created.status_code == 201
    detail = client.get(f"/api/dreams/{created.json()['id']}")
    assert detail.json()["reflections"] == {
        "strongest_emotion": "curiosity",
        "real_life_context": "I am thinking about changing jobs.",
    }


def test_web_home_renders_without_ai_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "DreamLoop Dashboard" in response.text
    assert "Your dreams have patterns. DreamLoop finds them locally." in response.text
    assert "Local-first dream intelligence" in response.text
    assert response.text.count("<h2>Your dreams have patterns. DreamLoop finds them locally.</h2>") == 0
    assert "data never leaves this machine" in response.text
    assert "DreamLoop" in response.text
    assert 'href="/patterns?lang=en"' in response.text
    assert 'href="/gallery?lang=en"' in response.text
    assert 'href="/log?lang=en"' in response.text
    assert 'href="/settings?lang=en"' in response.text
    assert 'href="#log"' not in response.text
    assert 'href="#insights"' not in response.text
    assert "CLI-first capture" not in response.text
    assert "Analysis queue" not in response.text
    assert 'action="/drafts/analyze?lang=en"' not in response.text


def test_log_prioritizes_capture_and_ai_analysis(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.get("/log?lang=en")

    assert response.status_code == 200
    assert 'class="primary-workbench"' in response.text
    assert "Log Dream" in response.text
    assert "AI Analysis" in response.text
    assert 'placeholder="Record a dream before it fades..."' in response.text
    assert 'action="/drafts/analyze?lang=en"' in response.text
    assert 'name="strongest_emotion"' in response.text
    assert 'name="waking_feeling"' in response.text
    assert 'name="important_elements"' in response.text
    assert 'name="real_life_context"' in response.text
    assert 'name="personal_association"' in response.text
    assert 'name="tags"' not in response.text
    assert 'name="manual_mood"' not in response.text
    assert "AI Analysis</button>" in response.text
    assert "data-loading-form" in response.text
    assert "data-loading-text" in response.text
    assert "Dream calendar" not in response.text
    assert "Dreamscape log" not in response.text


def test_dashboard_shows_rule_based_insight_and_recent_dreams(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    client.post("/api/dreams", json={"content": "A river crossed the station.", "tags": ["river"]})

    response = client.get("/?lang=en")

    assert response.status_code == 200
    assert "AI Insight" in response.text
    assert "A river crossed the station." in response.text
    assert "Log a Dream" in response.text
    assert "/log?lang=en" in response.text


def test_draft_analyze_does_not_persist_until_save(tmp_path):
    app = create_app(tmp_path)
    app.state.analyzer = LanguageAwareAnalyzer()
    client = TestClient(app)

    response = client.post("/drafts/analyze?lang=zh", data={"content": "我打开了一扇发光的门。"})

    assert response.status_code == 200
    assert "一场关于发现隐藏之门的梦。" in response.text
    assert "保存到本地" in response.text
    assert app.state.loop.list_dreams() == []
    assert app.state.analyzer.calls == [("我打开了一扇发光的门。", "zh")]


def test_draft_analyze_uses_optional_reflections_and_renders_detailed_report(tmp_path):
    app = create_app(tmp_path)
    app.state.analyzer = DetailedReflectionAnalyzer()
    client = TestClient(app)

    response = client.post(
        "/drafts/analyze?lang=zh",
        data={
            "content": "我在海底看到一扇蓝色的门。",
            "strongest_emotion": "害怕又好奇",
            "waking_feeling": "醒来后很紧张",
            "important_elements": "蓝色的门、海底",
            "real_life_context": "最近在考虑是否换工作",
            "personal_association": "门让我想到新的选择",
        },
    )

    assert response.status_code == 200
    assert app.state.loop.list_dreams() == []
    assert app.state.analyzer.calls == [
        (
            "我在海底看到一扇蓝色的门。",
            "zh",
            {
                "strongest_emotion": "害怕又好奇",
                "waking_feeling": "醒来后很紧张",
                "important_elements": "蓝色的门、海底",
                "real_life_context": "最近在考虑是否换工作",
                "personal_association": "门让我想到新的选择",
            },
        )
    ]
    assert "解释 1：你在靠近一个新选择" in response.text
    assert "我可以从中看到的现实问题" in response.text
    assert "我真正害怕的是失败，还是改变本身？" in response.text


def test_draft_analyze_renders_string_report_fields_as_single_list_items(tmp_path):
    app = create_app(tmp_path)
    app.state.analyzer = StaticAnalyzer(
        {
            "analysis_version": 2,
            "emotional_tone": "anxious",
            "symbols": ["station"],
            "themes": ["transition"],
            "summary": "A report about moving through an unfamiliar place.",
            "confidence": 0.72,
            "dream_details": "The subway station became a stranger neighborhood.",
            "real_life_links": "You may be comparing housing routes.",
            "real_life_questions": "Which option feels unreliable right now?",
            "verification_prompts": "Notice whether this maps to a recent decision.",
        }
    )
    client = TestClient(app)

    response = client.post("/drafts/analyze?lang=en", data={"content": "The station changed shape."})

    assert response.status_code == 200
    assert "<li>The subway station became a stranger neighborhood.</li>" in response.text
    assert "<li>T</li>" not in response.text


def test_draft_save_creates_dream_with_language_analysis(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    analysis = {
        "emotional_tone": "好奇",
        "symbols": ["门"],
        "themes": ["发现"],
        "summary": "一场关于发现隐藏之门的梦。",
        "confidence": 0.86,
    }

    response = client.post(
        "/drafts/save?lang=zh",
        data={
            "content": "我打开了一扇发光的门。",
            "analysis_json": json.dumps(analysis, ensure_ascii=False),
            "analysis_language": "zh",
            "reflections_json": json.dumps({"waking_feeling": "紧张"}, ensure_ascii=False),
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/dreams/1?lang=zh"
    dream = client.get("/api/dreams/1?lang=zh").json()
    assert dream["content"] == "我打开了一扇发光的门。"
    assert dream["reflections"] == {"waking_feeling": "紧张"}
    assert dream["analysis"]["summary"] == "一场关于发现隐藏之门的梦。"
    assert "report" not in dream["analysis"]["report"]
    assert "raw_json" not in dream["analysis"]["report"]
    assert client.get("/api/dreams/1?lang=en").json()["analysis"] is None


def test_web_single_dream_analysis_route_preserves_language(tmp_path):
    app = create_app(tmp_path)
    app.state.analyzer = LanguageAwareAnalyzer()
    client = TestClient(app)
    dream_id = client.post("/api/dreams", json={"content": "The moon was above the harbor."}).json()["id"]

    response = client.post(f"/dreams/{dream_id}/analyze?lang=zh", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == f"/dreams/{dream_id}?lang=zh"
    dream = client.get(f"/api/dreams/{dream_id}?lang=zh").json()
    assert dream["analysis_status"] == "analyzed"
    assert dream["analysis"]["summary"] == "一场关于发现隐藏之门的梦。"
    assert client.get(f"/api/dreams/{dream_id}?lang=en").json()["analysis"] is None
    home = client.get("/?lang=en")
    assert "Missing analysis" in home.text
    assert "一场关于发现隐藏之门的梦。" not in home.text


def test_web_can_delete_saved_dream(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    dream_id = client.post("/api/dreams", json={"content": "A dream to remove."}).json()["id"]

    detail = client.get(f"/dreams/{dream_id}?lang=en")
    assert detail.status_code == 200
    assert f'action="/dreams/{dream_id}/delete?lang=en"' in detail.text

    deleted = client.post(f"/dreams/{dream_id}/delete?lang=en", follow_redirects=False)

    assert deleted.status_code == 303
    assert deleted.headers["location"] == "/log?lang=en"
    assert client.get(f"/api/dreams/{dream_id}").status_code == 404


def test_api_can_delete_saved_dream(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    dream_id = client.post("/api/dreams", json={"content": "A dream to remove."}).json()["id"]

    response = client.delete(f"/api/dreams/{dream_id}")

    assert response.status_code == 200
    assert response.json() == {"deleted": dream_id}
    assert client.delete(f"/api/dreams/{dream_id}").status_code == 404


def test_api_analyzes_single_dream_with_override(tmp_path):
    app = create_app(tmp_path)
    app.state.analyzer = StaticAnalyzer(
        {
            "emotional_tone": "curious",
            "symbols": ["door"],
            "themes": ["discovery"],
            "summary": "A dream about finding a hidden door.",
            "confidence": 0.84,
        }
    )
    client = TestClient(app)
    first_id = client.post("/api/dreams", json={"content": "I watched the rain."}).json()["id"]
    second_id = client.post("/api/dreams", json={"content": "I opened a hidden door."}).json()["id"]

    response = client.post(f"/api/dreams/{second_id}/analyze?lang=en")

    assert response.status_code == 200
    assert response.json() == {"analyzed": second_id, "ai_configured": True, "provider": "test", "language": "en"}
    assert client.get(f"/api/dreams/{first_id}").json()["analysis_status"] == "pending"
    assert client.get(f"/api/dreams/{second_id}").json()["analysis"]["symbols"] == ["door"]


def test_api_analyze_returns_requested_language(tmp_path):
    app = create_app(tmp_path)
    app.state.analyzer = LanguageAwareAnalyzer()
    client = TestClient(app)
    dream_id = client.post("/api/dreams", json={"content": "I opened a hidden door."}).json()["id"]

    response = client.post(f"/api/dreams/{dream_id}/analyze?lang=zh")

    assert response.status_code == 200
    assert response.json()["language"] == "zh"
    assert client.get(f"/api/dreams/{dream_id}?lang=zh").json()["analysis"]["summary"] == "一场关于发现隐藏之门的梦。"
    assert client.get(f"/api/dreams/{dream_id}?lang=en").json()["analysis"] is None


def test_api_analyze_returns_422_for_wrong_output_language_without_persisting(tmp_path):
    app = create_app(tmp_path)
    app.state.analyzer = StaticAnalyzer(
        {"summary": "这个结果完全使用中文，因此不能作为英文分析写入本地数据库。"}
    )
    client = TestClient(app)
    dream_id = client.post("/api/dreams", json={"content": "I found a bright doorway."}).json()["id"]

    response = client.post(f"/api/dreams/{dream_id}/analyze?lang=en")

    assert response.status_code == 422
    assert "language" in response.json()["detail"].lower()
    assert client.get(f"/api/dreams/{dream_id}?lang=en").json()["analysis"] is None


def test_home_supports_english_and_chinese_language_toggle(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)

    english = client.get("/?lang=en")
    chinese = client.get("/?lang=zh")

    assert "DreamLoop Dashboard" in english.text
    assert "AI Insight" in english.text
    assert "DreamLoop 总览" in chinese.text
    assert "AI 洞察" in chinese.text
    assert 'data-lang="zh"' in english.text
    assert 'data-lang="en"' in chinese.text


def test_language_toggles_use_route_aware_paths(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    dream_id = client.post("/api/dreams", json={"content": "I saw the moon."}).json()["id"]

    pages = {
        "/?lang=en": "/?lang=zh",
        "/log?lang=en": "/log?lang=zh",
        "/patterns?lang=en": "/patterns?lang=zh",
        "/gallery?lang=en": "/gallery?lang=zh",
        "/settings?lang=en": "/settings?lang=zh",
        f"/dreams/{dream_id}?lang=en": f"/dreams/{dream_id}?lang=zh",
    }

    for source, target in pages.items():
        response = client.get(source)
        assert response.status_code == 200
        if source.startswith("/log"):
            assert 'action="/drafts/language"' in response.text
            assert 'name="lang" value="zh" data-lang="zh"' in response.text
        else:
            assert f'href="{target}" data-lang="zh"' in response.text
        assert 'href="?lang=' not in response.text


def test_draft_language_switch_preserves_state_without_persisting_or_reanalyzing(tmp_path):
    app = create_app(tmp_path)
    app.state.analyzer = DetailedReflectionAnalyzer()
    client = TestClient(app)
    content = "我在海底看到一扇蓝色的门。\n然后海水慢慢退去。"

    analyzed = client.post(
        "/drafts/analyze?lang=zh",
        data={
            "content": content,
            "strongest_emotion": "害怕又好奇",
            "real_life_context": "最近在考虑是否换工作",
        },
    )
    analysis_match = re.search(
        r'<textarea name="analysis_json" hidden>(.*?)</textarea>', analyzed.text, re.DOTALL
    )
    reflections_match = re.search(
        r'<textarea name="reflections_json" hidden>(.*?)</textarea>', analyzed.text, re.DOTALL
    )
    assert analysis_match and reflections_match

    switched = client.post(
        "/drafts/language",
        data={
            "lang": "en",
            "content": content,
            "analysis_json": html.unescape(analysis_match.group(1)),
            "analysis_language": "zh",
            "reflections_json": html.unescape(reflections_match.group(1)),
        },
    )

    assert switched.status_code == 200
    assert '<html lang="en">' in switched.text
    assert "Log Dream" in switched.text
    assert content in switched.text
    assert "这个梦把海底的门和现实中的压力联系在一起。" in switched.text
    assert "Analysis language: Chinese" in switched.text
    assert "Save Chinese analysis" in switched.text
    assert 'action="/drafts/language"' in switched.text
    assert "data-draft-language-form" in switched.text
    assert 'window.location.pathname === "/drafts/language"' in switched.text
    assert "window.history.replaceState(" in switched.text
    assert '`/log?lang=${document.documentElement.lang}${window.location.hash}`' in switched.text
    assert 'href="?lang=' not in switched.text
    assert app.state.analyzer.calls == [
        (
            content,
            "zh",
            {
                "strongest_emotion": "害怕又好奇",
                "real_life_context": "最近在考虑是否换工作",
            },
        )
    ]
    assert app.state.loop.list_dreams() == []


def test_unanalyzed_draft_language_switch_preserves_current_input(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    content = "I found a door.\nThen the lights changed."

    response = client.post(
        "/drafts/language",
        data={
            "lang": "zh",
            "content": content,
            "analysis_json": "",
            "analysis_language": "en",
            "reflections_json": json.dumps({"strongest_emotion": "uncertain"}),
        },
    )

    assert response.status_code == 200
    assert '<html lang="zh">' in response.text
    assert content in response.text
    assert 'value="uncertain"' in response.text
    assert app.state.loop.list_dreams() == []


def test_blank_log_language_switch_redirects_to_get_route(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/drafts/language",
        data={
            "lang": "zh",
            "content": "",
            "analysis_json": "",
            "analysis_language": "en",
            "reflections_json": "{}",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/log?lang=zh"
    rendered = client.get(response.headers["location"])
    assert rendered.status_code == 200
    assert '<html lang="zh">' in rendered.text


@pytest.mark.parametrize("reflections_json", ["not-json", "[]"])
def test_draft_language_switch_rejects_corrupt_reflection_state(tmp_path, reflections_json):
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/drafts/language",
        data={
            "lang": "en",
            "content": "I found a door.",
            "analysis_json": "",
            "analysis_language": "en",
            "reflections_json": reflections_json,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid reflections JSON"


def test_draft_post_languages_and_analysis_payload_are_strict(tmp_path):
    app = create_app(tmp_path)
    app.state.analyzer = LanguageAwareAnalyzer()
    client = TestClient(app)
    analysis_json = json.dumps(
        {
            "emotional_tone": "curious",
            "symbols": ["door"],
            "themes": ["discovery"],
            "summary": "A dream about finding a hidden door.",
            "confidence": 0.84,
        }
    )

    invalid_analysis_target = client.post(
        "/drafts/analyze?lang=fr", data={"content": "I found a door."}
    )
    invalid_switch_target = client.post(
        "/drafts/language",
        data={
            "lang": "fr",
            "content": "I found a door.",
            "analysis_json": analysis_json,
            "analysis_language": "en",
        },
    )
    invalid_saved_label = client.post(
        "/drafts/save?lang=en",
        data={
            "content": "I found a door.",
            "analysis_json": analysis_json,
            "analysis_language": "fr",
        },
    )
    non_object_analysis = client.post(
        "/drafts/language",
        data={
            "lang": "en",
            "content": "I found a door.",
            "analysis_json": "[]",
            "analysis_language": "en",
        },
    )

    assert invalid_analysis_target.status_code == 400
    assert invalid_switch_target.status_code == 400
    assert invalid_saved_label.status_code == 400
    assert non_object_analysis.status_code == 400
    assert app.state.analyzer.calls == []
    assert app.state.loop.list_dreams() == []


def test_draft_language_switch_rejects_relabeling_and_preserves_user_input(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    content = "I found a bright doorway.\nThe room became quiet."
    reflections = {"real_life_context": "I am deciding whether to change jobs."}

    response = client.post(
        "/drafts/language",
        data={
            "lang": "zh",
            "content": content,
            "analysis_json": json.dumps(
                {"summary": "这份结果明显使用中文，却被隐藏字段错误标记成了英文分析。"},
                ensure_ascii=False,
            ),
            "analysis_language": "en",
            "reflections_json": json.dumps(reflections),
        },
    )

    assert response.status_code == 422
    assert '<html lang="zh">' in response.text
    assert "分析内容与标记的英文不一致" in response.text
    assert content in response.text
    assert reflections["real_life_context"] in response.text
    assert app.state.loop.list_dreams() == []


def test_draft_save_revalidates_hidden_analysis_without_persisting(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/drafts/save?lang=en",
        data={
            "content": "I found a bright doorway.",
            "analysis_json": json.dumps(
                {"summary": "这份结果明显使用中文，却被隐藏字段错误标记成了英文分析。"},
                ensure_ascii=False,
            ),
            "analysis_language": "en",
            "reflections_json": json.dumps({"strongest_emotion": "uncertain"}),
        },
    )

    assert response.status_code == 422
    assert "Analysis content does not match its English label" in response.text
    assert "I found a bright doorway." in response.text
    assert "uncertain" in response.text
    assert app.state.loop.list_dreams() == []


def test_patterns_log_gallery_and_settings_are_real_pages(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    client.post("/api/dreams", json={"content": "Water covered the old city.", "tags": ["water"]})

    patterns = client.get("/patterns?lang=en")
    log = client.get("/log?lang=en")
    gallery = client.get("/gallery?lang=en")
    settings = client.get("/settings?lang=en")

    assert patterns.status_code == 200
    assert "Dream calendar" in patterns.text
    assert 'href="/log?lang=en&date=' in patterns.text
    assert "Mood spectrum" in patterns.text
    assert "Pattern summary" in patterns.text
    assert "Log Dream" not in patterns.text
    assert log.status_code == 200
    assert "Log Dream" in log.text
    assert "Dreamscape log" in log.text
    assert "Water covered the old city." in log.text
    assert "CLI-first capture" not in log.text
    assert gallery.status_code == 200
    assert "Dream Gallery" in gallery.text
    assert "Generate a visual memory" in gallery.text
    assert settings.status_code == 200
    assert "AI Provider" in settings.text
    assert "API Key" in settings.text
    assert "Custom OpenAI-compatible" in settings.text


def test_insights_redirects_to_patterns(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.get("/insights?lang=zh", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/patterns?lang=zh"


def test_log_page_can_filter_by_heatmap_date(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    client.post("/api/dreams", json={"content": "Water covered the old city.", "dreamed_on": "2026-06-10"})
    client.post("/api/dreams", json={"content": "I flew over rooftops.", "dreamed_on": "2026-06-11"})

    response = client.get("/log?lang=en&date=2026-06-10")

    assert response.status_code == 200
    assert "2026-06-10" in response.text
    assert "Water covered the old city." in response.text
    assert "I flew over rooftops." not in response.text


def test_patterns_symbol_links_filter_log(tmp_path):
    app = create_app(tmp_path)
    app.state.analyzer = StaticAnalyzer(
        {
            "emotional_tone": "uneasy",
            "symbols": ["water"],
            "themes": ["transition"],
            "summary": "A water dream about transition.",
            "confidence": 0.8,
        }
    )
    client = TestClient(app)
    water = client.post("/api/dreams", json={"content": "Water covered the old city."}).json()["id"]
    client.post("/api/dreams", json={"content": "I flew over rooftops."})
    client.post(f"/api/dreams/{water}/analyze?lang=en")

    patterns = client.get("/patterns?lang=en")
    filtered = client.get("/log?lang=en&symbol=water")

    assert 'href="/log?lang=en&symbol=water"' in patterns.text
    assert "Water covered the old city." in filtered.text
    assert "I flew over rooftops." not in filtered.text


def test_symbol_graph_api_and_patterns_empty_state(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)

    graph = client.get("/api/insights/symbol-graph?lang=en")
    patterns = client.get("/patterns?lang=en")

    assert graph.status_code == 200
    assert graph.json() == {"nodes": [], "edges": []}
    assert "Analyze some dreams first." in patterns.text
    assert "symbol-network" not in patterns.text


def test_symbol_graph_api_and_patterns_svg(tmp_path):
    app = create_app(tmp_path)
    app.state.analyzer = StaticAnalyzer(
        {
            "emotional_tone": "uneasy",
            "symbols": ["water", "station", "bridge"],
            "themes": ["transition"],
            "summary": "A dream about crossing water.",
            "confidence": 0.82,
        }
    )
    client = TestClient(app)
    dream_id = client.post("/api/dreams", json={"content": "Water covered a bridge by the station."}).json()["id"]
    client.post(f"/api/dreams/{dream_id}/analyze?lang=en")

    graph = client.get("/api/insights/symbol-graph?lang=en")
    patterns = client.get("/patterns?lang=en")

    assert graph.status_code == 200
    assert {"id": "water", "label": "water", "count": 1} in graph.json()["nodes"]
    assert {"source": "station", "target": "water", "weight": 1} in graph.json()["edges"]
    assert "symbol-network" in patterns.text
    assert "water" in patterns.text


def test_settings_updates_ai_provider_without_leaking_secret(tmp_path, monkeypatch):
    from dreamloop.analysis import ai_status

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/settings/ai?lang=zh",
        data={
            "provider": "deepseek",
            "model": "deepseek-v4-flash",
            "base_url": "https://api.deepseek.com",
            "api_key": "secret-from-form",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/settings?lang=zh&saved=1"
    status = ai_status(tmp_path)
    assert status.provider == "deepseek"
    assert status.model == "deepseek-v4-flash"
    settings = client.get("/settings?lang=zh")
    assert "secret-from-form" not in settings.text
    assert "deepseek-v4-flash" in settings.text


def test_settings_accepts_custom_openai_compatible_provider(tmp_path):
    from dreamloop.analysis import ai_status

    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/settings/ai?lang=en",
        data={
            "provider": "custom",
            "model": "local-model",
            "base_url": "http://localhost:1234/v1",
            "api_key": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    status = ai_status(tmp_path)
    assert status.provider == "custom"
    assert status.ready is True
    settings = client.get("/settings?lang=en")
    assert "Custom OpenAI-compatible" in settings.text
    assert "http://localhost:1234/v1" in settings.text


def test_create_dream_form_preserves_language(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/dreams?lang=zh",
        data={"content": "我梦见一条河。"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/dreams/1?lang=zh"


def test_detail_page_supports_chinese_language(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    dream_id = client.post("/api/dreams", json={"content": "I saw the moon."}).json()["id"]

    response = client.get(f"/dreams/{dream_id}?lang=zh")

    assert response.status_code == 200
    assert "返回总览" in response.text
    assert "AI 分析" in response.text
    assert "生成中文分析" in response.text


def test_detail_page_renders_detailed_analysis_sections(tmp_path):
    app = create_app(tmp_path)
    app.state.analyzer = DetailedReflectionAnalyzer()
    client = TestClient(app)
    dream_id = client.post(
        "/api/dreams",
        json={
            "content": "我在海底看到一扇蓝色的门。",
            "reflections": {"real_life_context": "最近在考虑是否换工作"},
        },
    ).json()["id"]
    client.post(f"/api/dreams/{dream_id}/analyze?lang=zh")

    response = client.get(f"/dreams/{dream_id}?lang=zh")

    assert response.status_code == 200
    assert "梦里的具体细节" in response.text
    assert "可能解释" in response.text
    assert "我可以从中看到的现实问题" in response.text
    assert "我真正害怕的是失败，还是改变本身？" in response.text


def test_detail_generates_local_visual_memory_and_gallery_shows_it(tmp_path):
    app = create_app(tmp_path)
    app.state.analyzer = LanguageAwareAnalyzer()
    client = TestClient(app)
    dream_id = client.post("/api/dreams", json={"content": "I found a blue door under the sea."}).json()["id"]
    client.post(f"/api/dreams/{dream_id}/analyze?lang=en")

    detail = client.get(f"/dreams/{dream_id}?lang=en")
    assert f'action="/dreams/{dream_id}/visual?lang=en"' in detail.text
    assert "Local visual memory" not in detail.text

    generated = client.post(
        f"/dreams/{dream_id}/visual?lang=en",
        data={"analysis_language": "en"},
        follow_redirects=False,
    )
    assert generated.status_code == 303
    assert generated.headers["location"] == f"/dreams/{dream_id}?lang=en"

    updated = client.get(f"/dreams/{dream_id}?lang=en")
    assert "Local visual memory" in updated.text
    assert "No image API was called" in updated.text
    assert "Generate dream image" in updated.text
    assert "Real image provider is not configured" in updated.text

    gallery = client.get("/gallery?lang=en")
    assert "Dream Gallery" in gallery.text
    assert "Local visual memory" in gallery.text
    assert "A dream about finding a hidden door" in gallery.text


def test_detail_and_gallery_render_compact_legacy_visual_title(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    dream_id = app.state.loop.add_dream("I crossed a quiet station.")
    with app.state.loop._connect() as db:
        db.execute(
            "UPDATE dreams SET visual_json = ? WHERE id = ?",
            (
                json.dumps(
                    {
                        "title": "First visual sentence. Second visual sentence must not render.",
                        "symbols": ["station"],
                        "themes": ["transition"],
                    }
                ),
                dream_id,
            ),
        )

    detail = client.get(f"/dreams/{dream_id}?lang=en")
    gallery = client.get("/gallery?lang=en")

    for response in (detail, gallery):
        assert response.status_code == 200
        assert "First visual sentence" in response.text
        assert "Second visual sentence" not in response.text


def test_detail_feedback_buttons_and_api_summary(tmp_path):
    app = create_app(tmp_path)
    app.state.analyzer = StructuredTermAnalyzer()
    client = TestClient(app)
    dream_id = client.post(
        "/api/dreams", json={"content": "I could not find the exit in a subway station."}
    ).json()["id"]
    client.post(f"/api/dreams/{dream_id}/analyze?lang=en")

    detail = client.get(f"/dreams/{dream_id}?lang=en")
    assert detail.status_code == 200
    assert f'action="/dreams/{dream_id}/feedback?lang=en"' in detail.text
    assert "Resonates" in detail.text
    assert "Not accurate" in detail.text
    assert "Unsure" in detail.text

    posted = client.post(
        f"/api/dreams/{dream_id}/feedback?lang=en",
        json={"interpretation_index": 0, "rating": "resonates", "reason": "This fits."},
    )
    assert posted.status_code == 201
    assert posted.json()["rating"] == "resonates"

    bad = client.post(
        f"/api/dreams/{dream_id}/feedback?lang=en",
        json={"interpretation_index": 0, "rating": "too_mystical"},
    )
    assert bad.status_code == 422

    summary = client.get("/api/feedback/summary?lang=en")
    assert summary.status_code == 200
    assert summary.json()["ratings"][0] == {"name": "resonates", "count": 1}
    assert {"name": "lost direction", "count": 1} in summary.json()["resonant_themes"]

    patterns = client.get("/patterns?lang=en")
    assert "Resonant themes" in patterns.text
    assert "lost direction" in patterns.text


def test_english_detail_uses_valid_chinese_analysis_as_labeled_fallback(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    dream_id = app.state.loop.add_dream_with_analysis(
        "我在海底看到一扇发光的门。",
        {"summary": "这份中文分析把发光的门与现实中的选择和犹豫联系起来。"},
        language="zh",
    )

    response = client.get(f"/dreams/{dream_id}?lang=en")

    assert response.status_code == 200
    assert "Back to dashboard" in response.text
    assert "Showing Chinese analysis" in response.text
    assert "这份中文分析把发光的门与现实中的选择和犹豫联系起来。" in response.text
    assert f'action="/dreams/{dream_id}/analyze?lang=en"' in response.text
    assert f'action="/dreams/{dream_id}/feedback?lang=en"' not in response.text
    assert 'name="analysis_language" value="zh"' in response.text


def test_detail_fallback_actions_use_analysis_language_and_keep_interface_language(tmp_path):
    app = create_app(tmp_path)
    app.state.image_generator = FakeImageGenerator()
    client = TestClient(app)
    dream_id = app.state.loop.add_dream_with_analysis(
        "我在海底看到一扇发光的门。",
        {
            "summary": "这份中文分析把发光的门与现实中的选择和犹豫联系起来。",
            "themes": ["现实选择"],
            "possible_interpretations": [
                {
                    "title": "靠近选择",
                    "interpretation": "这扇门可能对应一个正在靠近的现实选择。",
                    "dream_evidence": "门在海底发光。",
                    "real_life_connection": "你可能正面对需要权衡的决定。",
                    "verification_question": "最近哪个选择既吸引你又让你犹豫？",
                }
            ],
        },
        language="zh",
    )

    feedback = client.post(
        f"/dreams/{dream_id}/feedback?lang=en",
        data={"analysis_language": "zh", "interpretation_index": 0, "rating": "resonates"},
        follow_redirects=False,
    )
    visual = client.post(
        f"/dreams/{dream_id}/visual?lang=en",
        data={"analysis_language": "zh"},
        follow_redirects=False,
    )
    image = client.post(
        f"/dreams/{dream_id}/image?lang=en",
        data={"analysis_language": "zh"},
        follow_redirects=False,
    )

    assert feedback.status_code == visual.status_code == image.status_code == 303
    assert feedback.headers["location"] == f"/dreams/{dream_id}?lang=en"
    assert app.state.loop.feedback_for_dream(dream_id, language="zh")
    assert app.state.loop.feedback_for_dream(dream_id, language="en") == []
    with app.state.loop._connect() as db:
        image_row = db.execute(
            "SELECT language FROM dream_images WHERE dream_id = ? ORDER BY id DESC LIMIT 1",
            (dream_id,),
        ).fetchone()
    assert image_row["language"] == "zh"


@pytest.mark.parametrize("action", ["visual", "image", "feedback"])
def test_detail_analysis_language_tampering_returns_conflict_without_side_effect(tmp_path, action):
    app = create_app(tmp_path)
    app.state.image_generator = FakeImageGenerator()
    client = TestClient(app)
    dream_id = app.state.loop.add_dream_with_analysis(
        "我在海底看到一扇发光的门。",
        {"summary": "这份中文分析把发光的门与现实中的选择和犹豫联系起来。"},
        language="zh",
    )
    data = {"analysis_language": "en"}
    if action == "feedback":
        data["rating"] = "resonates"

    response = client.post(f"/dreams/{dream_id}/{action}?lang=en", data=data)

    assert response.status_code == 409
    assert app.state.loop.feedback_for_dream(dream_id, language="en") == []
    assert app.state.loop.get_dream(dream_id, language="zh")["visual_memory"] is None
    with app.state.loop._connect() as db:
        assert db.execute("SELECT COUNT(*) FROM dream_images WHERE dream_id = ?", (dream_id,)).fetchone()[0] == 0


def test_api_feedback_requires_valid_exact_language_analysis(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    dream_id = app.state.loop.add_dream_with_analysis(
        "我在海底看到一扇发光的门。",
        {"summary": "这份中文分析把发光的门与现实中的选择和犹豫联系起来。"},
        language="zh",
    )

    response = client.post(
        f"/api/dreams/{dream_id}/feedback?lang=en",
        json={"interpretation_index": 0, "rating": "resonates"},
    )

    assert response.status_code == 409
    assert app.state.loop.feedback_for_dream(dream_id, language="en") == []


def test_mislabeled_detail_exposes_regeneration_without_analysis_actions(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    dream_id = app.state.loop.add_dream("I found a bright doorway.")
    bad_english = normalize_analysis(
        {"summary": "这条记录虽然标记为英文，但实际内容明显全部使用中文。"}
    )
    with app.state.loop._connect() as db:
        db.execute(
            """
            INSERT INTO dream_analyses (
                dream_id, language, emotional_tone, symbols_json, themes_json, summary, confidence, raw_json
            ) VALUES (?, 'en', ?, ?, ?, ?, ?, ?)
            """,
            (
                dream_id,
                bad_english["emotional_tone"],
                json.dumps(bad_english["symbols"]),
                json.dumps(bad_english["themes"]),
                bad_english["summary"],
                bad_english["confidence"],
                bad_english["raw_json"],
            ),
        )

    detail = client.get(f"/dreams/{dream_id}?lang=en")
    api_read = client.get(f"/api/dreams/{dream_id}?lang=en")
    visual = client.post(f"/api/dreams/{dream_id}/visual?lang=en")

    assert detail.status_code == 200
    assert "stored language label does not match" in detail.text
    assert f'action="/dreams/{dream_id}/analyze?lang=en"' in detail.text
    assert f'action="/dreams/{dream_id}/visual?lang=en"' not in detail.text
    assert f'action="/dreams/{dream_id}/image?lang=en"' not in detail.text
    assert f'action="/dreams/{dream_id}/feedback?lang=en"' not in detail.text
    assert api_read.json()["analysis"] is None
    assert visual.status_code == 200
    assert visual.json()["title"] == "I found a bright doorway"


def test_structured_symbol_objects_do_not_leak_to_web_pages(tmp_path):
    app = create_app(tmp_path)
    app.state.analyzer = StructuredTermAnalyzer()
    client = TestClient(app)
    dream_id = client.post(
        "/api/dreams", json={"content": "I could not find the exit in a subway station."}
    ).json()["id"]

    client.post(f"/api/dreams/{dream_id}/analyze?lang=en")
    client.post(
        f"/dreams/{dream_id}/visual?lang=en",
        data={"analysis_language": "en"},
        follow_redirects=False,
    )

    for path in ("/?lang=en", "/patterns?lang=en", "/gallery?lang=en", f"/dreams/{dream_id}?lang=en"):
        response = client.get(path)
        assert response.status_code == 200
        rendered = html.unescape(response.text)
        assert '{"name"' not in rendered
        assert '"meaning"' not in rendered
        assert "subway station" in rendered


def test_api_generates_local_visual_memory(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    dream_id = client.post("/api/dreams", json={"content": "I crossed a red bridge."}).json()["id"]

    response = client.post(f"/api/dreams/{dream_id}/visual?lang=en")

    assert response.status_code == 200
    assert response.json()["kind"] == "local_card"
    assert client.get(f"/api/dreams/{dream_id}").json()["visual_memory"]["kind"] == "local_card"


def test_detail_separates_local_card_from_real_image_generation(tmp_path):
    app = create_app(tmp_path)
    app.state.analyzer = LanguageAwareAnalyzer()
    client = TestClient(app)
    dream_id = client.post("/api/dreams", json={"content": "I found a silver train under the moon."}).json()["id"]
    client.post(f"/api/dreams/{dream_id}/analyze?lang=en")

    detail = client.get(f"/dreams/{dream_id}?lang=en")

    assert detail.status_code == 200
    assert f'action="/dreams/{dream_id}/visual?lang=en"' in detail.text
    assert f'action="/dreams/{dream_id}/image?lang=en"' in detail.text
    assert "Generate local card" in detail.text
    assert "Real image provider is not configured" in detail.text
    assert "disabled" in detail.text


def test_api_generates_real_dream_image_with_configured_provider(tmp_path):
    app = create_app(tmp_path)
    app.state.analyzer = LanguageAwareAnalyzer()
    app.state.image_generator = FakeImageGenerator()
    save_image_config(tmp_path, provider="local_comfyui", model="dream-model", base_url="http://127.0.0.1:8188")
    client = TestClient(app)
    dream_id = client.post("/api/dreams", json={"content": "I found a silver train under the moon."}).json()["id"]
    client.post(f"/api/dreams/{dream_id}/analyze?lang=en")

    generated = client.post(f"/api/dreams/{dream_id}/image?lang=en")
    dream = client.get(f"/api/dreams/{dream_id}?lang=en").json()
    gallery = client.get("/gallery?lang=en")

    assert generated.status_code == 200
    assert generated.json()["status"] == "complete"
    assert generated.json()["provider"] == "local_comfyui"
    assert generated.json()["image_url"].startswith("/dreamloop-assets/images/")
    assert dream["image"]["id"] == generated.json()["id"]
    assert "dream-image" in gallery.text
    assert "silver train" in gallery.text


def test_settings_show_image_provider_without_leaking_secret(tmp_path):
    save_image_config(
        tmp_path,
        provider="cloud_openai_compatible",
        model="image-model",
        base_url="https://images.example/v1",
    )
    save_image_secret(tmp_path, "image-secret-token")
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.get("/settings?lang=en")
    status_response = client.get("/api/images/status")

    assert response.status_code == 200
    assert "Image Provider" in response.text
    assert "Custom cloud image endpoint" in response.text
    assert "image-model" in response.text
    assert "image-secret-token" not in response.text
    assert status_response.json()["provider"] == "cloud_openai_compatible"
    assert "image-secret-token" not in response.text + str(status_response.json())


def test_website_uses_subtle_page_background_assets(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)

    dashboard = client.get("/?lang=en")
    log = client.get("/log?lang=en")
    patterns = client.get("/patterns?lang=en")
    gallery = client.get("/gallery?lang=en")
    settings = client.get("/settings?lang=en")
    dream_id = client.post("/api/dreams", json={"content": "I found a folded map by the bed."}).json()["id"]
    detail = client.get(f"/dreams/{dream_id}?lang=en")

    backgrounds = {
        "dashboard": "bg-dashboard.png",
        "log": "bg-log.png",
        "patterns": "bg-patterns.png",
        "gallery": "bg-gallery.png",
        "settings": "bg-settings.png",
        "detail": "bg-detail.png",
    }

    assert dashboard.status_code == 200
    assert log.status_code == 200
    assert patterns.status_code == 200
    assert gallery.status_code == 200
    assert settings.status_code == 200
    assert detail.status_code == 200
    for page, filename in backgrounds.items():
        asset = Path("src/dreamloop/static/images/backgrounds") / filename
        assert asset.exists(), filename
        assert asset.stat().st_size > 500_000
    assert '<main class="dashboard page-dashboard">' in dashboard.text
    assert '<main class="dashboard page-log">' in log.text
    assert '<main class="dashboard page-patterns">' in patterns.text
    assert '<main class="dashboard page-gallery">' in gallery.text
    assert '<main class="dashboard page-settings">' in settings.text
    assert '<main class="dashboard detail-dashboard page-detail">' in detail.text
    assert "product-visual-card" not in dashboard.text
    assert "readme-workflow-review.png" not in dashboard.text
    assert "readme-local-first-privacy.png" not in settings.text


def test_settings_image_status_is_localized_in_chinese(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.get("/settings?lang=zh")

    assert response.status_code == 200
    assert "真实图像生成未开启，本地视觉卡片仍可使用。" in response.text
    assert "Real image generation is disabled" not in response.text


def test_dashboard_copy_and_language_toggle_do_not_use_mojibake(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)

    en = client.get("/?lang=en")
    zh = client.get("/?lang=zh")

    assert "Local-first dream intelligence" in en.text
    assert "<h2>Your dreams have patterns. DreamLoop finds them locally.</h2>" not in en.text
    mojibake_zh = "\u6d93\ue145\u67c3"
    assert mojibake_zh not in en.text + zh.text
    assert "中文" in en.text + zh.text


def test_gallery_empty_state_explains_detail_driven_visual_memory(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.get("/gallery?lang=zh")

    assert response.status_code == 200
    assert "梦境画廊" in response.text
    assert "先在梦境详情页生成一张视觉记忆" in response.text


def test_web_home_shows_provider_without_leaking_secret(tmp_path, monkeypatch):
    from dreamloop.analysis import save_ai_config, save_secret

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    save_ai_config(tmp_path, provider="deepseek")
    save_secret(tmp_path, "DEEPSEEK_API_KEY", "very-secret-token")
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.get("/settings?lang=en")

    assert response.status_code == 200
    assert "deepseek" in response.text
    assert "deepseek-v4-flash" in response.text
    assert "very-secret-token" not in response.text


def test_heatmap_endpoint_returns_stable_json(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    client.post("/api/dreams", json={"content": "I flew over bright rooftops.", "manual_mood": "excited"})

    response = client.get("/api/insights/heatmap")

    assert response.status_code == 200
    assert response.json()[0]["count"] == 1


def test_pattern_tracking_api_returns_similar_and_trends(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    first = client.post("/api/dreams", json={"content": "Water covered the old city.", "tags": ["water"]}).json()["id"]
    second = client.post("/api/dreams", json={"content": "I crossed water at sunrise.", "tags": ["water"]}).json()["id"]

    similar = client.get(f"/api/dreams/{first}/similar")
    trends = client.get("/api/insights/trends")

    assert similar.status_code == 200
    assert similar.json()[0]["id"] == second
    assert trends.status_code == 200
    assert trends.json()["tags"][0] == {"name": "water", "count": 2}
