"""Safe analysis of application and sample log files."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_LEVELS = ("ERROR", "WARNING", "CRITICAL")
LEVEL_PATTERN = re.compile(r"\b(?P<level>[A-Z][A-Z0-9_]*)\b")
TIMESTAMP_PATTERN = re.compile(r"^(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})")


@dataclass(frozen=True)
class LogEntry:
    """One matching line from a log file."""

    level: str
    message: str
    timestamp: str | None = None
    line_number: int = 0


@dataclass
class LogAnalysis:
    """Results and non-fatal errors from log analysis."""

    path: str
    counts: dict[str, int]
    entries: list[LogEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total_matches(self) -> int:
        return sum(self.counts.values())

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "counts": self.counts,
            "total_matches": self.total_matches,
            "entries": [entry.__dict__ for entry in self.entries],
            "errors": self.errors,
        }


def analyze_log(path: Path, levels: tuple[str, ...] = DEFAULT_LEVELS) -> LogAnalysis:
    """Find configured levels without failing the overall monitoring run."""

    normalized_levels = tuple(level.upper() for level in levels)
    counts = Counter({level: 0 for level in normalized_levels})
    result = LogAnalysis(path=str(path), counts=dict(counts))
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        result.errors.append(f"Log file not found: {path}")
        return result
    except (OSError, UnicodeError) as exc:
        result.errors.append(f"Unable to read log file {path}: {exc}")
        return result

    for line_number, line in enumerate(lines, start=1):
        match = LEVEL_PATTERN.search(line.upper())
        if not match or match.group("level") not in normalized_levels:
            continue
        level = match.group("level")
        result.counts[level] += 1
        timestamp_match = TIMESTAMP_PATTERN.search(line)
        result.entries.append(LogEntry(
            level=level,
            message=line,
            timestamp=timestamp_match.group("timestamp") if timestamp_match else None,
            line_number=line_number,
        ))
    return result