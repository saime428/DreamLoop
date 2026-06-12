from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .analysis import Analyzer, ai_status, build_analyzer, load_ai_config, normalize_analysis, save_ai_config, save_secret
from .core import DreamLoop

PACKAGE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "nav_capture": "Capture",
        "nav_analysis": "AI Analysis",
        "nav_insights": "Insights",
        "nav_local": "Local",
        "nav_logbook": "Logbook",
        "nav_settings": "Settings",
        "sidebar_count": "dreams stored in your local workspace",
        "eyebrow": "Local-first dream intelligence",
        "headline": "Good night, explorer",
        "tagline": "Your dreams have patterns. DreamLoop finds them locally.",
        "lede": "Record a dream, then ask a local or opt-in model to extract emotions, symbols, themes, and a concise summary.",
        "log_dream": "Log Dream",
        "local_write": "local write",
        "content_placeholder": "Record a dream before it fades...",
        "tags_placeholder": "water, door",
        "mood_placeholder": "mood",
        "save_locally": "Save locally",
        "analyze_dream": "AI Analysis",
        "save_without_ai": "Save without AI",
        "draft_analysis": "Draft analysis",
        "draft_not_saved": "Not saved yet",
        "save_analysis": "Save locally",
        "discard": "Discard",
        "generate_language_analysis": "Generate this language analysis",
        "generate_chinese_analysis": "Generate Chinese analysis",
        "generate_english_analysis": "Analyze now",
        "cli_first": "CLI-first capture",
        "ai_analysis": "AI Analysis",
        "no_dream": "Record a dream to unlock AI analysis.",
        "latest_dream": "Latest dream",
        "pending_analysis": "Pending analysis",
        "analyze_now": "Analyze now",
        "analysis_ready": "Structured analysis",
        "analysis_unavailable": "AI analysis is optional. Configure Ollama, DeepSeek, or OpenAI when you want model output.",
        "analysis_unavailable_before_save": "AI is not ready. You can still save the dream locally without analysis.",
        "analysis_failed": "Analysis failed. Nothing was saved yet.",
        "emotional_tone": "Emotional tone",
        "symbols": "Symbols",
        "themes": "Themes",
        "summary": "Summary",
        "confidence": "Confidence",
        "raw_json": "Raw JSON",
        "local_dreams": "Local dreams",
        "ai_provider": "AI provider",
        "analysis_queue": "Analysis queue",
        "privacy_mode": "Privacy mode",
        "sqlite_journal": "SQLite journal",
        "pending_entries": "pending entries",
        "data_never_leaves": "data never leaves this machine",
        "pattern_map": "Pattern map",
        "dream_constellation": "Dream constellation",
        "open_dream_day": "Click a date to open that day in the log.",
        "no_heatmap": "No dreams yet.",
        "signals": "Signals",
        "mood_spectrum": "Mood spectrum",
        "no_moods": "Manual moods appear here after capture.",
        "structured_output": "Structured output",
        "ai_insight": "AI Insight",
        "most_recurring": "Most recurring symbol across analyzed dreams.",
        "no_symbols": "No recurring symbols yet",
        "runtime": "Runtime",
        "local_runtime": "Starlit local runtime",
        "data_dir": "Data dir",
        "ollama_optional": "Ollama optional",
        "obsidian_roadmap": "roadmap",
        "provider_configured": "Provider configured. Secrets are stored locally and never rendered.",
        "local_logbook": "Local logbook",
        "dreamscape_log": "Dreamscape log",
        "first_dream_waiting": "Your first dream is waiting.",
        "no_mood": "no mood",
        "no_tags": "no tags",
        "back_dashboard": "Back to dashboard",
        "day_context": "Day context",
        "calendar_weather": "Calendar / Weather",
        "calendar": "Calendar",
        "weather": "Weather",
        "no_calendar": "No imported calendar events.",
        "no_weather": "No weather synced for this day.",
        "settings_title": "AI Provider",
        "settings_eyebrow": "Local model settings",
        "settings_copy": "Choose Ollama for local zero-cost analysis, use DeepSeek/OpenAI, or connect any OpenAI-compatible endpoint. Secrets stay in .dreamloop/secrets.env and are never rendered back.",
        "provider": "Provider",
        "model": "Model",
        "base_url": "Base URL",
        "api_key": "API Key",
        "api_key_placeholder": "Paste a key only when you want to replace it",
        "save_settings": "Save settings",
        "settings_saved": "Settings saved locally.",
        "settings_secret_note": "Existing keys are hidden. Leave API Key blank to keep the current secret.",
        "provider_status": "Provider status",
        "developer_note": "Developer note",
        "cli_note": "The CLI demo is useful for README screenshots and developer onboarding, but it no longer competes with the main dream analysis workflow.",
    },
    "zh": {
        "nav_capture": "记录",
        "nav_analysis": "AI 分析",
        "nav_insights": "洞察",
        "nav_local": "本地",
        "nav_logbook": "日志",
        "nav_settings": "设置",
        "sidebar_count": "条梦境保存在本地工作区",
        "eyebrow": "本地优先梦境智能",
        "headline": "晚安，探索者",
        "tagline": "你的梦有模式。DreamLoop 在本地发现它们。",
        "lede": "先记录梦境，再让本地或显式启用的模型提取情绪、符号、主题和摘要。",
        "log_dream": "记录梦境",
        "local_write": "本地写入",
        "content_placeholder": "趁梦还没散，先记下来...",
        "tags_placeholder": "水, 门",
        "mood_placeholder": "情绪",
        "save_locally": "保存到本地",
        "analyze_dream": "AI 分析",
        "save_without_ai": "无 AI 保存",
        "draft_analysis": "草稿分析",
        "draft_not_saved": "尚未保存",
        "save_analysis": "保存到本地",
        "discard": "放弃",
        "generate_language_analysis": "生成当前语言分析",
        "generate_chinese_analysis": "生成中文分析",
        "generate_english_analysis": "生成英文分析",
        "cli_first": "CLI 优先记录",
        "ai_analysis": "AI 分析",
        "no_dream": "先记录一条梦境，就可以开始 AI 分析。",
        "latest_dream": "最新梦境",
        "pending_analysis": "等待分析",
        "analyze_now": "立即分析",
        "analysis_ready": "结构化分析",
        "analysis_unavailable": "AI 分析是可选功能。需要模型输出时，再配置 Ollama、DeepSeek 或 OpenAI。",
        "analysis_unavailable_before_save": "AI 暂不可用，你仍可先把梦境保存到本地。",
        "analysis_failed": "分析失败。当前内容尚未保存。",
        "emotional_tone": "情绪基调",
        "symbols": "符号",
        "themes": "主题",
        "summary": "摘要",
        "confidence": "置信度",
        "raw_json": "原始 JSON",
        "local_dreams": "本地梦境",
        "ai_provider": "AI 提供方",
        "analysis_queue": "分析队列",
        "privacy_mode": "隐私模式",
        "sqlite_journal": "SQLite 日志",
        "pending_entries": "条待分析",
        "data_never_leaves": "数据默认不离机",
        "pattern_map": "模式地图",
        "dream_constellation": "梦境星图",
        "open_dream_day": "点击日期，查看当天梦境记录。",
        "no_heatmap": "还没有梦境。",
        "signals": "信号",
        "mood_spectrum": "情绪光谱",
        "no_moods": "记录手动情绪后会出现在这里。",
        "structured_output": "结构化输出",
        "ai_insight": "AI 洞察",
        "most_recurring": "分析结果里最常出现的符号。",
        "no_symbols": "还没有反复出现的符号",
        "runtime": "运行状态",
        "local_runtime": "本地运行环境",
        "data_dir": "数据目录",
        "ollama_optional": "Ollama 可选",
        "obsidian_roadmap": "路线图",
        "provider_configured": "模型已配置。密钥只保存在本地，不会渲染到页面。",
        "local_logbook": "本地日志",
        "dreamscape_log": "梦境记录",
        "first_dream_waiting": "第一条梦境正在等你。",
        "no_mood": "无情绪",
        "no_tags": "无标签",
        "back_dashboard": "返回工作台",
        "day_context": "当天上下文",
        "calendar_weather": "日历 / 天气",
        "calendar": "日历",
        "weather": "天气",
        "no_calendar": "没有导入的日历事件。",
        "no_weather": "这一天还没有同步天气。",
        "settings_title": "AI 提供方",
        "settings_eyebrow": "本地模型设置",
        "settings_copy": "选择 Ollama 可以零成本本地分析；也可以使用 DeepSeek/OpenAI，或连接任意 OpenAI-compatible 端点。密钥只写入 .dreamloop/secrets.env，不会回显到页面。",
        "provider": "提供方",
        "model": "模型",
        "base_url": "Base URL",
        "api_key": "API Key",
        "api_key_placeholder": "只有需要替换密钥时才粘贴",
        "save_settings": "保存设置",
        "settings_saved": "设置已保存到本地。",
        "settings_secret_note": "已有密钥会隐藏。API Key 留空表示保留当前密钥。",
        "provider_status": "模型状态",
        "developer_note": "开发者说明",
        "cli_note": "CLI 演示更适合 README 截图和开发者上手，不再占用梦境分析主流程。",
    },
}


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


