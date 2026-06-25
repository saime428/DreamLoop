from __future__ import annotations

import sys
from types import SimpleNamespace

from typer.testing import CliRunner

from dreamloop.cli import app
from dreamloop.images import save_image_config


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


def test_cli_doctor_reports_local_status_without_revealing_secrets(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    runner = CliRunner()

    runner.invoke(app, ["ai", "use", "deepseek"])
    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "DreamLoop doctor" in result.output
    assert "data_dir:" in result.output
    assert "sqlite:" in result.output
    assert "provider: deepseek" in result.output
    assert "image_provider:" in result.output
    assert "DEEPSEEK_API_KEY is not configured" in result.output
    assert "sk-" not in result.output


def test_cli_demo_adds_sample_data_without_resetting_existing_dreams(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    add_result = runner.invoke(app, ["add", "Do not remove this dream."])
    demo_result = runner.invoke(app, ["demo"])
    list_result = runner.invoke(app, ["list"])

    assert add_result.exit_code == 0
    assert demo_result.exit_code == 0
    assert "Added 3 demo dream" in demo_result.output
    assert list_result.output.count("#") >= 4
    assert "Do not remove this dream." in list_result.output


def test_cli_image_test_reports_provider_status(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_image_config(tmp_path, provider="local_card")
    result = CliRunner().invoke(app, ["image", "test"])

    assert result.exit_code == 0
    assert "local visual cards" in result.output


def test_cli_web_suggests_alt_port_when_bind_fails(monkeypatch):
    def fail_to_start(*args, **kwargs):
        raise OSError("address already in use")

    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(run=fail_to_start))

    result = CliRunner().invoke(app, ["web"])

    assert result.exit_code == 1
    assert "Failed to start DreamLoop on 127.0.0.1:8765" in result.output
    assert "dreamloop web --port 18080" in result.output
