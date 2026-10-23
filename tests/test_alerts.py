from app.alerts import generate_alerts
from app.monitor import SystemMetrics, Thresholds


def test_alert_contains_metric_observed_value_threshold_and_timestamp() -> None:
    metrics = SystemMetrics("2026-01-01T00:00:00+00:00", 91, 20, 86, "/", "Linux", [])
    alerts = generate_alerts(metrics, Thresholds(cpu=90, memory=80, disk=85))
    assert [alert.metric for alert in alerts] == ["cpu_percent", "disk_percent"]
    assert alerts[0].observed_value == 91
    assert alerts[0].threshold == 90
    assert alerts[0].timestamp.startswith("2026-01-01")
    assert "warning threshold" in alerts[0].message