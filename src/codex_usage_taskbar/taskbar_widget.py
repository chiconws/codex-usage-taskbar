from __future__ import annotations

import shutil
from datetime import datetime, timezone

from PySide6.QtCore import QPoint, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPalette, QPen
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .config import ALLOWED_POLL_INTERVALS, AppConfig
from .formatting import format_countdown, format_percentage
from .models import RateLimitSnapshot, RateLimitWindow
from .windows import (
    move_taskbar_child_to_screen_x,
    overlay_window_rect,
    primary_taskbar_handle,
    position_overlay,
    prepare_overlay,
    taskbar_overlay_should_be_visible,
)


class UsageBarWidget(QWidget):
    COMPACT_WIDTH = 128

    left_clicked = Signal()
    right_clicked = Signal(QPoint)
    drag_started = Signal(QPoint)
    drag_moved = Signal(QPoint)
    drag_finished = Signal()

    def __init__(self, parent: QWidget | None = None, *, compact: bool = False) -> None:
        super().__init__(parent)
        self.compact = compact
        self.show_countdowns = True
        self.show_usage = False
        self.alert_keys: set[int | str] = set()
        self.snapshot = RateLimitSnapshot((), datetime.now(timezone.utc))
        self.error_message: str | None = "Loading Codex usage..."
        self.stale_message: str | None = None
        self._press_global: QPoint | None = None
        self._dragging = False
        self.setMinimumWidth(self.COMPACT_WIDTH if compact else 250)
        if compact:
            self.setFixedWidth(self.COMPACT_WIDTH)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)

    def set_snapshot(self, snapshot: RateLimitSnapshot) -> None:
        self.snapshot = snapshot
        self.error_message = None
        self.stale_message = None
        self.updateGeometry()
        self.update()

    def set_error(self, message: str) -> None:
        if self.snapshot.windows:
            self.stale_message = message
            self.error_message = None
        else:
            self.error_message = message
        self.updateGeometry()
        self.update()

    def set_show_usage(self, show_usage: bool) -> None:
        self.show_usage = show_usage
        self.update()

    def set_alert_keys(self, alert_keys: set[int | str]) -> None:
        self.alert_keys = set(alert_keys)
        self.update()

    def visible_windows(self) -> tuple[RateLimitWindow, ...]:
        return tuple(
            window
            for window in self.snapshot.windows
            if window.has_data or self.alert_key(window) != "5 hours"
        )

    def display_percentage(self, window: RateLimitWindow) -> int:
        if not window.has_data:
            return 0
        return window.used_percent if self.show_usage else window.remaining_percent

    def fill_fraction(self, window: RateLimitWindow) -> float:
        return max(0.0, min(1.0, self.display_percentage(window) / 100))

    def fill_color(self, window: RateLimitWindow, accent: QColor | None = None) -> QColor:
        if self.show_usage:
            return QColor("#e3a34a")
        if window.remaining_percent <= 10:
            return QColor("#c96f7b")
        if window.remaining_percent <= 25:
            return QColor("#d0a15c")
        return QColor(accent or self.palette().color(QPalette.ColorRole.Highlight))

    @staticmethod
    def display_label(window: RateLimitWindow) -> str:
        return window.label

    def summary_text(self, window: RateLimitWindow, now: datetime) -> str:
        if not window.has_data:
            return "—" if self.compact else "No data"
        percentage = format_percentage(self.display_percentage(window)).replace(" remaining", "")
        if self.show_countdowns:
            countdown = format_countdown(window.resets_at, now)
            if self.compact and countdown == "reset time unavailable":
                countdown = "n/a"
            return f"{countdown} · {percentage}"
        return percentage

    @staticmethod
    def alert_key(window: RateLimitWindow) -> int | str:
        if window.window_duration_mins == 300 or window.label == "5 hours":
            return "5 hours"
        if window.window_duration_mins == 10080 or window.label == "Weekly":
            return "Weekly"
        return window.window_duration_mins if window.window_duration_mins is not None else window.label

    def sizeHint(self) -> QSize:
        width = self.COMPACT_WIDTH if self.compact else 250
        windows = self.visible_windows()
        if self.error_message or not windows:
            return QSize(width, 28)
        row_height = 30 if self.compact and len(windows) == 1 else (21 if self.compact else 23)
        return QSize(width, 4 + len(windows) * row_height)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_global = event.globalPosition().toPoint()
            self._dragging = False
            event.accept()
            return
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit(event.position().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._press_global is not None and event.buttons() & Qt.MouseButton.LeftButton:
            global_position = event.globalPosition().toPoint()
            if not self._dragging:
                distance = (global_position - self._press_global).manhattanLength()
                if distance < QApplication.startDragDistance():
                    return
                self._dragging = True
                self.drag_started.emit(self._press_global)
            self.drag_moved.emit(global_position)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self._dragging:
                self.drag_finished.emit()
            else:
                self.left_clicked.emit()
            self._press_global = None
            self._dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        background = self.palette().color(QPalette.ColorRole.Window)
        if background.lightness() > 160:
            background = QColor(245, 245, 248, 238)
            text_color = QColor("#25232b")
            track_color = QColor("#d8d6de")
        else:
            background = QColor(30, 29, 37, 238)
            text_color = QColor("#f5f2fb")
            track_color = QColor("#4b4857")
        painter.setBrush(background)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 7, 7)

        windows = self.visible_windows()
        if self.error_message or not windows:
            painter.setPen(QPen(text_color))
            painter.drawText(self.rect().adjusted(10, 0, -10, 0), Qt.AlignmentFlag.AlignVCenter, self.error_message or "No usage data")
            painter.end()
            return

        now = datetime.now(timezone.utc)
        margin = 6 if self.compact else 9
        single_compact_row = self.compact and len(windows) == 1
        row_height = 30 if single_compact_row else (21 if self.compact else 23)
        label_offset = 14 if single_compact_row else 10
        bar_offset = 18 if single_compact_row else 14
        bar_height = 6 if single_compact_row else (4 if self.compact else 5)
        accent = self.palette().color(QPalette.ColorRole.Highlight)
        for index, window in enumerate(windows):
            y = 3 + index * row_height
            label_font = QFont(self.font())
            label_font.setPointSize(8 if self.compact else max(8, self.font().pointSize()))
            label_font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(label_font)
            painter.setPen(QPen(text_color))
            label = self.display_label(window)
            painter.drawText(margin, y + label_offset, label)

            summary = self.summary_text(window, now)
            summary_width = painter.fontMetrics().horizontalAdvance(summary)
            summary_x = max(
                margin + painter.fontMetrics().horizontalAdvance(label) + 2,
                self.width() - margin - summary_width,
            )
            painter.drawText(summary_x, y + 10, summary)
            if self.alert_key(window) in self.alert_keys:
                indicator_x = summary_x - 8
                painter.setBrush(QColor("#c94848"))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(indicator_x, y + 2, 8, 8)
                indicator_font = QFont(label_font)
                indicator_font.setPointSize(6)
                indicator_font.setWeight(QFont.Weight.Bold)
                painter.setFont(indicator_font)
                painter.setPen(QPen(QColor("#ffffff")))
                painter.drawText(indicator_x, y + 1, 8, 9, Qt.AlignmentFlag.AlignCenter, "!")

            bar_rect = self.rect().adjusted(margin, 0, -margin, 0)
            bar_rect.setTop(y + bar_offset)
            bar_rect.setHeight(bar_height)
            painter.setBrush(track_color)
            painter.drawRoundedRect(bar_rect, 2.5, 2.5)
            if window.has_data:
                painter.setBrush(self.fill_color(window, accent))
                fill_width = int(bar_rect.width() * self.fill_fraction(window))
                if fill_width > 0:
                    fill_rect = bar_rect.adjusted(0, 0, fill_width - bar_rect.width(), 0)
                    painter.drawRoundedRect(fill_rect, 2.5, 2.5)
        if self.stale_message:
            painter.setPen(QPen(QColor("#c96f7b"), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -2, -2), 7, 7)
        painter.end()


