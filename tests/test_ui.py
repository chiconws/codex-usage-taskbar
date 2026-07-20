from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import win32con
import win32gui
import pytest

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QFont, QFontMetrics, QImage

from codex_usage_taskbar.models import AccountInfo, RateLimitSnapshot, RateLimitWindow
from codex_usage_taskbar.config import AppConfig
from codex_usage_taskbar.taskbar_widget import DetailsDialog, SettingsDialog, TaskbarOverlay, UsageBarWidget
from codex_usage_taskbar.windows import primary_taskbar_handle


def make_snapshot() -> RateLimitSnapshot:
    return RateLimitSnapshot(
        windows=(
            RateLimitWindow("5 hours", 300, 62, 38, None),
            RateLimitWindow("Weekly", 10080, 26, 74, None),
        ),
        fetched_at=datetime.now(timezone.utc),
    )


def snapshot_at(
    when: datetime,
    *,
    remaining: int,
    resets_at: datetime | None,
    duration: int | None = 300,
    label: str = "5 hours",
    has_data: bool = True,
) -> RateLimitSnapshot:
    return RateLimitSnapshot(
        windows=(
            RateLimitWindow(label, duration, 100 - remaining, remaining, resets_at, has_data=has_data),
        ),
        fetched_at=when,
    )


def test_remaining_mode_is_the_default_for_text_and_fill(qtbot):
    widget = UsageBarWidget()
    qtbot.addWidget(widget)
    widget.set_snapshot(make_snapshot())

    assert widget.show_usage is False
    assert widget.display_percentage(widget.snapshot.windows[0]) == 38
    assert widget.display_percentage(widget.snapshot.windows[1]) == 74
    assert widget.fill_fraction(widget.snapshot.windows[0]) == 0.38
    assert widget.fill_fraction(widget.snapshot.windows[1]) == 0.74


def test_usage_mode_uses_used_percentage_for_text_and_fill(qtbot):
    widget = UsageBarWidget()
    qtbot.addWidget(widget)
    widget.set_show_usage(True)
    widget.set_snapshot(make_snapshot())

    assert widget.display_percentage(widget.snapshot.windows[0]) == 62
    assert widget.display_percentage(widget.snapshot.windows[1]) == 26
    assert widget.fill_fraction(widget.snapshot.windows[0]) == 0.62
    assert widget.fill_fraction(widget.snapshot.windows[1]) == 0.26


def test_graphical_bar_grows_to_two_rows(qtbot):
    widget = UsageBarWidget()
    qtbot.addWidget(widget)
    widget.set_snapshot(make_snapshot())

    assert widget.sizeHint().height() >= 40
    assert isinstance(widget.sizeHint(), QSize)


def test_compact_widget_is_narrow_and_keeps_two_vertical_rows(qtbot):
    widget = UsageBarWidget(compact=True)
    qtbot.addWidget(widget)
    widget.set_snapshot(make_snapshot())

    assert widget.sizeHint().width() == 128
    assert widget.sizeHint().height() >= 40
    assert widget.show_countdowns is True
    assert [window.label for window in widget.snapshot.windows] == ["5 hours", "Weekly"]


def test_compact_widget_hides_missing_five_hour_row_and_expands_weekly_row(qtbot):
    widget = UsageBarWidget(compact=True)
    qtbot.addWidget(widget)
    snapshot = RateLimitSnapshot(
        windows=(
            RateLimitWindow("5 hours", 300, 0, 0, None, has_data=False),
            RateLimitWindow("Weekly", 10080, 26, 74, None),
        ),
        fetched_at=datetime.now(timezone.utc),
    )
    widget.set_snapshot(snapshot)

    assert [window.label for window in widget.visible_windows()] == ["Weekly"]
    assert widget.sizeHint().height() > 4 + 21


