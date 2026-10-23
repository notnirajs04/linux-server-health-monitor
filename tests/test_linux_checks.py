from app import linux_checks


def test_services_are_explicitly_unsupported_on_non_linux(monkeypatch) -> None:
    monkeypatch.setattr(linux_checks.platform, "system", lambda: "Windows")
    assert linux_checks.check_services(["ssh"]) == {"ssh": "unsupported on this platform"}


def test_service_command_failure_is_reported(monkeypatch) -> None:
    monkeypatch.setattr(linux_checks.platform, "system", lambda: "Linux")
    monkeypatch.setattr(linux_checks.shutil, "which", lambda command: "/usr/bin/systemctl")

    def fail(*args, **kwargs):
        raise OSError("systemctl unavailable")

    monkeypatch.setattr(linux_checks.subprocess, "run", fail)
    result = linux_checks.check_services(["ssh"])
    assert result["ssh"].startswith("check failed:")