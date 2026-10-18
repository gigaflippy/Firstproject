from __future__ import annotations

import httpx
import pytest

from pulsewatch.config import Target


def make_handler(routes: dict[str, int | Exception]):
    """Build a MockTransport handler: host -> status code or exception to raise."""

    def handler(request: httpx.Request) -> httpx.Response:
        outcome = routes[request.url.host]
        if isinstance(outcome, Exception):
            raise outcome
        return httpx.Response(outcome)

    return handler


@pytest.fixture
def targets() -> list[Target]:
    return [
        Target(name="good", url="https://good.test"),
        Target(name="bad", url="https://bad.test"),
        Target(name="slow", url="https://slow.test", timeout_seconds=0.1),
    ]


@pytest.fixture
def mock_client() -> httpx.AsyncClient:
    routes = {
        "good.test": 200,
        "bad.test": 503,
        "slow.test": httpx.ReadTimeout("timed out"),
    }
    return httpx.AsyncClient(transport=httpx.MockTransport(make_handler(routes)))
