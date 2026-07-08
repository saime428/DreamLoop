from __future__ import annotations

from pathlib import Path


def test_readme_leads_with_local_first_positioning_and_fast_start():
    text = Path("README.md").read_text(encoding="utf-8")
    first_screen = text[:2400]

    assert "docs/assets/detail-analysis-screenshot.png" in first_screen
    assert "docs/assets/dashboard-screenshot.png" in first_screen
    assert "docs/assets/cli-demo.gif" in text
    assert "actions/workflows/ci.yml/badge.svg" in first_screen
    assert "img.shields.io/pypi/v/dreamloop" in first_screen
    assert "img.shields.io/pypi/pyversions/dreamloop" in first_screen
    assert "[English](README.md) | [中文](README.zh-CN.md)" in first_screen
    assert "Your dreams have patterns. DreamLoop finds them locally." in first_screen
    assert "What You Get" in text
    assert "Private local journal" in text
    assert "AI interpretation" in text
    assert "Visual memory" in text
    assert "Runs fully local. Your data never leaves your machine." in first_screen
    assert "Free with Ollama." in first_screen
    assert "CLI-first" in first_screen
    assert "git clone https://github.com/saime428/DreamLoop.git" in first_screen
    assert "uv sync --extra dev" in first_screen
    assert "uv run dreamloop init" in first_screen
    assert "pipx install dreamloop" in first_screen
    assert "dreamloop export --format markdown" in text
    assert "Advanced Setup" in text
    assert "Future release assets" not in text
    assert "add terminal demo assets" not in text
    assert "cli-demo.cast" not in text


def test_readme_has_privacy_and_obsidian_roadmap_without_secret():
    text = Path("README.md").read_text(encoding="utf-8")

    assert "Privacy Promise" in text
    assert "Status" in text
    assert "Available now" in text
    assert "Next" in text
    assert "ghcr.io/saime428/dreamloop" in text
    assert "named volume" in text
    assert "secrets.env" in text
    assert "sk-" not in text


def test_chinese_readme_covers_local_first_loop_and_providers():
    text = Path("README.zh-CN.md").read_text(encoding="utf-8")
    first_screen = text[:2400]

    assert "DreamLoop" in text
    assert "docs/assets/detail-analysis-screenshot.png" in first_screen
    assert "你能得到什么" in text
    assert "本地优先" in text
    assert "六页闭环" in text
    assert "Ollama" in text
    assert "DeepSeek" in text
    assert "Custom OpenAI-compatible" in text
    assert "隐私承诺" in text
    assert "高级设置" in text
    assert "当前可用" in text
    assert "named volume" in text
    assert "docs/assets/cli-demo.gif" in text
    assert "img.shields.io/pypi/v/dreamloop" in text
    assert "img.shields.io/pypi/pyversions/dreamloop" in text
    assert "git clone https://github.com/saime428/DreamLoop.git" in first_screen
    assert "uv run dreamloop web" in first_screen
    assert "pipx install dreamloop" in text
    assert "pipx install dreamloop" in first_screen
    assert "dreamloop export --format markdown" in text
    assert "sk-" not in text


def test_release_assets_and_docs_exist():
    dashboard = Path("docs/assets/dashboard-screenshot.png")
    detail = Path("docs/assets/detail-analysis-screenshot.png")
    cli_demo = Path("docs/assets/cli-demo.gif")
    social = Path("docs/assets/social-preview.png")
    demo_script = Path("docs/demo-recording.md")
    changelog = Path("CHANGELOG.md")
    workflow = Path(".github/workflows/ci.yml")

    assert dashboard.exists()
    assert dashboard.stat().st_size > 10_000
    assert detail.exists()
    assert detail.stat().st_size > 10_000
    assert cli_demo.exists()
    assert cli_demo.stat().st_size > 5_000
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


def test_page_background_layer_sits_behind_content_but_above_page_floor():
    css = Path("src/dreamloop/static/style.css").read_text(encoding="utf-8")

    assert ".dashboard::before" in css
    assert ".dashboard > *" in css
    assert ".dashboard::before {\n  z-index: 0;" in css
    assert ".dashboard::after {\n  z-index: 0;" in css
    assert "--page-bg-opacity: 1" in css


def test_dashboard_css_uses_bedside_amber_tokens_without_remote_fonts():
    css = Path("src/dreamloop/static/style.css").read_text(encoding="utf-8")

    assert "--ink: #1a1714" in css
    assert "--paper: #2a2520" in css
    assert "--amber: #d4a574" in css
    assert "--sage: #8ba87a" in css
    assert "--rust: #c47a5a" in css
    assert "fonts.googleapis" not in css
    assert "@import url(" not in css
    assert "--violet" not in css
    assert "--cyan" not in css
    assert "--rose" not in css


def test_frontend_removes_neon_starfield_treatment():
    css = Path("src/dreamloop/static/style.css").read_text(encoding="utf-8")
    index = Path("src/dreamloop/templates/index.html").read_text(encoding="utf-8")
    detail = Path("src/dreamloop/templates/detail.html").read_text(encoding="utf-8")

    assert "body::before" not in css
    assert ".star-field" not in css
    assert "star-field" not in index
    assert "star-field" not in detail
    assert "#8e63ff" not in css
    assert "#52e7d2" not in css
    assert "#ff6ba8" not in css
