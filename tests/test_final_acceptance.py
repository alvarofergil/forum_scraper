from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRACKED_RUNTIME_ARTIFACTS = {
    "config/config.yaml",
    "data/monitor.db",
    ".env",
}


def read_text(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_portable_runtime_contract_is_documented_and_config_is_read_only() -> None:
    compose = yaml.safe_load(read_text("docker-compose.yml"))
    service = compose["services"]["forum-scraper"]
    readme = read_text("README.md")

    assert service["volumes"] == [
        "./config:/app/config:ro",
        "./data:/app/data",
        "./backups:/app/backups",
    ]
    for path in ("config/", "data/", "backups/", ".env"):
        assert path in readme
    assert "Raspberry" in readme


def test_v1_cli_commands_are_documented_for_local_and_docker_operation() -> None:
    readme = read_text("README.md")

    for command in (
        "bootstrap",
        "bootstrap --force",
        "run",
        "status",
        "favorites",
        "inspect <TOPIC_ID>",
        "retry-notifications",
        "backup",
        "favorite deactivate <TOPIC_ID>",
        "favorite reactivate <TOPIC_ID>",
        "debug-listing",
    ):
        assert f"python -m app {command}" in readme

    for command in ("bootstrap", "run", "status", "retry-notifications", "backup"):
        assert f"docker compose run --rm forum-scraper {command}" in readme


def test_secrets_and_runtime_state_are_not_tracked_as_project_artifacts() -> None:
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )
    tracked_files = set(result.stdout.splitlines())

    assert TRACKED_RUNTIME_ARTIFACTS.isdisjoint(tracked_files)
    assert "config/config.yaml" in read_text(".gitignore")
    assert ".env" in read_text(".gitignore")
    assert "data/*" in read_text(".gitignore")
    assert "backups/*" in read_text(".gitignore")


def test_env_example_contains_placeholders_without_secret_values() -> None:
    env_example = read_text(".env.example")

    assert "SMTP_PASSWORD=" in env_example
    assert "OPENAI_API_KEY=" in env_example
    assert "env-secret" not in env_example
    assert "example-password" not in env_example


def test_example_config_and_readme_use_no_ai_by_default() -> None:
    config = yaml.safe_load(read_text("config/config.example.yaml"))
    readme = read_text("README.md")

    assert config["ai"]["enabled"] is False
    assert config["ai"]["model"] is None
    assert "ai.enabled=false" in readme
    assert "ai.model" in readme
    assert "OPENAI_API_KEY" in readme
    assert "API key por si sola" in readme
    assert "no basta" in readme


def test_final_acceptance_includes_task_026_contracts() -> None:
    readme = read_text("README.md")
    task = read_text("SPECs/task_specs/TASK-026_global_quality_audit_remediation.md")

    assert "ai.model` no nulo" in readme
    assert "ultimos\ncheckpoints conocidos" in readme
    assert "OpenAI Structured Outputs" in task
    assert "un favorito debe representar el par `topic_id + watch_item_id`" in task
