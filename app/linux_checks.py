"""Optional Linux-only service checks with no privileged operations."""

from __future__ import annotations

import platform
import shutil
import subprocess


def check_services(services: list[str]) -> dict[str, str]:
    """Return systemd service states, or a clear unsupported status."""

    if platform.system() != "Linux":
        return {service: "unsupported on this platform" for service in services}
    if shutil.which("systemctl") is None:
        return {service: "systemctl unavailable" for service in services}

    statuses: dict[str, str] = {}
    for service in services:
        try:
            completed = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            statuses[service] = completed.stdout.strip() or completed.stderr.strip() or "unknown"
        except (OSError, subprocess.SubprocessError) as exc:
            statuses[service] = f"check failed: {exc}"
    return statuses