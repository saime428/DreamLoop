from __future__ import annotations

from pathlib import Path


def test_readme_leads_with_local_first_positioning_and_fast_start():
    text = Path("README.md").read_text(encoding="utf-8")
    first_screen = text[:1800]

    assert "docs/assets/dashboard-screenshot.png" in first_screen
    assert "actions/workflows/ci.yml/badge.svg" in first_screen
    assert "[English](README.md) | [中文](README.zh-CN.md)" in first_screen
    assert "Your dreams have patterns. DreamLoop finds them locally." in first_screen
    assert "Runs fully local. Your data never leaves your machine." in first_screen
    assert "Free with Ollama." in first_screen
    assert "CLI-first" in first_screen
    assert "git clone https://github.com/saime428/DreamLoop.git" in first_screen
    assert "uv sync --extra dev" in first_screen
    assert "uv run dreamloop init" in first_screen
    assert "pipx install dreamloop" in first_screen
    assert "Future release assets" not in text


def test_readme_has_privacy_and_obsidian_roadmap_without_secret():
    text = Path("README.md").read_text(encoding="utf-8")

    assert "Privacy Promise" in text
    assert "Obsidian" in text
    assert "v0.3" in text
    assert "secrets.env" in text
    assert "sk-" not in text


def test_chinese_readme_covers_local_first_loop_and_providers():
    text = Path("README.zh-CN.md").read_text(encoding="utf-8")
    first_screen = text[:1800]

    assert "DreamLoop" in text
    assert "本地优先" in text
    assert "六页闭环" in text
    assert "Ollama" in text
    assert "DeepSeek" in text
    assert "Custom OpenAI-compatible" in text
    assert "隐私承诺" in text
    assert "git clone https://github.com/saime428/DreamLoop.git" in first_screen
    assert "uv run dreamloop web" in first_screen
    assert "pipx install dreamloop" in text
    assert "pipx install dreamloop" in first_screen
    assert "sk-" not in text


def test_release_assets_and_docs_exist():
    dashboard = Path("docs/assets/dashboard-screenshot.png")
    social = Path("docs/assets/social-preview.png")
    demo_script = Path("docs/demo-recording.md")
    changelog = Path("CHANGELOG.md")
    workflow = Path(".github/workflows/ci.yml")

    assert dashboard.exists()
    assert dashboard.stat().st_size > 10_000
    assert social.exists()
    assert social.stat().st_size > 10_000
    assert "dreamloop init" in demo_script.read_text(encoding="utf-8")
    assert "v0.1.0" in changelog.read_text(encoding="utf-8")
    assert "uv run --extra dev pytest" in workflow.read_text(encoding="utf-8")


def test_dashboard_css_has_subtle_transitions_and_reduced_motion():
    css = Path("src/dreamloop/static/style.css").read_text(encoding="utf-8")

    assert "@keyframes page-soft-enter" in css
    assert "prefers-reduced-motion: reduce" in css
    assert ".dashboard-hero h2" in css
    assert "clamp(20px, 2vw, 28px)" in css
