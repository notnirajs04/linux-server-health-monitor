from types import SimpleNamespace

from app import network_checks


def test_dns_resolution_success(monkeypatch) -> None:
    monkeypatch.setattr(
        network_checks.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("192.0.2.1", 0))],
    )
    result = network_checks.resolve_dns("example.test")
    assert result["status"] == "healthy"
    assert result["resolved_addresses"] == ["192.0.2.1"]


def test_dns_failure_is_structured(monkeypatch) -> None:
    monkeypatch.setattr(
        network_checks.socket,
        "getaddrinfo",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("not found")),
    )
    result = network_checks.resolve_dns("missing.test")
    assert result["status"] == "critical"
    assert "not found" in result["error"]


def test_tcp_success_and_failure(monkeypatch) -> None:
    connection = SimpleNamespace(close=lambda: None)
    monkeypatch.setattr(network_checks.socket, "create_connection", lambda address, timeout: connection)
    assert network_checks.check_tcp("example.test", 443)["status"] == "healthy"
    monkeypatch.setattr(
        network_checks.socket,
        "create_connection",
        lambda address, timeout: (_ for _ in ()).throw(TimeoutError("timed out")),
    )
    failed = network_checks.check_tcp("example.test", 443)
    assert failed["status"] == "critical"
    assert "timed out" in failed["error"]


def test_http_success_and_http_error(monkeypatch) -> None:
    class Response:
        status = 204

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    response = Response()
    monkeypatch.setattr(network_checks.urllib.request, "urlopen", lambda request, timeout: response)
    assert network_checks.check_http("https://example.test")["status"] == "healthy"
    monkeypatch.setattr(
        network_checks.urllib.request,
        "urlopen",
        lambda request, timeout: (_ for _ in ()).throw(
            network_checks.urllib.error.HTTPError("url", 503, "unavailable", {}, None)
        ),
    )
    failed = network_checks.check_http("https://example.test")
    assert failed["status_code"] == 503
    assert failed["status"] == "critical"


def test_network_checks_can_be_disabled_or_reject_invalid_config() -> None:
    assert network_checks.run_network_checks({"enabled": False})["checks"] == []
    result = network_checks.run_network_checks({"enabled": True, "timeout_seconds": 0})
    assert result["errors"] == ["timeout_seconds must be greater than zero"]