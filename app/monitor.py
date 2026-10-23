"""Cross-platform system health metric collection."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil
import platform


@dataclass(frozen=True)
class Thresholds:
    """Warning thresholds expressed as percentages."""

    cpu: float = 80.0
    memory: float = 80.0
    disk: float = 85.0

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if not 0 <= value <= 100:
                raise ValueError(f"{name} threshold must be between 0 and 100")


@dataclass
class SystemMetrics:
    """A snapshot of system resource usage."""

    timestamp: str
    cpu_percent: float | None
    memory_percent: float | None
    disk_percent: float | None
    disk_path: str
    platform: str
    collection_errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_disk_path() -> Path:
    """Return a disk path valid for the current operating system."""

    return Path(Path.cwd().anchor) if psutil.WINDOWS else Path("/")


def collect_system_metrics(disk_path: Path | None = None) -> SystemMetrics:
    """Collect metrics while recording unsupported or inaccessible resources."""

    errors: list[str] = []
    timestamp = datetime.now(timezone.utc).isoformat()
    selected_path = disk_path or default_disk_path()

    try:
        cpu_percent: float | None = psutil.cpu_percent(interval=0.1)
    except (AttributeError, OSError, RuntimeError, SystemError) as exc:
        cpu_percent = None
        errors.append(f"CPU metric unavailable: {exc}")

    try:
        memory_percent: float | None = float(psutil.virtual_memory().percent)
    except (AttributeError, OSError, RuntimeError, SystemError) as exc:
        memory_percent = None
        errors.append(f"Memory metric unavailable: {exc}")

    try:
        disk_percent: float | None = float(psutil.disk_usage(str(selected_path)).percent)
    except (AttributeError, OSError, RuntimeError, SystemError) as exc:
        disk_percent = None
        errors.append(f"Disk metric unavailable for {selected_path}: {exc}")

    return SystemMetrics(
        timestamp=timestamp,
        cpu_percent=cpu_percent,
        memory_percent=memory_percent,
        disk_percent=disk_percent,
        disk_path=str(selected_path),
        platform=platform.system(),
        collection_errors=errors,
    )


def determine_health(metrics: SystemMetrics, thresholds: Thresholds) -> str:
    """Return healthy, warning, or unknown based on available measurements."""

    values = (metrics.cpu_percent, metrics.memory_percent, metrics.disk_percent)
    if all(value is None for value in values):
        return "unknown"
    if any(value is not None and value >= limit for value, limit in zip(
        values, (thresholds.cpu, thresholds.memory, thresholds.disk)
    )):
        return "warning"
    return "healthy"