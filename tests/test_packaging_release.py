from __future__ import annotations

import tomllib
from pathlib import Path

from dreamloop import __version__
from dreamloop.cli import main
from dreamloop.web import create_app


ROOT = Path(__file__).resolve().parents[1]


def test_project_has_pipx_ready_package_structure():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert (ROOT / "src" / "dreamloop" / "__init__.py").exists()
    assert (ROOT / "src" / "dreamloop" / "templates" / "index.html").exists()
    assert (ROOT / "src" / "dreamloop" / "templates" / "detail.html").exists()
    assert (ROOT / "src" / "dreamloop" / "static" / "style.css").exists()
    assert pyproject["project"]["scripts"]["dreamloop"] == "dreamloop.cli:main"
    assert callable(main)


def test_project_version_is_consistent_across_package_and_web_app():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    app = create_app(ROOT)

    assert pyproject["project"]["version"] == "0.2.0"
    assert __version__ == pyproject["project"]["version"]
    assert app.version == pyproject["project"]["version"]


def test_ci_installs_checks_console_script_and_package_metadata():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "uv sync --extra dev" in workflow
    assert "uv run dreamloop --help" in workflow
    assert "uv run --extra dev pytest" in workflow
    assert "uv build" in workflow
    assert "uv run --extra dev twine check dist/*" in workflow


def test_ci_runs_clean_wheel_smoke_test_for_runtime_assets():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "Smoke test installed wheel" in workflow
    assert "pip install dist/*.whl" in workflow
    assert "dreamloop --help" in workflow
    assert "templates" in workflow
    assert "static" in workflow
    assert "create_app().title == \"DreamLoop\"" in workflow


def test_publish_workflow_uses_trusted_publishing_without_secrets():
    workflow = (ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")

    assert "id-token: write" in workflow
    assert "pypa/gh-action-pypi-publish@release/v1" in workflow
    assert "uv run --extra dev twine check dist/*" in workflow
    assert "password" not in workflow.lower()
    assert "token" not in workflow.lower().replace("id-token", "")


def test_docker_files_support_one_command_demo_without_uv_runtime():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

    assert "FROM python:3.11-slim" in dockerfile
    assert "pip install /app" in dockerfile
    assert "pip install uv" not in dockerfile
    assert "dreamloop demo --if-empty" in compose
    assert "dreamloop web --host 0.0.0.0 --port 8765" in compose
    assert ".dreamloop/" in dockerignore
    assert ".git/" in dockerignore
    assert ".venv/" in dockerignore
    assert "dist/" in dockerignore


def test_docker_publish_workflow_pushes_lowercase_ghcr_image_without_slowing_ci():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "docker.yml").read_text(encoding="utf-8")

    assert "docker build" not in ci.lower()
    assert "ghcr.io/saime428/dreamloop" in workflow
    assert "workflow_dispatch" in workflow
    assert "release:" in workflow
    assert "docker/build-push-action" in workflow
