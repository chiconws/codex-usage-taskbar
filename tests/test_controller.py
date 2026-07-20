from __future__ import annotations

from datetime import datetime, timezone

from codex_usage_taskbar.config import AppConfig, load_config
from codex_usage_taskbar.models import AccountInfo, RateLimitSnapshot, RateLimitWindow
from codex_usage_taskbar.taskbar_widget import TaskbarOverlay
from codex_usage_taskbar.controller import UsageController


SNAPSHOT = RateLimitSnapshot(
    windows=(RateLimitWindow("Weekly", 10080, 26, 74, None),),
    fetched_at=datetime.now(timezone.utc),
)


class SuccessfulClient:
    def set_command(self, command):
        self.command = command

    def read_usage(self):
        return SNAPSHOT


class FailedClient:
    def set_command(self, command):
        self.command = command

    def read_usage(self):
        raise RuntimeError("not authenticated")


class UsageClient:
    def set_command(self, command):
        self.command = command

    def read_usage(self):
        return RateLimitSnapshot(
            windows=SNAPSHOT.windows,
            fetched_at=SNAPSHOT.fetched_at,
            account=AccountInfo(email="person@example.com", plan_type="Pro"),
        )


def test_controller_updates_overlay_from_background_refresh(qtbot, tmp_path):
    overlay = TaskbarOverlay(AppConfig(start_with_windows=False))
    qtbot.addWidget(overlay)
    controller = UsageController(SuccessfulClient(), overlay, tmp_path / "config.json")

    controller.refresh()
    qtbot.waitUntil(lambda: overlay.bar.snapshot.windows == SNAPSHOT.windows, timeout=2000)

    assert overlay.bar.error_message is None
    controller.stop()


def test_controller_refreshes_hidden_details_with_account_metadata_from_read_usage(qtbot, tmp_path):
    overlay = TaskbarOverlay(AppConfig(start_with_windows=False))
    qtbot.addWidget(overlay)
    controller = UsageController(UsageClient(), overlay, tmp_path / "config.json")

    controller.refresh()
    qtbot.waitUntil(lambda: overlay.details.account_value.text() == "person@example.com", timeout=2000)

    assert overlay.details.isVisible() is False
    assert overlay.details.plan_value.text() == "Pro"
    controller.stop()


def test_controller_shows_error_when_refresh_fails(qtbot, tmp_path):
    overlay = TaskbarOverlay(AppConfig(start_with_windows=False))
    qtbot.addWidget(overlay)
    controller = UsageController(FailedClient(), overlay, tmp_path / "config.json")

    controller.refresh()
    qtbot.waitUntil(lambda: overlay.bar.error_message == "not authenticated", timeout=2000)

    controller.stop()


def test_controller_persists_settings_and_updates_startup(qtbot, tmp_path):
    overlay = TaskbarOverlay(AppConfig(start_with_windows=False))
    qtbot.addWidget(overlay)
    startup_values = []
    controller = UsageController(
        SuccessfulClient(),
        overlay,
        tmp_path / "config.json",
        startup_setter=startup_values.append,
    )

    overlay.config_updated.emit(AppConfig(start_with_windows=True, poll_interval_seconds=300))

    saved = (tmp_path / "config.json").read_text(encoding="utf-8")
    assert "300" in saved
    assert startup_values == [True]
    controller.stop()


def test_controller_persists_dragged_taskbar_position(qtbot, tmp_path):
    overlay = TaskbarOverlay(AppConfig(start_with_windows=False, show_usage=True))
    qtbot.addWidget(overlay)
    controller = UsageController(SuccessfulClient(), overlay, tmp_path / "config.json")

    overlay.position_changed.emit(0.42)

    saved = (tmp_path / "config.json").read_text(encoding="utf-8")
    assert "0.42" in saved
    assert load_config(tmp_path / "config.json").show_usage is True
    assert overlay.config.taskbar_position_ratio == 0.42
    controller.stop()
