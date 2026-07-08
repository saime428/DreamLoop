# DreamLoop Project Context

Last maintained: 2026-07-08

## What This Project Is

DreamLoop is a local-first AI dream journal. The core promise is private capture, SQLite storage in `.dreamloop/`, optional AI analysis, and optional visual memory/image generation. The web product loop is Dashboard -> Log -> Detail -> Patterns -> Gallery -> Settings.

## How To Work On It

- Install/dev sync: `uv sync --extra dev`
- Run tests: `uv run --extra dev python -m pytest`
- Start app: `uv run dreamloop web`
- Alternate Windows port: `uv run dreamloop web --port 18080`
- Build package: `uv build`
- One-command demo: `docker compose up` then open `http://localhost:8765`

## Main Files

- `src/dreamloop/core.py`: DreamLoop public API, dream CRUD, analysis storage, feedback, trends, symbol graph entrypoint, image records.
- `src/dreamloop/analysis.py`: AI provider config, secret loading, OpenAI-compatible analyzers, prompt/JSON normalization.
- `src/dreamloop/database.py`: SQLite connection, schema creation, and migrations.
- `src/dreamloop/demo_data.py`: English and Chinese demo dreams with precomputed analysis/reflections.
- `src/dreamloop/graph.py`: stdlib symbol co-occurrence graph generation.
- `src/dreamloop/images.py`: image provider config and optional cloud image generation; ComfyUI is only a readiness placeholder until a workflow exists.
- `src/dreamloop/importers.py`: calendar parsing and Open-Meteo helpers.
- `src/dreamloop/schema.py`: FastAPI request models.
- `src/dreamloop/visuals.py`: visual-memory normalization, image URLs, and prompt helpers.
- `src/dreamloop/cli.py`: Typer commands for init/add/list/show/analyze/doctor/demo/web/export/provider config.
- `src/dreamloop/web.py`: FastAPI app, Jinja routes, JSON API, English/Chinese UI strings.
- `src/dreamloop/export_markdown.py`: Markdown/Obsidian-style export.
- `src/dreamloop/templates/` and `src/dreamloop/static/`: web UI.
- `tests/`: focused coverage for core workflow, API/web, CLI, AI/image config, packaging, README positioning, Markdown export.

## Product And Safety Rules

- Keep local-first and privacy-first behavior. Dream text should stay local unless the user explicitly configures a cloud provider.
- Never print or render secrets. Keys belong in `.dreamloop/secrets.env`, and `.dreamloop/` must stay ignored.
- Prefer Ollama/local paths by default. DeepSeek/OpenAI/custom endpoints are opt-in.
- Image generation is opt-in. Local visual cards must work without any image API.
- Keep the project small and forkable; reuse existing helpers before adding new dependencies or abstractions.
- Demo data should be safe to seed repeatedly through `dreamloop demo --if-empty`.
- Docker runtime installs the package with `pip install /app`; `uv` remains a dev tool, not a container runtime dependency.

## Current Growth-Maintenance Slice

- README and README.zh-CN now lead with demo analysis output, a Detail screenshot, a shorter quick start, Docker, Markdown export, and a v0.2 roadmap focused on Markdown export, Docker, symbol graph, and GHCR.
- `dreamloop demo` supports `--language en|zh` and `--if-empty`.
- The Patterns page includes an inline-SVG symbol relationship graph, with an empty state when no analyzed dreams exist.
- Docker files and a GHCR release/manual workflow were added. Main CI intentionally stays fast and does not build Docker images.
- Open-source signals added: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and a repo label target of `good first issue`.

## Current Worktree Note

As of 2026-07-04, `git status --short` showed existing uncommitted work before this context file was added:

- Modified: `.gitignore`, `CHANGELOG.md`, `src/dreamloop/cli.py`
- Untracked: `src/dreamloop/export_markdown.py`, `tests/test_export_markdown.py`

Treat those as user/previous-agent changes. Do not revert them unless explicitly asked.

As of 2026-07-08, this maintenance run is on branch `codex/growth-maintenance`. The 2026-07-04 files above may still appear alongside this run's new edits; review before staging so unrelated previous-agent work is not accidentally mixed into a commit.
