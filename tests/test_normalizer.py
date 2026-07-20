from datetime import datetime, timezone

import pytest

import codex_usage_taskbar.normalizer as normalizer


FETCHED_AT = datetime(2026, 7, 14, 18, 0, tzinfo=timezone.utc)


def test_normalizes_weekly_and_five_hour_windows_as_remaining_percentages():
    payload = {
        "rateLimitsByLimitId": {
            "codex": {
                "primary": {
                    "usedPercent": 26,
                    "windowDurationMins": 10080,
                    "resetsAt": 1784545373,
                },
                "secondary": {
                    "usedPercent": 62,
                    "windowDurationMins": 300,
                    "resetsAt": 1784520000,
                },
                "credits": {"balance": "999"},
            }
        }
    }

    snapshot = normalizer.normalize_rate_limits(payload, FETCHED_AT)

    assert [window.label for window in snapshot.windows] == ["5 hours", "Weekly"]
    assert [window.remaining_percent for window in snapshot.windows] == [38, 74]
    assert [window.used_percent for window in snapshot.windows] == [62, 26]
    assert all(window.has_data for window in snapshot.windows)
    assert all(window.resets_at.tzinfo == timezone.utc for window in snapshot.windows)
    assert snapshot.fetched_at == FETCHED_AT


def test_selects_display_windows_by_duration_regardless_of_response_field():
    payload = {
        "rateLimits": {
            "primary": {"usedPercent": 62, "windowDurationMins": 300},
            "secondary": {"usedPercent": 26, "windowDurationMins": 10080},
        }
    }

    snapshot = normalizer.normalize_rate_limits(payload, FETCHED_AT)

    assert [window.label for window in snapshot.windows] == ["5 hours", "Weekly"]
    assert [window.used_percent for window in snapshot.windows] == [62, 26]
    assert all(window.has_data for window in snapshot.windows)


@pytest.mark.parametrize("used_percent", ["not-a-number", None])
def test_unusable_percentage_is_normalized_as_no_data_not_full_availability(used_percent):
    payload = {
        "rateLimits": {
            "primary": {"usedPercent": used_percent, "windowDurationMins": 10080},
            "secondary": {"usedPercent": 62, "windowDurationMins": 300},
        }
    }

    snapshot = normalizer.normalize_rate_limits(payload, FETCHED_AT)

    weekly = next(window for window in snapshot.windows if window.label == "Weekly")
    assert weekly.has_data is False
    assert weekly.used_percent == 0
    assert weekly.remaining_percent == 0


def test_prefers_codex_bucket_and_falls_back_to_legacy_rate_limits():
    payload = {
        "rateLimits": {
            "primary": {"usedPercent": 90, "windowDurationMins": 60}
        },
        "rateLimitsByLimitId": {
            "other": {
                "primary": {"usedPercent": 1, "windowDurationMins": 60}
            }
        },
    }

    snapshot = normalizer.normalize_rate_limits(payload, FETCHED_AT)

    assert len(snapshot.windows) == 2
    assert snapshot.windows[0].label == "5 hours"
    assert snapshot.windows[0].has_data is False
    assert snapshot.windows[1].remaining_percent == 10
    assert snapshot.windows[1].label == "1 hour"


def test_missing_secondary_window_creates_no_data_five_hour_placeholder():
    payload = {
        "rateLimits": {
            "primary": {"usedPercent": 100, "windowDurationMins": 10080}
        }
    }

    snapshot = normalizer.normalize_rate_limits(payload, FETCHED_AT)

    assert len(snapshot.windows) == 2
    assert snapshot.windows[0].label == "5 hours"
    assert snapshot.windows[0].has_data is False
    assert snapshot.windows[0].remaining_percent == 0
    assert snapshot.windows[0].resets_at is None
    assert snapshot.windows[1].remaining_percent == 0


def test_invalid_or_empty_payload_produces_empty_snapshot():
    assert normalizer.normalize_rate_limits({}, FETCHED_AT).windows == ()
    assert normalizer.normalize_rate_limits({"rateLimits": None}, FETCHED_AT).windows == ()


def test_percentages_are_clamped_to_renderable_range():
    payload = {
        "rateLimits": {
            "primary": {"usedPercent": 125, "windowDurationMins": 10080},
            "secondary": {"usedPercent": -10, "windowDurationMins": 300},
        }
    }

    snapshot = normalizer.normalize_rate_limits(payload, FETCHED_AT)

    by_label = {window.label: window for window in snapshot.windows}
    assert by_label["5 hours"].used_percent == 0
    assert by_label["5 hours"].remaining_percent == 100
    assert by_label["Weekly"].used_percent == 100
    assert by_label["Weekly"].remaining_percent == 0


def test_normalizes_account_email_and_plan_type_and_attaches_it_to_snapshot():
    account = {"email": "user@example.com", "planType": "pro", "name": "ignored"}

    normalized = normalizer.normalize_account({"account": account})
    assert normalized.email == "user@example.com"
    assert normalized.plan_type == "pro"
    snapshot = normalizer.normalize_rate_limits({"account": account}, FETCHED_AT)
    assert snapshot.account.email == "user@example.com"
    assert snapshot.account.plan_type == "pro"


def test_malformed_account_fields_become_none_but_account_mapping_is_preserved():
    payload = {
        "account": {
            "email": "",
            "planType": 123,
        }
    }

    normalized = normalizer.normalize_account(payload)
    assert normalized.email is None
    assert normalized.plan_type is None


def test_missing_or_non_mapping_account_returns_none():
    assert normalizer.normalize_account({}) is None
    assert normalizer.normalize_account({"account": None}) is None
    assert normalizer.normalize_account({"account": "user@example.com"}) is None
