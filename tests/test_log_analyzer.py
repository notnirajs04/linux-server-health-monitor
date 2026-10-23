from pathlib import Path

from app.log_analyzer import analyze_log


def test_log_levels_and_timestamps_are_counted(tmp_path: Path) -> None:
    log = tmp_path / "sample.log"
    log.write_text(
        "2026-01-01 10:00:00 ERROR failed\n"
        "WARNING no timestamp\n"
        "2026-01-01 10:02:00 CRITICAL stopped\n",
        encoding="utf-8",
    )
    result = analyze_log(log)
    assert result.counts == {"ERROR": 1, "WARNING": 1, "CRITICAL": 1}
    assert result.entries[0].timestamp == "2026-01-01 10:00:00"
    assert result.entries[1].timestamp is None


def test_missing_log_is_non_fatal(tmp_path: Path) -> None:
    result = analyze_log(tmp_path / "missing.log")
    assert result.total_matches == 0
    assert result.errors


def test_unreadable_log_is_non_fatal(tmp_path: Path, monkeypatch) -> None:
    log = tmp_path / "unreadable.log"
    log.write_text("ERROR hidden", encoding="utf-8")
    monkeypatch.setattr(Path, "read_text", lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("denied")))
    result = analyze_log(log)
    assert result.counts == {"ERROR": 0, "WARNING": 0, "CRITICAL": 0}
    assert "Unable to read" in result.errors[0]