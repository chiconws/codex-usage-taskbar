from __future__ import annotations

import math
from datetime import datetime


def format_percentage(remaining_percent: int) -> str:
    value = max(0, min(100, int(remaining_percent)))
    return f"{value}% remaining"


def format_countdown(reset_at: datetime | None, now: datetime) -> str:
    if reset_at is None:
        return "reset time unavailable"

    seconds = (reset_at - now).total_seconds()
    if seconds <= 0:
        return "now"

    total_minutes = max(1, math.ceil(seconds / 60))
    days, minutes = divmod(total_minutes, 24 * 60)
    hours, minutes = divmod(minutes, 60)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes and len(parts) < 2:
        parts.append(f"{minutes}m")
    return " ".join(parts)