def _lang(value: str | None) -> str:
    return value if value in TRANSLATIONS else "en"


def _home_url(lang: str, **params: str) -> str:
    query = {"lang": _lang(lang), **{key: val for key, val in params.items() if val}}
    return "/?" + "&".join(f"{key}={value}" for key, value in query.items())


def _page_url(page: str, lang: str, **params: str) -> str:
    path = "/" if page == "capture" else f"/{page}"
    query = {"lang": _lang(lang), **{key: val for key, val in params.items() if val}}
    return path + "?" + "&".join(f"{key}={value}" for key, value in query.items())


def _analyzer_override(app: FastAPI) -> Analyzer | None:
    analyzer = getattr(app.state, "analyzer", None)
    return analyzer if analyzer is not None else None


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

    def render_home(
        request: Request,
        lang: str = "en",
        *,
        page: str = "capture",
        analysis_error: bool = False,
        draft: dict[str, Any] | None = None,
        draft_content: str = "",
        settings_saved: bool = False,
        date_filter: str = "",
    ) -> Any:
        lang = _lang(lang)
        dreams = loop.list_dreams()
        localized_dreams = [loop.get_dream(dream["id"], language=lang) for dream in dreams]
        log_dreams = [
            dream for dream in localized_dreams if not date_filter or dream["dreamed_on"] == date_filter
        ]
        latest_dream = localized_dreams[0] if localized_dreams else None
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "dreams": localized_dreams,
                "log_dreams": log_dreams,
                "latest_dream": latest_dream,
                "heatmap": loop.heatmap(),
                "ai": ai_status(loop.root),
                "ai_config": load_ai_config(loop.root),
                "trends": loop.trends(language=lang),
                "data_dir": loop.data_dir,
                "pending_count": sum(1 for dream in localized_dreams if dream["analysis"] is None),
                "mood_spectrum": _mood_spectrum(dreams),
                "lang": lang,
                "page": page,
                "t": TRANSLATIONS[lang],
                "analysis_error": analysis_error,
                "draft": draft,
                "draft_content": draft_content,
                "settings_saved": settings_saved,
                "date_filter": date_filter,
            },
        )

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request, lang: str = "en", analysis_error: str = "") -> Any:
        return render_home(request, lang, analysis_error=bool(analysis_error))

    @app.get("/insights", response_class=HTMLResponse)
    def insights(request: Request, lang: str = "en") -> Any:
        return render_home(request, lang, page="insights")

    @app.get("/log", response_class=HTMLResponse)
    def logbook(request: Request, lang: str = "en", date: str = "") -> Any:
        return render_home(request, lang, page="log", date_filter=date)

    @app.get("/settings", response_class=HTMLResponse)
    def settings(request: Request, lang: str = "en", saved: str = "") -> Any:
        return render_home(request, lang, page="settings", settings_saved=bool(saved))

    @app.post("/settings/ai")
    def save_ai_settings(
        lang: str = "en",
        provider: str = Form(...),
        model: str = Form(""),
        base_url: str = Form(""),
        api_key: str = Form(""),
    ) -> RedirectResponse:
        provider = provider.strip().lower()
        if provider not in {"ollama", "deepseek", "openai", "custom", "none"}:
            raise HTTPException(status_code=400, detail="Unsupported AI provider")
        save_ai_config(loop.root, provider=provider, model=model.strip() or None, base_url=base_url.strip() or None)
        if api_key.strip() and provider in {"deepseek", "openai", "custom"}:
            secret_name = {
                "deepseek": "DEEPSEEK_API_KEY",
                "openai": "OPENAI_API_KEY",
                "custom": "CUSTOM_API_KEY",
            }[provider]
            save_secret(loop.root, secret_name, api_key.strip())
        return RedirectResponse(_page_url("settings", lang, saved="1"), status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/dreams")
    def create_dream_form(
        lang: str = "en",
        content: str = Form(...),
        tags: str = Form(""),
        manual_mood: str = Form(""),
    ) -> RedirectResponse:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        loop.add_dream(content, tags=tag_list, mood=manual_mood or None)
        return RedirectResponse(_home_url(lang), status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/drafts/analyze", response_class=HTMLResponse)
    def analyze_draft(request: Request, lang: str = "en", content: str = Form(...)) -> Any:
        lang = _lang(lang)
        analyzer = _analyzer_override(request.app) or build_analyzer(loop.root)
        if analyzer is None:
            return render_home(request, lang, analysis_error=True, draft_content=content)

        try:
            normalized = normalize_analysis(analyzer.analyze(content, language=lang))
        except Exception:
            return render_home(request, lang, analysis_error=True, draft_content=content)

        return render_home(
            request,
            lang,
            draft={
                "content": content.strip(),
                "analysis": normalized,
                "analysis_json": normalized["raw_json"],
                "language": lang,
            },
        )

    @app.post("/drafts/save")
    def save_draft(
        lang: str = "en",
        content: str = Form(...),
        analysis_json: str = Form(...),
        analysis_language: str = Form("en"),
    ) -> RedirectResponse:
        try:
            analysis = json.loads(analysis_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid analysis JSON") from exc
        loop.add_dream_with_analysis(content, analysis, language=_lang(analysis_language))
        return RedirectResponse(_home_url(lang), status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/dreams/{dream_id}/analyze")
    def analyze_dream_form(request: Request, dream_id: int, lang: str = "en") -> RedirectResponse:
        lang = _lang(lang)
        analyzer = _analyzer_override(request.app)
        try:
            loop.analyze_dream(dream_id, analyzer, language=lang)
        except Exception:
            return RedirectResponse(
                _home_url(lang, analysis_error="1"),
                status_code=status.HTTP_303_SEE_OTHER,
            )
        return RedirectResponse(_home_url(lang), status_code=status.HTTP_303_SEE_OTHER)

    @app.get("/dreams/{dream_id}", response_class=HTMLResponse)
    def dream_detail(request: Request, dream_id: int, lang: str = "en") -> Any:
        lang = _lang(lang)
        try:
            dream = loop.get_dream(dream_id, language=lang)
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
                "lang": lang,
                "t": TRANSLATIONS[lang],
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
    def api_get_dream(dream_id: int, lang: str = "en") -> dict[str, Any]:
        try:
            return loop.get_dream(dream_id, language=_lang(lang))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Dream not found") from exc

    @app.get("/api/dreams/{dream_id}/similar")
    def api_similar_dreams(dream_id: int) -> list[dict[str, Any]]:
        try:
            return loop.similar_dreams(dream_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Dream not found") from exc

    @app.post("/api/dreams/{dream_id}/analyze")
    def api_analyze_dream(request: Request, dream_id: int, lang: str = "en") -> dict[str, Any]:
        lang = _lang(lang)
        analyzer = _analyzer_override(request.app)
        status_payload = ai_status(loop.root)
        if analyzer is None and not status_payload.ready:
            raise HTTPException(status_code=409, detail=status_payload.warning or "AI provider is not ready.")
        try:
            analyzed = loop.analyze_dream(dream_id, analyzer, language=lang)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Dream not found") from exc
        return {
            "analyzed": analyzed,
            "ai_configured": True,
            "provider": "test" if analyzer is not None else status_payload.provider,
            "language": lang,
        }

    @app.post("/api/analyze/pending")
    def api_analyze_pending(lang: str = "en") -> dict[str, Any]:
        analyzed = loop.analyze_pending(language=_lang(lang))
        status = ai_status(loop.root)
        return {"analyzed": analyzed, "ai_configured": status.ready, "provider": status.provider, "language": _lang(lang)}

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
    def api_trends(lang: str = "en") -> dict[str, list[dict[str, Any]]]:
        return loop.trends(language=_lang(lang))

    return app
