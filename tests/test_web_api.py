from __future__ import annotations

from fastapi.testclient import TestClient

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
    assert "AI not configured" in response.text
    assert "DreamLoop" in response.text


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
