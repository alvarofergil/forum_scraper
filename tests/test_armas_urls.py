import pytest

from sources.armas_es.urls import (
    ArmasUrlError,
    canonical_topic_page_url,
    canonical_topic_url,
    extract_topic_id,
    normalize_listing_page_url,
    normalize_topic_url,
    resolve_forum_url,
)


def test_url_with_sid_produces_canonical_topic_url() -> None:
    url = "https://www.armas.es/foros/viewtopic.php?f=96&t=12345&sid=abc123"

    assert normalize_topic_url(url) == "https://www.armas.es/foros/viewtopic.php?f=96&t=12345"


def test_start_post_anchor_and_extra_query_do_not_change_identity() -> None:
    url = "https://www.armas.es/foros/viewtopic.php?f=96&t=12345&start=18&p=999#p999"

    assert extract_topic_id(url) == "12345"
    assert normalize_topic_url(url) == "https://www.armas.es/foros/viewtopic.php?f=96&t=12345"


def test_relative_url_is_resolved_before_normalization() -> None:
    url = "./viewtopic.php?f=96&t=12345&sid=abc123"

    assert normalize_topic_url(url) == "https://www.armas.es/foros/viewtopic.php?f=96&t=12345"


def test_external_absolute_url_with_topic_id_is_rejected() -> None:
    url = "https://example.invalid/foros/viewtopic.php?f=96&t=12345"

    with pytest.raises(ArmasUrlError, match="host"):
        normalize_topic_url(url)


def test_forum_url_can_be_resolved_from_relative_path() -> None:
    url = "viewforum.php?f=96&start=18"

    assert resolve_forum_url(url) == "https://www.armas.es/foros/viewforum.php?f=96&start=18"


def test_listing_page_url_is_canonicalized_with_safe_query() -> None:
    url = "./viewforum.php?f=96&p=999&start=18&sid=abc#p999"

    assert normalize_listing_page_url(url) == (
        "https://www.armas.es/foros/viewforum.php?f=96&start=18"
    )


def test_listing_page_url_must_stay_on_configured_host_path_and_forum() -> None:
    assert (
        normalize_listing_page_url("https://example.invalid/foros/viewforum.php?f=96&start=18")
        is None
    )
    assert normalize_listing_page_url("./viewtopic.php?f=96&t=123&start=18") is None
    assert normalize_listing_page_url("./viewforum.php?f=97&start=18", forum_id=96) is None


@pytest.mark.parametrize("start", ["abc", "-1", "18&start=36"])
def test_listing_page_url_rejects_untrusted_start_values(start: str) -> None:
    assert normalize_listing_page_url(f"./viewforum.php?f=96&start={start}") is None


def test_canonical_topic_url_uses_configured_forum_id() -> None:
    assert canonical_topic_url("12345", forum_id=99) == (
        "https://www.armas.es/foros/viewtopic.php?f=99&t=12345"
    )


def test_canonical_topic_page_url_adds_start_only_for_later_pages() -> None:
    assert canonical_topic_page_url("12345", start=0) == (
        "https://www.armas.es/foros/viewtopic.php?f=96&t=12345"
    )
    assert canonical_topic_page_url("12345", start=18) == (
        "https://www.armas.es/foros/viewtopic.php?f=96&t=12345&start=18"
    )


def test_canonical_topic_page_url_rejects_negative_start() -> None:
    with pytest.raises(ArmasUrlError, match="start"):
        canonical_topic_page_url("12345", start=-1)


def test_url_without_topic_id_fails_explicitly() -> None:
    with pytest.raises(ArmasUrlError, match="missing topic id"):
        extract_topic_id("https://www.armas.es/foros/viewtopic.php?f=96&sid=abc123")


def test_blank_topic_id_fails_explicitly() -> None:
    with pytest.raises(ArmasUrlError, match="missing topic id"):
        canonical_topic_url(" ")


def test_invalid_base_url_scheme_fails_explicitly() -> None:
    with pytest.raises(ArmasUrlError, match="base_url"):
        canonical_topic_url("12345", base_url="ftp://www.armas.es")