def test_compact_rows_include_reset_countdowns_in_five_hour_then_weekly_order(qtbot):
    widget = UsageBarWidget(compact=True)
    qtbot.addWidget(widget)
    now = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    snapshot = RateLimitSnapshot(
        windows=(
            RateLimitWindow("5 hours", 300, 62, 38, now + timedelta(hours=1, minutes=30)),
            RateLimitWindow("Weekly", 10080, 26, 74, now + timedelta(days=2, hours=4)),
        ),
        fetched_at=now,
    )
    widget.set_snapshot(snapshot)

    assert widget.show_countdowns is True
    assert [widget.summary_text(window, now) for window in snapshot.windows] == ["1h 30m · 38%", "2d 4h · 74%"]

    details = DetailsDialog()
    qtbot.addWidget(details)
    details.set_snapshot(snapshot)
    assert details.bar.summary_text(snapshot.windows[0], now) == "1h 30m · 38%"
    unavailable = RateLimitWindow("5 hours", 300, 62, 38, None)
    assert details.bar.summary_text(unavailable, now) == "reset time unavailable · 38%"


def test_usage_mode_uses_amber_fill_while_remaining_mode_keeps_existing_colors(qtbot):
    widget = UsageBarWidget()
    qtbot.addWidget(widget)
    low_remaining = RateLimitWindow("5 hours", 300, 90, 10, None)

    assert widget.fill_color(low_remaining).name() == "#c96f7b"
    widget.set_show_usage(True)
    assert widget.fill_color(low_remaining).name() == "#e3a34a"


def test_details_settings_button_emits_signal_and_overlay_opens_settings(qtbot):
    dialog = DetailsDialog()
    qtbot.addWidget(dialog)
    with qtbot.waitSignal(dialog.settings_requested):
        dialog.settings_button.click()

    overlay = TaskbarOverlay(AppConfig(start_with_windows=False))
    qtbot.addWidget(overlay)
    overlay.details.settings_requested.emit()

    assert overlay.details.settings_button.text() == "Settings"
    assert overlay._settings is not None
    overlay.close()


def test_unexpected_reset_alert_persists_until_details_is_opened(qtbot):
    overlay = TaskbarOverlay(AppConfig(start_with_windows=False))
    qtbot.addWidget(overlay)
    now = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    key = "5 hours"
    overlay.set_snapshot(snapshot_at(now, remaining=35, resets_at=now + timedelta(hours=2)))
    overlay.set_snapshot(snapshot_at(now + timedelta(minutes=5), remaining=100, resets_at=now + timedelta(hours=5)))

    assert overlay.bar.alert_keys == {key}
    assert overlay.details.bar.alert_keys == {key}
    overlay.show_details()
    assert overlay.bar.alert_keys == set()
    assert overlay.details.bar.alert_keys == set()
    overlay.close()


@pytest.mark.parametrize("previous_duration, current_duration", [(300, None), (None, 300)])
def test_unexpected_reset_alert_matches_mixed_duration_rows_by_label(qtbot, previous_duration, current_duration):
    overlay = TaskbarOverlay(AppConfig(start_with_windows=False))
    qtbot.addWidget(overlay)
    now = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    previous = snapshot_at(
        now,
        remaining=35,
        resets_at=now + timedelta(hours=2),
        duration=previous_duration,
    )
    current = snapshot_at(
        now + timedelta(minutes=5),
        remaining=100,
        resets_at=now + timedelta(hours=5),
        duration=current_duration,
    )

    overlay.set_snapshot(previous)
    overlay.set_snapshot(current)

    assert overlay.bar.alert_keys == {UsageBarWidget.alert_key(current.windows[0])}
    overlay.close()


@pytest.mark.parametrize("alert_duration, later_duration", [(300, None), (None, 300)])
def test_unexpected_reset_alert_keeps_stable_identity_when_later_row_changes_form(
    qtbot, alert_duration, later_duration
):
    overlay = TaskbarOverlay(AppConfig(start_with_windows=False))
    qtbot.addWidget(overlay)
    now = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    prior = snapshot_at(
        now,
        remaining=35,
        resets_at=now + timedelta(hours=2),
        duration=alert_duration,
    )
    alerting = snapshot_at(
        now + timedelta(minutes=5),
        remaining=100,
        resets_at=now + timedelta(hours=5),
        duration=alert_duration,
    )
    later = snapshot_at(
        now + timedelta(minutes=10),
        remaining=90,
        resets_at=now + timedelta(hours=4),
        duration=later_duration,
    )

    overlay.set_snapshot(prior)
    overlay.set_snapshot(alerting)
    assert overlay.bar.alert_keys == {"5 hours"}

    overlay.set_snapshot(later)

    assert overlay.bar.alert_keys == {"5 hours"}
    assert UsageBarWidget.alert_key(later.windows[0]) in overlay.bar.alert_keys
    overlay.close()


