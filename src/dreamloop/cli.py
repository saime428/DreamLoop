from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Annotated

import typer

from .analysis import ai_is_configured
from .core import DreamLoop

app = typer.Typer(help="Local-first AI dream journal.")
import_app = typer.Typer(help="Import local data.")
weather_app = typer.Typer(help="Sync local context such as weather.")
app.add_typer(import_app, name="import")
app.add_typer(weather_app, name="weather")


@app.command()
def init() -> None:
    loop = DreamLoop()
    loop.init()
    typer.echo(f"DreamLoop initialized at {loop.data_dir}")


@app.command()
def add(
    content: Annotated[str, typer.Argument(help="Dream text to save.")],
    tag: Annotated[list[str] | None, typer.Option("--tag", "-t")] = None,
    mood: Annotated[str | None, typer.Option("--mood", "-m")] = None,
    dreamed_on: Annotated[str | None, typer.Option("--date", help="Dream date as YYYY-MM-DD.")] = None,
) -> None:
    parsed_date = date.fromisoformat(dreamed_on) if dreamed_on else None
    dream_id = DreamLoop().add_dream(content, tags=tag or [], mood=mood, dreamed_on=parsed_date)
    typer.echo(f"Saved dream #{dream_id} (analysis pending)")


@app.command("list")
def list_dreams() -> None:
    dreams = DreamLoop().list_dreams()
    for dream in dreams:
        tags = ", ".join(dream["tags"]) or "no tags"
        mood = dream["manual_mood"] or "no mood"
        typer.echo(f"#{dream['id']} {dream['dreamed_on']} [{mood}] {tags} - {dream['content']}")


@app.command()
def show(dream_id: int) -> None:
    dream = DreamLoop().get_dream(dream_id)
    typer.echo(json.dumps(dream, ensure_ascii=False, indent=2))


@app.command()
def analyze(pending: Annotated[bool, typer.Option("--pending")] = False) -> None:
    if not pending:
        typer.echo("Use --pending to analyze queued dreams.")
        raise typer.Exit(code=1)
    if not ai_is_configured():
        typer.echo("AI not configured. Set OPENAI_API_KEY or keep using DreamLoop as a local journal.")
        return
    analyzed = DreamLoop().analyze_pending()
    typer.echo(f"Analyzed {len(analyzed)} pending dream(s).")


@app.command()
def web(host: str = "127.0.0.1", port: int = 8765) -> None:
    import uvicorn

    uvicorn.run("dreamloop.web:create_app", factory=True, host=host, port=port)


@app.command()
def export() -> None:
    loop = DreamLoop()
    out = loop.data_dir / "exports" / f"dreamloop-export-{date.today().isoformat()}.json"
    loop.init()
    out.write_text(json.dumps(loop.list_dreams(), ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(f"Exported dreams to {out}")


@import_app.command("ics")
def import_ics(path: Path) -> None:
    count = DreamLoop().import_ics(path)
    typer.echo(f"Imported {count} calendar event(s).")


@weather_app.command("sync")
def weather_sync(lat: float, lon: float) -> None:
    count = DreamLoop().sync_weather(lat, lon)
    typer.echo(f"Synced {count} weather day(s).")
