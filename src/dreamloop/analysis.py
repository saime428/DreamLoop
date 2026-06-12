from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol


class Analyzer(Protocol):
    def analyze(self, content: str) -> dict[str, Any]:
        """Return structured dream analysis for a dream text."""


@dataclass(frozen=True)
class StaticAnalyzer:
    result: dict[str, Any]

    def analyze(self, content: str) -> dict[str, Any]:
        return dict(self.result)


class OpenAIAnalyzer:
    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        self.model = model

    def analyze(self, content: str) -> dict[str, Any]:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install dreamloop[ai] to enable OpenAI analysis.") from exc

        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        client = OpenAI()
        response = client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Analyze dreams as structured data. Return only JSON with "
                        "emotional_tone, symbols, themes, summary, and confidence."
                    ),
                },
                {"role": "user", "content": content},
            ],
        )
        text = response.output_text
        return json.loads(text)


def ai_is_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


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
