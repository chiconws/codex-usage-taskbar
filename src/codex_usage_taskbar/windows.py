from __future__ import annotations

from PySide6.QtCore import QPoint, QSize
from PySide6.QtWidgets import QApplication, QWidget

import win32con
import win32gui


def primary_taskbar_rect() -> tuple[int, int, int, int] | None:
    hwnd = primary_taskbar_handle()
    if not hwnd:
        return None
    return win32gui.GetWindowRect(hwnd)


def primary_taskbar_handle() -> int | None:
    hwnd = win32gui.FindWindow("Shell_TrayWnd", None)
    return int(hwnd) if hwnd else None


def prepare_overlay(widget: QWidget) -> None:
    hwnd = int(widget.winId())
    try:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(
            hwnd,
            win32con.GWL_EXSTYLE,
            style | win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_NOACTIVATE,
        )
    except win32gui.error:
        pass


def attach_overlay_to_taskbar(widget: QWidget, taskbar_hwnd: int) -> bool:
    """Make the taskbar the overlay's owner so it stays above the taskbar surface.

    Windows 11 renders much of the taskbar through a XAML composition surface. A
    normal ``WS_CHILD`` inserted under ``Shell_TrayWnd`` can exist and still be
    completely hidden by that surface. An owned top-level window is the pattern
    used by taskbar-docked widgets: it remains a regular Qt window, but the shell
    keeps it associated with and above the taskbar.
    """
    hwnd = int(widget.winId())
    try:
        current_owner = win32gui.GetWindow(hwnd, win32con.GW_OWNER)
        if current_owner != taskbar_hwnd:
            win32gui.SetWindowLong(hwnd, win32con.GWL_HWNDPARENT, taskbar_hwnd)
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOPMOST,
                0,
                0,
                0,
                0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
            )

        exstyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(
            hwnd,
            win32con.GWL_EXSTYLE,
            exstyle | win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_NOACTIVATE,
        )
        return True
    except win32gui.error:
        return False


def calculate_taskbar_child_position(
    taskbar: tuple[int, int, int, int],
    widget_size: QSize,
    position_ratio: float | None,
    margin: int = 8,
    left_safety_offset: int = 180,
) -> QPoint:
    left, top, right, bottom = taskbar
    taskbar_width = max(0, right - left)
    widget_width = widget_size.width()
    available_width = max(0, taskbar_width - widget_width - 2 * margin)
    if position_ratio is None:
        position_ratio = left_safety_offset / available_width if available_width else 0.0
    position_ratio = max(0.0, min(1.0, float(position_ratio)))
    x = margin + round(available_width * position_ratio)
    y = max(0, ((bottom - top) - widget_size.height()) // 2)
    return QPoint(x, y)


def taskbar_position_ratio(
    taskbar: tuple[int, int, int, int], widget_rect: tuple[int, int, int, int], margin: int = 8
) -> float:
    left, _top, right, _bottom = taskbar
    widget_left, _widget_top, widget_right, _widget_bottom = widget_rect
    available_width = max(0, (right - left) - (widget_right - widget_left) - 2 * margin)
    if not available_width:
        return 0.0
    return max(0.0, min(1.0, (widget_left - left - margin) / available_width))


def position_taskbar_child(
    widget: QWidget,
    taskbar: tuple[int, int, int, int],
    position_ratio: float | None,
    margin: int = 8,
) -> bool:
    """Position the taskbar-owned top-level window in screen coordinates.

    The historical name is retained for the small internal API and its tests;
    this is intentionally no longer a child-window operation.
    """
    hwnd = int(widget.winId())
    screen_position = calculate_overlay_position(
        taskbar,
        widget.size(),
        margin=margin,
        position_ratio=position_ratio,
    )
    try:
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOP,
            screen_position.x(),
            screen_position.y(),
            widget.width(),
            widget.height(),
            win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW | win32con.SWP_NOZORDER,
        )
        return True
    except win32gui.error:
        return False


def overlay_window_rect(widget: QWidget) -> tuple[int, int, int, int]:
    return win32gui.GetWindowRect(int(widget.winId()))


def move_taskbar_child_to_screen_x(
    widget: QWidget, screen_x: int, margin: int = 8
) -> float | None:
    taskbar_hwnd = primary_taskbar_handle()
    taskbar = primary_taskbar_rect()
    if taskbar_hwnd is None or taskbar is None:
        return None
    if not attach_overlay_to_taskbar(widget, taskbar_hwnd):
        return None
    widget.adjustSize()
    left, _top, right, _bottom = taskbar
    available_width = max(0, (right - left) - widget.width() - 2 * margin)
    if not available_width:
        ratio = 0.0
    else:
        ratio = max(0.0, min(1.0, (screen_x - left - margin) / available_width))
    if not position_taskbar_child(widget, taskbar, ratio, margin):
        return None
    return ratio


def calculate_overlay_position(
    taskbar: tuple[int, int, int, int],
    widget_size: QSize,
    margin: int = 8,
    left_safety_offset: int = 180,
    position_ratio: float | None = None,
) -> QPoint:
    left, top, right, bottom = taskbar
    width = widget_size.width()
    height = widget_size.height()
    if position_ratio is None:
        preferred_x = left + margin + left_safety_offset
    else:
        available_width = max(0, (right - left) - width - 2 * margin)
        ratio = max(0.0, min(1.0, float(position_ratio)))
        preferred_x = left + margin + round(available_width * ratio)
    max_x = right - width - margin
    x = max(left + margin, min(preferred_x, max_x))
    y = top + max(0, ((bottom - top) - height) // 2)
    return QPoint(x, y)


def position_overlay(widget: QWidget, position_ratio: float | None = None, margin: int = 8) -> bool:
    taskbar_hwnd = primary_taskbar_handle()
    taskbar = primary_taskbar_rect()
    if taskbar_hwnd is None or taskbar is None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return False
        available = screen.availableGeometry()
        taskbar = (available.left(), available.bottom() - 40, available.right(), available.bottom())
        widget.adjustSize()
        widget.move(calculate_overlay_position(taskbar, widget.size(), margin))
        return False

    if not attach_overlay_to_taskbar(widget, taskbar_hwnd):
        return False
    widget.adjustSize()
    return position_taskbar_child(widget, taskbar, position_ratio, margin)
