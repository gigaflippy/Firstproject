from pulsewatch.probe import probe


async def test_up(mock_client, targets):
    r = await probe(mock_client, targets[0], "eu-test")
    assert r.up is True
    assert r.status_code == 200
    assert r.latency_ms is not None and r.latency_ms >= 0
    assert r.error is None
    assert r.region == "eu-test"


async def test_unexpected_status_is_down(mock_client, targets):
    r = await probe(mock_client, targets[1], "eu-test")
    assert r.up is False
    assert r.status_code == 503
    assert "503" in r.error


async def test_timeout_is_down_and_does_not_raise(mock_client, targets):
    r = await probe(mock_client, targets[2], "eu-test")
    assert r.up is False
    assert r.status_code is None
    assert r.latency_ms is None
    assert r.error == "timeout"
