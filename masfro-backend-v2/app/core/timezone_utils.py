"""
Timezone utilities for Philippine Time (UTC+8) support.

This module provides utilities for working with Philippine Time (PHT/UTC+8)
throughout the MAS-FRO system to ensure consistent timestamp handling.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
import pytz

# Philippine timezone (UTC+8)
PHT = pytz.timezone('Asia/Manila')
UTC = pytz.UTC

def get_philippine_time() -> datetime:
    """
    Get current Philippine time with timezone awareness.
    
    Returns:
        datetime: Current time in Philippine timezone (UTC+8)
    """
    return datetime.now(PHT)

def get_utc_time() -> datetime:
    """
    Get current UTC time with timezone awareness.
    
    Returns:
        datetime: Current time in UTC
    """
    return datetime.now(UTC)

def to_philippine_time(dt: datetime) -> datetime:
    """
    Convert any datetime to Philippine time.
    
    Args:
        dt: Datetime to convert (can be naive or aware)
        
    Returns:
        datetime: Timezone-aware datetime in Philippine time
    """
    if dt.tzinfo is None:
        # Assume naive datetime is in local time
        dt = PHT.localize(dt)
    return dt.astimezone(PHT)

def to_utc(dt: datetime) -> datetime:
    """
    Convert any datetime to UTC.
    
    Args:
        dt: Datetime to convert (can be naive or aware)
        
    Returns:
        datetime: Timezone-aware datetime in UTC
    """
    if dt.tzinfo is None:
        # Assume naive datetime is in Philippine time
        dt = PHT.localize(dt)
    return dt.astimezone(UTC)

def format_philippine_time(dt: Optional[datetime] = None, format_str: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
    """
    Format datetime in Philippine time for display.
    
    Args:
        dt: Datetime to format (uses current time if None)
        format_str: Format string for strftime
        
    Returns:
        str: Formatted datetime string
    """
    if dt is None:
        dt = get_philippine_time()
    else:
        dt = to_philippine_time(dt)
    return dt.strftime(format_str)

def parse_philippine_time(time_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    Parse a time string assuming Philippine timezone.
    
    Args:
        time_str: Time string to parse
        format_str: Format string for strptime
        
    Returns:
        datetime: Timezone-aware datetime in Philippine time
    """
    naive_dt = datetime.strptime(time_str, format_str)
    return PHT.localize(naive_dt)

def get_time_ago(dt: datetime) -> str:
    """
    Get human-readable time ago string.
    
    Args:
        dt: Datetime to compare with current Philippine time
        
    Returns:
        str: Human-readable time difference
    """
    now = get_philippine_time()
    dt = to_philippine_time(dt)
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return f"{int(seconds)} seconds ago"
    elif seconds < 3600:
        return f"{int(seconds / 60)} minutes ago"
    elif seconds < 86400:
        return f"{int(seconds / 3600)} hours ago"
    else:
        return f"{int(seconds / 86400)} days ago"