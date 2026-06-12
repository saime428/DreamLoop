from __future__ import annotations

from fastapi.testclient import TestClient

from dreamloop.analysis import StaticAnalyzer
from dreamloop.web import create_app


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
    assert "Good night, explorer" in response.text
    assert "Your dreams have patterns. DreamLoop finds them locally." in response.text
    assert "Ollama optional" in response.text
    assert "CLI-first" in response.text
    assert "Obsidian" in response.text
    assert "data never leaves this machine" in response.text
    assert "Dream constellation" in response.text
    assert "Mood spectrum" in response.text
    assert "AI Insight" in response.text
    assert "Dreamscape log" in response.text
    assert "Starlit local runtime" in response.text
    assert "DreamLoop" in response.text


def test_web_home_prioritizes_capture_and_ai_analysis(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.get("/?lang=en")

    assert response.status_code == 200
    assert 'class="primary-workbench"' in response.text
    assert "Log Dream" in response.text
    assert "AI Analysis" in response.text
    assert 'placeholder="Record a dream before it fades..."' in response.text
    assert response.text.index("Log Dream") < response.text.index("Dream constellation")
    assert response.text.index("AI Analysis") < response.text.index("Dreamscape log")


def test_web_home_shows_analyze_now_for_latest_pending_dream(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    client.post("/api/dreams", json={"content": "A river crossed the station.", "tags": ["river"]})

    response = client.get("/?lang=en")

    assert response.status_code == 200
    assert "Pending analysis" in response.text
    assert "Analyze now" in response.text
    assert "/dreams/1/analyze?lang=en" in response.text


def test_web_single_dream_analysis_route_preserves_language(tmp_path):
    app = create_app(tmp_path)
    app.state.analyzer = StaticAnalyzer(
        {
            "emotional_tone": "calm",
            "symbols": ["moon"],
            "themes": ["arrival"],
            "summary": "A quiet dream about arriving under moonlight.",
            "confidence": 0.9,
        }
    )
    client = TestClient(app)
    dream_id = client.post("/api/dreams", json={"content": "The moon was above the harbor."}).json()["id"]

    response = client.post(f"/dreams/{dream_id}/analyze?lang=zh", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/?lang=zh"
    dream = client.get(f"/api/dreams/{dream_id}").json()
    assert dream["analysis_status"] == "analyzed"
    assert dream["analysis"]["summary"] == "A quiet dream about arriving under moonlight."
    home = client.get("/?lang=en")
    assert "Structured analysis" in home.text
    assert "A quiet dream about arriving under moonlight." in home.text


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

    response = client.post(f"/api/dreams/{second_id}/analyze")

    assert response.status_code == 200
    assert response.json() == {"analyzed": second_id, "ai_configured": True, "provider": "test"}
    assert client.get(f"/api/dreams/{first_id}").json()["analysis_status"] == "pending"
    assert client.get(f"/api/dreams/{second_id}").json()["analysis"]["symbols"] == ["door"]


def test_home_supports_english_and_chinese_language_toggle(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)

    english = client.get("/?lang=en")
    chinese = client.get("/?lang=zh")

    assert "Log Dream" in english.text
    assert "AI Analysis" in english.text
    assert "记录梦境" in chinese.text
    assert "AI 分析" in chinese.text
    assert 'data-lang="zh"' in english.text
    assert 'data-lang="en"' in chinese.text


def test_create_dream_form_preserves_language(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/dreams?lang=zh",
        data={"content": "我梦见一条河。", "tags": "河", "manual_mood": "平静"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/?lang=zh"


def test_detail_page_supports_chinese_language(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    dream_id = client.post("/api/dreams", json={"content": "I saw the moon."}).json()["id"]

    response = client.get(f"/dreams/{dream_id}?lang=zh")

    assert response.status_code == 200
    assert "返回工作台" in response.text
    assert "AI 分析" in response.text


def test_web_home_shows_provider_without_leaking_secret(tmp_path, monkeypatch):
    from dreamloop.analysis import save_ai_config, save_secret

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    save_ai_config(tmp_path, provider="deepseek")
    save_secret(tmp_path, "DEEPSEEK_API_KEY", "very-secret-token")
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.get("/")

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
