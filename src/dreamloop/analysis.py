from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx


DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_OLLAMA_MODEL = "qwen3:8b"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"


class Analyzer(Protocol):
    def analyze(self, content: str, language: str = "en") -> dict[str, Any]:
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

    def analyze(self, content: str, language: str = "en") -> dict[str, Any]:
        return dict(self.result)


@dataclass(frozen=True)
class OpenAICompatibleAnalyzer:
    provider: str
    model: str
    base_url: str
    api_key: str
    response_format: dict[str, str]

    def analyze(self, content: str, language: str = "en") -> dict[str, Any]:
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
                    "content": (
                        "Analyze dreams as structured data. Return only JSON with "
                        "emotional_tone, symbols, themes, summary, and confidence. "
                        "Keep JSON keys in English. Write all field values in "
                        f"{output_language}."
                    ),
                },
                {"role": "user", "content": content},
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


class LegacyResponsesAnalyzer:
    def __init__(self, model: str = DEFAULT_OPENAI_MODEL) -> None:
        self.model = model

    def analyze(self, content: str, language: str = "en") -> dict[str, Any]:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install dreamloop[ai] to enable OpenAI analysis.") from exc

        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        output_language = "Simplified Chinese" if language == "zh" else "English"
        client = OpenAI()
        response = client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Analyze dreams as structured data. Return only JSON with "
                        "emotional_tone, symbols, themes, summary, and confidence. "
                        "Keep JSON keys in English. Write all field values in "
                        f"{output_language}."
                    ),
                },
                {"role": "user", "content": content},
            ],
        )
        text = response.output_text
        return json.loads(text)


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
    path.write_text(json.dumps({"ai": config}, ensure_ascii=False, indent=2), encoding="utf-8")
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
    return {"provider": "ollama", "model": DEFAULT_OLLAMA_MODEL, "base_url": DEFAULT_OLLAMA_BASE_URL}


def load_secrets(root: str | Path | None = None) -> dict[str, str]:
    secrets = read_secret_file(dreamloop_dir(root) / "secrets.env")
    for name in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY"):
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
    symbols = result.get("symbols") or []
    themes = result.get("themes") or []
    if isinstance(symbols, str):
        symbols = [symbols]
    if isinstance(themes, str):
        themes = [themes]

    confidence = result.get("confidence", 0.0)
    try:
        confidence_value = float(confidence)
    except (TypeError, ValueError):
        confidence_value = 0.0

    return {
        "emotional_tone": str(result.get("emotional_tone") or "unknown"),
        "symbols": [str(item) for item in symbols],
        "themes": [str(item) for item in themes],
        "summary": str(result.get("summary") or ""),
        "confidence": max(0.0, min(confidence_value, 1.0)),
        "raw_json": json.dumps(result, ensure_ascii=False),
    }
