from __future__ import annotations

from pathlib import Path


def test_readme_leads_with_local_first_positioning_and_fast_start():
    text = Path("README.md").read_text(encoding="utf-8")
    first_screen = text[:1400]

    assert "docs/assets/hero-dashboard.svg" in first_screen
    assert "[English](README.md) | [中文](README.zh-CN.md)" in first_screen
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


def test_chinese_readme_covers_local_first_loop_and_providers():
    text = Path("README.zh-CN.md").read_text(encoding="utf-8")

    assert "DreamLoop" in text
    assert "本地优先" in text
    assert "六页闭环" in text
    assert "Ollama" in text
    assert "DeepSeek" in text
    assert "Custom OpenAI-compatible" in text
    assert "隐私承诺" in text
    assert "pipx install dreamloop" in text
    assert "sk-" not in text


def test_hero_asset_matches_dreamscape_dashboard_direction():
    svg = Path("docs/assets/hero-dashboard.svg").read_text(encoding="utf-8")

    assert "Good night, explorer" in svg
    assert "Dream constellation" in svg
    assert "Mood spectrum" in svg
    assert "AI Insight" in svg
    assert "Dreamscape log" in svg
