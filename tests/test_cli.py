from __future__ import annotations

from typer.testing import CliRunner

from dreamloop.cli import app


def test_cli_help_renders_without_type_errors():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Local-first AI dream journal" in result.output
