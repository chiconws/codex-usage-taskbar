from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import winreg


APP_NAME = "CodexUsageTaskbar"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def startup_command(executable: str | None = None) -> str:
    if executable:
        return subprocess.list2cmdline([executable])
    if getattr(sys, "frozen", False):
        return subprocess.list2cmdline([sys.executable])
    return subprocess.list2cmdline([sys.executable, str(Path(sys.argv[0]).resolve())])


def set_start_with_windows(enabled: bool, executable: str | None = None) -> None:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, startup_command(executable))
            return
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass

