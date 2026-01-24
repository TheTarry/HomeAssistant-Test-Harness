"""Time manipulation utilities for integration tests."""

import logging
from datetime import datetime, timedelta
from typing import Callable, Optional

from .exceptions import DockerError, TimeMachineError

logger = logging.getLogger(__name__)


class TimeMachine:
    """Manages time manipulation for integration tests using libfaketime.

    This class allows tests to freeze time at specific points or advance time
    incrementally, enabling deterministic testing of time-based automations.
    """

    def __init__(
        self,
        apply_faketime: Callable[[str], None],
        on_time_set: Optional[Callable[[], None]] = None,
    ) -> None:
        """Initialize the time machine.

        Args:
            apply_faketime: Callback to apply faketime configuration (receives time string).
            on_time_set: Optional callback to invoke after setting time (e.g., token regeneration).
        """
        self._apply_faketime = apply_faketime
        self._on_time_set = on_time_set
        self._fake_time: Optional[datetime] = None
        self._time_offset_seconds: int = 0

    def set_time(self, dt: datetime) -> None:
        """Set the current time for the test environment.

        This freezes time at the specified datetime using libfaketime.
        The time is in Europe/London timezone.

        Args:
            dt: The datetime to set as current time. Should be a naive datetime
                (assumed to be Europe/London timezone) or timezone-aware.

        Example:
            time.set_time(datetime(2026, 1, 5, 7, 30))  # Monday at 7:30 AM

        Raises:
            TimeMachineError: If time manipulation fails.
        """
        # Format datetime for libfaketime: "YYYY-MM-DD HH:MM:SS"
        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")

        try:
            self._apply_faketime(time_str)
            self._fake_time = dt
            self._time_offset_seconds = 0
            logger.debug(f"Set time to {time_str}")

            # Invoke callback if provided (e.g., to regenerate access tokens)
            if self._on_time_set is not None:
                self._on_time_set()
        except Exception as e:
            raise TimeMachineError(f"Failed to set time to {time_str}: {e}")

    def advance_time(self, seconds: int) -> None:
        """Advance time by the specified number of seconds.

        This is cumulative - calling advance_time(60) twice will advance time by
        120 seconds total from the initial time set by set_time() or from real time.

        If set_time() has not been called yet, the first call to advance_time() will
        use the current real time as the baseline and advance from there.

        Args:
            seconds: Number of seconds to advance time. Must be non-negative.

        Example:
            # Without set_time() - advances from current real time
            time.advance_time(60)  # Advance 1 minute from now

            # With set_time()
            time.set_time(datetime(2026, 1, 5, 10, 0))  # Set to 10:00 AM
            time.advance_time(3600)  # Advance 1 hour -> now 11:00 AM
            time.advance_time(1800)  # Advance 30 mins -> now 11:30 AM

        Raises:
            ValueError: If seconds is negative.
            TimeMachineError: If time manipulation fails.
        """
        if seconds < 0:
            raise ValueError(f"Cannot advance time backwards. To go back in time, use " f"set_time() with an earlier datetime instead " f"(received {seconds} seconds).")

        # If no fake time set yet, use current real time as baseline
        if self._fake_time is None:
            self._fake_time = datetime.now()
            logger.debug(f"Using current real time as baseline: {self._fake_time.strftime('%Y-%m-%d %H:%M:%S')}")

        self._time_offset_seconds += seconds

        # Calculate new absolute time
        new_time = self._fake_time + timedelta(seconds=self._time_offset_seconds)
        time_str = new_time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            self._apply_faketime(time_str)
            logger.debug(f"Advanced time by {seconds}s (total offset: {self._time_offset_seconds}s) -> {time_str}")
        except Exception as e:
            raise TimeMachineError(f"Failed to advance time by {seconds}s to {time_str}: {e}")

    def reset_time(self) -> None:
        """Reset time to real time.

        Overwrites the faketime configuration with "+0", allowing containers
        to use real system time again.
        """
        try:
            self._apply_faketime("+0")
            self._fake_time = None
            self._time_offset_seconds = 0
            logger.debug("Reset time to real time")
        except DockerError as e:
            # Don't raise exception during reset - this is often called during teardown
            logger.debug(f"Failed to reset time (may be expected during teardown): {e}")
