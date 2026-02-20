"""
Timezone utilities for Philippine Time (UTC+8) support.

This module provides utilities for working with Philippine Time (PHT/UTC+8)
throughout the MAS-FRO system to ensure consistent timestamp handling.
"""

from datetime import datetime
import pytz

# Philippine timezone (UTC+8)
PHT = pytz.timezone('Asia/Manila')

def get_philippine_time() -> datetime:
    """
    Get current Philippine time with timezone awareness.

    Returns:
        datetime: Current time in Philippine timezone (UTC+8)
    """
    return datetime.now(PHT)
