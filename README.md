# Linux Server Health Monitoring & Log Analyzer

A beginner-friendly, portfolio-quality monitoring tool for a Linux server or Windows development machine. It collects CPU, memory, and disk metrics, analyzes configurable log files, creates threshold warnings, checks selected Linux services, and writes JSON and CSV reports.

The application is intentionally read-only. It does not change system configuration, restart services, delete or rotate logs, or require administrator privileges for normal monitoring.

## Objectives

- Demonstrate practical Python, Linux, Bash, testing, and reporting skills.
- Keep Windows development reliable while supporting Ubuntu through WSL.
- Make failures visible and non-fatal where a metric or log cannot be read.

## What the Application Does

Each run performs one health-check cycle:

1. Collects CPU, memory, disk, timestamp, platform, and collection-error information.
2. Compares available percentages with configurable warning thresholds.
3. Reads the configured log file and counts `ERROR`, `WARNING`, `CRITICAL`, or other selected levels.
4. Checks configured Linux services with read-only `systemctl is-active` calls.
5. Saves a complete JSON report and a compact CSV summary.

The health status can be `healthy`, `warning`, or `unknown`. A `warning` means a configured threshold was reached; it is not confirmation of a system failure. Missing metrics and unreadable logs are reported without crashing the run.

Network and backup checks are disabled by default in the sample configuration. Enable only the small set of hosts, endpoints, and backup paths that you are authorized to inspect.

## Network Diagnostics

When `network_checks.enabled` is `true`, the application can perform DNS resolution, TCP connectivity checks, and lightweight HTTP/HTTPS requests. Each result includes the target, status, elapsed time, and error details where applicable. Checks use Python's standard library, explicit timeouts, and normal TLS certificate verification. No network ranges or arbitrary ports are scanned.

## Backup Verification

When `backup_checks.enabled` is `true`, each configured target is checked read-only for existence, file type, file size, last-modified time, age, and empty or stale status. Statuses are `healthy`, `warning`, `critical`, or `unknown`.

Presence is not integrity verification: this tool does not open, restore, copy, compress, delete, or overwrite backups, and it cannot prove that a backup is recoverable.

## Architecture

| Module | Responsibility |
| --- | --- |
| `app/monitor.py` | CPU, memory, disk metrics; platform-aware disk path; health status |
| `app/log_analyzer.py` | Configurable log levels, counts, timestamps, and safe file errors |
| `app/alerts.py` | Threshold warnings with metric, value, limit, and timestamp |
| `app/reports.py` | Structured report model plus timestamped JSON and CSV output |
| `app/linux_checks.py` | Optional `systemctl is-active` checks on Linux only |
| `app/network_checks.py` | Configurable DNS, TCP, and HTTP/HTTPS diagnostics |
| `app/backup_checks.py` | Read-only backup existence, age, and size verification |
| `app/main.py` | Configuration, orchestration, and CLI output |

The normal health states are `healthy`, `warning`, and `unknown`. A warning means a configured threshold was reached; it is not confirmation of a system failure.

## Project Layout

```text
Linux/
├── app/
│   ├── __init__.py
│   ├── alerts.py
│   ├── backup_checks.py
│   ├── linux_checks.py
│   ├── log_analyzer.py
│   ├── main.py
│   ├── monitor.py
│   ├── network_checks.py
│   └── reports.py
├── config/config.json
├── logs/sample.log
├── reports/
├── scripts/health_check.sh
├── tests/
├── requirements.txt
├── .gitignore
└── README.md
```

## Technology Stack

Python 3.11+, `psutil`, `pytest`, JSON, CSV, Bash, Git, VS Code, Anaconda, and Ubuntu through WSL.

## Prerequisites and Installation

The project supports Python 3.11 or newer. Windows development uses a project-local Conda environment at `D:\Linux\.conda`. Ubuntu/WSL uses a separate Linux virtual environment because Windows and Linux environments are not interchangeable.

### Windows Installation

Open Anaconda PowerShell Prompt or PowerShell with Conda available, then run from `D:\Linux`:

```powershell
cd D:\Linux
conda create --prefix .conda python=3.11 -y
conda activate .\.conda
python -m pip install -r requirements.txt
```

The verified Windows environment used Python 3.11 and installed `psutil` and `pytest` from `requirements.txt`.

## Windows Usage

From PowerShell, after activating the project-local environment:

```powershell
conda activate .\.conda
python -m app.main --config config/config.json
```

Run the automated tests with:

```powershell
python -m pytest -q
```

