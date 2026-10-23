"""Read-only verification of configured backup files and directories."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def verify_backup_target(
    target: dict[str, Any],
    root: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Inspect one target without copying, opening, modifying, or deleting it."""

    checked_at = now or datetime.now(timezone.utc)
    name = str(target.get("name", "unnamed"))
    raw_path = target.get("path")
    result: dict[str, Any] = {
        "name": name,
        "path": str(raw_path) if raw_path is not None else "",
        "status": "unknown",
        "exists": False,
        "is_file": None,
        "size_bytes": None,
        "last_modified": None,
        "age_hours": None,
        "max_age_hours": target.get("max_age_hours"),
        "allow_empty": bool(target.get("allow_empty", False)),
        "error": None,
    }
    try:
        max_age = float(target.get("max_age_hours", 24))
        if max_age < 0:
            raise ValueError("max_age_hours must be zero or greater")
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError("path must be a non-empty string")
    except (TypeError, ValueError) as exc:
        result["error"] = str(exc)
        return result

    path = Path(raw_path)
    if root is not None and not path.is_absolute():
        path = root / path
    result["path"] = str(path)
    try:
        stat = path.stat()
        result["exists"] = True
        result["is_file"] = path.is_file()
        result["size_bytes"] = stat.st_size if path.is_file() else None
        modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
        result["last_modified"] = modified.isoformat()
        result["age_hours"] = round(max(0.0, (checked_at - modified).total_seconds() / 3600), 3)

        empty = path.is_file() and stat.st_size == 0
        if path.is_dir():
            empty = not any(path.iterdir())
        if empty and not result["allow_empty"]:
            result["status"] = "warning"
            result["error"] = "backup target is empty"
        elif result["age_hours"] > max_age:
            result["status"] = "warning"
            result["error"] = f"backup is older than {max_age:g} hours"
        else:
            result["status"] = "healthy"
    except FileNotFoundError:
        result["status"] = "critical"
        result["error"] = "backup target does not exist"
    except (OSError, PermissionError) as exc:
        result["error"] = str(exc)
    return result


def run_backup_checks(
    settings: dict[str, Any] | None,
    root: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Verify all configured targets and isolate errors per target."""

    settings = settings or {}
    if not settings.get("enabled", False):
        return {"enabled": False, "checks": [], "errors": []}
    targets = settings.get("targets", [])
    if not isinstance(targets, list):
        return {"enabled": True, "checks": [], "errors": ["targets must be a list"]}
    checks = []
    for target in targets:
        if not isinstance(target, dict):
            checks.append({"name": "invalid", "status": "unknown", "error": "target must be an object"})
        else:
            checks.append(verify_backup_target(target, root=root, now=now))
    return {"enabled": True, "checks": checks, "errors": []}