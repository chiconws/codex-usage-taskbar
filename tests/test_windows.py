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
