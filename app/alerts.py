"""Threshold-based resource alerts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .monitor import SystemMetrics, Thresholds


@dataclass(frozen=True)
class Alert:
    """A threshold observation requiring attention, not proof of failure."""

    metric: str
    observed_value: float | None
    threshold: float | None
    timestamp: str
    severity: str = "warning"
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def generate_alerts(
    metrics: SystemMetrics,
    thresholds: Thresholds,
    network_results: dict[str, Any] | None = None,
    backup_results: dict[str, Any] | None = None,
) -> list[Alert]:
    """Generate resource, network, and backup alerts."""

    candidates = (
        ("cpu_percent", metrics.cpu_percent, thresholds.cpu),
        ("memory_percent", metrics.memory_percent, thresholds.memory),
        ("disk_percent", metrics.disk_percent, thresholds.disk),
    )
    alerts: list[Alert] = []
    for metric, observed, threshold in candidates:
        if observed is not None and observed >= threshold:
            alerts.append(Alert(
                metric=metric,
                observed_value=observed,
                threshold=threshold,
                timestamp=metrics.timestamp,
                message=(f"{metric} is {observed:.1f}%, at or above the "
                         f"configured warning threshold of {threshold:.1f}%."),
            ))
    for result in (network_results or {}).get("checks", []):
        if result.get("status") != "healthy":
            label = result.get("hostname") or result.get("host") or result.get("endpoint") or "unknown"
            alerts.append(Alert(
                metric=f"network_{result.get('check_type', 'check')}",
                observed_value=None,
                threshold=None,
                timestamp=metrics.timestamp,
                severity="critical",
                message=f"Network check for {label} failed: {result.get('error') or 'check unsuccessful'}",
            ))
    for result in (backup_results or {}).get("checks", []):
        if result.get("status") != "healthy":
            alerts.append(Alert(
                metric="backup_check",
                observed_value=None,
                threshold=None,
                timestamp=metrics.timestamp,
                severity="critical" if result.get("status") == "critical" else "warning",
                message=f"Backup {result.get('name', 'unknown')} is {result.get('status', 'unknown')}: "
                        f"{result.get('error') or 'verification unsuccessful'}",
            ))
    return alerts