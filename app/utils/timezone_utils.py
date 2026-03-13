"""
Timezone Utilities - EST/EDT Support
=====================================

All timestamps in this system use US/Eastern timezone (EST/EDT).
This module provides utilities for consistent timezone handling.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# US Eastern timezone (handles EST/EDT automatically)
EASTERN_TZ = ZoneInfo("America/New_York")


def now_est() -> datetime:
    """
    Get current time in US/Eastern timezone (EST/EDT).
    Replaces datetime.utcnow() throughout the codebase.

    Returns:
        datetime: Current time in US/Eastern with timezone info

    Example:
        >>> now_est()
        datetime.datetime(2026, 3, 12, 23, 30, 0, tzinfo=ZoneInfo('America/New_York'))
    """
    return datetime.now(EASTERN_TZ)


def utc_to_est(dt: datetime) -> datetime:
    """
    Convert UTC datetime to EST/EDT.

    Args:
        dt: UTC datetime (naive or aware)

    Returns:
        datetime: Same moment in US/Eastern timezone

    Example:
        >>> utc_dt = datetime(2026, 3, 13, 4, 30)  # 4:30 AM UTC
        >>> utc_to_est(utc_dt)
        datetime.datetime(2026, 3, 12, 23, 30, tzinfo=ZoneInfo('America/New_York'))  # 11:30 PM EST
    """
    if dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(EASTERN_TZ)


def est_to_utc(dt: datetime) -> datetime:
    """
    Convert EST/EDT datetime to UTC.

    Args:
        dt: EST/EDT datetime (naive or aware)

    Returns:
        datetime: Same moment in UTC
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=EASTERN_TZ)
    return dt.astimezone(timezone.utc)


def format_est(dt: datetime, fmt: str = "%Y-%m-%d %I:%M:%S %p %Z") -> str:
    """
    Format datetime in EST/EDT with timezone abbreviation.

    Args:
        dt: Datetime to format (will be converted to EST if not already)
        fmt: strftime format string (default shows "11:30:00 PM EST")

    Returns:
        str: Formatted datetime string

    Example:
        >>> dt = now_est()
        >>> format_est(dt)
        "2026-03-12 11:30:00 PM EST"

        >>> format_est(dt, "%m/%d/%Y %I:%M %p")
        "03/12/2026 11:30 PM"
    """
    if dt.tzinfo is None or dt.tzinfo.tzname(dt) != EASTERN_TZ.tzname(dt):
        dt = utc_to_est(dt)
    return dt.strftime(fmt)


# Convenience formats
def format_est_short(dt: datetime) -> str:
    """Format as: 03/12 11:30 PM"""
    return format_est(dt, "%m/%d %I:%M %p")


def format_est_date(dt: datetime) -> str:
    """Format as: March 12, 2026"""
    return format_est(dt, "%B %d, %Y")


def format_est_datetime(dt: datetime) -> str:
    """Format as: 03/12/2026 11:30:00 PM EST"""
    return format_est(dt, "%m/%d/%Y %I:%M:%S %p %Z")


def format_est_log(dt: datetime) -> str:
    """Format for logging: 2026-03-12 23:30:00 EST"""
    return format_est(dt, "%Y-%m-%d %H:%M:%S %Z")


# Database helpers
def db_now():
    """
    Returns current timestamp for database operations.
    Use this instead of datetime.utcnow() in model defaults.
    """
    return now_est()
