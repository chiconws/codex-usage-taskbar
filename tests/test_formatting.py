from datetime import datetime, timedelta, timezone

from codex_usage_taskbar.formatting import format_countdown, format_percentage


NOW = datetime(2026, 7, 14, 18, 0, tzinfo=timezone.utc)


def test_formats_remaining_percentage():
    assert format_percentage(74) == "74% remaining"
    assert format_percentage(0) == "0% remaining"


def test_formats_countdown_using_days_hours_and_minutes():
    assert format_countdown(NOW + timedelta(days=4, hours=2, minutes=11), NOW) == "4d 2h"
    assert format_countdown(NOW + timedelta(hours=1, minutes=47), NOW) == "1h 47m"
    assert format_countdown(NOW + timedelta(minutes=4), NOW) == "4m"


def test_formats_expired_and_missing_resets():
    assert format_countdown(NOW - timedelta(seconds=1), NOW) == "now"
    assert format_countdown(None, NOW) == "reset time unavailable"

