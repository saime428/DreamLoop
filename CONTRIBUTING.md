# Contributing to DreamLoop

DreamLoop is intentionally small, local-first, and privacy-focused. Contributions should keep that shape.

## Local Setup

```bash
git clone https://github.com/saime428/DreamLoop.git
cd DreamLoop
uv sync --extra dev
uv run dreamloop init
uv run dreamloop demo
uv run dreamloop web
```

Run tests before opening a PR:

```bash
uv run --extra dev pytest
```

## Good First Issues

- Improve local model prompts.
- Add `.ics` fixtures.
- Polish dashboard accessibility.
- Expand Markdown/Obsidian export.
- Improve terminal demo recording automation.

## Privacy Rules

- Do not commit `.dreamloop/`.
- Do not print or render API keys.
- Keep cloud AI and image generation explicit opt-in paths.
- Demo and README assets should use sample data, not private dreams.

## PR Checklist

- Tests pass with `uv run --extra dev pytest`.
- README or docs are updated for user-facing changes.
- New behavior has a focused test.
- No secrets, generated local data, or private dream text are committed.
