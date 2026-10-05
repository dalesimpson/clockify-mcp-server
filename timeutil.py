"""Date/time helpers for converting local times to the UTC format Clockify expects."""

from datetime import date, datetime, time, timedelta, timezone
from typing import Union
from zoneinfo import ZoneInfo

from config import config

DateLike = Union[str, datetime, date]


def local_tz() -> ZoneInfo:
    """Return the configured local timezone (CLOCKIFY_TIMEZONE, default America/Toronto)."""
    return ZoneInfo(config.timezone)


def _is_date_only(value: str) -> bool:
    return len(value.strip()) == 10


def to_datetime(value: DateLike, end_of_day: bool = False) -> datetime:
    """
    Parse a date or datetime into an aware datetime.

    - Values without an offset are interpreted in the configured local timezone.
    - A date-only value maps to local midnight at the start of that day, or, when
      end_of_day is True, local midnight at the start of the following day (so a
      date-only end bound includes the whole day).
    """
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        if _is_date_only(text):
            value = date.fromisoformat(text)
        else:
            value = datetime.fromisoformat(text)

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=local_tz())
        return value

    # Plain date
    day = value + timedelta(days=1) if end_of_day else value
    return datetime.combine(day, time.min, tzinfo=local_tz())


def to_clockify_utc(value: DateLike, end_of_day: bool = False) -> str:
    """Convert a date/datetime to Clockify's UTC format: YYYY-MM-DDTHH:MM:SSZ."""
    dt = to_datetime(value, end_of_day=end_of_day).astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
