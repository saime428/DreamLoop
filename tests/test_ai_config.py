from __future__ import annotations

import os
import re
import stat

import pytest

import dreamloop.analysis as analysis
from dreamloop.analysis import (
    AnalysisIncomplete,
    AnalysisLanguageMismatch,
    DeepSeekAnalyzer,
    OpenAICompatibleAnalyzer,
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
    if os.name != "nt":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_secret_rejects_newline_injection(tmp_path):
    with pytest.raises(ValueError, match="single line"):
        save_secret(tmp_path, "CUSTOM_API_KEY", "safe\nOPENAI_API_KEY=overwritten")


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
    assert status.warning is None
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


def test_analysis_prompt_requires_detailed_reality_grounded_report():
    assert hasattr(analysis, "analysis_system_prompt")
    prompt = analysis.analysis_system_prompt("zh")

    assert "analysis_version" in prompt
    assert "possible_interpretations" in prompt
    assert "real_life_questions" in prompt
    assert "至少 2" in prompt
    assert "不要把梦说死" in prompt
    assert "梦境具体细节" in prompt
    assert "现实处境" in prompt


def test_analysis_user_payload_includes_optional_reflections_without_empty_fields():
    assert hasattr(analysis, "build_analysis_user_payload")
    payload = analysis.build_analysis_user_payload(
        "我在海底看到一扇蓝色的门。",
        {
            "strongest_emotion": "害怕又好奇",
            "waking_feeling": "",
            "real_life_context": "最近在考虑是否换工作",
        },
        language="zh",
    )

    assert "梦境内容" in payload
    assert "我在海底看到一扇蓝色的门。" in payload
    assert "strongest_emotion: 害怕又好奇" in payload
    assert "real_life_context: 最近在考虑是否换工作" in payload
    assert "waking_feeling" not in payload


def test_english_prompt_and_payload_add_no_chinese_scaffolding():
    prompt = analysis.analysis_system_prompt("en")
    payload = analysis.build_analysis_user_payload(
        "I found a blue door under the sea.",
        {"strongest_emotion": "curious", "real_life_context": "Considering a job change."},
        language="en",
    )

    assert not re.search(r"[\u3400-\u4dbf\u4e00-\u9fff]", prompt)
    assert not re.search(r"[\u3400-\u4dbf\u4e00-\u9fff]", payload)
    assert "JSON keys in English" in prompt
    assert "another language" in prompt


def test_prompt_preserves_cross_language_user_text():
    dream = "我在海底看到一扇蓝色的门。"

    payload = analysis.build_analysis_user_payload(dream, language="en")
    chinese_prompt = analysis.analysis_system_prompt("zh")

    assert dream in payload
    assert "另一种语言" in chinese_prompt
    assert "JSON" in chinese_prompt
    assert "英文" in chinese_prompt


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"summary": "这个梦境反映了你在现实选择中的犹豫和期待，需要继续观察自己的感受。"}, "zh"),
        ({"summary": "This dream reflects uncertainty around a real decision and invites careful observation."}, "en"),
        ({"summary": "The dream quote 梦见门 is brief, while the full interpretation stays grounded in present choices."}, "en"),
        ({"summary": "这个梦围绕现实中的选择展开，也保留了 OpenAI 这个英文名称作为短暂线索。"}, "zh"),
        ({"summary": "现实选择需要观察 abcdefghijklmno"}, "unknown"),
        ({"summary": "calm door"}, "unknown"),
    ],
)
def test_detect_analysis_language(payload, expected):
    assert analysis.detect_analysis_language(payload) == expected


def test_detect_analysis_language_ignores_raw_json_text():
    payload = {
        "summary": "too short",
        "raw_json": "This duplicated serialized report must not make an incomplete result look English.",
    }

    assert analysis.detect_analysis_language(payload) == "unknown"


def _provider_analyzer() -> OpenAICompatibleAnalyzer:
    return OpenAICompatibleAnalyzer(
        provider="test",
        model="test-model",
        base_url="http://example.invalid/v1",
        api_key="test-key",
        response_format={"type": "json_object"},
    )


def test_provider_returns_matching_language_without_retry(monkeypatch):
    calls = []

    def fake_request(self, messages):
        calls.append(messages)
        return {"summary": "This detailed analysis stays in English and connects the dream to a current decision."}

    monkeypatch.setattr(OpenAICompatibleAnalyzer, "_request", fake_request)

    result = _provider_analyzer().analyze("我梦见一扇门。", language="en")

    assert len(calls) == 1
    assert result["summary"].startswith("This detailed analysis")


def test_provider_retries_one_opposite_language_response(monkeypatch):
    responses = [
        {"summary": "这个分析错误地使用了中文，需要模型按目标语言重新生成完整内容。"},
        {"summary": "The corrected analysis is written in English and relates the dream to a present choice."},
    ]
    calls = []

    def fake_request(self, messages):
        calls.append(messages)
        return responses.pop(0)

    monkeypatch.setattr(OpenAICompatibleAnalyzer, "_request", fake_request)

    result = _provider_analyzer().analyze("我梦见一扇门。", language="en")

    assert len(calls) == 2
    assert result["summary"].startswith("The corrected analysis")
    assert "English" in calls[1][0]["content"]


def test_provider_stops_after_two_opposite_language_responses(monkeypatch):
    calls = []

    def fake_request(self, messages):
        calls.append(messages)
        return {"summary": "这个分析仍然全部使用中文，因此不能作为英文分析结果保存。"}

    monkeypatch.setattr(OpenAICompatibleAnalyzer, "_request", fake_request)

    with pytest.raises(AnalysisLanguageMismatch):
        _provider_analyzer().analyze("I found a door.", language="en")

    assert len(calls) == 2


def test_provider_does_not_retry_incomplete_output(monkeypatch):
    calls = []

    def fake_request(self, messages):
        calls.append(messages)
        return {"summary": "too short"}

    monkeypatch.setattr(OpenAICompatibleAnalyzer, "_request", fake_request)

    with pytest.raises(AnalysisIncomplete):
        _provider_analyzer().analyze("I found a door.", language="en")

    assert len(calls) == 1
