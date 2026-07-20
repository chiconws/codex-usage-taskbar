from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_POLL_INTERVAL_SECONDS = 60
ALLOWED_POLL_INTERVALS = (30, 60, 300)


@dataclass(frozen=True, slots=True)
class AppConfig:
    start_with_windows: bool = True
    show_usage: bool = False
    poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS
    codex_command: str | None = None
    taskbar_position_ratio: float | None = None


def default_config_path() -> Path:
    app_data = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return app_data / "CodexUsageTaskbar" / "config.json"


def load_config(path: Path) -> AppConfig:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return AppConfig()
        poll_interval = raw.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS)
        if poll_interval not in ALLOWED_POLL_INTERVALS:
            return AppConfig()
        command = raw.get("codex_command")
        if command is not None and not isinstance(command, str):
            return AppConfig()
        position_ratio = raw.get("taskbar_position_ratio")
        if position_ratio is not None:
            if isinstance(position_ratio, bool):
                return AppConfig()
            try:
                position_ratio = float(position_ratio)
            except (TypeError, ValueError):
                return AppConfig()
            if not 0.0 <= position_ratio <= 1.0:
                return AppConfig()
        show_usage = raw.get("show_usage", False)
        if not isinstance(show_usage, bool):
            show_usage = False
        return AppConfig(
            start_with_windows=bool(raw.get("start_with_windows", True)),
            show_usage=show_usage,
            poll_interval_seconds=poll_interval,
            codex_command=command or None,
            taskbar_position_ratio=position_ratio,
        )
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return AppConfig()


def save_config(path: Path, config: AppConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(config), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
