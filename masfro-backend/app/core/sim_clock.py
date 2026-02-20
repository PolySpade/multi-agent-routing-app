# filename: app/core/sim_clock.py

"""
Simulated Clock for Flood Decay Testing

Provides a module-level singleton clock that can be manually advanced or
sped up, enabling flood decay testing without waiting for real wall-clock time.

All time-age calculations in hazard_agent.py funnel through sim_clock.now(),
so advancing the clock triggers decay on the next hazard recalculation cycle.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional


class SimulatedClock:
    """
    A simulated UTC clock that supports manual time advance and speedup.

    - advance(minutes): Jump forward N simulated minutes instantly.
    - set_speedup(factor): Run time at Nx real speed (factor=60 → 1 real sec = 60 sim sec).
    - reset(): Return to real wall-clock time.
    """

    def __init__(self) -> None:
        self._offset_seconds: float = 0.0
        self._speedup_factor: float = 1.0
        self._speedup_started_at: Optional[datetime] = None
        self._speedup_base_offset: float = 0.0

    def now(self) -> datetime:
        """Return current simulated UTC time."""
        wall_now = datetime.now(timezone.utc)
        speedup_extra = 0.0
        if self._speedup_started_at is not None and self._speedup_factor != 1.0:
            elapsed_wall = (wall_now - self._speedup_started_at).total_seconds()
            speedup_extra = elapsed_wall * (self._speedup_factor - 1.0)
        total_offset = self._offset_seconds + self._speedup_base_offset + speedup_extra
        return wall_now + timedelta(seconds=total_offset)

    def advance(self, minutes: float) -> None:
        """Add N simulated minutes to the clock offset instantly."""
        # Capture any accumulated speedup into the base offset first so that
        # the starting reference for future speedup is correct.
        self._flush_speedup()
        self._offset_seconds += minutes * 60.0

    def set_speedup(self, factor: float) -> None:
        """
        Set the time speedup multiplier.

        factor=1.0  → real-time (default)
        factor=60.0 → 1 real second = 60 simulated seconds
        factor=0.0  → pause simulated time
        """
        if factor < 0:
            raise ValueError("Speedup factor must be >= 0")
        self._flush_speedup()
        self._speedup_factor = factor
        if factor != 1.0:
            self._speedup_started_at = datetime.now(timezone.utc)
        else:
            self._speedup_started_at = None

    def reset(self) -> None:
        """Reset the clock to real wall-clock time."""
        self._offset_seconds = 0.0
        self._speedup_factor = 1.0
        self._speedup_started_at = None
        self._speedup_base_offset = 0.0

    def get_status(self) -> dict:
        """Return a dict describing the current clock state."""
        wall_now = datetime.now(timezone.utc)
        sim_now = self.now()
        total_offset_min = (sim_now - wall_now).total_seconds() / 60.0
        return {
            "wall_time": wall_now.isoformat(),
            "sim_time": sim_now.isoformat(),
            "offset_minutes": round(total_offset_min, 3),
            "speedup_factor": self._speedup_factor,
            "is_real_time": (
                self._offset_seconds == 0.0
                and self._speedup_base_offset == 0.0
                and self._speedup_factor == 1.0
            ),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _flush_speedup(self) -> None:
        """Accumulate any active speedup offset into the base so reference is reset."""
        if self._speedup_started_at is not None and self._speedup_factor != 1.0:
            wall_now = datetime.now(timezone.utc)
            elapsed_wall = (wall_now - self._speedup_started_at).total_seconds()
            self._speedup_base_offset += elapsed_wall * (self._speedup_factor - 1.0)
        self._speedup_started_at = None


# Module-level singleton — import this in other modules.
sim_clock = SimulatedClock()
