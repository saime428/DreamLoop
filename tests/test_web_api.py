from __future__ import annotations

import json

from fastapi.testclient import TestClient

from dreamloop.analysis import StaticAnalyzer
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


def test_web_home_renders_without_ai_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "DreamLoop Dashboard" in response.text
    assert "Your dreams have patterns. DreamLoop finds them locally." in response.text
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
    assert 'name="tags"' not in response.text
    assert 'name="manual_mood"' not in response.text
    assert "AI Analysis</button>" in response.text
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
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/dreams/1?lang=zh"
    dream = client.get("/api/dreams/1?lang=zh").json()
    assert dream["content"] == "我打开了一扇发光的门。"
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
    assert "Water covered the old city." in gallery.text
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
    assert "返回工作台" in response.text
    assert "AI 分析" in response.text
    assert "生成梦境画面" in response.text


def test_gallery_empty_state_explains_detail_driven_visual_memory(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.get("/gallery?lang=zh")

    assert response.status_code == 200
    assert "梦境画廊" in response.text
    assert "先在梦境详情页生成或保存视觉记忆" in response.text


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