Reports are written under `D:\Linux\reports\`. The default configuration uses the included `logs/sample.log`, so Windows execution does not depend on private Windows event logs or Linux system logs.

## Ubuntu / WSL Usage

If Ubuntu is not installed, open PowerShell as Administrator and run:

```powershell
wsl --install -d Ubuntu
```

Restart if Windows requests it, then open the Ubuntu application. All commands below must be run in the Ubuntu terminal, not PowerShell.

First install Python's virtual-environment support. Use the package matching the Python version reported by `python3 --version`:

```bash
sudo apt update
sudo apt install -y python3.14-venv python3.14-full python3-pip
```

If Ubuntu uses another Python 3 minor version, replace `python3.14-venv` and `python3.14-full` with the matching package names. For example, some releases use `python3-venv` and `python3-full`.

Create a Linux virtual environment in Ubuntu's native home filesystem:

```bash
cd /mnt/d/Linux
mkdir -p ~/.venvs
python3 -m venv ~/.venvs/linux-monitor
source ~/.venvs/linux-monitor/bin/activate
python -m pip install -r requirements.txt
```

The shell prompt should include `(linux-monitor)` after activation. Keep this environment under `~/.venvs`, not `/mnt/d/Linux/.venv`; project files can remain on the Windows-mounted drive while the Linux environment stays on the native Linux filesystem.

Run the application and tests:

```bash
python -m app.main --config config/config.json
python -m pytest -q
```

The routine script is:

```bash
bash scripts/health_check.sh
```

On Linux, `services` in `config/config.json` can contain service names such as `cron` or `ssh`. The tool runs read-only `systemctl is-active` checks. A service status such as `inactive` is reported as information and does not currently create a resource-threshold alert. Reading protected logs may require appropriate user permissions; this project intentionally analyzes only the supplied sample log by default.

## Verified Cross-Platform Results

The same project and configuration were run in both environments:

| Environment | Result | Notes |
| --- | --- | --- |
| Windows project-local Conda environment | `warning` | Memory measured `83.4%`, above the `80%` threshold; network checks passed |
| Ubuntu through WSL | `healthy` | Memory measured `7.6%`; DNS, TCP, and HTTPS checks passed |

Both runs detected the same three sample-log entries. The different resource values are expected because Windows and WSL expose different system views. On Ubuntu, `cron` was active and `ssh` was inactive; service state is reported informationally and does not create a resource alert.

## Configuration

Edit `config/config.json`:

```json
{
  "thresholds": {"cpu": 80, "memory": 80, "disk": 85},
  "log_file": "logs/sample.log",
  "log_levels": ["ERROR", "WARNING", "CRITICAL"],
  "services": ["cron", "ssh"],
  "reports_dir": "reports",
  "network_checks": {
    "enabled": false,
    "timeout_seconds": 3,
    "dns_hosts": ["example.com"],
    "tcp_targets": [{"host": "example.com", "port": 443}],
    "http_endpoints": ["https://example.com"]
  },
  "backup_checks": {
    "enabled": false,
    "targets": [
      {
        "name": "sample_backup",
        "path": "backups/sample_backup.zip",
        "max_age_hours": 24,
        "allow_empty": false
      }
    ]
  }
}
```

Thresholds must be percentages from 0 through 100. Network timeouts must be greater than zero. Backup ages must be zero or greater. Relative paths are resolved from the project root. Missing or unreadable logs become report errors instead of stopping collection.

Set either module's `enabled` value to `false` to disable it. A disabled module produces an empty result section and does not create alerts.

To analyze another readable log, change `log_file` to a relative or absolute path. Do not point the tool at sensitive logs unless the user has permission to read them and the data is safe to handle.

## Reports

Each run creates files like `health_report_20261023T161637Z.json` and `health_report_20261023T161637Z.csv`. JSON contains the UTC generation time, health status, all metrics, collection errors, alerts, matching log entries, Linux service statuses, network check results, and backup check results. CSV contains the original health and log fields plus network and backup check/failure counts. Generated report files are ignored by Git.

Example console summary:

```text
{
  "health_status": "warning",
  "alerts": 1,
  "log_matches": 3,
  "reports": {"json": "reports/...json", "csv": "reports/...csv"}
}
```

## Testing

Run all deterministic tests after activating the relevant environment:

```powershell
python -m pytest -q
```

The tests mock system metrics and external network operations. They cover normal and high values, threshold boundaries, unsupported metrics, log level counting, missing and unreadable logs, alert contents, DNS/TCP/HTTP success and failure, disabled and invalid network configuration, existing/missing/empty/stale backups, disabled and invalid backup configuration, and JSON/CSV output. They never depend on live internet access, real backup locations, or the development computer's actual CPU or memory load.

The verified Windows and WSL runs produced:

```text
Windows: 23 passed
Ubuntu/WSL: 23 passed

Ubuntu/WSL health_status: healthy
Ubuntu/WSL alerts: 0
Ubuntu/WSL log_matches: 3

Windows health_status: warning
Windows alert: memory_percent was 83.4% against an 80% threshold
```

## Troubleshooting

- **`ModuleNotFoundError: psutil`**: activate the intended environment and run `python -m pip install -r requirements.txt`. Do not use the Windows Conda environment from inside WSL.
- **`ensurepip` or `.venv/bin/activate` error in WSL**: install the matching Ubuntu `python3-venv` package, remove the incomplete environment, and recreate it under `~/.venvs/linux-monitor`.
- **`python` command not found in WSL**: activate the Linux environment first with `source ~/.venvs/linux-monitor/bin/activate`, or use `python3` before creating it.
- **Disk metric unavailable**: psutil or the selected filesystem may not support the current runtime. The report records the error and continues; verify the environment with `python -c "import psutil; print(psutil.disk_usage('/'))"` in Ubuntu.
- **Log file not found**: check the relative path in `config/config.json`; relative paths start at the project root.
- **Service status is unsupported**: service checks are Linux-only and require `systemctl`; Windows reports this explicitly.
- **Network checks fail**: confirm the host, port, URL, and timeout in `network_checks`. External connectivity is not guaranteed, so disabled checks produce no network alerts.
- **Backup check is warning or critical**: verify the configured path and age policy. A healthy presence check does not prove backup integrity or recoverability.
- **Permission denied**: use a readable log file or an account with appropriate read permission. Do not grant broad permissions or alter system logs just for this tool.

## Limitations and Future Improvements

This is a lightweight single-run monitor, not a daemon or production alerting service. It does not rotate logs, send email, change services, inspect every operating-system log, or persist historical time series. Future work could add scheduled execution, configurable alert destinations, richer parsers for common log formats, retention policies, service-state alerts, and a dashboard.

## Git and Portfolio Workflow

```bash
git init
git add .
git commit -m "Build Linux server health monitor"
git branch -M main
git remote add origin <your-repository-url>
git push -u origin main
```

Review the generated reports before publishing and keep private logs, credentials, and machine-specific paths out of Git.