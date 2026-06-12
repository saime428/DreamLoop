from __future__ import annotations

import tomllib
from pathlib import Path

from dreamloop.cli import main


ROOT = Path(__file__).resolve().parents[1]


def test_project_has_pipx_ready_package_structure():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert (ROOT / "src" / "dreamloop" / "__init__.py").exists()
    assert (ROOT / "src" / "dreamloop" / "templates" / "index.html").exists()
    assert (ROOT / "src" / "dreamloop" / "templates" / "detail.html").exists()
    assert (ROOT / "src" / "dreamloop" / "static" / "style.css").exists()
    assert pyproject["project"]["scripts"]["dreamloop"] == "dreamloop.cli:main"
    assert callable(main)


def test_ci_installs_checks_console_script_and_package_metadata():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "uv sync --extra dev" in workflow
    assert "uv run dreamloop --help" in workflow
    assert "uv run --extra dev pytest" in workflow
    assert "uv build" in workflow
    assert "uv run --extra dev twine check dist/*" in workflow


def test_publish_workflow_uses_trusted_publishing_without_secrets():
    workflow = (ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")

    assert "id-token: write" in workflow
    assert "pypa/gh-action-pypi-publish@release/v1" in workflow
    assert "uv run --extra dev twine check dist/*" in workflow
    assert "password" not in workflow.lower()
    assert "token" not in workflow.lower().replace("id-token", "")
