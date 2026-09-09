from __future__ import annotations

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_docker_compose_mounts_portable_runtime_directories() -> None:
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))

    service = compose["services"]["forum-scraper"]

    assert service["build"]["context"] == "."
    assert service["env_file"] == [{"path": ".env", "required": False}]
    assert service["volumes"] == [
        "./config:/app/config:ro",
        "./data:/app/data",
        "./backups:/app/backups",
    ]
    assert service["command"] == ["run"]


def test_dockerfile_uses_package_entrypoint_and_non_root_runtime() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM python:3.12-slim" in dockerfile
    assert "python -m pip install -e ." in dockerfile
    assert "USER forum" in dockerfile
    assert 'ENTRYPOINT ["python", "-m", "app"]' in dockerfile


def test_env_example_documents_only_environment_variable_names() -> None:
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    for key in (
        "SMTP_HOST=",
        "SMTP_PORT=587",
        "SMTP_USER=",
        "SMTP_PASSWORD=",
        "NOTIFICATION_EMAIL=",
        "OPENAI_API_KEY=",
    ):
        assert key in env_example

    assert "example-password" not in env_example
