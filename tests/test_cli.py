from __future__ import annotations

from typer.testing import CliRunner

from dreamloop.cli import app


def test_cli_help_renders_without_type_errors():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Local-first AI dream journal" in result.output


def test_cli_ai_status_and_use_commands(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    use_result = runner.invoke(app, ["ai", "use", "ollama", "--model", "qwen3:8b"])
    status_result = runner.invoke(app, ["ai", "status"])

    assert use_result.exit_code == 0
    assert status_result.exit_code == 0
    assert "ollama" in status_result.output
    assert "qwen3:8b" in status_result.output
