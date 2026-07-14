# Changelog

## Unreleased

- Bump the next release target to v0.2.0.
- Add Markdown export with Obsidian-friendly frontmatter via `dreamloop export --format markdown`.
- Export one `.md` file per dream plus an `_index.md` wikilink index under `.dreamloop/exports/dreamloop-export-markdown-YYYY-MM-DD/`.
- Add Docker and docker-compose one-command demo.
- Add GHCR publish workflow.
- Add `dreamloop demo --language zh --if-empty`.
- Add symbol relationship network graph on Patterns.
- Add `/api/insights/symbol-graph` endpoint.
- Add `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md`.
- Extract database, schema, demo data, importers, visuals, and graph modules, reducing `core.py` from 1074 to 751 lines.
- Add 5 Chinese demo samples with full reflections.
- Fix N+1 query problem in dashboard rendering: batch-load dreams with analysis in 3 queries instead of 10N+.
- Fix ICS import path traversal: reject paths outside the `.dreamloop/` data directory.
- Constrain `FeedbackCreate.rating` to `Literal["resonates", "not_accurate", "unsure"]`.
- Remove unused `LegacyResponsesAnalyzer` class.
- Add `--no-cache-dir` to Dockerfile `pip install` to reduce image size.

## v0.1.2 - 2026-06-14

DreamLoop's second patch tightens first-screen quality and introduces an explicit image-generation path:

- Reduced Dashboard hero title weight and spacing so the screenshot screen no longer visually overflows.
- Added subtle page-enter transitions and sidebar active-state motion, with `prefers-reduced-motion` support.
- Fixed the language toggle mojibake so Chinese renders as `中文`.
- Added optional image provider configuration: local visual cards by default, ComfyUI readiness checks, and a custom OpenAI-compatible cloud image endpoint.
- Added `dream_images` storage and `.dreamloop/assets/images/` output for generated image files.
- Added dream image web/API routes and `dreamloop image test`.
- Gallery now prefers real generated images and falls back to local visual memory cards.

## v0.1.1 - 2026-06-14

This patch focuses on first-impression reliability and the trust loop around interpretation quality:

- Fixed Dashboard hero overflow in English and Chinese so the README-ready screenshot no longer breaks at common desktop widths.
- Added `dreamloop doctor` for local setup checks covering data directory, SQLite, AI provider, Ollama/custom endpoints, and hidden key status.
- Added `dreamloop demo` to seed sample local dreams, mock analyses, and visual memory cards without requiring cloud AI.
- Added local feedback on interpretation reports: resonates, not accurate, and unsure.
- Added a `user_feedback` SQLite table plus API endpoints for feedback capture and summary.
- Added high-resonance theme summaries to Patterns.
- Added Settings privacy audit copy explaining what may leave the machine for cloud AI, weather sync, and future sync features.

## v0.1.0 - 2026-06-13

DreamLoop's first public release turns the project into a usable local-first dream journal:

- Six-page Web loop: Dashboard, Log, Detail, Patterns, Gallery, and Settings.
- Draft-first dream capture: analyze first, then save locally when the result looks useful.
- Detailed interpretation reports with optional reflection prompts, multiple hypotheses, reality-grounded questions, and backward-compatible structured output.
- Local SQLite storage under `.dreamloop/`, automatically ignored by Git.
- AI providers: Ollama, DeepSeek, OpenAI, custom OpenAI-compatible endpoints, and capture-only mode.
- Multilingual UI and per-language AI analysis for English and Chinese.
- Clickable pattern calendar, symbol trends, theme trends, local gallery cards, and detail pages.
- CLI entry point: `dreamloop init`, `dreamloop add`, `dreamloop web`, AI provider commands, imports, weather sync, and export.
- English and Chinese README files with privacy-first positioning and Obsidian-oriented roadmap.

Release assets:

- Real dashboard screenshot in `docs/assets/dashboard-screenshot.png`.
- Social preview image in `docs/assets/social-preview.png`.
- Reproducible demo recording guide in `docs/demo-recording.md`.
