# Changelog

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
