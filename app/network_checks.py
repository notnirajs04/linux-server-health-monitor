"""Configurable, read-only DNS, TCP, and HTTP diagnostics."""

from __future__ import annotations

import socket
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Callable


def _timed_call(function: Callable[[], Any], timeout_seconds: float) -> tuple[Any | None, str | None]:
    """Run a blocking standard-library operation with a caller-defined timeout."""

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(function)
    try:
        return future.result(timeout=timeout_seconds), None
    except FutureTimeoutError:
        future.cancel()
        return None, f"operation timed out after {timeout_seconds:g} seconds"
    except Exception as exc:  # Individual diagnostics must not stop a run.
        return None, str(exc)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def resolve_dns(hostname: str, timeout_seconds: float = 3.0) -> dict[str, Any]:
    """Resolve a hostname and return addresses, timing, and a structured status."""

    started = time.perf_counter()
    addresses, error = _timed_call(
        lambda: socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM),
        timeout_seconds,
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    resolved = sorted({item[4][0] for item in addresses or []})
    return {
        "check_type": "dns",
        "hostname": hostname,
        "resolved_addresses": resolved,
        "status": "healthy" if resolved and error is None else "critical",
        "elapsed_ms": elapsed_ms,
        "error": error if error else ("hostname returned no addresses" if not resolved else None),
    }


def check_tcp(host: str, port: int, timeout_seconds: float = 3.0) -> dict[str, Any]:
    """Check whether a TCP connection can be opened."""

    started = time.perf_counter()
    connection, error = _timed_call(
        lambda: socket.create_connection((host, port), timeout=timeout_seconds),
        timeout_seconds,
    )
    if connection is not None:
        connection.close()
    return {
        "check_type": "tcp",
        "host": host,
        "port": port,
        "status": "healthy" if error is None else "critical",
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        "error": error,
    }


def check_http(endpoint: str, timeout_seconds: float = 3.0) -> dict[str, Any]:
    """Make a lightweight request using urllib's default TLS verification."""

    started = time.perf_counter()
    status_code: int | None = None
    error: str | None = None
    try:
        request = urllib.request.Request(endpoint, method="GET")
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status_code = response.status
    except urllib.error.HTTPError as exc:
        status_code = exc.code
        error = f"HTTP {exc.code}: {exc.reason}"
    except (OSError, ValueError, urllib.error.URLError) as exc:
        error = str(exc)
    return {
        "check_type": "http",
        "endpoint": endpoint,
        "status_code": status_code,
        "status": "healthy" if status_code is not None and 200 <= status_code < 400 else "critical",
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        "error": error,
    }


def run_network_checks(settings: dict[str, Any] | None) -> dict[str, Any]:
    """Run configured checks, returning errors for invalid entries instead of raising."""

    settings = settings or {}
    if not settings.get("enabled", False):
        return {"enabled": False, "checks": [], "errors": []}
    try:
        timeout = float(settings.get("timeout_seconds", 3))
        if timeout <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
    except (TypeError, ValueError) as exc:
        return {"enabled": True, "checks": [], "errors": [str(exc)]}

    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    for hostname in settings.get("dns_hosts", []):
        if not isinstance(hostname, str) or not hostname.strip():
            errors.append("dns_hosts entries must be non-empty strings")
            continue
        checks.append(resolve_dns(hostname, timeout))
    for target in settings.get("tcp_targets", []):
        try:
            host = target["host"]
            port = int(target["port"])
            if not isinstance(host, str) or not host or not 1 <= port <= 65535:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            errors.append("tcp_targets entries require a valid host and port 1-65535")
            continue
        checks.append(check_tcp(host, port, timeout))
    for endpoint in settings.get("http_endpoints", []):
        if not isinstance(endpoint, str) or not endpoint.startswith(("http://", "https://")):
            errors.append("http_endpoints entries must be HTTP or HTTPS URLs")
            continue
        checks.append(check_http(endpoint, timeout))
    return {"enabled": True, "checks": checks, "errors": errors}