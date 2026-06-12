from __future__ import annotations

from dreamloop.analysis import (
    DeepSeekAnalyzer,
    OllamaAnalyzer,
    ai_status,
    build_analyzer,
    save_ai_config,
    save_secret,
)


def test_local_secret_is_written_inside_ignored_dreamloop_dir(tmp_path):
    path = save_secret(tmp_path, "DEEPSEEK_API_KEY", "secret-value")

    assert path == tmp_path / ".dreamloop" / "secrets.env"
    assert "DEEPSEEK_API_KEY=secret-value" in path.read_text(encoding="utf-8")
    assert ".dreamloop/" in (tmp_path / ".gitignore").read_text(encoding="utf-8")


def test_deepseek_provider_uses_official_openai_compatible_defaults(tmp_path):
    save_ai_config(tmp_path, provider="deepseek")
    save_secret(tmp_path, "DEEPSEEK_API_KEY", "secret-value")

    status = ai_status(tmp_path)
    analyzer = build_analyzer(tmp_path)

    assert status.provider == "deepseek"
    assert status.model == "deepseek-v4-flash"
    assert status.base_url == "https://api.deepseek.com"
    assert status.mode == "cloud"
    assert status.ready is True
    assert isinstance(analyzer, DeepSeekAnalyzer)
    assert analyzer.base_url == "https://api.deepseek.com"
    assert analyzer.model == "deepseek-v4-flash"
    assert analyzer.response_format == {"type": "json_object"}


def test_secret_file_reader_tolerates_utf8_bom(tmp_path):
    save_ai_config(tmp_path, provider="deepseek")
    secrets = tmp_path / ".dreamloop" / "secrets.env"
    secrets.write_text("DEEPSEEK_API_KEY=secret-value\n", encoding="utf-8-sig")

    status = ai_status(tmp_path)

    assert status.ready is True


def test_ollama_provider_is_local_and_does_not_need_key(tmp_path):
    save_ai_config(tmp_path, provider="ollama", model="qwen3:8b")

    status = ai_status(tmp_path)
    analyzer = build_analyzer(tmp_path)

    assert status.provider == "ollama"
    assert status.model == "qwen3:8b"
    assert status.base_url == "http://localhost:11434/v1"
    assert status.mode == "local"
    assert status.ready is True
    assert isinstance(analyzer, OllamaAnalyzer)
    assert analyzer.api_key == "ollama"


def test_custom_openai_compatible_provider_uses_configured_endpoint(tmp_path):
    save_ai_config(
        tmp_path,
        provider="custom",
        model="local-model",
        base_url="http://localhost:1234/v1",
    )

    status = ai_status(tmp_path)
    analyzer = build_analyzer(tmp_path)

    assert status.provider == "custom"
    assert status.model == "local-model"
    assert status.base_url == "http://localhost:1234/v1"
    assert status.mode == "custom"
    assert status.ready is True
    assert analyzer is not None
    assert analyzer.provider == "custom"
    assert analyzer.api_key == "local"
