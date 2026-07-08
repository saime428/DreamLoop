from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class DreamCreate(BaseModel):
    content: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    manual_mood: str | None = None
    dreamed_on: date | None = None
    reflections: dict[str, str] = Field(default_factory=dict)


class WeatherSync(BaseModel):
    lat: float
    lon: float


class FeedbackCreate(BaseModel):
    interpretation_index: int = Field(ge=0)
    rating: str
    reason: str = ""
