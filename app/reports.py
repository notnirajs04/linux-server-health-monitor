"""JSON and CSV report generation."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_report(
    metrics: dict[str, Any],
    health_status: str,
    alerts: list[dict[str, Any]],
    log_analysis: dict[str, Any],
    service_statuses: dict[str, str] | None = None,
    network_results: dict[str, Any] | None = None,
    backup_results: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the serializable report object shared by JSON and CSV writers."""

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "health_status": health_status,
        "metrics": metrics,
        "alerts": alerts,
        "log_analysis": log_analysis,
        "service_statuses": service_statuses or {},
        "network_checks": network_results or {"enabled": False, "checks": [], "errors": []},
        "backup_checks": backup_results or {"enabled": False, "checks": [], "errors": []},
    }


def generate_reports(report: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    """Write timestamped JSON and CSV files and return their paths."""

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        json_path = output_dir / f"health_report_{stamp}.json"
        csv_path = output_dir / f"health_report_{stamp}.csv"
        json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        rows = [
            ("health_status", report["health_status"]),
            ("cpu_percent", report["metrics"].get("cpu_percent")),
            ("memory_percent", report["metrics"].get("memory_percent")),
            ("disk_percent", report["metrics"].get("disk_percent")),
            ("alert_count", len(report["alerts"])),
            ("log_match_count", report["log_analysis"].get("total_matches", 0)),
            ("network_check_count", len(report.get("network_checks", {}).get("checks", []))),
            ("network_failure_count", sum(
                check.get("status") != "healthy"
                for check in report.get("network_checks", {}).get("checks", [])
            )),
            ("backup_check_count", len(report.get("backup_checks", {}).get("checks", []))),
            ("backup_failure_count", sum(
                check.get("status") != "healthy"
                for check in report.get("backup_checks", {}).get("checks", [])
            )),
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(("metric", "value"))
            writer.writerows(rows)
        return {"json": json_path, "csv": csv_path}
    except (OSError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Report generation failed: {exc}") from exc