class DetailsDialog(QDialog):
    refresh_requested = Signal()
    settings_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Codex usage")
        self.setMinimumWidth(390)
        self.status_label = QLabel("No usage data")
        self.status_label.setWordWrap(True)
        self.bar = UsageBarWidget(self)
        self.bar.setMinimumWidth(360)
        self.plan_value = QLabel("Unavailable")
        self.account_value = QLabel("Unavailable")
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_requested)
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.settings_requested)

        layout = QVBoxLayout(self)
        account_form = QFormLayout()
        account_form.addRow("Plan", self.plan_value)
        account_form.addRow("Account", self.account_value)
        layout.addLayout(account_form)
        layout.addWidget(self.bar)
        layout.addWidget(self.status_label)
        actions = QHBoxLayout()
        actions.addWidget(self.refresh_button)
        actions.addWidget(self.settings_button)
        layout.addLayout(actions)

    def set_snapshot(self, snapshot: RateLimitSnapshot) -> None:
        self.bar.set_snapshot(snapshot)
        account = snapshot.account
        self.plan_value.setText(account.plan_type if account and account.plan_type else "Unavailable")
        self.account_value.setText(account.email if account and account.email else "Unavailable")
        self.status_label.setText(f"Last refreshed: {snapshot.fetched_at.astimezone().strftime('%Y-%m-%d %H:%M:%S')}")

    def set_show_usage(self, show_usage: bool) -> None:
        self.bar.set_show_usage(show_usage)

    def set_error(self, message: str) -> None:
        self.bar.set_error(message)
        self.status_label.setText(message)


