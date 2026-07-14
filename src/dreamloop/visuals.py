from __future__ import annotations

import re
import sqlite3
import unicodedata
from typing import Any

from .analysis import normalize_text_list


def normalize_visual_accent(value: Any, fallback: str) -> str:
    legacy_accents = {
        "#69f0d7": "#8ba87a",
        "#8e63ff": "#d4a574",
        "#ff6ba8": "#c47a5a",
        "#78d7ff": "#8ba87a",
        "#a68cff": "#d4a574",
        "#ffe27a": "#e8c089",
        "#88f0a6": "#8ba87a",
        "#5cc8ff": "#9a7b56",
        "#f58bd1": "#c47a5a",
        "#f7c66b": "#d4a574",
        "#8d7aff": "#a67c6a",
        "#5de2d0": "#8ba87a",
    }
    accent = str(value or fallback).strip().lower()
    return legacy_accents.get(accent, accent if accent.startswith("#") and len(accent) == 7 else fallback)


def normalize_visual_memory(payload: dict[str, Any]) -> dict[str, Any]:
    visual = dict(payload)
    symbols = normalize_text_list(visual.get("symbols"))
    themes = normalize_text_list(visual.get("themes"))
    title_values = normalize_text_list(visual.get("title"))
    title_candidate = title_values[0] if title_values else (symbols[0] if symbols else "Local visual memory")
    title = compact_visual_title(title_candidate)
    prompt = str(visual.get("prompt") or "").strip()
    if '"name"' in prompt or '"meaning"' in prompt or "{'name'" in prompt or "{'meaning'" in prompt:
        prompt_parts = ["Local visual memory card."]
        if symbols:
            prompt_parts.append(f"Symbols: {', '.join(symbols[:5])}.")
        if themes:
            prompt_parts.append(f"Themes: {', '.join(themes[:5])}.")
        prompt = " ".join(prompt_parts)
    visual["kind"] = str(visual.get("kind") or "local_card")
    visual["title"] = title
    visual["prompt"] = prompt
    visual["symbols"] = symbols[:5]
    visual["themes"] = themes[:5]
    visual["accent_1"] = normalize_visual_accent(visual.get("accent_1"), "#8ba87a")
    visual["accent_2"] = normalize_visual_accent(visual.get("accent_2"), "#d4a574")
    visual["accent_3"] = normalize_visual_accent(visual.get("accent_3"), "#c47a5a")
    return visual


def compact_visual_title(value: Any) -> str:
    candidate = str(value or "").strip()
    segments = [segment.strip() for segment in re.split(r"[\n。！？.!?]", candidate)]
    title = next((segment for segment in segments if segment), candidate)
    if len(title) <= 48:
        return title

    # Keep common extended grapheme sequences intact without a runtime dependency.
    clusters: list[str] = []
    for char in title:
        previous = clusters[-1] if clusters else ""
        if previous and (
            _extends_grapheme(char)
            or previous.endswith("\u200d")
            or (
                _is_regional_indicator(char)
                and len(previous) == 1
                and _is_regional_indicator(previous)
            )
        ):
            clusters[-1] += char
        else:
            clusters.append(char)

    compact: list[str] = []
    code_points = 0
    for cluster in clusters:
        if code_points + len(cluster) > 47:
            break
        compact.append(cluster)
        code_points += len(cluster)
    return "".join(compact).rstrip() + "…"


def _extends_grapheme(char: str) -> bool:
    code_point = ord(char)
    return (
        unicodedata.category(char).startswith("M")
        or char == "\u200d"
        or 0xFE00 <= code_point <= 0xFE0F
        or 0x1F3FB <= code_point <= 0x1F3FF
        or 0xE0100 <= code_point <= 0xE01EF
        or 0xE0020 <= code_point <= 0xE007F
    )


def _is_regional_indicator(char: str) -> bool:
    return 0x1F1E6 <= ord(char) <= 0x1F1FF


def image_from_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    image = dict(row)
    image["image_url"] = image_url(image.get("image_path", ""))
    return image


def image_url(image_path: str) -> str:
    if not image_path:
        return ""
    if image_path.startswith("assets/"):
        return f"/dreamloop-assets/{image_path.removeprefix('assets/')}"
    return f"/dreamloop-assets/{image_path.lstrip('/')}"


def build_dream_image_prompt(dream: dict[str, Any]) -> str:
    analysis = dream.get("analysis") or {}
    report = analysis.get("report") or {}
    parts = [
        "Create a cinematic, dreamlike illustration based on this dream.",
        f"Dream text: {dream.get('content', '')}",
    ]
    if analysis.get("summary"):
        parts.append(f"Interpretive summary: {analysis['summary']}")
    if analysis.get("emotional_tone"):
        parts.append(f"Core emotion: {analysis['emotional_tone']}")
    symbols = normalize_text_list(analysis.get("symbols"))
    if symbols:
        parts.append(f"Important people, objects, and scenes: {', '.join(symbols[:6])}")
    details = normalize_text_list(report.get("dream_details"))
    if details:
        parts.append(f"Concrete dream details to preserve: {', '.join(details[:4])}")
    parts.append("Avoid text, logos, UI, gore, and literal JSON. Keep it atmospheric but specific.")
    return " ".join(part for part in parts if part.strip())
