from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from typer.testing import CliRunner

from dreamloop.analysis import StaticAnalyzer
from dreamloop.cli import app
from dreamloop.core import DreamLoop
from dreamloop.export_markdown import (
    default_markdown_export_dir,
    export_markdown,
    render_dream_markdown,
)


def test_export_markdown_writes_frontmatter_and_analysis_sections(tmp_path):
    loop = DreamLoop(tmp_path)
    analyzer = StaticAnalyzer(
        {
            "emotional_tone": "calm",
            "symbols": ["moon", "door"],
            "themes": ["threshold"],
            "summary": "A calm threshold dream.",
            "confidence": 0.9,
            "dream_details": ["A moonlit door appeared at the end of a hallway."],
            "possible_interpretations": [
                {
                    "title": "A new opening",
                    "interpretation": "The door marks a possible next step.",
                    "dream_evidence": "The door appears at the end of the hallway.",
                    "real_life_connection": "This may echo a recent decision.",
                    "verification_question": "What choice feels close but not ready?",
                }
            ],
            "verification_prompts": ["Compare the dream with this week's recurring pressure."],
        }
    )
    dream_id = loop.add_dream(
        "I saw a moonlit door.",
        tags=["night"],
        mood="calm",
        dreamed_on=date(2026, 6, 24),
        reflections={"strongest_emotion": "calm curiosity"},
    )
    loop.analyze_dream(dream_id, analyzer=analyzer, language="en")
    loop.add_feedback(dream_id, language="en", interpretation_index=0, rating="resonates", reason="felt accurate")

    out_dir = export_markdown(loop, language="en")
    dream_file = out_dir / "2026-06-24-dream-001.md"
    index_file = out_dir / "_index.md"

    assert dream_file.exists()
    assert index_file.exists()
    text = dream_file.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "dreamed_on: 2026-06-24" in text
    assert "source: dreamloop" in text
    assert "tags:" in text
    assert "  - night" in text
    assert "themes:" in text
    assert "  - threshold" in text
    assert "## Dream text" in text
    assert "I saw a moonlit door." in text
    assert "## Analysis summary" in text
    assert "## Possible interpretations" in text
    assert "## Feedback" in text
    assert "resonates" in text
    assert "[[2026-06-24-dream-001]]" in index_file.read_text(encoding="utf-8")


def test_render_dream_markdown_handles_pending_dream_without_analysis(tmp_path):
    loop = DreamLoop(tmp_path)
    dream_id = loop.add_dream("Pending dream only.", dreamed_on=date(2026, 1, 2))
    dream = loop.get_dream(dream_id, language="en")

    text = render_dream_markdown(dream, language="en")

    assert "analysis_status: pending" in text
    assert "themes: []" in text
    assert "## Analysis summary" not in text
    assert "Pending dream only." in text


def test_cli_export_supports_json_and_markdown_formats(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    loop = DreamLoop(tmp_path)
    loop.add_dream("Export me.", dreamed_on=date(2026, 6, 24))

    json_result = runner.invoke(app, ["export"])
    markdown_result = runner.invoke(app, ["export", "--format", "markdown", "--language", "en"])

    assert json_result.exit_code == 0
    assert markdown_result.exit_code == 0
    assert "Exported dreams to" in json_result.output
    assert "Exported 1 dream(s) to" in markdown_result.output

    json_path = tmp_path / ".dreamloop" / "exports" / f"dreamloop-export-{date.today().isoformat()}.json"
    markdown_dir = default_markdown_export_dir(loop)
    assert json_path.exists()
    assert markdown_dir.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload[0]["content"] == "Export me."
    assert (markdown_dir / "2026-06-24-dream-001.md").exists()


def test_cli_export_rejects_unknown_format(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["export", "--format", "yaml"])
    assert result.exit_code == 1
    assert "Format must be one of: json, markdown." in result.output
