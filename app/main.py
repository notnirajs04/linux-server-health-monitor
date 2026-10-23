"""Command-line entry point for the monitoring application."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .alerts import generate_alerts
from .backup_checks import run_backup_checks
from .linux_checks import check_services
from .log_analyzer import DEFAULT_LEVELS, analyze_log
from .monitor import Thresholds, collect_system_metrics, determine_health
from .network_checks import run_network_checks
from .reports import build_report, generate_reports

ROOT = Path(__file__).resolve().parent.parent


def load_config(path: Path) -> dict[str, Any]:
    """Load and validate JSON configuration, applying beginner-friendly defaults."""

    defaults: dict[str, Any] = {
        "thresholds": {"cpu": 80, "memory": 80, "disk": 85},
        "log_file": "logs/sample.log",
        "log_levels": list(DEFAULT_LEVELS),
        "services": [],
        "reports_dir": "reports",
        "network_checks": {"enabled": False, "timeout_seconds": 3, "dns_hosts": [], "tcp_targets": [], "http_endpoints": []},
        "backup_checks": {"enabled": False, "targets": []},
    }
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("configuration root must be a JSON object")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"Unable to load configuration {path}: {exc}") from exc
    for key, value in loaded.items():
        if key == "thresholds":
            if not isinstance(value, dict):
                raise RuntimeError("configuration thresholds must be an object")
            defaults["thresholds"].update(value)
        elif key in ("network_checks", "backup_checks"):
            if not isinstance(value, dict):
                raise RuntimeError(f"configuration {key} must be an object")
            defaults[key].update(value)
        else:
            defaults[key] = value
    return defaults


def run(config_path: Path) -> dict[str, Any]:
    """Run one monitoring cycle and write both report formats."""

    config = load_config(config_path)
    thresholds = Thresholds(**config["thresholds"])
    metrics = collect_system_metrics()
    log_path = Path(config["log_file"])
    if not log_path.is_absolute():
        log_path = ROOT / log_path
    analysis = analyze_log(log_path, tuple(config["log_levels"]))
    network_results = run_network_checks(config.get("network_checks"))
    backup_results = run_backup_checks(config.get("backup_checks"), root=ROOT)
    alerts = generate_alerts(metrics, thresholds, network_results, backup_results)
    services = check_services(list(config.get("services", [])))
    health_status = determine_health(metrics, thresholds)
    if health_status != "unknown" and any(alerts):
        health_status = "warning"
    report = build_report(
        metrics=metrics.to_dict(),
        health_status=health_status,
        alerts=[alert.to_dict() for alert in alerts],
        log_analysis=analysis.to_dict(),
        service_statuses=services,
        network_results=network_results,
        backup_results=backup_results,
    )
    reports_dir = Path(config["reports_dir"])
    if not reports_dir.is_absolute():
        reports_dir = ROOT / reports_dir
    paths = generate_reports(report, reports_dir)
    report["report_paths"] = {kind: str(path) for kind, path in paths.items()}
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect system health metrics and analyze logs.")
    parser.add_argument("--config", type=Path, default=ROOT / "config" / "config.json")
    args = parser.parse_args()
    report = run(args.config)
    print(json.dumps({
        "health_status": report["health_status"],
        "alerts": len(report["alerts"]),
        "log_matches": report["log_analysis"]["total_matches"],
        "reports": report["report_paths"],
    }, indent=2))


if __name__ == "__main__":
    main()