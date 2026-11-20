from datetime import datetime, timezone


def utcnow() -> datetime:
    """Store all times in UTC; convert to local time only when displaying."""
    return datetime.now(timezone.utc)
