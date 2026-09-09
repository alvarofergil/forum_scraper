from pathlib import Path

import pytest

from app.config import ConfigError, load_config, load_email_environment
from app.models import CandidateStatus, EventType, ListingType, utc_now


def write_config(tmp_path: Path, content: str) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(content, encoding="utf-8")
    return config_path


def test_valid_config_loads_typed_values(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
source:
  type: armas_es
  base_url: "https://www.armas.es"
  forum_id: 96
bootstrap:
  pages: 10
discovery:
  overlap_minutes: 30
  max_pages_per_run: 50
favorites:
  check_every_run: true
  unavailable_confirmation_runs: 2
scraping:
  request_delay_seconds: 2
  timeout_seconds: 20
  max_retries: 3
ai:
  enabled: true
  model: null
  match_confidence_threshold: 0.85
notifications:
  email_enabled: true
  notify_event_types:
    - NEW_FAVORITE
    - PRICE_CHANGED
debug:
  save_failed_html: false
watchlist:
  - id: item_001
    brand: "Marca A"
    model: "Modelo X"
    aliases:
      - "MarcaA ModeloX"
""",
    )

    config = load_config(config_path)

    assert config.source.type == "armas_es"
    assert config.source.forum_id == 96
    assert config.bootstrap.pages == 10
    assert config.ai.model is None
    assert config.ai.match_confidence_threshold == 0.85
    assert config.notifications.notify_event_types == (
        EventType.NEW_FAVORITE,
        EventType.PRICE_CHANGED,
    )
    assert config.watchlist[0].aliases == ("MarcaA ModeloX",)


def test_example_config_is_valid() -> None:
    config = load_config(Path("config/config.example.yaml"))

    assert config.source.type == "armas_es"
    assert config.ai.enabled is False
    assert config.ai.model is None
    assert config.notifications.notify_event_types


def test_invalid_config_fails_with_clear_error(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
source:
  type: armas_es
  base_url: "https://www.armas.es"
  forum_id: 96
watchlist:
  - id: item_001
    brand: ""
    model: "Modelo X"
""",
    )

    with pytest.raises(ConfigError, match="watchlist\\[0\\].brand"):
        load_config(config_path)


def test_unknown_source_type_is_rejected(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
source:
  type: other_forum
  base_url: "https://www.example.invalid"
  forum_id: 96
watchlist:
  - id: item_001
    brand: "Marca A"
    model: "Modelo X"
""",
    )

    with pytest.raises(ConfigError, match="source.type"):
        load_config(config_path)


@pytest.mark.parametrize("base_url", ["not-a-url", "www.armas.es", "ftp://www.armas.es"])
def test_source_base_url_must_be_absolute_http_url(tmp_path: Path, base_url: str) -> None:
    config_path = write_config(
        tmp_path,
        f"""
source:
  type: armas_es
  base_url: "{base_url}"
  forum_id: 96
watchlist:
  - id: item_001
    brand: "Marca A"
    model: "Modelo X"
""",
    )

    with pytest.raises(ConfigError, match="source.base_url"):
        load_config(config_path)


def test_unknown_notification_event_type_is_rejected(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
source:
  type: armas_es
  base_url: "https://www.armas.es"
  forum_id: 96
notifications:
  notify_event_types:
    - NEW_FAVORITE
    - SURPRISE
watchlist:
  - id: item_001
    brand: "Marca A"
    model: "Modelo X"
""",
    )

    with pytest.raises(ConfigError, match="notifications.notify_event_types\\[1\\]"):
        load_config(config_path)


def test_ai_disabled_without_model_is_representable(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
source:
  type: armas_es
  base_url: "https://www.armas.es"
  forum_id: 96
ai:
  enabled: false
  model: null
watchlist:
  - id: item_001
    brand: "Marca A"
    model: "Modelo X"
""",
    )

    config = load_config(config_path)

    assert config.ai.enabled is False
    assert config.ai.model is None


def test_empty_ai_model_is_rejected(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
source:
  type: armas_es
  base_url: "https://www.armas.es"
  forum_id: 96
ai:
  enabled: true
  model: " "
watchlist:
  - id: item_001
    brand: "Marca A"
    model: "Modelo X"
""",
    )

    with pytest.raises(ConfigError, match="ai.model"):
        load_config(config_path)


def test_yaml_secrets_are_rejected(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
source:
  type: armas_es
  base_url: "https://www.armas.es"
  forum_id: 96
notifications:
  smtp_password: "not-allowed"
watchlist:
  - id: item_001
    brand: "Marca A"
    model: "Modelo X"
""",
    )

    with pytest.raises(ConfigError, match="secrets must come from environment"):
        load_config(config_path)


def test_email_secrets_are_loaded_from_environment_mapping() -> None:
    env = {
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "user@example.invalid",
        "SMTP_PASSWORD": "example-password",
        "NOTIFICATION_EMAIL": "target@example.invalid",
    }

    email = load_email_environment(env)

    assert email.smtp_host == "smtp.gmail.com"
    assert email.smtp_port == 587
    assert email.smtp_user == "user@example.invalid"
    assert email.notification_email == "target@example.invalid"


def test_email_environment_missing_secret_fails() -> None:
    with pytest.raises(ConfigError, match="SMTP_PASSWORD"):
        load_email_environment(
            {
                "SMTP_HOST": "smtp.gmail.com",
                "SMTP_PORT": "587",
                "SMTP_USER": "user@example.invalid",
                "NOTIFICATION_EMAIL": "target@example.invalid",
            }
        )


def test_domain_enums_and_utc_time_are_available() -> None:
    assert ListingType.OFFER.value == "OFFER"
    assert CandidateStatus.PENDING.value == "PENDING"
    assert utc_now().tzinfo is not None
