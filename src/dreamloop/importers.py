from __future__ import annotations

import json
from datetime import date
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


def value_at(payload: dict[str, Any], key: str, index: int) -> Any:
    values = payload.get(key, [])
    return values[index] if index < len(values) else None


def fetch_open_meteo(lat: float, lon: float) -> dict[str, Any]:
    query = urlencode(
        {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
            "timezone": "auto",
            "past_days": 30,
            "forecast_days": 1,
        }
    )
    with urlopen(f"https://api.open-meteo.com/v1/forecast?{query}", timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_ics(text: str) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT" and current is not None:
            if "starts_on" in current:
                events.append(current)
            current = None
        elif current is not None and ":" in line:
            key, value = line.split(":", 1)
            upper_key = key.upper()
            if upper_key == "UID":
                current["uid"] = value
            elif upper_key.startswith("DTSTART"):
                current["starts_on"] = parse_ics_date(value)
            elif upper_key.startswith("DTEND"):
                current["ends_on"] = parse_ics_date(value)
            elif upper_key == "SUMMARY":
                current["summary"] = value.replace("\\,", ",")
    return events


def parse_ics_date(value: str) -> str:
    if "T" in value:
        return date.fromisoformat(value[:8]).isoformat()
    return date.fromisoformat(f"{value[:4]}-{value[4:6]}-{value[6:8]}").isoformat()
