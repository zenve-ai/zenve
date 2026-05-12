from __future__ import annotations

from datetime import datetime, timezone


def time_ago(dt: datetime | str) -> str:
    """Return a human-readable relative time string (e.g. '3 days ago', '2 min ago')."""
    if isinstance(dt, str):
        dt = dt.rstrip("Z")
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(dt, fmt).replace(tzinfo=timezone.utc)
                break
            except ValueError:
                continue
        if isinstance(dt, str):
            return dt

    now = datetime.now(tz=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "just now"
    if seconds < 3600:
        m = seconds // 60
        return f"{m} min ago"
    if seconds < 86400:
        h = seconds // 3600
        return f"{h} hour{'s' if h != 1 else ''} ago"
    d = seconds // 86400
    return f"{d} day{'s' if d != 1 else ''} ago"
