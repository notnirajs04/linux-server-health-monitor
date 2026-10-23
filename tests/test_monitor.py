from pathlib import Path

import pytest

from app.monitor import SystemMetrics, Thresholds, collect_system_metrics, determine_health


def test_health_for_normal_metrics() -> None:
    metrics = SystemMetrics("now", 20, 40, 50, "/", "Linux", [])
    assert determine_health(metrics, Thresholds()) == "healthy"


@pytest.mark.parametrize("values", [(80, 10, 10), (10, 80, 10), (10, 10, 85)])
def test_threshold_boundary_is_warning(values: tuple[float, float, float]) -> None:
    metrics = SystemMetrics("now", *values, "/", "Linux", [])
    assert determine_health(metrics, Thresholds()) == "warning"


def test_all_unsupported_metrics_are_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.monitor.psutil.cpu_percent", lambda interval: (_ for _ in ()).throw(OSError("no cpu")))
    monkeypatch.setattr("app.monitor.psutil.virtual_memory", lambda: (_ for _ in ()).throw(OSError("no memory")))
    monkeypatch.setattr("app.monitor.psutil.disk_usage", lambda path: (_ for _ in ()).throw(OSError("no disk")))
    metrics = collect_system_metrics(Path("/"))
    assert determine_health(metrics, Thresholds()) == "unknown"
    assert len(metrics.collection_errors) == 3


def test_collect_system_metrics_uses_mocked_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.monitor.psutil.cpu_percent", lambda interval: 12.5)
    monkeypatch.setattr("app.monitor.psutil.virtual_memory", lambda: type("Memory", (), {"percent": 33.0})())
    monkeypatch.setattr("app.monitor.psutil.disk_usage", lambda path: type("Disk", (), {"percent": 44.0})())
    metrics = collect_system_metrics(Path("/"))
    assert (metrics.cpu_percent, metrics.memory_percent, metrics.disk_percent) == (12.5, 33.0, 44.0)