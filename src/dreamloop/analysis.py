from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx


DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_OLLAMA_MODEL = "qwen3:8b"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"

REFLECTION_LABELS = {
    "strongest_emotion": "Dream's strongest emotion",
    "waking_feeling": "Feeling after waking",
    "important_elements": "Most important people, objects, or scenes",
    "real_life_context": "Recent real-life situations that may be related",
    "personal_association": "What this dream makes the dreamer think of",
}

REPORT_LIST_FIELDS = {
    "dream_details",
    "important_elements",
    "real_life_links",
    "personal_associations",
    "real_life_questions",
    "verification_prompts",
}

INTERPRETATION_FIELDS = {
    "title",
    "interpretation",
    "dream_evidence",
    "real_life_connection",
    "verification_question",
}


class Analyzer(Protocol):
    def analyze(
        self,
        content: str,
        language: str = "en",
        reflections: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Return structured dream analysis for a dream text."""


@dataclass(frozen=True)
class AIStatus:
    provider: str
    model: str | None
    base_url: str | None
    mode: str
    ready: bool
    warning: str | None = None


@dataclass(frozen=True)
class StaticAnalyzer:
    result: dict[str, Any]

    def analyze(
        self,
        content: str,
        language: str = "en",
        reflections: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return dict(self.result)


@dataclass(frozen=True)
class OpenAICompatibleAnalyzer:
    provider: str
    model: str
    base_url: str
    api_key: str
    response_format: dict[str, str]

    def analyze(
        self,
        content: str,
        language: str = "en",
        reflections: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install dreamloop[ai] to enable cloud model analysis.") from exc

        output_language = "Simplified Chinese" if language == "zh" else "English"
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": analysis_system_prompt(language),
                },
                {"role": "user", "content": build_analysis_user_payload(content, reflections or {})},
            ],
            response_format=self.response_format,
        )
        text = response.choices[0].message.content or "{}"
        return json.loads(text)


class DeepSeekAnalyzer(OpenAICompatibleAnalyzer):
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_DEEPSEEK_MODEL,
        base_url: str = DEFAULT_DEEPSEEK_BASE_URL,
    ) -> None:
        super().__init__(
            provider="deepseek",
            model=model,
            base_url=base_url,
            api_key=api_key,
            response_format={"type": "json_object"},
        )


class OllamaAnalyzer(OpenAICompatibleAnalyzer):
    def __init__(
        self,
        model: str = DEFAULT_OLLAMA_MODEL,
        base_url: str = DEFAULT_OLLAMA_BASE_URL,
    ) -> None:
        super().__init__(
            provider="ollama",
            model=model,
            base_url=base_url,
            api_key="ollama",
            response_format={"type": "json_object"},
        )


class OpenAIAnalyzer(OpenAICompatibleAnalyzer):
    def __init__(self, model: str = DEFAULT_OPENAI_MODEL, api_key: str | None = None) -> None:
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        super().__init__(
            provider="openai",
            model=model,
            base_url="https://api.openai.com/v1",
            api_key=key,
            response_format={"type": "json_object"},
        )


def save_ai_config(
    root: str | Path | None = None,
    *,
    provider: str,
    model: str | None = None,
    base_url: str | None = None,
) -> Path:
    config = default_ai_config(provider)
    if model:
        config["model"] = model
    if base_url:
        config["base_url"] = base_url
    path = dreamloop_dir(root) / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(payload, dict):
        payload = {}
    payload["ai"] = config
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    ensure_gitignore(root)
    return path


def save_secret(root: str | Path | None, name: str, value: str) -> Path:
    path = dreamloop_dir(root) / "secrets.env"
    path.parent.mkdir(parents=True, exist_ok=True)
    secrets = read_secret_file(path)
    secrets[name] = value
    path.write_text(
        "\n".join(f"{key}={val}" for key, val in sorted(secrets.items())) + "\n",
        encoding="utf-8",
    )
    ensure_gitignore(root)
    return path


def ai_status(root: str | Path | None = None) -> AIStatus:
    config = load_ai_config(root)
    provider = config["provider"]
    secrets = load_secrets(root)
    model = config.get("model")
    base_url = config.get("base_url")

    if provider == "none":
        return AIStatus("none", None, None, "local", False, "AI analysis disabled.")
    if provider == "ollama":
        return AIStatus("ollama", model, base_url, "local", True, "Ollama optional; capture works if it is offline.")
    if provider == "deepseek":
        ready = bool(secrets.get("DEEPSEEK_API_KEY"))
        warning = None if ready else "DEEPSEEK_API_KEY is not configured."
        return AIStatus("deepseek", model, base_url, "cloud", ready, warning)
    if provider == "openai":
        ready = bool(secrets.get("OPENAI_API_KEY"))
        warning = None if ready else "OPENAI_API_KEY is not configured."
        return AIStatus("openai", model, base_url, "cloud", ready, warning)
    if provider == "custom":
        ready = bool(model and base_url)
        warning = None if ready else "Custom provider needs both model and base URL."
        return AIStatus("custom", model, base_url, "custom", ready, warning)
    return AIStatus(provider, model, base_url, "unknown", False, f"Unknown AI provider: {provider}")


def ai_is_configured(root: str | Path | None = None) -> bool:
    return ai_status(root).ready


def build_analyzer(root: str | Path | None = None) -> Analyzer | None:
    status = ai_status(root)
    if not status.ready:
        return None
    secrets = load_secrets(root)
    if status.provider == "ollama":
        return OllamaAnalyzer(model=status.model or DEFAULT_OLLAMA_MODEL, base_url=status.base_url or DEFAULT_OLLAMA_BASE_URL)
    if status.provider == "deepseek":
        return DeepSeekAnalyzer(
            api_key=secrets["DEEPSEEK_API_KEY"],
            model=status.model or DEFAULT_DEEPSEEK_MODEL,
            base_url=status.base_url or DEFAULT_DEEPSEEK_BASE_URL,
        )
    if status.provider == "openai":
        return OpenAIAnalyzer(model=status.model or DEFAULT_OPENAI_MODEL, api_key=secrets["OPENAI_API_KEY"])
    if status.provider == "custom":
        return OpenAICompatibleAnalyzer(
            provider="custom",
            model=status.model or "model",
            base_url=status.base_url or "",
            api_key=secrets.get("CUSTOM_API_KEY") or "local",
            response_format={"type": "json_object"},
        )
    return None


def test_provider_connection(root: str | Path | None = None) -> str:
    status = ai_status(root)
    if not status.ready:
        return status.warning or "AI provider is not ready."
    if status.provider == "ollama":
        url = (status.base_url or DEFAULT_OLLAMA_BASE_URL).rstrip("/").removesuffix("/v1")
        try:
            response = httpx.get(f"{url}/api/tags", timeout=2)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return f"Ollama configured, but local server is not responding: {exc}"
        return f"Ollama ready at {status.base_url}"
    return f"{status.provider} configured with model {status.model}"


def load_ai_config(root: str | Path | None = None) -> dict[str, str]:
    path = dreamloop_dir(root) / "config.json"
    if not path.exists():
        return default_ai_config("ollama")
    payload = json.loads(path.read_text(encoding="utf-8"))
    provider = payload.get("ai", {}).get("provider", "ollama")
    config = default_ai_config(provider)
    config.update({key: val for key, val in payload.get("ai", {}).items() if val is not None})
    return config


def default_ai_config(provider: str) -> dict[str, str]:
    if provider == "deepseek":
        return {"provider": "deepseek", "model": DEFAULT_DEEPSEEK_MODEL, "base_url": DEFAULT_DEEPSEEK_BASE_URL}
    if provider == "openai":
        return {"provider": "openai", "model": DEFAULT_OPENAI_MODEL, "base_url": "https://api.openai.com/v1"}
    if provider == "none":
        return {"provider": "none", "model": "", "base_url": ""}
    if provider == "custom":
        return {"provider": "custom", "model": "", "base_url": ""}
    return {"provider": "ollama", "model": DEFAULT_OLLAMA_MODEL, "base_url": DEFAULT_OLLAMA_BASE_URL}


def load_secrets(root: str | Path | None = None) -> dict[str, str]:
    secrets = read_secret_file(dreamloop_dir(root) / "secrets.env")
    for name in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CUSTOM_API_KEY"):
        if os.getenv(name):
            secrets[name] = os.environ[name]
    return secrets


def read_secret_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    secrets: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        secrets[key.strip().lstrip("\ufeff")] = value.strip()
    return secrets


def clean_reflections(reflections: dict[str, Any] | None) -> dict[str, str]:
    if not reflections:
        return {}
    cleaned: dict[str, str] = {}
    for key in REFLECTION_LABELS:
        value = reflections.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            cleaned[key] = text
    return cleaned


def is_meaningful_term(value: Any) -> bool:
    text = str(value).strip()
    if not text:
        return False
    if text in {"-", "?", "??", "???", "????", "?????", "？", "？？"}:
        return False
    if re.fullmatch(r"[\W_?？]+", text, flags=re.UNICODE):
        return False
    return bool(re.search(r"[0-9A-Za-z\u4e00-\u9fff]", text))


_JSON_MISSING = object()


def parse_jsonish_text(value: str) -> Any:
    text = value.strip()
    if not text or text[0] not in "[{":
        return _JSON_MISSING
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return _JSON_MISSING


def _first_normalized(value: Any, *, display: bool = False) -> str:
    values = normalize_display_list(value) if display else normalize_text_list(value)
    return values[0] if values else ""


def _mapping_term(value: dict[str, Any]) -> str:
    for key in ("name", "label", "title"):
        if key in value:
            text = _first_normalized(value.get(key))
            if is_meaningful_term(text):
                return text
    for key in ("symbol", "theme", "term", "value"):
        if key in value:
            text = _first_normalized(value.get(key))
            if is_meaningful_term(text):
                return text
    return ""


def _mapping_display_text(value: dict[str, Any]) -> str:
    name = _mapping_term(value)
    meaning = _first_normalized(value.get("meaning"), display=True) if "meaning" in value else ""
    if name and meaning and name != meaning:
        return f"{name}: {meaning}"
    if name:
        return name
    for key in ("summary", "description", "interpretation", "text", "value"):
        if key in value:
            text = _first_normalized(value.get(key), display=True)
            if is_meaningful_term(text):
                return text
    if meaning:
        return meaning
    return ""


def normalize_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        parsed = parse_jsonish_text(text)
        if parsed is not _JSON_MISSING:
            return normalize_text_list(parsed)
        return [text] if is_meaningful_term(text) else []
    if isinstance(value, dict):
        text = _mapping_term(value)
        return [text] if is_meaningful_term(text) else []
    if isinstance(value, (list, tuple, set)):
        items: list[str] = []
        for item in value:
            items.extend(normalize_text_list(item))
        return items
    text = str(value).strip()
    return [text] if is_meaningful_term(text) else []


def normalize_display_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        parsed = parse_jsonish_text(text)
        if parsed is not _JSON_MISSING:
            return normalize_display_list(parsed)
        return [text] if is_meaningful_term(text) else []
    if isinstance(value, dict):
        text = _mapping_display_text(value)
        return [text] if is_meaningful_term(text) else []
    if isinstance(value, (list, tuple, set)):
        items: list[str] = []
        for item in value:
            items.extend(normalize_display_list(item))
        return items
    text = str(value).strip()
    return [text] if is_meaningful_term(text) else []


def normalize_interpretations(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    raw_items = value if isinstance(value, list) else [value]
    normalized: list[dict[str, str]] = []
    for item in raw_items:
        if isinstance(item, dict):
            entry = {
                key: str(item.get(key) or "").strip()
                for key in INTERPRETATION_FIELDS
                if str(item.get(key) or "").strip()
            }
            if entry:
                normalized.append(entry)
            continue
        text = str(item).strip()
        if is_meaningful_term(text):
            normalized.append({"interpretation": text})
    return normalized


def normalize_report_payload(result: dict[str, Any]) -> dict[str, Any]:
    report = dict(result)
    if "symbols" in report:
        report["symbols"] = normalize_text_list(report["symbols"])
    if "themes" in report:
        report["themes"] = normalize_text_list(report["themes"])
    for key in REPORT_LIST_FIELDS:
        if key in report:
            report[key] = normalize_display_list(report[key])
    if "possible_interpretations" in report:
        report["possible_interpretations"] = normalize_interpretations(report["possible_interpretations"])
    for key in ("core_emotion", "waking_feeling"):
        if isinstance(report.get(key), (list, tuple, set)):
            report[key] = " ".join(normalize_text_list(report[key]))
        elif report.get(key) is not None:
            report[key] = str(report[key]).strip()
    return report


def build_analysis_user_payload(content: str, reflections: dict[str, Any] | None = None) -> str:
    cleaned = clean_reflections(reflections)
    lines = ["梦境内容 / Dream content:", content.strip()]
    if cleaned:
        lines.append("")
        lines.append("用户可选补充 / Optional dreamer context:")
        for key, value in cleaned.items():
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def analysis_system_prompt(language: str = "en") -> str:
    output_language = "Simplified Chinese" if language == "zh" else "English"
    length_hint = "800-1500 Chinese characters" if language == "zh" else "900-1600 English words"
    zh_requirements = (
        "不要把梦说死。不要用玄学断言。必须回到梦境具体细节，重视情绪多于物品符号，"
        "并联系用户提供的现实处境。至少 2 个 possible_interpretations。"
    )
    return (
        "You are DreamLoop's dream analysis engine. Return only valid JSON. "
        "Keep JSON keys in English and write all field values in "
        f"{output_language}. Produce a detailed, reality-grounded report of about {length_hint}. "
        f"{zh_requirements} "
        "The analysis must be specific to the dream text, not a generic template. "
        "Prefer emotional dynamics and recent life context over mystical symbolism. "
        "Offer multiple hypotheses and make each one verifiable by the dreamer. "
        "Never claim certainty, diagnose, predict the future, or say one dream proves something. "
        "Return this schema: analysis_version, emotional_tone, symbols, themes, summary, confidence, "
        "dream_details, core_emotion, waking_feeling, important_elements, real_life_links, "
        "personal_associations, possible_interpretations, real_life_questions, verification_prompts. "
        "possible_interpretations must contain at least 2 objects with title, interpretation, "
        "dream_evidence, real_life_connection, and verification_question. "
        "real_life_questions should focus on what reality problem the dream may help the user notice."
    )


def dreamloop_dir(root: str | Path | None = None) -> Path:
    return Path(root or Path.cwd()) / ".dreamloop"


def ensure_gitignore(root: str | Path | None = None) -> None:
    root_path = Path(root or Path.cwd())
    gitignore = root_path / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if ".dreamloop/" in existing.splitlines():
        return
    prefix = "" if not existing or existing.endswith("\n") else "\n"
    gitignore.write_text(existing + prefix + ".dreamloop/\n", encoding="utf-8")


def normalize_analysis(result: dict[str, Any]) -> dict[str, Any]:
    report = normalize_report_payload(result)
    symbols = normalize_text_list(result.get("symbols"))
    themes = normalize_text_list(result.get("themes"))

    confidence = result.get("confidence", 0.0)
    try:
        confidence_value = float(confidence)
    except (TypeError, ValueError):
        confidence_value = 0.0

    return {
        "emotional_tone": str(result.get("emotional_tone") or "unknown"),
        "symbols": symbols,
        "themes": themes,
        "summary": str(result.get("summary") or ""),
        "confidence": max(0.0, min(confidence_value, 1.0)),
        "report": report,
        "raw_json": json.dumps(report, ensure_ascii=False),
    }
