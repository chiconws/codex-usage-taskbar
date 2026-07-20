from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal

from .codex_client import CodexAppServerClient
from .config import AppConfig, save_config
from .startup import set_start_with_windows
from .taskbar_widget import TaskbarOverlay


class _RefreshSignals(QObject):
    snapshot_ready = Signal(object)
    error = Signal(str)


class _RefreshTask(QRunnable):
    def __init__(self, client: CodexAppServerClient) -> None:
        super().__init__()
        self.client = client
        self.signals = _RefreshSignals()

    def run(self) -> None:
        try:
            snapshot = self.client.read_usage()
        except Exception as exc:  # worker boundary: convert all failures to UI-safe text
            self.signals.error.emit(str(exc) or "Codex usage refresh failed")
        else:
            self.signals.snapshot_ready.emit(snapshot)


class UsageController(QObject):
    """Coordinate background refreshes, persistence, and taskbar UI state."""

    def __init__(
        self,
        client: CodexAppServerClient,
        overlay: TaskbarOverlay,
        config_path: Path,
        startup_setter: Callable[[bool], None] = set_start_with_windows,
    ) -> None:
        super().__init__(overlay)
        self.client = client
        self.overlay = overlay
        self.config_path = config_path
        self.startup_setter = startup_setter
        self._pool = QThreadPool.globalInstance()
        self._active = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(overlay.config.poll_interval_seconds * 1000)
        overlay.refresh_requested.connect(self.refresh)
        overlay.details.refresh_requested.connect(self.refresh)
        overlay.config_updated.connect(self._apply_config)
        overlay.position_changed.connect(self._save_position)
        overlay.open_codex_requested.connect(self.open_codex)

    def refresh(self) -> None:
        if self._active:
            return
        self._active = True
        task = _RefreshTask(self.client)
        task.signals.snapshot_ready.connect(self._on_snapshot)
        task.signals.error.connect(self._on_error)
        self._pool.start(task)

    def stop(self) -> None:
        self._timer.stop()

    def _on_snapshot(self, snapshot) -> None:
        self._active = False
        self.overlay.set_snapshot(snapshot)

    def _on_error(self, message: str) -> None:
        self._active = False
        self.overlay.set_error(message)

    def _apply_config(self, config: AppConfig) -> None:
        self.client.set_command(config.codex_command)
        save_config(self.config_path, config)
        self.startup_setter(config.start_with_windows)
        self._timer.start(config.poll_interval_seconds * 1000)

    def _save_position(self, ratio: float) -> None:
        config = AppConfig(
            start_with_windows=self.overlay.config.start_with_windows,
            show_usage=self.overlay.config.show_usage,
            poll_interval_seconds=self.overlay.config.poll_interval_seconds,
            codex_command=self.overlay.config.codex_command,
            taskbar_position_ratio=ratio,
        )
        self.overlay.config = config
        save_config(self.config_path, config)

    def open_codex(self) -> None:
        executable = shutil.which("codex")
        if executable is None:
            self.overlay.set_error("Codex executable was not found")
            return
        try:
            subprocess.Popen(
                [executable, "app"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as exc:
            self.overlay.set_error(f"Could not open Codex: {exc}")
