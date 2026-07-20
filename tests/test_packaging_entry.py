from __future__ import annotations

from codex_usage_taskbar.main import main as package_main


def test_packaging_entry_exposes_package_main() -> None:
    from packaging_entry import main

    assert main is package_main