class SettingsDialog(QDialog):
    config_saved = Signal(object)

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Codex usage settings")
        self.config = config
        self.start_checkbox = QCheckBox("Start with Windows")
        self.start_checkbox.setChecked(config.start_with_windows)
        self.show_usage_checkbox = QCheckBox("Show usage instead of remaining")
        self.show_usage_checkbox.setChecked(config.show_usage)
        self.interval_combo = QComboBox()
        for seconds in ALLOWED_POLL_INTERVALS:
            label = f"{seconds} seconds" if seconds < 60 else f"{seconds // 60} minutes"
            self.interval_combo.addItem(label, seconds)
        index = self.interval_combo.findData(config.poll_interval_seconds)
        self.interval_combo.setCurrentIndex(max(0, index))
        self.command_edit: QLineEdit | None = None

        form = QFormLayout()
        form.addRow(self.start_checkbox)
        form.addRow(self.show_usage_checkbox)
        form.addRow("Refresh interval", self.interval_combo)
        if config.codex_command or shutil.which("codex") is None:
            self.command_edit = QLineEdit(config.codex_command or "")
            browse = QPushButton("Browse")
            browse.clicked.connect(self._browse_command)
            command_row = QWidget(self)
            command_layout = QHBoxLayout(command_row)
            command_layout.setContentsMargins(0, 0, 0, 0)
            command_layout.addWidget(self.command_edit)
            command_layout.addWidget(browse)
            form.addRow("Codex executable", command_row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _save(self) -> None:
        command = self.config.codex_command
        if self.command_edit is not None:
            command = self.command_edit.text().strip() or None
        config = AppConfig(
            start_with_windows=self.start_checkbox.isChecked(),
            show_usage=self.show_usage_checkbox.isChecked(),
            poll_interval_seconds=int(self.interval_combo.currentData()),
            codex_command=command,
            taskbar_position_ratio=self.config.taskbar_position_ratio,
        )
        self.config_saved.emit(config)
        self.accept()

    def _browse_command(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Codex executable")
        if path and self.command_edit is not None:
            self.command_edit.setText(path)


class TaskbarOverlay(QWidget):
    """A compact top-level window owned and positioned by the primary taskbar."""

    refresh_requested = Signal()
    open_codex_requested = Signal()
    config_updated = Signal(object)
    position_changed = Signal(float)

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.bar = UsageBarWidget(self, compact=True)
        self.details = DetailsDialog(self)
        self.bar.set_show_usage(config.show_usage)
        self.details.set_show_usage(config.show_usage)
        self._snapshot: RateLimitSnapshot | None = None
        self._details_error: str | None = None
        self._pending_alert_keys: set[int | str] = set()
        self._settings: SettingsDialog | None = None
        self._drag_anchor_x: int | None = None
        self._drag_ratio: float | None = None
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.bar)
        self.bar.left_clicked.connect(self.show_details)
        self.bar.right_clicked.connect(self.show_context_menu)
        self.bar.drag_started.connect(self._begin_drag)
        self.bar.drag_moved.connect(self._move_drag)
        self.bar.drag_finished.connect(self._finish_drag)
        self.details.settings_requested.connect(self.show_settings)
        self._position_timer = QTimer(self)
        self._position_timer.timeout.connect(self.relocate)
        self._position_timer.start(2000)
        self._visibility_timer = QTimer(self)
        self._visibility_timer.timeout.connect(self._update_visibility)
        self._visibility_timer.start(250)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        prepare_overlay(self)
        # Qt may finish applying the top-level window state after showEvent
        # returns. Establish the Win32 owner on the next event-loop turn so Qt
        # cannot immediately clear it again.
        QTimer.singleShot(0, self.relocate)

    def relocate(self) -> None:
        if self._drag_anchor_x is None:
            position_overlay(self, self.config.taskbar_position_ratio)

    def _update_visibility(self) -> None:
        taskbar_hwnd = primary_taskbar_handle()
        if taskbar_hwnd is None:
            return
        should_be_visible = taskbar_overlay_should_be_visible(taskbar_hwnd, int(self.winId()))
        if should_be_visible == self.isVisible():
            return
        if should_be_visible:
            self.show()
        else:
            self.hide()

    def _begin_drag(self, global_position: QPoint) -> None:
        rect = overlay_window_rect(self)
        self._drag_anchor_x = global_position.x() - rect[0]
        self._drag_ratio = self.config.taskbar_position_ratio

    def _move_drag(self, global_position: QPoint) -> None:
        if self._drag_anchor_x is None:
            return
        ratio = move_taskbar_child_to_screen_x(self, global_position.x() - self._drag_anchor_x)
        if ratio is not None:
            self._drag_ratio = ratio

    def _finish_drag(self) -> None:
        ratio = self._drag_ratio
        self._drag_anchor_x = None
        self._drag_ratio = None
        if ratio is None:
            return
        self.config = AppConfig(
            start_with_windows=self.config.start_with_windows,
            show_usage=self.config.show_usage,
            poll_interval_seconds=self.config.poll_interval_seconds,
            codex_command=self.config.codex_command,
            taskbar_position_ratio=ratio,
        )
        self.position_changed.emit(ratio)

    def set_snapshot(self, snapshot: RateLimitSnapshot) -> None:
        if self._snapshot is not None:
            self._pending_alert_keys.update(self._unexpected_reset_alerts(self._snapshot, snapshot))
        self._snapshot = snapshot
        self._details_error = None
        self.bar.set_snapshot(snapshot)
        self.details.set_snapshot(snapshot)
        self._apply_alert_keys()

    @staticmethod
    def _unexpected_reset_alerts(previous: RateLimitSnapshot, current: RateLimitSnapshot) -> set[int | str]:
        alert_keys: set[int | str] = set()
        for window in current.windows:
            prior = next(
                (
                    candidate
                    for candidate in previous.windows
                    if window.window_duration_mins is not None
                    and candidate.window_duration_mins == window.window_duration_mins
                ),
                None,
            )
            if prior is None:
                prior = next((candidate for candidate in previous.windows if candidate.label == window.label), None)
            if (
                prior is not None
                and prior.has_data
                and window.has_data
                and prior.resets_at is not None
                and window.resets_at is not None
                and prior.remaining_percent < 100
                and window.remaining_percent == 100
                and prior.resets_at > current.fetched_at
            ):
                alert_keys.add(UsageBarWidget.alert_key(window))
        return alert_keys

    def _apply_alert_keys(self) -> None:
        self.bar.set_alert_keys(self._pending_alert_keys)
        self.details.bar.set_alert_keys(self._pending_alert_keys)

    def set_error(self, message: str) -> None:
        self._details_error = message
        self.bar.set_error(message)
        self.details.set_error(message)

    def show_details(self) -> None:
        if self._snapshot is not None:
            self.details.set_snapshot(self._snapshot)
        if self._details_error is not None:
            self.details.set_error(self._details_error)
        self._pending_alert_keys.clear()
        self._apply_alert_keys()
        self.details.show()
        self.details.raise_()
        self.details.activateWindow()

    def show_context_menu(self, point: QPoint) -> None:
        menu = QMenu(self)
        details_action = menu.addAction("Details")
        refresh_action = menu.addAction("Refresh")
        open_codex_action = menu.addAction("Open Codex")
        settings_action = menu.addAction("Settings")
        menu.addSeparator()
        exit_action = menu.addAction("Exit")
        chosen = menu.exec(self.bar.mapToGlobal(point))
        if chosen == details_action:
            self.show_details()
        elif chosen == refresh_action:
            self.refresh_requested.emit()
        elif chosen == open_codex_action:
            self.open_codex_requested.emit()
        elif chosen == settings_action:
            self.show_settings()
        elif chosen == exit_action:
            self.close()

    def show_settings(self) -> None:
        self._settings = SettingsDialog(self.config, self)
        self._settings.config_saved.connect(self._apply_config)
        self._settings.show()

    def _apply_config(self, config: AppConfig) -> None:
        self.config = AppConfig(
            start_with_windows=config.start_with_windows,
            show_usage=config.show_usage,
            poll_interval_seconds=config.poll_interval_seconds,
            codex_command=config.codex_command,
            taskbar_position_ratio=config.taskbar_position_ratio,
        )
        self.bar.set_show_usage(self.config.show_usage)
        self.details.set_show_usage(self.config.show_usage)
        self.config_updated.emit(self.config)
        self._position_timer.start(2000)
        self.refresh_requested.emit()

    def closeEvent(self, event) -> None:
        self._position_timer.stop()
        self._visibility_timer.stop()
        super().closeEvent(event)
        app = QApplication.instance()
        if app is not None:
            app.quit()
