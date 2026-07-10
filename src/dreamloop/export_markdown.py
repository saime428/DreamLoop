from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .analysis import REFLECTION_LABELS
from .core import DreamLoop, normalize_language

EXPORT_SOURCE = "dreamloop"


def dream_markdown_stem(dream: dict[str, Any]) -> str:
    dreamed_on = str(dream.get("dreamed_on") or date.today().isoformat())
    dream_id = int(dream["id"])
    return f"{dreamed_on}-dream-{dream_id:03d}"


def _yaml_scalar(value: Any) -> str:
    if value is None:
        return '""'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _yaml_list_block(key: str, items: list[str]) -> list[str]:
    if not items:
        return [f"{key}: []"]
    lines = [f"{key}:"]
    for item in items:
        lines.append(f"  - {_yaml_scalar(item)}")
    return lines


def render_frontmatter(dream: dict[str, Any], analysis: dict[str, Any] | None, *, language: str) -> str:
    analysis = analysis or {}
    lines = [
        "---",
        f"id: {int(dream['id'])}",
        f"dreamed_on: {_yaml_scalar(dream.get('dreamed_on'))}",
        f"created_at: {_yaml_scalar(dream.get('created_at'))}",
        f"mood: {_yaml_scalar(dream.get('manual_mood') or '')}",
        f"analysis_status: {_yaml_scalar(dream.get('analysis_status') or 'pending')}",
        f"analysis_language: {_yaml_scalar(language)}",
        f"source: {_yaml_scalar(EXPORT_SOURCE)}",
    ]
    lines.extend(_yaml_list_block("tags", list(dream.get("tags") or [])))
    lines.extend(_yaml_list_block("themes", list(analysis.get("themes") or [])))
    lines.extend(_yaml_list_block("symbols", list(analysis.get("symbols") or [])))
    if analysis:
        lines.append(f"emotional_tone: {_yaml_scalar(analysis.get('emotional_tone') or '')}")
        lines.append(f"confidence: {float(analysis.get('confidence') or 0.0)}")
        lines.append(f"summary: {_yaml_scalar(analysis.get('summary') or '')}")
    lines.append("---")
    return "\n".join(lines)


def _markdown_list(items: list[str]) -> str:
    if not items:
        return "_None recorded._"
    return "\n".join(f"- {item}" for item in items)


def _markdown_interpretations(items: list[dict[str, str]]) -> str:
    if not items:
        return "_No structured interpretations recorded._"
    chunks: list[str] = []
    for index, item in enumerate(items, start=1):
        title = item.get("title") or f"Interpretation {index}"
        chunks.append(f"### {title}")
        for label, key in (
            ("Interpretation", "interpretation"),
            ("Dream evidence", "dream_evidence"),
            ("Real-life connection", "real_life_connection"),
            ("Verification question", "verification_question"),
        ):
            value = str(item.get(key) or "").strip()
            if value:
                chunks.append(f"- **{label}:** {value}")
        chunks.append("")
    return "\n".join(chunks).strip()


