from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .codex_client import CodexAppServerClient
from .config import default_config_path, load_config, save_config
from .controller import UsageController
from .startup import set_start_with_windows
from .taskbar_widget import TaskbarOverlay


def _application_icon_path() -> Path:
    """Find the bundled icon in both source and PyInstaller environments."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "assets" / "codex_usage_icon.ico"
    return Path(__file__).resolve().parents[2] / "assets" / "codex_usage_icon.ico"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Codex Usage Taskbar")
    icon_path = _application_icon_path()
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    app.setQuitOnLastWindowClosed(False)

    config_path = default_config_path()
    config = load_config(config_path)
    save_config(config_path, config)
    set_start_with_windows(config.start_with_windows)

    overlay = TaskbarOverlay(config)
    overlay.show()
    client = CodexAppServerClient(command=config.codex_command)
    controller = UsageController(client, overlay, config_path)
    controller.refresh()
    app.aboutToQuit.connect(controller.stop)
    app.aboutToQuit.connect(overlay.close)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
