from __future__ import annotations

import json

from codex_usage_taskbar.config import AppConfig, load_config, save_config


def test_missing_config_uses_personal_app_defaults(tmp_path):
    config = load_config(tmp_path / "config.json")

    assert config == AppConfig(start_with_windows=True, poll_interval_seconds=60, codex_command=None)
    assert config.show_usage is False


def test_config_round_trips_only_supported_preferences(tmp_path):
    path = tmp_path / "config.json"
    save_config(
        path,
        AppConfig(
            start_with_windows=False,
            poll_interval_seconds=300,
            codex_command="codex",
            taskbar_position_ratio=0.35,
            show_usage=True,
        ),
    )

    assert load_config(path) == AppConfig(
        start_with_windows=False,
        poll_interval_seconds=300,
        codex_command="codex",
        taskbar_position_ratio=0.35,
        show_usage=True,
    )
    raw = path.read_text(encoding="utf-8")
    assert "token" not in raw.lower()
    assert "credit" not in raw.lower()


def test_non_boolean_show_usage_falls_back_to_false(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"show_usage": "true"}), encoding="utf-8")

    assert load_config(path).show_usage is False


def test_malformed_config_falls_back_to_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"poll_interval_seconds": "fast"}), encoding="utf-8")

    assert load_config(path) == AppConfig()
