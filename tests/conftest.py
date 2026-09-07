"""Global pytest safeguards."""

from __future__ import annotations

import socket

import pytest


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unit tests must use fake transports and never open real sockets."""

    class BlockedSocket(socket.socket):
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise AssertionError("network access is blocked in unit tests")

    monkeypatch.setattr(socket, "socket", BlockedSocket)
