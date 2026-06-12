from __future__ import annotations

from pathlib import Path


def test_readme_leads_with_local_first_positioning_and_fast_start():
    text = Path("README.md").read_text(encoding="utf-8")
    first_screen = text[:1400]

    assert "docs/assets/hero-dashboard.svg" in first_screen
    assert "Your dreams have patterns. DreamLoop finds them locally." in first_screen
    assert "Runs fully local. Your data never leaves your machine." in first_screen
    assert "Free with Ollama." in first_screen
    assert "CLI-first" in first_screen
    assert "pipx install dreamloop" in first_screen
    assert "dreamloop init" in first_screen
    assert "dreamloop add" in first_screen


def test_readme_has_privacy_and_obsidian_roadmap_without_secret():
    text = Path("README.md").read_text(encoding="utf-8")

    assert "Privacy Promise" in text
    assert "Obsidian" in text
    assert "v0.3" in text
    assert "secrets.env" in text
    assert "sk-" not in text
