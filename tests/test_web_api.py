from __future__ import annotations

import html
import json

from fastapi.testclient import TestClient

from dreamloop.analysis import StaticAnalyzer
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
    assert "生成梦境画面" in response.text


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

    generated = client.post(f"/dreams/{dream_id}/visual?lang=en", follow_redirects=False)
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
    assert "A dream about finding a hidden door." in gallery.text


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
    assert bad.status_code == 400

    summary = client.get("/api/feedback/summary?lang=en")
    assert summary.status_code == 200
    assert summary.json()["ratings"][0] == {"name": "resonates", "count": 1}
    assert {"name": "lost direction", "count": 1} in summary.json()["resonant_themes"]

    patterns = client.get("/patterns?lang=en")
    assert "Resonant themes" in patterns.text
    assert "lost direction" in patterns.text


def test_structured_symbol_objects_do_not_leak_to_web_pages(tmp_path):
    app = create_app(tmp_path)
    app.state.analyzer = StructuredTermAnalyzer()
    client = TestClient(app)
    dream_id = client.post(
        "/api/dreams", json={"content": "I could not find the exit in a subway station."}
    ).json()["id"]

    client.post(f"/api/dreams/{dream_id}/analyze?lang=en")
    client.post(f"/dreams/{dream_id}/visual?lang=en", follow_redirects=False)

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
