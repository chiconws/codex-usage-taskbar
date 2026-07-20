from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AccountInfo:
    """Display-only account metadata returned by the Codex account service."""

    email: str | None
    plan_type: str | None


@dataclass(frozen=True, slots=True)
class RateLimitWindow:
    """One server-provided rate-limit window, normalized for presentation."""

    label: str
    window_duration_mins: int | None
    used_percent: int
    remaining_percent: int
    resets_at: datetime | None
    has_data: bool = True


@dataclass(frozen=True, slots=True)
class RateLimitSnapshot:
    """The usage windows returned by the Codex account service."""

    windows: tuple[RateLimitWindow, ...]
    fetched_at: datetime
    account: AccountInfo | None = None
