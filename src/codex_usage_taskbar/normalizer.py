from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from .models import AccountInfo, RateLimitSnapshot, RateLimitWindow


def normalize_account(payload: Mapping[str, Any]) -> AccountInfo | None:
    """Extract the displayable account fields from an account response."""

    account = payload.get("account")
    if not isinstance(account, Mapping):
        return None
    return AccountInfo(
        email=_optional_text(account.get("email")),
        plan_type=_optional_text(account.get("planType")),
    )


def normalize_rate_limits(
    payload: Mapping[str, Any], fetched_at: datetime | None = None
) -> RateLimitSnapshot:
    """Convert the app-server rate-limit response into display-only data.

    Credits and token-related fields are intentionally ignored. The widget only
    needs percentages, window durations, and reset timestamps.
    """

    if fetched_at is None:
        fetched_at = datetime.now(timezone.utc)
    account = normalize_account(payload)

    bucket = _select_codex_bucket(payload)
    if not isinstance(bucket, Mapping):
        return RateLimitSnapshot(windows=(), fetched_at=fetched_at, account=account)

    candidates = (
        _normalize_window(bucket.get("primary")),
        _normalize_window(bucket.get("secondary")),
    )
    if all(candidate is None for candidate in candidates):
        return RateLimitSnapshot(windows=(), fetched_at=fetched_at, account=account)

    five_hour = _window_for_duration(candidates, 300)
    weekly = _window_for_duration(candidates, 10080)
    fallback = next(
        (
            candidate
            for candidate in candidates
            if candidate is not None and candidate is not five_hour and candidate is not weekly
        ),
        None,
    )
    windows = [five_hour or _five_hour_placeholder(), weekly or fallback or _weekly_placeholder()]
    return RateLimitSnapshot(windows=tuple(windows), fetched_at=fetched_at, account=account)


def _select_codex_bucket(payload: Mapping[str, Any]) -> Any:
    by_limit_id = payload.get("rateLimitsByLimitId")
    if isinstance(by_limit_id, Mapping):
        codex_bucket = by_limit_id.get("codex")
        if isinstance(codex_bucket, Mapping):
            return codex_bucket
    return payload.get("rateLimits")


def _normalize_window(value: Any) -> RateLimitWindow | None:
    if not isinstance(value, Mapping):
        return None

    used_percent = _clamp_percent(value.get("usedPercent"))
    duration = _optional_int(value.get("windowDurationMins"))
    if used_percent is None:
        return RateLimitWindow(
            label=_label_for_duration(duration),
            window_duration_mins=duration,
            used_percent=0,
            remaining_percent=0,
            resets_at=_timestamp(value.get("resetsAt")),
            has_data=False,
        )
    return RateLimitWindow(
        label=_label_for_duration(duration),
        window_duration_mins=duration,
        used_percent=used_percent,
        remaining_percent=100 - used_percent,
        resets_at=_timestamp(value.get("resetsAt")),
    )


def _five_hour_placeholder() -> RateLimitWindow:
    return RateLimitWindow(
        label="5 hours",
        window_duration_mins=300,
        used_percent=0,
        remaining_percent=0,
        resets_at=None,
        has_data=False,
    )


def _weekly_placeholder() -> RateLimitWindow:
    return RateLimitWindow(
        label="Weekly",
        window_duration_mins=10080,
        used_percent=0,
        remaining_percent=0,
        resets_at=None,
        has_data=False,
    )


def _window_for_duration(
    candidates: tuple[RateLimitWindow | None, RateLimitWindow | None], duration: int
) -> RateLimitWindow | None:
    return next(
        (candidate for candidate in candidates if candidate is not None and candidate.window_duration_mins == duration),
        None,
    )


def _clamp_percent(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _optional_text(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value


def _timestamp(value: Any) -> datetime | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _label_for_duration(duration: int | None) -> str:
    if duration == 10080:
        return "Weekly"
    if duration == 300:
        return "5 hours"
    if duration == 60:
        return "1 hour"
    if duration is None:
        return "Usage"
    if duration % 1440 == 0:
        days = duration // 1440
        return f"{days} day" if days == 1 else f"{days} days"
    if duration % 60 == 0:
        hours = duration // 60
        return f"{hours} hour" if hours == 1 else f"{hours} hours"
    return f"{duration} minutes"


def _window_sort_key(window: RateLimitWindow) -> tuple[int, int, int, str]:
    duration = window.window_duration_mins
    if window.label == "5 hours":
        slot = 0
    elif window.label == "Weekly":
        slot = 1
    else:
        slot = 2
    return (
        slot,
        0 if window.has_data else 1,
        -(duration if duration is not None else -1),
        window.label,
    )
