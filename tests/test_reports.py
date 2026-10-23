import csv
import json
from pathlib import Path

from app.reports import build_report, generate_reports


def test_json_and_csv_reports_are_written(tmp_path: Path) -> None:
    report = build_report(
        metrics={"cpu_percent": 10, "memory_percent": 20, "disk_percent": 30},
        health_status="healthy",
        alerts=[],
        log_analysis={"total_matches": 2},
        network_results={"enabled": True, "checks": [{"status": "healthy"}], "errors": []},
        backup_results={"enabled": True, "checks": [{"status": "warning"}], "errors": []},
    )
    paths = generate_reports(report, tmp_path / "reports")
    assert paths["json"].exists()
    assert paths["csv"].exists()
    assert json.loads(paths["json"].read_text(encoding="utf-8"))["health_status"] == "healthy"
    with paths["csv"].open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    assert {row["metric"] for row in rows} >= {"health_status", "cpu_percent", "log_match_count"}
    assert json.loads(paths["json"].read_text(encoding="utf-8"))["backup_checks"]["checks"][0]["status"] == "warning"
    assert {row["metric"] for row in rows} >= {"network_check_count", "backup_failure_count"}