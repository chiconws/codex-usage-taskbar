from __future__ import annotations

from PySide6.QtCore import QPoint, QSize
import win32con

from codex_usage_taskbar import windows


def test_overlay_position_uses_left_taskbar_safety_offset():
    position = windows.calculate_overlay_position((100, 900, 900, 940), QSize(128, 24))

    assert position == QPoint(288, 908)


def test_owned_overlay_ratio_uses_screen_coordinates():
    position = windows.calculate_overlay_position(
        (100, 900, 900, 940), QSize(128, 24), position_ratio=0.5
    )

    assert position == QPoint(436, 908)


def test_taskbar_position_ratio_maps_to_parent_coordinates():
    position = windows.calculate_taskbar_child_position(
        (100, 900, 900, 940), QSize(128, 24), position_ratio=0.5
    )

    assert position == QPoint(336, 8)


def test_taskbar_position_ratio_round_trips_from_widget_geometry():
    ratio = windows.taskbar_position_ratio(
        (100, 900, 900, 940), (436, 908, 564, 932)
    )

    assert ratio == 0.5


def test_attach_overlay_makes_taskbar_the_window_owner(monkeypatch):
    captured = {}

    class DummyWidget:
        def winId(self):
            return 123

    def get_window_long(_hwnd, field):
        return 0x90000000 if field == win32con.GWL_STYLE else win32con.WS_EX_TOPMOST

    def set_window_long(_hwnd, field, value):
        captured[field] = value

    def set_window_pos(hwnd, insert_after, x, y, width, height, flags):
        captured["topmost"] = (hwnd, insert_after, x, y, width, height, flags)

    monkeypatch.setattr(windows.win32gui, "GetWindowLong", get_window_long)
    monkeypatch.setattr(windows.win32gui, "GetWindow", lambda _hwnd, _relation: 0)
    monkeypatch.setattr(windows.win32gui, "SetWindowLong", set_window_long)
    monkeypatch.setattr(windows.win32gui, "SetWindowPos", set_window_pos)

    assert windows.attach_overlay_to_taskbar(DummyWidget(), 456) is True
    assert captured[win32con.GWL_HWNDPARENT] == 456
    assert captured["topmost"][1] == win32con.HWND_TOPMOST
    assert captured[win32con.GWL_EXSTYLE] & win32con.WS_EX_TOOLWINDOW
    assert captured[win32con.GWL_EXSTYLE] & win32con.WS_EX_NOACTIVATE


def test_fullscreen_foreground_window_obstructs_taskbar_widget(monkeypatch):
    foreground_hwnd = 700
    taskbar_hwnd = 500
    widget_hwnd = 123
    monitor_rect = (0, 0, 1920, 1080)

    monkeypatch.setattr(windows.win32gui, "GetForegroundWindow", lambda: foreground_hwnd)
    monkeypatch.setattr(windows.win32gui, "IsWindow", lambda _hwnd: True)
    monkeypatch.setattr(windows.win32gui, "GetClassName", lambda _hwnd: "Chrome_WidgetWin_1")
    monkeypatch.setattr(
        windows.win32process,
        "GetWindowThreadProcessId",
        lambda _hwnd: (1, 9999),
    )
    monkeypatch.setattr(
        windows.win32api,
        "MonitorFromWindow",
        lambda _hwnd, _flag: 42,
    )
    monkeypatch.setattr(
        windows.win32api,
        "GetMonitorInfo",
        lambda _monitor: {"Monitor": monitor_rect},
    )
    monkeypatch.setattr(
        windows.win32gui,
        "GetWindowRect",
        lambda _hwnd: monitor_rect,
    )

    assert windows.is_taskbar_obstructed(taskbar_hwnd, widget_hwnd) is True


def test_maximized_foreground_window_does_not_obstruct_taskbar_widget(monkeypatch):
    monitor_rect = (0, 0, 1920, 1080)

    monkeypatch.setattr(windows.win32gui, "GetForegroundWindow", lambda: 700)
    monkeypatch.setattr(windows.win32gui, "IsWindow", lambda _hwnd: True)
    monkeypatch.setattr(windows.win32gui, "GetClassName", lambda _hwnd: "Chrome_WidgetWin_1")
    monkeypatch.setattr(
        windows.win32process,
        "GetWindowThreadProcessId",
        lambda _hwnd: (1, 9999),
    )
    monkeypatch.setattr(windows.win32api, "MonitorFromWindow", lambda _hwnd, _flag: 42)
    monkeypatch.setattr(
        windows.win32api,
        "GetMonitorInfo",
        lambda _monitor: {"Monitor": monitor_rect},
    )
    monkeypatch.setattr(windows.win32gui, "GetWindowRect", lambda _hwnd: (0, 0, 1920, 1040))

    assert windows.is_taskbar_obstructed(500, 123) is False


def test_taskbar_overlay_visibility_follows_shell_visibility_and_obstruction(monkeypatch):
    monkeypatch.setattr(windows.win32gui, "IsWindowVisible", lambda _hwnd: True)
    monkeypatch.setattr(windows, "is_taskbar_obstructed", lambda _taskbar, _widget: True)

    assert windows.taskbar_overlay_should_be_visible(500, 123) is False

    monkeypatch.setattr(windows, "is_taskbar_obstructed", lambda _taskbar, _widget: False)
    assert windows.taskbar_overlay_should_be_visible(500, 123) is True
