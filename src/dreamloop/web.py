from __future__ import annotations

import json
import html as html_lib
import math
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit

from fastapi import FastAPI, Form, HTTPException, Request, status
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .analysis import (
    AnalysisIncomplete,
    AnalysisLanguageMismatch,
    Analyzer,
    ai_status,
    build_analyzer,
    clean_reflections,
    load_ai_config,
    normalize_analysis,
    require_analysis_language,
    save_ai_config,
    save_secret,
)
from .core import AnalysisUnavailableError, DreamLoop, call_analyzer
from .images import image_status, load_image_config, save_image_config, save_image_secret
from .schema import DreamCreate, FeedbackCreate, WeatherSync

PACKAGE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))
REFLECTION_FIELD_KEYS = [
    "strongest_emotion",
    "waking_feeling",
    "important_elements",
    "real_life_context",
    "personal_association",
]

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "nav_dashboard": "Dashboard",
        "nav_log": "Log",
        "nav_patterns": "Patterns",
        "nav_gallery": "Gallery",
        "nav_settings": "Settings",
        "sidebar_count": "dreams stored in your local workspace",
        "dashboard_eyebrow": "Local-first dream intelligence",
        "dashboard_title": "DreamLoop Dashboard",
        "dashboard_tagline": "Your dreams have patterns. DreamLoop finds them locally.",
        "dashboard_hero_title": "Local-first dream intelligence",
        "dashboard_lede": "A six-page loop for private capture, structured AI analysis, pattern discovery, visual memory, and trust settings.",
        "dashboard_cta": "Log a Dream",
        "quick_loop": "Dashboard -> Log -> Detail -> Patterns -> Gallery -> Settings",
        "log_eyebrow": "High-frequency capture",
        "log_title": "Log Dream",
        "log_lede": "Write the dream first. Ask AI to analyze it. Save only after you like the draft result.",
        "local_write": "analysis-first workflow",
        "content_placeholder": "Record a dream before it fades...",
        "reflection_prompt": "Optional prompts",
        "strongest_emotion": "Strongest emotion in the dream",
        "strongest_emotion_placeholder": "e.g. anxious, calm, curious, trapped",
        "waking_feeling": "Feeling after waking",
        "waking_feeling_placeholder": "What stayed with you after waking?",
        "important_elements": "Most important people / objects / scenes",
        "important_elements_placeholder": "Who or what mattered most in the dream?",
        "real_life_context": "Recent real-life situations that may be related",
        "real_life_context_placeholder": "Work, relationships, decisions, stress, conversations...",
        "personal_association": "What this dream makes me think of",
        "personal_association_placeholder": "Any memory, image, phrase, or current concern it brings up",
        "analyze_dream": "AI Analysis",
        "analyzing_dream": "Analyzing and verifying English output...",
        "save_without_ai": "Save without AI",
        "draft_analysis": "Draft analysis",
        "draft_not_saved": "Not saved yet",
        "draft_changed": "The dream changed. Analyze it again before saving this draft.",
        "save_analysis": "Save locally",
        "analysis_language_zh": "Analysis language: Chinese",
        "analysis_language_en": "Analysis language: English",
        "save_analysis_zh": "Save Chinese analysis",
        "save_analysis_en": "Save English analysis",
        "discard": "Discard",
        "delete_dream": "Delete dream",
        "delete_confirm": "Delete this dream from local storage?",
        "generate_chinese_analysis": "Generate Chinese analysis",
        "generate_english_analysis": "Analyze now",
        "generate_dream_image": "Generate dream image",
        "generate_local_card": "Generate local card",
        "real_image_not_ready": "Real image provider is not configured.",
        "dream_image_title": "Dream image",
        "regenerate_visual_memory": "Regenerate local card",
        "visual_memory_title": "Local visual memory",
        "visual_memory_saved": "Visual memory saved locally.",
        "visual_memory_local_note": "No image API was called. This card is generated from the dream text and analysis, then stored locally.",
        "visual_memory_note": "Generate a local visual-memory card without calling an image API by default.",
        "ai_analysis": "AI Analysis",
        "ai_insight": "AI Insight",
        "no_dream": "Record a dream to unlock AI analysis.",
        "latest_dream": "Latest dream",
        "pending_analysis": "Pending analysis",
        "missing_analysis": "Missing analysis",
        "analysis_ready": "Structured analysis",
        "analysis_unavailable": "AI analysis is optional. Configure Ollama, DeepSeek, OpenAI, or a custom endpoint when you want model output.",
        "analysis_unavailable_before_save": "AI is not ready. You can still save the dream locally without analysis.",
        "analysis_error_provider": "Analysis failed. Nothing was saved yet.",
        "analysis_error_language_en": "Analysis content does not match its English label. Regenerate it before saving.",
        "analysis_error_language_zh": "Analysis content does not match its Chinese label. Regenerate it before saving.",
        "analysis_error_incomplete": "The analysis is too incomplete to verify. Regenerate it before saving.",
        "analysis_fallback_en": "Showing English analysis because no valid Chinese analysis is available.",
        "analysis_fallback_zh": "Showing Chinese analysis because no valid English analysis is available.",
        "analysis_mismatch": "The stored language label does not match the analysis content. Regenerate this analysis before using it.",
        "analysis_detected_en": "The content appears to be English.",
        "analysis_detected_zh": "The content appears to be Chinese.",
        "analysis_incomplete_stored": "The stored analysis is too incomplete to verify. Regenerate it before using it.",
        "emotional_tone": "Emotional tone",
        "symbols": "Symbols",
        "themes": "Themes",
        "summary": "Summary",
        "confidence": "Confidence",
        "raw_json": "Raw JSON",
        "dream_details": "Dream details",
        "core_emotion": "Core emotion",
        "important_context": "Your added context",
        "real_life_links": "Possible real-life links",
        "possible_interpretations": "Possible interpretations",
        "real_life_questions": "What I can notice in real life",
        "verification_prompts": "Questions to verify for yourself",
        "feedback_title": "Was this useful?",
        "feedback_resonates": "Resonates",
        "feedback_not_accurate": "Not accurate",
        "feedback_unsure": "Unsure",
        "feedback_reason_placeholder": "Optional note",
        "feedback_saved": "Feedback saved locally.",
        "resonant_themes": "Resonant themes",
        "no_feedback": "Feedback will appear here after you rate an interpretation.",
        "local_dreams": "Local dreams",
        "analyzed": "Analyzed",
        "ai_provider": "AI provider",
        "analysis_queue": "Analysis queue",
        "privacy_mode": "Privacy mode",
        "sqlite_journal": "SQLite journal",
        "pending_entries": "pending entries",
        "data_never_leaves": "data never leaves this machine",
        "pattern_map": "Pattern map",
        "dream_calendar": "Dream calendar",
        "open_dream_day": "Click a date to open that day in the log.",
        "no_heatmap": "No dreams yet.",
        "signals": "Signals",
        "mood_spectrum": "Mood spectrum",
        "no_moods": "Moods appear here after saved analysis or manual capture.",
        "structured_output": "Structured output",
        "most_recurring": "Most recurring symbol across analyzed dreams.",
        "no_symbols": "No recurring symbols yet",
        "symbol_graph": "Symbol network",
        "symbol_graph_empty": "Analyze some dreams first.",
        "pattern_summary": "Pattern summary",
        "theme_trends": "Theme trends",
        "runtime": "Runtime",
        "local_runtime": "Local runtime",
        "data_dir": "Data dir",
        "provider_configured": "Provider configured. Secrets are stored locally and never rendered.",
        "local_logbook": "Local logbook",
        "dreamscape_log": "Dreamscape log",
        "first_dream_waiting": "Your first dream is waiting.",
        "no_mood": "no mood",
        "no_tags": "no tags",
        "filter": "Filter",
        "clear_filter": "Clear filter",
        "recent_dreams": "Recent dreams",
        "back_dashboard": "Back to dashboard",
        "day_context": "Day context",
        "calendar_weather": "Calendar / Weather",
        "calendar": "Calendar",
        "weather": "Weather",
        "no_calendar": "No imported calendar events.",
        "no_weather": "No weather synced for this day.",
        "gallery_title": "Dream Gallery",
        "gallery_eyebrow": "Visual memory",
        "gallery_empty": "Generate a visual memory from a dream detail page first.",
        "gallery_note": "Shows local visual cards derived from saved dreams. Full image generation remains opt-in.",
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
        "image_provider_title": "Image Provider",
        "image_provider_copy": "Keep local cards as the default, connect local ComfyUI, or explicitly opt into a custom cloud image endpoint.",
        "image_provider": "Image provider",
        "local_card_provider": "Local card only",
        "local_comfyui_provider": "Local ComfyUI",
        "cloud_image_provider": "Custom cloud image endpoint",
        "image_provider_status": "Image provider status",
        "image_ready": "Image generation ready.",
        "image_not_ready": "Real image generation is off. Local visual cards still work.",
        "image_comfyui_pending": "Local ComfyUI is saved for future workflow-backed generation. Local visual cards still work.",
        "privacy_audit": "Privacy audit",
        "privacy_audit_copy": "Dream text stays in local SQLite by default. Cloud AI sends the dream and optional reflection fields only after you choose DeepSeek, OpenAI, or a custom endpoint. Weather sync sends coordinates to Open-Meteo. Future backup or Obsidian sync features should remain explicit opt-in actions.",
        "provider_status": "Provider status",
        "developer_note": "Developer note",
        "cli_note": "Start DreamLoop with dreamloop web or scripts/start-dreamloop.cmd. A native desktop shell remains on the roadmap.",
    },
    "zh": {
        "nav_dashboard": "总览",
        "nav_log": "录入",
        "nav_patterns": "规律",
        "nav_gallery": "记忆",
        "nav_settings": "设置",
        "sidebar_count": "条梦境保存在本地工作区",
        "dashboard_eyebrow": "本地优先的梦境智能",
        "dashboard_title": "DreamLoop 总览",
        "dashboard_tagline": "梦会重复说话，DreamLoop 帮你在本地听见。",
        "dashboard_hero_title": "本地优先的梦境智能",
        "dashboard_lede": "从记录、分析到规律和视觉记忆，六页完成一个私密闭环；设置页负责把信任说清楚。",
        "dashboard_cta": "记录梦境",
        "quick_loop": "总览 -> 录入 -> 详情 -> 规律 -> 记忆 -> 设置",
        "log_eyebrow": "高频录入",
        "log_title": "记录梦境",
        "log_lede": "先写下梦境，再让 AI 生成分析草稿。确认有用后，再保存到本地。",
        "local_write": "先分析，再保存",
        "content_placeholder": "趁梦还没散，先记下来...",
        "reflection_prompt": "可选补充",
        "strongest_emotion": "梦里最强的情绪",
        "strongest_emotion_placeholder": "比如：焦虑、平静、好奇、被困住",
        "waking_feeling": "醒来后的感觉",
        "waking_feeling_placeholder": "醒来后最残留的感受是什么？",
        "important_elements": "梦里最重要的人 / 物 / 场景",
        "important_elements_placeholder": "谁或什么最重要？哪个场景最挥之不去？",
        "real_life_context": "最近现实中可能相关的事",
        "real_life_context_placeholder": "工作、关系、决定、压力、对话都可以写",
        "personal_association": "这个梦让我想到什么",
        "personal_association_placeholder": "它让你想起的记忆、画面、词语或现实烦恼",
        "analyze_dream": "AI 分析",
        "analyzing_dream": "正在分析并核对中文输出……",
        "save_without_ai": "不分析，直接保存",
        "draft_analysis": "草稿分析",
        "draft_not_saved": "尚未保存到本地",
        "draft_changed": "梦境内容已修改，请重新分析后再保存这份草稿。",
        "save_analysis": "保存到本地",
        "analysis_language_zh": "分析语言：中文",
        "analysis_language_en": "分析语言：英文",
        "save_analysis_zh": "保存中文分析",
        "save_analysis_en": "保存英文分析",
        "discard": "放弃",
        "delete_dream": "删除记录",
        "delete_confirm": "确定要从本地删除这条梦境记录吗？",
        "generate_chinese_analysis": "生成中文分析",
        "generate_english_analysis": "生成英文分析",
        "generate_dream_image": "生成梦境画面",
        "generate_local_card": "生成本地视觉卡片",
        "real_image_not_ready": "真实图像 provider 尚未配置。",
        "dream_image_title": "梦境图像",
        "regenerate_visual_memory": "重新生成本地卡片",
        "visual_memory_title": "本地视觉记忆",
        "visual_memory_saved": "视觉记忆已保存到本地。",
        "visual_memory_local_note": "没有调用图像 API。这张卡片由梦境文本和分析结果生成，并只保存在本地。",
        "visual_memory_note": "生成一张本地视觉记忆卡片，默认不会调用图像 API。",
        "ai_analysis": "AI 分析",
        "ai_insight": "AI 洞察",
        "no_dream": "先记录一条梦境，AI 分析会出现在这里。",
        "latest_dream": "最新梦境",
        "pending_analysis": "等待分析",
        "missing_analysis": "缺少该语言分析",
        "analysis_ready": "结构化分析",
        "analysis_unavailable": "AI 是可选项。想要模型分析时，再配置 Ollama、DeepSeek、OpenAI 或自定义端点。",
        "analysis_unavailable_before_save": "AI 暂不可用；你也可以先把梦境直接保存到本地。",
        "analysis_error_provider": "分析失败。当前内容尚未保存。",
        "analysis_error_language_en": "分析内容与标记的英文不一致，请重新生成后再保存。",
        "analysis_error_language_zh": "分析内容与标记的中文不一致，请重新生成后再保存。",
        "analysis_error_incomplete": "分析内容不足，无法核对语言，请重新生成后再保存。",
        "analysis_fallback_en": "当前显示英文分析，因为没有可用的中文分析。",
        "analysis_fallback_zh": "当前显示中文分析，因为没有可用的英文分析。",
        "analysis_mismatch": "已保存的语言标签与分析内容不一致；重新生成前不能使用这份分析。",
        "analysis_detected_en": "内容看起来是英文。",
        "analysis_detected_zh": "内容看起来是中文。",
        "analysis_incomplete_stored": "已保存的分析内容不足，无法核对语言；请重新生成。",
        "emotional_tone": "情绪基调",
        "symbols": "符号",
        "themes": "主题",
        "summary": "摘要",
        "confidence": "置信度",
        "raw_json": "原始 JSON",
        "dream_details": "梦里的具体细节",
        "core_emotion": "核心情绪",
        "important_context": "你补充的线索",
        "real_life_links": "可能关联的现实处境",
        "possible_interpretations": "可能解释",
        "real_life_questions": "我可以从中看到的现实问题",
        "verification_prompts": "可以自我验证的问题",
        "feedback_title": "这段解释有帮助吗？",
        "feedback_resonates": "有共鸣",
        "feedback_not_accurate": "不准",
        "feedback_unsure": "不确定",
        "feedback_reason_placeholder": "可选备注",
        "feedback_saved": "反馈已保存到本地。",
        "resonant_themes": "高共鸣主题",
        "no_feedback": "给解释打分后，共鸣主题会出现在这里。",
        "local_dreams": "本地梦境",
        "analyzed": "已分析",
        "ai_provider": "AI 提供方",
        "analysis_queue": "分析队列",
        "privacy_mode": "隐私模式",
        "sqlite_journal": "SQLite 日志",
        "pending_entries": "条待分析",
        "data_never_leaves": "默认不离开本机",
        "pattern_map": "模式地图",
        "dream_calendar": "梦境日历",
        "open_dream_day": "点击日期，查看当天梦境记录。",
        "no_heatmap": "还没有梦境。",
        "signals": "信号",
        "mood_spectrum": "情绪光谱",
        "no_moods": "保存分析或手动记录后，情绪会出现在这里。",
        "structured_output": "结构化输出",
        "most_recurring": "分析结果里最常出现的符号。",
        "no_symbols": "还没有反复出现的符号",
        "symbol_graph": "符号网络",
        "symbol_graph_empty": "先分析一些梦境。",
        "pattern_summary": "模式摘要",
        "theme_trends": "主题趋势",
        "runtime": "运行状态",
        "local_runtime": "本地运行",
        "data_dir": "数据目录",
        "provider_configured": "模型已配置；密钥只保存在本地，不会显示在页面里。",
        "local_logbook": "本地日志",
        "dreamscape_log": "梦境记录",
        "first_dream_waiting": "第一条梦境正在等你。",
        "no_mood": "无情绪",
        "no_tags": "无标签",
        "filter": "筛选",
        "clear_filter": "清除筛选",
        "recent_dreams": "最近梦境",
        "back_dashboard": "返回总览",
        "day_context": "当天上下文",
        "calendar_weather": "日历 / 天气",
        "calendar": "日历",
        "weather": "天气",
        "no_calendar": "没有导入的日历事件。",
        "no_weather": "这一天还没有同步天气。",
        "gallery_title": "梦境画廊",
        "gallery_eyebrow": "视觉记忆",
        "gallery_empty": "先在梦境详情页生成一张视觉记忆。",
        "gallery_note": "展示由已保存梦境生成的本地视觉卡片；完整图像生成仍然是可选路线。",
        "settings_title": "AI 提供方",
        "settings_eyebrow": "本地模型设置",
        "settings_copy": "Ollama 适合零成本本地分析；DeepSeek、OpenAI 和自定义端点适合需要云模型或自建网关的场景。密钥只写入 .dreamloop/secrets.env，页面不会回显。",
        "provider": "提供方",
        "model": "模型",
        "base_url": "Base URL",
        "api_key": "API Key",
        "api_key_placeholder": "需要更换密钥时再粘贴",
        "save_settings": "保存设置",
        "settings_saved": "设置已保存到本地。",
        "settings_secret_note": "已有密钥会隐藏。API Key 留空表示保留当前密钥。",
        "image_provider_title": "图像提供方",
        "image_provider_copy": "默认只生成本地视觉卡片；也可以连接本机 ComfyUI，或显式开启自定义云端图像接口。",
        "image_provider": "图像提供方",
        "local_card_provider": "仅本地卡片",
        "local_comfyui_provider": "本地 ComfyUI",
        "cloud_image_provider": "自定义云端图像接口",
        "image_provider_status": "图像状态",
        "image_ready": "真实图像生成已就绪。",
        "image_not_ready": "真实图像生成未开启，本地视觉卡片仍可使用。",
        "image_comfyui_pending": "本地 ComfyUI 配置已保存；接入 workflow 前，本地视觉卡片仍可使用。",
        "privacy_audit": "隐私审计",
        "privacy_audit_copy": "默认情况下，梦境正文只写入本地 SQLite。只有当你明确选择 DeepSeek、OpenAI 或自定义端点时，云模型才会收到梦境和你填写的可选补充。天气同步会把经纬度发送给 Open-Meteo。未来的备份或 Obsidian 同步也应该保持显式开启。",
        "provider_status": "模型状态",
        "developer_note": "开发者说明",
        "cli_note": "当前可用 dreamloop web 或 scripts/start-dreamloop.cmd 启动；原生桌面壳仍在路线图里。",
    },
}


