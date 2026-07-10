from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx

from .analysis import dreamloop_dir, ensure_gitignore, read_secret_file, save_secret

DEFAULT_COMFYUI_BASE_URL = "http://127.0.0.1:8188"
IMAGE_SECRET_NAME = "IMAGE_API_KEY"
IMAGE_PROVIDERS = {"local_card", "local_comfyui", "cloud_openai_compatible"}


@dataclass(frozen=True)
class ImageStatus:
    provider: str
    model: str | None
    base_url: str | None
    mode: str
    ready: bool
    warning: str | None = None


class ImageGenerator(Protocol):
    provider: str
    model: str | None

    def generate(self, prompt: str) -> bytes:
        """Return image bytes for a prompt."""


def load_image_config(root: str | Path | None = None) -> dict[str, str]:
    path = dreamloop_dir(root) / "config.json"
    if not path.exists():
        return default_image_config("local_card")
    payload = json.loads(path.read_text(encoding="utf-8"))
    provider = payload.get("image", {}).get("provider", "local_card")
    config = default_image_config(provider)
    config.update({key: val for key, val in payload.get("image", {}).items() if val is not None})
    return config


def save_image_config(
    root: str | Path | None = None,
    *,
    provider: str,
    model: str | None = None,
    base_url: str | None = None,
) -> Path:
    provider = provider.strip().lower()
    if provider not in IMAGE_PROVIDERS:
        raise ValueError(f"Unsupported image provider: {provider}")
    config = default_image_config(provider)
    if model:
        config["model"] = model
    if base_url:
        config["base_url"] = base_url
    path = dreamloop_dir(root) / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _read_config_payload(path)
    payload["image"] = config
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    ensure_gitignore(root)
    return path


def save_image_secret(root: str | Path | None, value: str) -> Path:
    return save_secret(root, IMAGE_SECRET_NAME, value)


def image_status(root: str | Path | None = None) -> ImageStatus:
    config = load_image_config(root)
    provider = config["provider"]
    model = config.get("model")
    base_url = config.get("base_url")
    secrets = load_image_secrets(root)
    if provider == "local_card":
        return ImageStatus(
            provider="local_card",
            model=None,
            base_url=None,
            mode="local",
            ready=False,
            warning="Real image generation is disabled; local visual cards are available.",
        )
    if provider == "local_comfyui":
        warning = (
            "Local ComfyUI is configured, but DreamLoop needs a workflow before it can submit prompts. "
            "Local visual cards still work."
            if base_url
            else "Local ComfyUI needs a base URL."
        )
        ready = False
        return ImageStatus(provider, model, base_url, "local", ready, warning)
    if provider == "cloud_openai_compatible":
        ready = bool(model and base_url and secrets.get(IMAGE_SECRET_NAME))
        warning = None if ready else "Cloud image generation needs model, base URL, and API key."
        return ImageStatus(provider, model, base_url, "cloud", ready, warning)
    return ImageStatus(provider, model, base_url, "unknown", False, f"Unknown image provider: {provider}")


def test_image_provider_connection(root: str | Path | None = None) -> str:
    status = image_status(root)
    if status.provider == "local_card":
        return status.warning or "Image provider uses local visual cards."
    if status.provider == "local_comfyui":
        if not status.base_url:
            return status.warning or "Local ComfyUI needs a base URL."
        try:
            response = httpx.get(f"{(status.base_url or '').rstrip('/')}/system_stats", timeout=2)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return f"Local ComfyUI configured, but server is not responding: {exc}"
        return (
            f"Local ComfyUI is reachable at {status.base_url}, but image generation is disabled "
            "until a workflow is configured."
        )
    if not status.ready:
        return status.warning or "Image provider is not ready."
    return f"{status.provider} configured with model {status.model}"


def build_image_generator(root: str | Path | None = None) -> ImageGenerator | None:
    status = image_status(root)
    if not status.ready:
        return None
    if status.provider == "cloud_openai_compatible":
        secrets = load_image_secrets(root)
        return OpenAICompatibleImageGenerator(
            base_url=status.base_url or "",
            model=status.model or "",
            api_key=secrets[IMAGE_SECRET_NAME],
        )
    return None


@dataclass(frozen=True)
class OpenAICompatibleImageGenerator:
    base_url: str
    model: str
    api_key: str
    provider: str = "cloud_openai_compatible"

    def generate(self, prompt: str) -> bytes:
        response = httpx.post(
            f"{self.base_url.rstrip('/')}/images/generations",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "prompt": prompt, "size": "1024x1024", "response_format": "b64_json"},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        item = (payload.get("data") or [{}])[0]
        if item.get("b64_json"):
            return base64.b64decode(item["b64_json"])
        if item.get("url"):
            image_response = httpx.get(item["url"], timeout=60)
            image_response.raise_for_status()
            return image_response.content
        raise RuntimeError("Image provider returned no image data.")


def default_image_config(provider: str) -> dict[str, str]:
    if provider == "local_comfyui":
        return {"provider": "local_comfyui", "model": "", "base_url": DEFAULT_COMFYUI_BASE_URL}
    if provider == "cloud_openai_compatible":
        return {"provider": "cloud_openai_compatible", "model": "", "base_url": ""}
    return {"provider": "local_card", "model": "", "base_url": ""}


def load_image_secrets(root: str | Path | None = None) -> dict[str, str]:
    secrets = read_secret_file(dreamloop_dir(root) / "secrets.env")
    if os.getenv(IMAGE_SECRET_NAME):
        secrets[IMAGE_SECRET_NAME] = os.environ[IMAGE_SECRET_NAME]
    return secrets


def _read_config_payload(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}
