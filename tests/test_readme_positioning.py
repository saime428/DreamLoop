from __future__ import annotations

import hashlib
import re
from pathlib import Path


def test_readme_leads_with_local_first_positioning_and_fast_start():
    text = Path("README.md").read_text(encoding="utf-8")
    first_screen = text[:2400]

    assert "docs/assets/detail-analysis-screenshot.jpg" in first_screen
    assert "docs/assets/dashboard-screenshot.jpg" in first_screen
    assert "docs/assets/settings-privacy-screenshot.jpg" in text
    assert "docs/assets/gallery-screenshot.jpg" in text
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
    assert "docs/assets/detail-analysis-screenshot-zh.jpg" in first_screen
    assert "docs/assets/dashboard-screenshot-zh.jpg" in first_screen
    assert "docs/assets/settings-privacy-screenshot-zh.jpg" in text
    assert "docs/assets/gallery-screenshot-zh.jpg" in text
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
    screenshots = [
        Path("docs/assets/dashboard-screenshot.jpg"),
        Path("docs/assets/detail-analysis-screenshot.jpg"),
        Path("docs/assets/gallery-screenshot.jpg"),
        Path("docs/assets/settings-privacy-screenshot.jpg"),
        Path("docs/assets/dashboard-screenshot-zh.jpg"),
        Path("docs/assets/detail-analysis-screenshot-zh.jpg"),
        Path("docs/assets/gallery-screenshot-zh.jpg"),
        Path("docs/assets/settings-privacy-screenshot-zh.jpg"),
    ]
    cli_demo = Path("docs/assets/cli-demo.gif")
    social = Path("docs/assets/social-preview.png")
    demo_script = Path("docs/demo-recording.md")
    changelog = Path("CHANGELOG.md")
    workflow = Path(".github/workflows/ci.yml")

    for screenshot in screenshots:
        assert screenshot.exists()
        assert screenshot.stat().st_size > 30_000
        assert screenshot.read_bytes().startswith(b"\xff\xd8")
    assert cli_demo.exists()
    assert cli_demo.stat().st_size > 5_000
    assert social.exists()
    assert social.stat().st_size > 10_000
    assert "dreamloop init" in demo_script.read_text(encoding="utf-8")
    assert "v0.1.0" in changelog.read_text(encoding="utf-8")
    assert "uv run --extra dev pytest" in workflow.read_text(encoding="utf-8")


def test_dashboard_css_has_subtle_transitions_and_reduced_motion():
    css = Path("src/dreamloop/static/style.css").read_text(encoding="utf-8")
    index = Path("src/dreamloop/templates/index.html").read_text(encoding="utf-8")
    web = Path("src/dreamloop/web.py").read_text(encoding="utf-8")

    assert "@keyframes page-soft-enter" in css
    assert "@keyframes dl-breathe" in css
    assert "prefers-reduced-motion: reduce" in css
    assert "font-variant-numeric: tabular-nums" in css
    assert "::-webkit-scrollbar-thumb" in css
    assert "backdrop-filter" not in css
    assert "translateY(-2px)" not in css
    assert ".constellation-map > .empty-state" in css
    assert "minmax(38px, 1fr)" not in css
    assert "align-content: start" in css
    assert 'class="empty-state empty-state-illustrated"' in index
    assert index.count('class="empty-state-icon"') == 3
    assert "v0.1" not in web
    assert ".dashboard-hero h2" in css
    assert "font-size: clamp(" not in css


def test_page_background_layer_sits_behind_content_but_above_page_floor():
    css = Path("src/dreamloop/static/style.css").read_text(encoding="utf-8")

    assert ".dashboard::before" in css
    assert ".dashboard > *" in css
    assert ".dashboard::before {\n  z-index: 0;" in css
    assert ".dashboard::after {\n  z-index: 0;" in css
    assert "--page-bg-opacity: 1" in css


def test_dashboard_css_uses_reference_violet_tokens_without_remote_fonts():
    css = Path("src/dreamloop/static/style.css").read_text(encoding="utf-8")

    assert "--ink: #080711" in css
    assert "--paper: #110e24" in css
    assert "--amber: #e2c181" in css
    assert "--sage: #a7d18d" in css
    assert "--rust: #d07d7d" in css
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


def test_frontend_prioritizes_capture_and_bundles_chinese_fonts():
    css = Path("src/dreamloop/static/style.css").read_text(encoding="utf-8")
    index = Path("src/dreamloop/templates/index.html").read_text(encoding="utf-8")
    detail = Path("src/dreamloop/templates/detail.html").read_text(encoding="utf-8")
    font_dir = Path("src/dreamloop/static/fonts/noto")

    assert index.index("data-loading-button") < index.index('class="reflection-disclosure"')
    assert "autofocus" not in index
    assert 'aria-current="page"' in index
    assert 'aria-current="page"' in detail
    assert 'font-family: "Noto Sans SC"' in css
    assert 'font-family: "Noto Serif SC"' in css
    assert "grid-template-columns: minmax(0, 1fr) 280px" in css
    assert (font_dir / "NotoSansSC-DreamLoop.woff2").stat().st_size == 7_782_072
    assert (font_dir / "NotoSerifSC-DreamLoop.woff2").stat().st_size == 11_032_420
    assert (font_dir / "OFL.txt").exists()
    assert (font_dir / "OFL-NotoSerifSC.txt").exists()
    assert not Path("src/dreamloop/static/fonts/aptos").exists()
    assert Path("src/dreamloop/static/fonts/cascadia/OFL.txt").exists()


def test_frontend_uses_pinned_full_cmap_fonts_and_fixed_type_scale():
    css = Path("src/dreamloop/static/style.css").read_text(encoding="utf-8")
    font_dir = Path("src/dreamloop/static/fonts/noto")
    expected_hashes = {
        "NotoSansSC-DreamLoop.woff2": "aef8c34277afad81ecd0227138a830263c0caea65b7aea66d1195395f097b55a",
        "NotoSerifSC-DreamLoop.woff2": "4ee9b0921ec9bd3f8b04587c7bc66c62731045e89d74eec054f37fc7a2d26383",
        "OFL.txt": "1c05c68c34f9708415aada51f17e1b0092d2cea709bf4a94cd38114f9e73d7d9",
        "OFL-NotoSerifSC.txt": "5e0da210fb04058a8c0087985d2d456b931c2579811a49655721d3cf0c36b6d6",
    }

    for name, expected in expected_hashes.items():
        digest = hashlib.sha256((font_dir / name).read_bytes()).hexdigest()
        assert digest == expected

    assert '--font-display: "Noto Serif SC", serif' in css
    assert '--font-body: "Noto Sans SC", sans-serif' in css
    assert '--font-mono: "Cascadia Mono", "Noto Sans SC", monospace' in css
    assert css.count("?v=20260714-full-cmap") == 2
    assert not re.search(r"font-size:\s*clamp\([^;]*vw", css)
    assert "font-size: 10px" not in css
    assert "font-size: 11px" not in css
    assert "letter-spacing: 0.08em" not in css
    assert "grid-template-columns: minmax(0, 0.85fr) minmax(72px, 1fr) 28px" in css
    visual_rule = css.split(".local-visual-card strong {", 1)[1].split("}", 1)[0]
    assert "font-size: 24px" in visual_rule
    assert "line-height: 1.25" in visual_rule
    assert "overflow-wrap: anywhere" in visual_rule
