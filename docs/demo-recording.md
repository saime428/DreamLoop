# DreamLoop Demo Recording Guide

This guide records a short, reproducible demo for README and social assets. It is intentionally scriptable so maintainers can regenerate a GIF or cast without inventing a flow.

## Setup

```bash
git clone https://github.com/saime428/DreamLoop.git
cd DreamLoop
uv sync --extra dev
uv run dreamloop init
uv run dreamloop demo --if-empty
```

Expected output:

```text
DreamLoop initialized at .dreamloop
Added 3 demo dream(s): #1, #2, #3
```

Use `uv run dreamloop demo --if-empty --language zh` when recording the Chinese flow. The `--if-empty` flag keeps repeated recording runs from duplicating sample dreams.

## CLI capture

```bash
uv run dreamloop list
uv run dreamloop export --format markdown
```

Show that DreamLoop seeds local sample dreams under `.dreamloop/dreamloop.sqlite3`, keeps mock analysis local, and can export Obsidian-friendly Markdown without a cloud model.

## Web loop

```bash
uv run dreamloop web --host 127.0.0.1 --port 8765
```

Open:

```text
http://127.0.0.1:8765/?lang=en
```

Record these beats:

1. Dashboard shows the local-first overview, AI Insight, heatmap, stats, and recent dreams.
2. Log page shows the dream input, optional reflection prompts, and saved demo timeline.
3. Detail page shows dream text, structured analysis, feedback, raw JSON foldout, and visual-memory action.
4. Patterns page shows clickable calendar, symbols, themes, and the symbol network that filters back to Log.
5. Gallery shows local visual memory cards.
6. Settings page shows Ollama, DeepSeek, OpenAI, Custom OpenAI-compatible, and None without rendering secrets.

## Optional Ollama analysis

If Ollama is installed:

```bash
ollama pull qwen3:8b
uv run dreamloop ai use ollama --model qwen3:8b
uv run dreamloop ai test
```

Then record:

```bash
uv run dreamloop analyze --pending
```

Expected result: pending dreams receive structured analysis while the original text stays local.

## Suggested GIF framing

- 1280x720 or 1440x900 viewport.
- Keep the first 10 seconds focused on Dashboard -> Log -> Detail.
- End on Settings to reinforce the privacy promise.
- Do not show API keys, terminal history containing secrets, or `.dreamloop/secrets.env`.

## Current CLI GIF asset

The committed `docs/assets/cli-demo.gif` is a lightweight terminal-style asset generated with `ffmpeg`, using the no-cloud demo path:

```bash
pipx install dreamloop
dreamloop init
dreamloop demo
dreamloop doctor
dreamloop web
```

It is intentionally small and dependency-light. If you regenerate it, keep the same promise: no secrets, no cloud model calls, and a visible local-first flow.