def render_body(
    dream: dict[str, Any],
    analysis: dict[str, Any] | None,
    *,
    feedback: list[dict[str, Any]] | None = None,
) -> str:
    analysis = analysis or {}
    report = analysis.get("report") or {}
    dreamed_on = dream.get("dreamed_on") or "unknown date"
    sections = [f"# Dream {dreamed_on}", "", "## Dream text", "", str(dream.get("content") or "").strip()]

    reflections = dream.get("reflections") or {}
    if reflections:
        sections.extend(["", "## Reflections"])
        for key, label in REFLECTION_LABELS.items():
            value = str(reflections.get(key) or "").strip()
            if value:
                sections.extend(["", f"### {label}", "", value])

    if analysis:
        sections.extend(
            [
                "",
                "## Analysis summary",
                "",
                f"**Emotional tone:** {analysis.get('emotional_tone') or 'n/a'}",
                f"**Confidence:** {analysis.get('confidence') or 'n/a'}",
                "",
                str(analysis.get("summary") or "").strip(),
            ]
        )

        report_sections = [
            ("Dream details", report.get("dream_details")),
            ("Core emotion", [report.get("core_emotion")] if report.get("core_emotion") else []),
            ("Important elements", report.get("important_elements")),
            ("Real-life links", report.get("real_life_links")),
            ("Personal associations", report.get("personal_associations")),
            ("Real-life questions", report.get("real_life_questions")),
            ("Verification prompts", report.get("verification_prompts")),
        ]
        for title, values in report_sections:
            normalized = [str(item).strip() for item in (values or []) if str(item).strip()]
            if title == "Core emotion" and report.get("core_emotion"):
                normalized = [str(report.get("core_emotion")).strip()]
            if not normalized:
                continue
            sections.extend(["", f"## {title}", "", _markdown_list(normalized)])

        interpretations = report.get("possible_interpretations") or []
        if interpretations:
            sections.extend(["", "## Possible interpretations", "", _markdown_interpretations(interpretations)])

    if feedback:
        sections.extend(["", "## Feedback"])
        for item in feedback:
            rating = item.get("rating") or "unknown"
            reason = str(item.get("reason") or "").strip()
            index = item.get("interpretation_index")
            label = f"Interpretation {int(index) + 1}" if index is not None else "Analysis"
            line = f"- **{label}:** {rating}"
            if reason:
                line += f" — {reason}"
            sections.append(line)

    return "\n".join(sections).strip() + "\n"


def render_dream_markdown(
    dream: dict[str, Any],
    *,
    language: str = "en",
    feedback: list[dict[str, Any]] | None = None,
) -> str:
    analysis = dream.get("analysis")
    frontmatter = render_frontmatter(dream, analysis, language=language)
    body = render_body(dream, analysis, feedback=feedback)
    return f"{frontmatter}\n\n{body}"


def render_index_markdown(exported: list[tuple[str, dict[str, Any]]], *, export_date: str) -> str:
    lines = [
        "---",
        f"title: DreamLoop Export {export_date}",
        f"exported_on: {_yaml_scalar(export_date)}",
        f"source: {_yaml_scalar(EXPORT_SOURCE)}",
        f"dream_count: {len(exported)}",
        "---",
        "",
        f"# DreamLoop Export {export_date}",
        "",
        f"Exported **{len(exported)}** dream(s) from local SQLite.",
        "",
    ]
    if exported:
        lines.append("## Dreams")
        lines.append("")
        for stem, dream in exported:
            summary = str((dream.get("analysis") or {}).get("summary") or dream.get("content") or "").strip()
            if len(summary) > 120:
                summary = summary[:117].rstrip() + "..."
            lines.append(f"- [[{stem}]] — {summary}")
    else:
        lines.append("_No dreams exported._")
    lines.append("")
    return "\n".join(lines)


def default_markdown_export_dir(loop: DreamLoop) -> Path:
    return loop.data_dir / "exports" / f"dreamloop-export-markdown-{date.today().isoformat()}"


def export_markdown(
    loop: DreamLoop,
    *,
    output_dir: Path | None = None,
    language: str = "en",
) -> Path:
    loop.init()
    language = normalize_language(language)
    out_dir = output_dir or default_markdown_export_dir(loop)
    out_dir.mkdir(parents=True, exist_ok=True)

    exported: list[tuple[str, dict[str, Any]]] = []
    for summary in loop.list_dreams():
        dream = loop.get_dream(int(summary["id"]), language=language)
        feedback = loop.feedback_for_dream(int(summary["id"]), language=language)
        stem = dream_markdown_stem(dream)
        markdown = render_dream_markdown(dream, language=language, feedback=feedback)
        (out_dir / f"{stem}.md").write_text(markdown, encoding="utf-8")
        exported.append((stem, dream))

    index = render_index_markdown(exported, export_date=date.today().isoformat())
    (out_dir / "_index.md").write_text(index, encoding="utf-8")
    return out_dir
