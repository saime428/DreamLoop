from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .analysis import ai_status
from .core import DreamLoop

PACKAGE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))


def _mood_spectrum(dreams: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for dream in dreams:
        mood = (dream.get("manual_mood") or "").strip()
        if mood:
            counts[mood] = counts.get(mood, 0) + 1

    if not counts:
        return []

    total = sum(counts.values())
    return [
        {"name": name, "count": count, "percent": max(12, round(count / total * 100))}
        for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


class DreamCreate(BaseModel):
    content: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    manual_mood: str | None = None
    dreamed_on: date | None = None


class WeatherSync(BaseModel):
    lat: float
    lon: float


def create_app(root: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="DreamLoop", version="0.1.0")
    loop = DreamLoop(root)
    loop.init()
    app.state.loop = loop
    app.mount("/static", StaticFiles(directory=str(PACKAGE_DIR / "static")), name="static")

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request) -> Any:
        dreams = loop.list_dreams()
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "dreams": dreams,
                "heatmap": loop.heatmap(),
                "ai": ai_status(loop.root),
                "trends": loop.trends(),
                "data_dir": loop.data_dir,
                "pending_count": sum(1 for dream in dreams if dream["analysis_status"] == "pending"),
                "mood_spectrum": _mood_spectrum(dreams),
            },
        )

    @app.post("/dreams")
    def create_dream_form(
        content: str = Form(...),
        tags: str = Form(""),
        manual_mood: str = Form(""),
    ) -> RedirectResponse:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        loop.add_dream(content, tags=tag_list, mood=manual_mood or None)
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)

    @app.get("/dreams/{dream_id}", response_class=HTMLResponse)
    def dream_detail(request: Request, dream_id: int) -> Any:
        try:
            dream = loop.get_dream(dream_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Dream not found") from exc
        context = loop.day_context(date.fromisoformat(dream["dreamed_on"]))
        return templates.TemplateResponse(
            request,
            "detail.html",
            {
                "dream": dream,
                "context": context,
                "ai": ai_status(loop.root),
            },
        )

    @app.post("/api/dreams", status_code=201)
    def api_create_dream(payload: DreamCreate) -> dict[str, int]:
        dream_id = loop.add_dream(
            payload.content,
            tags=payload.tags,
            mood=payload.manual_mood,
            dreamed_on=payload.dreamed_on,
        )
        return {"id": dream_id}

    @app.get("/api/dreams")
    def api_list_dreams() -> list[dict[str, Any]]:
        return loop.list_dreams()

    @app.get("/api/dreams/{dream_id}")
    def api_get_dream(dream_id: int) -> dict[str, Any]:
        try:
            return loop.get_dream(dream_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Dream not found") from exc

    @app.get("/api/dreams/{dream_id}/similar")
    def api_similar_dreams(dream_id: int) -> list[dict[str, Any]]:
        try:
            return loop.similar_dreams(dream_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Dream not found") from exc

    @app.post("/api/analyze/pending")
    def api_analyze_pending() -> dict[str, Any]:
        analyzed = loop.analyze_pending()
        status = ai_status(loop.root)
        return {"analyzed": analyzed, "ai_configured": status.ready, "provider": status.provider}

    @app.post("/api/import/ics")
    def api_import_ics(path: str) -> dict[str, int]:
        return {"imported": loop.import_ics(path)}

    @app.post("/api/weather/sync")
    def api_weather_sync(payload: WeatherSync) -> dict[str, int]:
        return {"synced": loop.sync_weather(payload.lat, payload.lon)}

    @app.get("/api/insights/heatmap")
    def api_heatmap() -> list[dict[str, Any]]:
        return loop.heatmap()

    @app.get("/api/insights/trends")
    def api_trends() -> dict[str, list[dict[str, Any]]]:
        return loop.trends()

    return app