def _mood_spectrum(dreams: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for dream in dreams:
        analysis = dream.get("analysis") or {}
        mood = (dream.get("manual_mood") or analysis.get("emotional_tone") or "").strip()
        if mood:
            counts[mood] = counts.get(mood, 0) + 1

    total = sum(counts.values())
    if not total:
        return []
    return [
        {"name": name, "count": count, "percent": max(12, round(count / total * 100))}
        for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _lang(value: str | None) -> str:
    return value if value in TRANSLATIONS else "en"


def _form_lang(value: str) -> str:
    if value not in TRANSLATIONS:
        raise HTTPException(status_code=400, detail="Unsupported language")
    return value


def _collect_reflections(
    strongest_emotion: str = "",
    waking_feeling: str = "",
    important_elements: str = "",
    real_life_context: str = "",
    personal_association: str = "",
) -> dict[str, str]:
    return clean_reflections(
        {
            "strongest_emotion": strongest_emotion,
            "waking_feeling": waking_feeling,
            "important_elements": important_elements,
            "real_life_context": real_life_context,
            "personal_association": personal_association,
        }
    )


def _reflection_fields(lang: str, values: dict[str, str] | None = None) -> list[dict[str, str]]:
    t = TRANSLATIONS[_lang(lang)]
    values = values or {}
    return [
        {
            "name": key,
            "label": t[key],
            "placeholder": t[f"{key}_placeholder"],
            "value": values.get(key, ""),
        }
        for key in REFLECTION_FIELD_KEYS
    ]


def _draft_from_form(
    content: str,
    analysis_json: str,
    analysis_language: str,
    reflections_json: str,
) -> dict[str, Any]:
    try:
        analysis_payload = json.loads(analysis_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid analysis JSON") from exc
    if not isinstance(analysis_payload, dict):
        raise HTTPException(status_code=400, detail="Invalid analysis JSON")

    reflections = _reflections_from_json(reflections_json)
    normalized = normalize_analysis(analysis_payload)
    require_analysis_language(normalized.get("report") or {}, analysis_language)
    return {
        "content": content.strip(),
        "reflections": reflections,
        "reflections_json": json.dumps(reflections, ensure_ascii=False),
        "analysis": normalized,
        "analysis_payload": analysis_payload,
        "analysis_json": normalized["raw_json"],
        "language": analysis_language,
    }


def _reflections_from_json(reflections_json: str) -> dict[str, str]:
    try:
        payload = json.loads(reflections_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid reflections JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid reflections JSON")
    return clean_reflections(payload)


def _analysis_error_code(exc: Exception, language: str) -> str:
    if isinstance(exc, AnalysisLanguageMismatch):
        return f"language_{language}"
    if isinstance(exc, AnalysisIncomplete):
        return "incomplete"
    return "provider"


def _page_url(page: str, lang: str, **params: str) -> str:
    path = "/" if page in {"", "dashboard"} else f"/{page}"
    query = {"lang": _lang(lang), **{key: val for key, val in params.items() if val}}
    return path + "?" + urlencode(query)


def _dream_url(dream_id: int, lang: str, **params: str) -> str:
    query = {"lang": _lang(lang), **{key: val for key, val in params.items() if val}}
    return f"/dreams/{dream_id}?" + urlencode(query)


def _origin_tuple(value: str) -> tuple[str, str, int] | None:
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return None
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError:
        return None
    return parsed.scheme, parsed.hostname.rstrip(".").lower(), port


def _is_same_origin_write(request: Request) -> bool:
    source = request.headers.get("origin") or request.headers.get("referer")
    if not source:
        return True
    return _origin_tuple(source) == _origin_tuple(str(request.base_url))


def _analyzer_override(app: FastAPI) -> Analyzer | None:
    analyzer = getattr(app.state, "analyzer", None)
    return analyzer if analyzer is not None else None


def _image_generator_override(app: FastAPI) -> Any | None:
    generator = getattr(app.state, "image_generator", None)
    return generator if generator is not None else None


def _localized_image_status(status_payload: Any, lang: str) -> str:
    t = TRANSLATIONS[_lang(lang)]
    if status_payload.ready:
        return t["image_ready"]
    if status_payload.provider == "local_comfyui":
        return t["image_comfyui_pending"]
    return t["image_not_ready"]


def _analysis_terms(dream: dict[str, Any], key: str) -> set[str]:
    analysis = dream.get("analysis") or {}
    return {str(item).lower() for item in analysis.get(key, [])}


def _matches_log_filter(
    dream: dict[str, Any],
    *,
    date_filter: str = "",
    symbol_filter: str = "",
    theme_filter: str = "",
) -> bool:
    if date_filter and dream["dreamed_on"] != date_filter:
        return False
    if symbol_filter:
        symbol = symbol_filter.lower()
        tag_terms = {str(tag).lower() for tag in dream.get("tags", [])}
        if symbol not in _analysis_terms(dream, "symbols") and symbol not in tag_terms:
            return False
    if theme_filter and theme_filter.lower() not in _analysis_terms(dream, "themes"):
        return False
    return True


def _dashboard_insight(dreams: list[dict[str, Any]], trends: dict[str, list[dict[str, Any]]], lang: str) -> dict[str, str]:
    t = TRANSLATIONS[lang]
    if dreams and dreams[0]["analysis"] is None:
        body = (
            "The latest saved dream has no analysis in this language yet. Open Detail to generate it."
            if lang == "en"
            else "最新保存的梦境还没有当前语言分析。打开详情页即可生成。"
        )
        return {"title": t["missing_analysis"], "body": body}
    if trends["symbols"]:
        symbol = trends["symbols"][0]
        body = (
            f"{symbol['name']} appears {symbol['count']} time(s) across analyzed dreams."
            if lang == "en"
            else f"{symbol['name']} 在已分析梦境中出现了 {symbol['count']} 次。"
        )
        return {"title": str(symbol["name"]), "body": body}
    if dreams:
        body = (
            f"{len(dreams)} local dream(s) are stored. More analysis will make recurring patterns visible."
            if lang == "en"
            else f"本地已保存 {len(dreams)} 条梦境。分析越多，反复出现的模式会越清楚。"
        )
        return {"title": t["local_dreams"], "body": body}
    body = (
        "Start with one dream. DreamLoop will keep the text local and build insight from there."
        if lang == "en"
        else "先记录一条梦境。DreamLoop 会把原文留在本地，再从那里生长出洞察。"
    )
    return {"title": t["ai_insight"], "body": body}


def _dashboard_stats(dreams: list[dict[str, Any]], trends: dict[str, list[dict[str, Any]]], ai: Any, lang: str) -> list[dict[str, str]]:
    t = TRANSLATIONS[lang]
    analyzed = sum(1 for dream in dreams if dream["analysis"])
    top_symbol = trends["symbols"][0]["name"] if trends["symbols"] else "-"
    return [
        {"label": t["local_dreams"], "value": str(len(dreams)), "detail": t["sqlite_journal"]},
        {"label": t["analyzed"], "value": str(analyzed), "detail": t["structured_output"]},
        {"label": t["ai_provider"], "value": str(ai.provider), "detail": ai.model or "capture only"},
        {"label": t["privacy_mode"], "value": "opt-in", "detail": f"{t['data_never_leaves']} / {top_symbol}"},
    ]


def _symbol_graph_svg(graph: dict[str, list[dict[str, Any]]]) -> str:
    nodes = graph.get("nodes") or []
    if not nodes:
        return ""
    width = 420
    height = 260
    center_x = width / 2
    center_y = height / 2
    radius = 92
    positions: dict[str, tuple[float, float]] = {}
    for index, node in enumerate(nodes):
        angle = (2 * math.pi * index / len(nodes)) - (math.pi / 2)
        positions[str(node["id"])] = (center_x + radius * math.cos(angle), center_y + radius * math.sin(angle))

    parts = [f'<svg class="symbol-network" viewBox="0 0 {width} {height}" role="img" aria-label="Symbol network">']
    for edge in graph.get("edges") or []:
        source = positions.get(str(edge["source"]))
        target = positions.get(str(edge["target"]))
        if not source or not target:
            continue
        stroke_width = 1 + min(int(edge.get("weight") or 1), 4)
        parts.append(
            f'<line x1="{source[0]:.1f}" y1="{source[1]:.1f}" x2="{target[0]:.1f}" y2="{target[1]:.1f}" stroke-width="{stroke_width}" />'
        )
    for node in nodes:
        x, y = positions[str(node["id"])]
        label = html_lib.escape(str(node["label"]))
        count = int(node.get("count") or 1)
        circle_radius = 12 + min(count * 3, 12)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{circle_radius}" />')
        parts.append(f'<text x="{x:.1f}" y="{y + circle_radius + 14:.1f}">{label}</text>')
    parts.append("</svg>")
    return "".join(parts)


def create_app(root: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="DreamLoop", version="0.2.0")
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "*.localhost", "[::1]", "testserver"],
    )

    @app.middleware("http")
    async def reject_cross_origin_writes(request: Request, call_next: Any) -> Any:
        if request.method not in {"GET", "HEAD", "OPTIONS"} and not _is_same_origin_write(request):
            return JSONResponse(
                {"detail": "Cross-origin write requests are not allowed."},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return await call_next(request)

    loop = DreamLoop(root)
    loop.init()
    app.state.loop = loop
    app.mount("/static", StaticFiles(directory=str(PACKAGE_DIR / "static")), name="static")
    app.mount("/dreamloop-assets", StaticFiles(directory=str(loop.data_dir / "assets")), name="dreamloop_assets")

    def require_exact_analysis(dream_id: int, language: str) -> None:
        dream = loop.get_dream(dream_id, language=language)
        if dream.get("analysis") is None:
            raise AnalysisUnavailableError(
                f"Dream {dream_id} has no valid {language} analysis."
            )

    def render_home(
        request: Request,
        lang: str = "en",
        *,
        page: str = "dashboard",
        analysis_error: str = "",
        draft: dict[str, Any] | None = None,
        draft_content: str = "",
        draft_reflections: dict[str, str] | None = None,
        response_status: int = status.HTTP_200_OK,
        settings_saved: bool = False,
        date_filter: str = "",
        symbol_filter: str = "",
        theme_filter: str = "",
    ) -> Any:
        lang = _lang(lang)
        if analysis_error not in {"", "provider", "language_en", "language_zh", "incomplete"}:
            analysis_error = ""
        localized_dreams = loop.list_dreams_with_analysis(language=lang)
        trends = loop.trends_from_dreams(localized_dreams)
        symbol_graph = loop.symbol_graph_from_dreams(localized_dreams)
        ai_payload = ai_status(loop.root)
        image_payload = image_status(loop.root)
        log_dreams = [
            dream
            for dream in localized_dreams
            if _matches_log_filter(
                dream,
                date_filter=date_filter,
                symbol_filter=symbol_filter,
                theme_filter=theme_filter,
            )
        ]
        filtered_log = bool(date_filter or symbol_filter or theme_filter)
        if page == "log" and filtered_log:
            latest_dream = log_dreams[0] if log_dreams else None
        else:
            latest_dream = localized_dreams[0] if localized_dreams else None
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "dreams": localized_dreams,
                "log_dreams": log_dreams,
                "recent_dreams": localized_dreams[:3],
                "gallery_cards": [dream for dream in localized_dreams if dream.get("image") or dream.get("visual_memory")],
                "latest_dream": latest_dream,
                "heatmap": loop.heatmap(),
                "ai": ai_payload,
                "ai_config": load_ai_config(loop.root),
                "image": image_payload,
                "image_status_text": _localized_image_status(image_payload, lang),
                "image_config": load_image_config(loop.root),
                "trends": trends,
                "symbol_graph": symbol_graph,
                "symbol_graph_svg": _symbol_graph_svg(symbol_graph),
                "feedback_summary": loop.feedback_summary(language=lang),
                "dashboard_insight": _dashboard_insight(localized_dreams, trends, lang),
                "dashboard_stats": _dashboard_stats(localized_dreams, trends, ai_payload, lang),
                "data_dir": loop.data_dir,
                "pending_count": sum(1 for dream in localized_dreams if dream["analysis"] is None),
                "mood_spectrum": _mood_spectrum(localized_dreams),
                "lang": lang,
                "page": page,
                "t": TRANSLATIONS[lang],
                "language_urls": {
                    "zh": _page_url(page, "zh"),
                    "en": _page_url(page, "en"),
                },
                "analysis_error": analysis_error,
                "draft": draft,
                "draft_content": draft_content,
                "reflection_fields": _reflection_fields(lang, (draft or {}).get("reflections") or draft_reflections),
                "settings_saved": settings_saved,
                "date_filter": date_filter,
                "symbol_filter": symbol_filter,
                "theme_filter": theme_filter,
            },
            status_code=response_status,
        )

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request, lang: str = "en", analysis_error: str = "") -> Any:
        return render_home(request, lang, page="dashboard", analysis_error=analysis_error)

    @app.get("/patterns", response_class=HTMLResponse)
    def patterns(request: Request, lang: str = "en") -> Any:
        return render_home(request, lang, page="patterns")

    @app.get("/insights")
    def insights(lang: str = "en") -> RedirectResponse:
        return RedirectResponse(_page_url("patterns", lang), status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    @app.get("/gallery", response_class=HTMLResponse)
    def gallery(request: Request, lang: str = "en") -> Any:
        return render_home(request, lang, page="gallery")

    @app.get("/log", response_class=HTMLResponse)
    def logbook(
        request: Request,
        lang: str = "en",
        date: str = "",
        symbol: str = "",
        theme: str = "",
        analysis_error: str = "",
    ) -> Any:
        return render_home(
            request,
            lang,
            page="log",
            date_filter=date,
            symbol_filter=symbol,
            theme_filter=theme,
            analysis_error=analysis_error,
        )

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

    @app.post("/settings/image")
    def save_image_settings(
        lang: str = "en",
        provider: str = Form(...),
        model: str = Form(""),
        base_url: str = Form(""),
        api_key: str = Form(""),
    ) -> RedirectResponse:
        try:
            save_image_config(loop.root, provider=provider, model=model.strip() or None, base_url=base_url.strip() or None)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if api_key.strip() and provider == "cloud_openai_compatible":
            save_image_secret(loop.root, api_key.strip())
        return RedirectResponse(_page_url("settings", lang, saved="1"), status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/dreams")
    def create_dream_form(
        lang: str = "en",
        content: str = Form(...),
        tags: str = Form(""),
        manual_mood: str = Form(""),
        strongest_emotion: str = Form(""),
        waking_feeling: str = Form(""),
        important_elements: str = Form(""),
        real_life_context: str = Form(""),
        personal_association: str = Form(""),
    ) -> RedirectResponse:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        dream_id = loop.add_dream(
            content,
            tags=tag_list,
            mood=manual_mood or None,
            reflections=_collect_reflections(
                strongest_emotion,
                waking_feeling,
                important_elements,
                real_life_context,
                personal_association,
            ),
        )
        return RedirectResponse(_dream_url(dream_id, lang), status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/drafts/analyze", response_class=HTMLResponse)
    def analyze_draft(
        request: Request,
        lang: str = "en",
        content: str = Form(...),
        strongest_emotion: str = Form(""),
        waking_feeling: str = Form(""),
        important_elements: str = Form(""),
        real_life_context: str = Form(""),
        personal_association: str = Form(""),
    ) -> Any:
        lang = _form_lang(lang)
        reflections = _collect_reflections(
            strongest_emotion,
            waking_feeling,
            important_elements,
            real_life_context,
            personal_association,
        )
        analyzer = _analyzer_override(request.app) or build_analyzer(loop.root)
        if analyzer is None:
            return render_home(
                request,
                lang,
                page="log",
                analysis_error="provider",
                draft_content=content,
                draft_reflections=reflections,
            )

        try:
            normalized = normalize_analysis(call_analyzer(analyzer, content, lang, reflections))
        except (AnalysisLanguageMismatch, AnalysisIncomplete) as exc:
            return render_home(
                request,
                lang,
                page="log",
                analysis_error=_analysis_error_code(exc, lang),
                draft_content=content,
                draft_reflections=reflections,
                response_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
            )
        except Exception:
            return render_home(
                request,
                lang,
                page="log",
                analysis_error="provider",
                draft_content=content,
                draft_reflections=reflections,
            )

        return render_home(
            request,
            lang,
            page="log",
            draft={
                "content": content.strip(),
                "reflections": reflections,
                "reflections_json": json.dumps(reflections, ensure_ascii=False),
                "analysis": normalized,
                "analysis_json": normalized["raw_json"],
                "language": lang,
            },
        )

    @app.post("/drafts/language", response_class=HTMLResponse)
    def switch_draft_language(
        request: Request,
        lang: str = Form(...),
        content: str = Form(""),
        analysis_json: str = Form(""),
        analysis_language: str = Form(...),
        reflections_json: str = Form("{}"),
    ) -> Any:
        target_language = _form_lang(lang)
        reflections = _reflections_from_json(reflections_json)
        if not analysis_json.strip():
            if not content.strip() and not reflections:
                return RedirectResponse(
                    _page_url("log", target_language),
                    status_code=status.HTTP_303_SEE_OTHER,
                )
            return render_home(
                request,
                target_language,
                page="log",
                draft_content=content,
                draft_reflections=reflections,
            )
        analysis_language = _form_lang(analysis_language)
        try:
            draft = _draft_from_form(
                content,
                analysis_json,
                analysis_language,
                reflections_json,
            )
        except (AnalysisLanguageMismatch, AnalysisIncomplete) as exc:
            return render_home(
                request,
                target_language,
                page="log",
                analysis_error=_analysis_error_code(exc, analysis_language),
                draft_content=content,
                draft_reflections=reflections,
                response_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
            )
        return render_home(request, target_language, page="log", draft=draft)

    @app.post("/drafts/save")
    def save_draft(
        request: Request,
        lang: str = "en",
        content: str = Form(...),
        analysis_json: str = Form(...),
        analysis_language: str = Form("en"),
        reflections_json: str = Form("{}"),
    ) -> Any:
        lang = _form_lang(lang)
        analysis_language = _form_lang(analysis_language)
        try:
            draft = _draft_from_form(
                content,
                analysis_json,
                analysis_language,
                reflections_json,
            )
            dream_id = loop.add_dream_with_analysis(
                draft["content"],
                draft["analysis_payload"],
                language=analysis_language,
                reflections=draft["reflections"],
            )
        except (AnalysisLanguageMismatch, AnalysisIncomplete) as exc:
            return render_home(
                request,
                lang,
                page="log",
                analysis_error=_analysis_error_code(exc, analysis_language),
                draft_content=content,
                draft_reflections=_reflections_from_json(reflections_json),
                response_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
            )
        return RedirectResponse(_dream_url(dream_id, lang), status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/dreams/{dream_id}/analyze")
    def analyze_dream_form(request: Request, dream_id: int, lang: str = "en") -> RedirectResponse:
        lang = _lang(lang)
        analyzer = _analyzer_override(request.app)
        try:
            loop.analyze_dream(dream_id, analyzer, language=lang)
        except (AnalysisLanguageMismatch, AnalysisIncomplete) as exc:
            return RedirectResponse(
                _dream_url(
                    dream_id,
                    lang,
                    analysis_error=_analysis_error_code(exc, lang),
                ),
                status_code=status.HTTP_303_SEE_OTHER,
            )
        except Exception:
            return RedirectResponse(
                _dream_url(dream_id, lang, analysis_error="provider"),
                status_code=status.HTTP_303_SEE_OTHER,
            )
        return RedirectResponse(_dream_url(dream_id, lang), status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/dreams/{dream_id}/delete")
    def delete_dream_form(dream_id: int, lang: str = "en") -> RedirectResponse:
        if not loop.delete_dream(dream_id):
            raise HTTPException(status_code=404, detail="Dream not found")
        return RedirectResponse(_page_url("log", lang), status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/dreams/{dream_id}/visual")
    def generate_visual_form(
        dream_id: int,
        lang: str = "en",
        analysis_language: str = Form(...),
    ) -> RedirectResponse:
        interface_language = _lang(lang)
        analysis_language = _form_lang(analysis_language)
        try:
            require_exact_analysis(dream_id, analysis_language)
            loop.generate_visual_memory(dream_id, language=analysis_language)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Dream not found") from exc
        except AnalysisUnavailableError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RedirectResponse(
            _dream_url(dream_id, interface_language),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    @app.post("/dreams/{dream_id}/image")
    def generate_image_form(
        request: Request,
        dream_id: int,
        lang: str = "en",
        analysis_language: str = Form(...),
    ) -> RedirectResponse:
        interface_language = _lang(lang)
        analysis_language = _form_lang(analysis_language)
        try:
            require_exact_analysis(dream_id, analysis_language)
            loop.generate_dream_image(
                dream_id,
                language=analysis_language,
                generator=_image_generator_override(request.app),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Dream not found") from exc
        except AnalysisUnavailableError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception:
            return RedirectResponse(
                _dream_url(dream_id, interface_language),
                status_code=status.HTTP_303_SEE_OTHER,
            )
        return RedirectResponse(
            _dream_url(dream_id, interface_language),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    @app.post("/dreams/{dream_id}/feedback")
    def save_feedback_form(
        dream_id: int,
        lang: str = "en",
        analysis_language: str = Form(...),
        interpretation_index: int = Form(0),
        rating: str = Form(...),
        reason: str = Form(""),
    ) -> RedirectResponse:
        interface_language = _lang(lang)
        analysis_language = _form_lang(analysis_language)
        try:
            loop.add_feedback(
                dream_id,
                language=analysis_language,
                interpretation_index=interpretation_index,
                rating=rating,
                reason=reason,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except AnalysisUnavailableError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Dream not found") from exc
        return RedirectResponse(
            _dream_url(dream_id, interface_language),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    @app.get("/dreams/{dream_id}", response_class=HTMLResponse)
    def dream_detail(
        request: Request,
        dream_id: int,
        lang: str = "en",
        analysis_error: str = "",
    ) -> Any:
        lang = _lang(lang)
        if analysis_error not in {"", "provider", "language_en", "language_zh", "incomplete"}:
            analysis_error = ""
        try:
            dream = loop.get_dream(
                dream_id,
                language=lang,
                allow_analysis_fallback=True,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Dream not found") from exc
        context = loop.day_context(date.fromisoformat(dream["dreamed_on"]))
        return templates.TemplateResponse(
            request,
            "detail.html",
            {
                "dream": dream,
                "feedback": loop.feedback_for_dream(
                    dream_id,
                    language=dream.get("displayed_analysis_language") or lang,
                ),
                "context": context,
                "ai": ai_status(loop.root),
                "image": image_status(loop.root),
                "lang": lang,
                "t": TRANSLATIONS[lang],
                "analysis_error": analysis_error,
                "language_urls": {
                    "zh": _dream_url(dream_id, "zh"),
                    "en": _dream_url(dream_id, "en"),
                },
            },
        )

    @app.post("/api/dreams", status_code=201)
    def api_create_dream(payload: DreamCreate) -> dict[str, int]:
        dream_id = loop.add_dream(
            payload.content,
            tags=payload.tags,
            mood=payload.manual_mood,
            dreamed_on=payload.dreamed_on,
            reflections=payload.reflections,
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

    @app.delete("/api/dreams/{dream_id}")
    def api_delete_dream(dream_id: int) -> dict[str, int]:
        if not loop.delete_dream(dream_id):
            raise HTTPException(status_code=404, detail="Dream not found")
        return {"deleted": dream_id}

    @app.post("/api/dreams/{dream_id}/visual")
    def api_generate_visual(dream_id: int, lang: str = "en") -> dict[str, Any]:
        try:
            return loop.generate_visual_memory(dream_id, language=_lang(lang))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Dream not found") from exc

    @app.post("/api/dreams/{dream_id}/image")
    def api_generate_image(request: Request, dream_id: int, lang: str = "en") -> dict[str, Any]:
        try:
            return loop.generate_dream_image(
                dream_id,
                language=_lang(lang),
                generator=_image_generator_override(request.app),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Dream not found") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/dreams/{dream_id}/feedback", status_code=201)
    def api_add_feedback(dream_id: int, payload: FeedbackCreate, lang: str = "en") -> dict[str, Any]:
        try:
            feedback_id = loop.add_feedback(
                dream_id,
                language=_lang(lang),
                interpretation_index=payload.interpretation_index,
                rating=payload.rating,
                reason=payload.reason,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except AnalysisUnavailableError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Dream not found") from exc
        return {
            "id": feedback_id,
            "dream_id": dream_id,
            "language": _lang(lang),
            "interpretation_index": payload.interpretation_index,
            "rating": payload.rating,
        }

    @app.get("/api/dreams/{dream_id}/similar")
    def api_similar_dreams(dream_id: int, lang: str = "en") -> list[dict[str, Any]]:
        try:
            return loop.similar_dreams(dream_id, language=_lang(lang))
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
        except (AnalysisLanguageMismatch, AnalysisIncomplete) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
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
        language = _lang(lang)
        try:
            analyzed = loop.analyze_pending(language=language)
        except (AnalysisLanguageMismatch, AnalysisIncomplete) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        status_payload = ai_status(loop.root)
        return {
            "analyzed": analyzed,
            "ai_configured": status_payload.ready,
            "provider": status_payload.provider,
            "language": language,
        }

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

    @app.get("/api/insights/symbol-graph")
    def api_symbol_graph(lang: str = "en") -> dict[str, list[dict[str, Any]]]:
        return loop.symbol_graph(language=_lang(lang))

    @app.get("/api/feedback/summary")
    def api_feedback_summary(lang: str = "en") -> dict[str, list[dict[str, Any]]]:
        return loop.feedback_summary(language=_lang(lang))

    @app.get("/api/images/status")
    def api_images_status() -> dict[str, Any]:
        status_payload = image_status(loop.root)
        return {
            "provider": status_payload.provider,
            "model": status_payload.model,
            "base_url": status_payload.base_url,
            "mode": status_payload.mode,
            "ready": status_payload.ready,
            "warning": status_payload.warning,
        }

    return app