def test_compact_unavailable_reset_summary_fits_with_alert_indicator(qtbot):
    widget = UsageBarWidget(compact=True)
    qtbot.addWidget(widget)
    now = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    snapshot = snapshot_at(now, remaining=38, resets_at=None)
    widget.set_snapshot(snapshot)
    widget.set_alert_keys({"5 hours"})
    widget.resize(widget.sizeHint())

    window = snapshot.windows[0]
    font = QFont(widget.font())
    font.setPointSize(8)
    font.setWeight(QFont.Weight.DemiBold)
    metrics = QFontMetrics(font)
    summary = widget.summary_text(window, now)
    summary_width = metrics.horizontalAdvance(summary)
    margin = 6
    summary_x = widget.width() - margin - summary_width
    indicator_x = summary_x - 8

    assert summary == "n/a · 38%"
    assert summary_width + 8 + (2 * margin) <= widget.width()
    assert indicator_x >= 0
    assert summary_x + summary_width <= widget.width() - margin


def test_alert_key_renders_visible_red_indicator_pixels_in_compact_row(qtbot):
    widget = UsageBarWidget(compact=True)
    qtbot.addWidget(widget)
    widget.set_snapshot(snapshot_at(
        datetime(2026, 7, 15, 12, 5, tzinfo=timezone.utc),
        remaining=100,
        resets_at=datetime(2026, 7, 15, 17, 0, tzinfo=timezone.utc),
        duration=None,
    ))
    widget.set_alert_keys({"5 hours"})
    widget.resize(widget.sizeHint())

    image = QImage(widget.size(), QImage.Format.Format_ARGB32)
    image.fill(0)
    widget.render(image)

    red_pixels = sum(
        1
        for x in range(image.width())
        for y in range(image.height())
        if (color := image.pixelColor(x, y)).red() > 170
        and color.red() > color.green() * 1.35
        and color.red() > color.blue() * 1.35
    )
    assert red_pixels >= 8


def test_unexpected_reset_alert_does_not_retrigger_until_usage_drops_below_full(qtbot):
    overlay = TaskbarOverlay(AppConfig(start_with_windows=False))
    qtbot.addWidget(overlay)
    now = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    reset = now + timedelta(hours=2)
    overlay.set_snapshot(snapshot_at(now, remaining=35, resets_at=reset))
    overlay.set_snapshot(snapshot_at(now + timedelta(minutes=5), remaining=100, resets_at=reset))
    overlay.show_details()
    overlay.set_snapshot(snapshot_at(now + timedelta(minutes=10), remaining=100, resets_at=reset))

    assert overlay.bar.alert_keys == set()
    overlay.close()


@pytest.mark.parametrize(
    ("previous", "current"),
    [
        (snapshot_at(datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc), remaining=35, resets_at=datetime(2026, 7, 15, 14, 0, tzinfo=timezone.utc)), None),
        (snapshot_at(datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc), remaining=35, resets_at=datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)), snapshot_at(datetime(2026, 7, 15, 12, 5, tzinfo=timezone.utc), remaining=100, resets_at=datetime(2026, 7, 15, 17, 0, tzinfo=timezone.utc))),
        (snapshot_at(datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc), remaining=35, resets_at=None), snapshot_at(datetime(2026, 7, 15, 12, 5, tzinfo=timezone.utc), remaining=100, resets_at=datetime(2026, 7, 15, 17, 0, tzinfo=timezone.utc))),
        (snapshot_at(datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc), remaining=35, resets_at=datetime(2026, 7, 15, 14, 0, tzinfo=timezone.utc)), snapshot_at(datetime(2026, 7, 15, 12, 5, tzinfo=timezone.utc), remaining=100, resets_at=None)),
        (snapshot_at(datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc), remaining=35, resets_at=datetime(2026, 7, 15, 14, 0, tzinfo=timezone.utc), has_data=False), snapshot_at(datetime(2026, 7, 15, 12, 5, tzinfo=timezone.utc), remaining=100, resets_at=datetime(2026, 7, 15, 17, 0, tzinfo=timezone.utc))),
    ],
)
def test_unexpected_reset_alert_is_suppressed_for_non_alerting_snapshots(qtbot, previous, current):
    overlay = TaskbarOverlay(AppConfig(start_with_windows=False))
    qtbot.addWidget(overlay)
    overlay.set_snapshot(previous)
    if current is not None:
        overlay.set_snapshot(current)

    assert overlay.bar.alert_keys == set()
    overlay.close()


