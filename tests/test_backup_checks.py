import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.backup_checks import run_backup_checks, verify_backup_target


def test_existing_backup_file_is_healthy(tmp_path: Path) -> None:
    backup = tmp_path / "backup.zip"
    backup.write_bytes(b"backup data")
    result = verify_backup_target(
        {"name": "daily", "path": "backup.zip", "max_age_hours": 24},
        root=tmp_path,
        now=datetime.now(timezone.utc),
    )
    assert result["status"] == "healthy"
    assert result["size_bytes"] == 11


def test_missing_backup_is_critical(tmp_path: Path) -> None:
    result = verify_backup_target({"name": "missing", "path": "missing.zip"}, root=tmp_path)
    assert result["status"] == "critical"
    assert result["exists"] is False


def test_empty_backup_is_warning_unless_allowed(tmp_path: Path) -> None:
    backup = tmp_path / "empty.zip"
    backup.touch()
    result = verify_backup_target({"name": "empty", "path": "empty.zip"}, root=tmp_path)
    assert result["status"] == "warning"
    allowed = verify_backup_target({"name": "empty", "path": "empty.zip", "allow_empty": True}, root=tmp_path)
    assert allowed["status"] == "healthy"


def test_stale_backup_is_warning(tmp_path: Path) -> None:
    backup = tmp_path / "old.zip"
    backup.write_bytes(b"old")
    old_time = (datetime.now(timezone.utc) - timedelta(hours=48)).timestamp()
    os.utime(backup, (old_time, old_time))
    result = verify_backup_target(
        {"name": "old", "path": "old.zip", "max_age_hours": 24},
        root=tmp_path,
        now=datetime.now(timezone.utc),
    )
    assert result["status"] == "warning"
    assert "older" in result["error"]


def test_backup_checks_can_be_disabled_or_reject_invalid_config(tmp_path: Path) -> None:
    assert run_backup_checks({"enabled": False}, root=tmp_path)["checks"] == []
    invalid = run_backup_checks({"enabled": True, "targets": "not-a-list"}, root=tmp_path)
    assert invalid["errors"] == ["targets must be a list"]
    invalid_age = verify_backup_target({"name": "bad", "path": "x", "max_age_hours": -1}, root=tmp_path)
    assert invalid_age["status"] == "unknown"