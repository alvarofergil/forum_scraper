from collections.abc import Mapping
from dataclasses import dataclass

import pytest

from sources.armas_es.client import (
    ArmasBlockedError,
    ArmasEsClient,
    ArmasHttpResponse,
    ArmasHttpTransientError,
    ArmasTopicNotFoundError,
    ArmasTopicUnavailableError,
    ArmasTransportError,
)


@dataclass(frozen=True)
class RecordedCall:
    url: str
    headers: Mapping[str, str]
    timeout_seconds: float


class FakeTransport:
    def __init__(self, *outcomes: ArmasHttpResponse | Exception) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[RecordedCall] = []

    def __call__(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> ArmasHttpResponse:
        self.calls.append(RecordedCall(url, dict(headers), timeout_seconds))
        if not self.outcomes:
            raise AssertionError("unexpected HTTP call")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def ok_response(text: str = "ok") -> ArmasHttpResponse:
    return ArmasHttpResponse(status_code=200, text=text, final_url="https://www.armas.es/foros/")


def test_get_listing_page_uses_viewforum_url_and_user_agent() -> None:
    transport = FakeTransport(ok_response("listing"))
    client = ArmasEsClient(
        transport=transport,
        request_delay_seconds=0,
        user_agent="PersonalForumMonitor/Test",
    )

    response = client.get_listing_page(start=18)

    assert response.text == "listing"
    assert transport.calls[0].url == "https://www.armas.es/foros/viewforum.php?f=96&start=18"
    assert transport.calls[0].headers["User-Agent"] == "PersonalForumMonitor/Test"


def test_get_topic_uses_canonical_topic_url() -> None:
    transport = FakeTransport(ok_response("topic"))
    client = ArmasEsClient(transport=transport, request_delay_seconds=0)

    client.get_topic("12345")

    assert transport.calls[0].url == "https://www.armas.es/foros/viewtopic.php?f=96&t=12345"


def test_retry_transient_http_status_then_success() -> None:
    transport = FakeTransport(
        ArmasHttpResponse(status_code=503, text="temporary", final_url="https://example.invalid"),
        ok_response("recovered"),
    )
    clock = FakeClock()
    client = ArmasEsClient(
        transport=transport,
        request_delay_seconds=2,
        max_retries=1,
        sleeper=clock.sleep,
        monotonic=clock.monotonic,
    )

    response = client.get_listing_page()

    assert response.text == "recovered"
    assert len(transport.calls) == 2
    assert clock.sleeps == [2]


def test_retry_transient_transport_error_then_success() -> None:
    transport = FakeTransport(
        TimeoutError("timeout"),
        ok_response("recovered"),
    )
    client = ArmasEsClient(
        transport=transport,
        request_delay_seconds=0,
        max_retries=1,
    )

    response = client.get_listing_page()

    assert response.text == "recovered"
    assert len(transport.calls) == 2


def test_retries_are_bounded() -> None:
    transport = FakeTransport(
        ArmasHttpResponse(status_code=503, text="temporary", final_url="https://example.invalid"),
        ArmasHttpResponse(status_code=503, text="temporary", final_url="https://example.invalid"),
        ArmasHttpResponse(status_code=503, text="temporary", final_url="https://example.invalid"),
    )
    client = ArmasEsClient(
        transport=transport,
        request_delay_seconds=0,
        max_retries=2,
    )

    with pytest.raises(ArmasHttpTransientError, match="HTTP 503"):
        client.get_listing_page()

    assert len(transport.calls) == 3


def test_delay_is_invoked_between_consecutive_requests() -> None:
    transport = FakeTransport(ok_response("one"), ok_response("two"))
    clock = FakeClock()
    client = ArmasEsClient(
        transport=transport,
        request_delay_seconds=2,
        sleeper=clock.sleep,
        monotonic=clock.monotonic,
    )

    client.get_listing_page()
    client.get_topic("12345")

    assert clock.sleeps == [2]


def test_explicit_blocking_status_raises_clear_error_without_retry() -> None:
    transport = FakeTransport(
        ArmasHttpResponse(status_code=403, text="forbidden", final_url="https://example.invalid")
    )
    client = ArmasEsClient(transport=transport, request_delay_seconds=0, max_retries=3)

    with pytest.raises(ArmasBlockedError, match="explicit block"):
        client.get_listing_page()

    assert len(transport.calls) == 1


def test_non_transient_http_error_is_not_retried() -> None:
    transport = FakeTransport(
        ArmasHttpResponse(status_code=404, text="not found", final_url="https://example.invalid")
    )
    client = ArmasEsClient(transport=transport, request_delay_seconds=0, max_retries=3)

    with pytest.raises(ArmasTopicNotFoundError, match="HTTP 404"):
        client.get_listing_page()

    assert len(transport.calls) == 1


def test_topic_unavailable_status_is_distinguishable() -> None:
    transport = FakeTransport(
        ArmasHttpResponse(status_code=410, text="gone", final_url="https://example.invalid")
    )
    client = ArmasEsClient(transport=transport, request_delay_seconds=0, max_retries=3)

    with pytest.raises(ArmasTopicUnavailableError, match="HTTP 410"):
        client.get_topic("12345")

    assert len(transport.calls) == 1


def test_transport_error_is_clear_after_retries_are_exhausted() -> None:
    transport = FakeTransport(TimeoutError("timeout"), TimeoutError("timeout"))
    client = ArmasEsClient(transport=transport, request_delay_seconds=0, max_retries=1)

    with pytest.raises(ArmasTransportError, match="transport failed"):
        client.get_listing_page()

    assert len(transport.calls) == 2