def test_widget_preserves_limit_label_casing(qtbot):
    widget = UsageBarWidget(compact=True)
    qtbot.addWidget(widget)

    assert widget.display_label(make_snapshot().windows[0]) == "5 hours"
    assert widget.display_label(make_snapshot().windows[1]) == "Weekly"


def test_placeholder_bar_has_no_fill(qtbot):
    widget = UsageBarWidget(compact=True)
    qtbot.addWidget(widget)
    placeholder = RateLimitWindow("5 hours", 300, 0, 0, None, has_data=False)
    widget.set_show_usage(True)

    assert widget.display_percentage(placeholder) == 0
    assert widget.fill_fraction(placeholder) == 0.0


def test_details_dialog_shows_account_metadata_and_unavailable_values(qtbot):
    dialog = DetailsDialog()
    qtbot.addWidget(dialog)
    snapshot = RateLimitSnapshot(
        windows=make_snapshot().windows,
        fetched_at=datetime.now(timezone.utc),
        account=AccountInfo(email="person@example.com", plan_type="Pro"),
    )

    dialog.set_snapshot(snapshot)

    assert dialog.plan_value.text() == "Pro"
    assert dialog.account_value.text() == "person@example.com"

    dialog.set_snapshot(
        RateLimitSnapshot(
            windows=make_snapshot().windows,
            fetched_at=datetime.now(timezone.utc),
            account=AccountInfo(email=None, plan_type=None),
        )
    )

    assert dialog.plan_value.text() == "Unavailable"
    assert dialog.account_value.text() == "Unavailable"

    dialog.set_snapshot(
        RateLimitSnapshot(
            windows=make_snapshot().windows,
            fetched_at=datetime.now(timezone.utc),
        )
    )

    assert dialog.plan_value.text() == "Unavailable"
    assert dialog.account_value.text() == "Unavailable"

    dialog.set_snapshot(
        RateLimitSnapshot(
            windows=make_snapshot().windows,
            fetched_at=datetime.now(timezone.utc),
            account=AccountInfo(email="person@example.com", plan_type=None),
        )
    )

    assert dialog.plan_value.text() == "Unavailable"
    assert dialog.account_value.text() == "person@example.com"


def test_taskbar_overlay_uses_the_same_usage_mode_for_both_bars(qtbot):
    overlay = TaskbarOverlay(AppConfig(start_with_windows=False, show_usage=True))
    qtbot.addWidget(overlay)

    assert overlay.bar.show_usage is True
    assert overlay.details.bar.show_usage is True

    overlay.close()


def test_taskbar_overlay_updates_hidden_details_with_snapshot_metadata(qtbot):
    overlay = TaskbarOverlay(AppConfig(start_with_windows=False))
    qtbot.addWidget(overlay)
    snapshot = RateLimitSnapshot(
        windows=make_snapshot().windows,
        fetched_at=datetime.now(timezone.utc),
        account=AccountInfo(email="person@example.com", plan_type="Pro"),
    )

    overlay.set_snapshot(snapshot)

    assert overlay.details.isVisible() is False
    assert overlay.details.plan_value.text() == "Pro"
    assert overlay.details.account_value.text() == "person@example.com"
    overlay.close()


def test_taskbar_overlay_preserves_hidden_details_error_until_next_snapshot(qtbot):
    overlay = TaskbarOverlay(AppConfig(start_with_windows=False))
    qtbot.addWidget(overlay)
    snapshot = make_snapshot()
    overlay.set_snapshot(snapshot)

    overlay.set_error("Refresh failed; showing stale data")
    assert overlay.details.isVisible() is False

    overlay.show_details()
    assert overlay.details.status_label.text() == "Refresh failed; showing stale data"

    overlay.set_snapshot(snapshot)
    assert overlay.details.status_label.text().startswith("Last refreshed:")
    overlay.close()


