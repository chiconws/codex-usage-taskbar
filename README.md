# Codex Usage Taskbar

[![CI](https://github.com/chiconws/codex-usage-taskbar/actions/workflows/ci.yml/badge.svg)](https://github.com/chiconws/codex-usage-taskbar/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/chiconws/codex-usage-taskbar)](https://github.com/chiconws/codex-usage-taskbar/releases)

A compact Windows 11 taskbar widget for Codex account usage.

It reads rate-limit data from the locally installed, logged-in Codex CLI app-server. It does not read `auth.json`, count tokens, display credits, or send telemetry.

## Features

- Two 128 px rows: 5 hours above Weekly, with reset countdown, percentage, and a graphical bar.
- Defaults to remaining usage; Settings can switch to used usage.
- The 5-hour row is omitted when Codex does not provide that limit.
- Taskbar-docked, draggable, and remembers its position.
- Click for account details and Settings.
- Hides during true fullscreen video or games and returns afterward.

## Screenshots

![Compact taskbar widget](assets/screenshots/taskbar-widget.png)

![Details window](assets/screenshots/details-window.png)

![Settings window](assets/screenshots/settings-window.png)

## Install

Download the latest Windows ZIP from the [GitHub Releases page](https://github.com/chiconws/codex-usage-taskbar/releases), extract it, and run `CodexUsageTaskbar.exe`.

## Run from source

Codex CLI must be installed and logged in.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m codex_usage_taskbar.main
```

Run the tests with Qt's headless mode:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m pytest -q
```

## Build

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\build.ps1
```

The portable executable is written to `dist\CodexUsageTaskbar\CodexUsageTaskbar.exe`.

## License

MIT. See [LICENSE](LICENSE), [CONTRIBUTING.md](CONTRIBUTING.md), and [SECURITY.md](SECURITY.md).