def test_compact_bar_emits_drag_signals_instead_of_clicking_details(qtbot):
    widget = UsageBarWidget(compact=True)
    qtbot.addWidget(widget)
    drag_started = []
    drag_moved = []
    widget.drag_started.connect(drag_started.append)
    widget.drag_moved.connect(drag_moved.append)

    qtbot.mousePress(widget, Qt.MouseButton.LeftButton, pos=QPoint(10, 10))
    qtbot.mouseMove(widget, QPoint(40, 10), delay=10)
    qtbot.mouseRelease(widget, Qt.MouseButton.LeftButton, pos=QPoint(40, 10))

    assert drag_started
    assert drag_moved


def test_details_dialog_does_not_show_tokens_or_credits(qtbot):
    dialog = DetailsDialog()
    qtbot.addWidget(dialog)
    dialog.set_snapshot(make_snapshot())

    visible_text = " ".join(label.text() for label in dialog.findChildren(type(dialog.status_label)))
    assert "token" not in visible_text.lower()
    assert "credit" not in visible_text.lower()
    assert dialog.bar.show_countdowns is True


def test_taskbar_overlay_can_show_without_activation(qtbot):
    overlay = TaskbarOverlay(AppConfig(start_with_windows=False))
    qtbot.addWidget(overlay)
    overlay.show()
    qtbot.wait(20)

    assert overlay.isVisible()
    overlay.close()


def test_settings_dialog_saves_show_usage_checkbox_with_other_config_values(qtbot):
    dialog = SettingsDialog(
        AppConfig(
            start_with_windows=False,
            show_usage=False,
            poll_interval_seconds=300,
            codex_command="C:/tools/codex.exe",
            taskbar_position_ratio=0.42,
        )
    )
    qtbot.addWidget(dialog)
    saved = []
    dialog.config_saved.connect(saved.append)

    assert dialog.show_usage_checkbox.isChecked() is False
    dialog.show_usage_checkbox.setChecked(True)
    dialog._save()

    assert saved[0] == AppConfig(
        start_with_windows=False,
        show_usage=True,
        poll_interval_seconds=300,
        codex_command="C:/tools/codex.exe",
        taskbar_position_ratio=0.42,
    )


def test_taskbar_overlay_propagates_show_usage_to_both_bars_immediately(qtbot):
    overlay = TaskbarOverlay(AppConfig(start_with_windows=False, show_usage=False))
    qtbot.addWidget(overlay)

    assert overlay.bar.show_usage is False
    assert overlay.details.bar.show_usage is False

    overlay._apply_config(AppConfig(start_with_windows=True, poll_interval_seconds=300, show_usage=True))

    assert overlay.config.show_usage is True
    assert overlay.bar.show_usage is True
    assert overlay.details.bar.show_usage is True
    overlay.close()


def test_taskbar_overlay_preserves_show_usage_when_finishing_drag(qtbot):
    overlay = TaskbarOverlay(AppConfig(start_with_windows=False, show_usage=True))
    qtbot.addWidget(overlay)
    overlay._drag_ratio = 0.42

    overlay._finish_drag()

    assert overlay.config.show_usage is True
    overlay.close()


@pytest.mark.skipif(os.environ.get("QT_QPA_PLATFORM") == "offscreen", reason="offscreen Qt has no Win32 HWND")
def test_taskbar_overlay_is_owned_by_the_native_taskbar(qtbot):
    taskbar = primary_taskbar_handle()
    assert taskbar
    overlay = TaskbarOverlay(AppConfig(start_with_windows=False))
    qtbot.addWidget(overlay)
    overlay.show()
    qtbot.waitUntil(lambda: win32gui.GetWindow(int(overlay.winId()), win32con.GW_OWNER) == taskbar, timeout=1000)

    style = win32gui.GetWindowLong(int(overlay.winId()), win32con.GWL_STYLE)
    assert not style & win32con.WS_CHILD
    assert style & win32con.WS_POPUP
    overlay.close()
