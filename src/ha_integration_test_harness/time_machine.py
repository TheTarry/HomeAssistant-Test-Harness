"""Time manipulation utilities for integration tests."""

import logging
from datetime import datetime, time, timedelta
from typing import Any, Callable, Optional, Union, overload

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
        get_entity_state: Optional[Callable[[str], Optional[dict[str, Any]]]] = None,
    ) -> None:
        """Initialize the time machine.

        Args:
            apply_faketime: Callback to apply faketime configuration (receives time string).
            on_time_set: Optional callback to invoke after setting time (e.g., token regeneration).
            get_entity_state: Optional callback to get entity state (e.g., for sunrise/sunset times).
        """
        self._apply_faketime = apply_faketime
        self._on_time_set = on_time_set
        self._get_entity_state = get_entity_state
        self._fake_time: Optional[datetime] = None
        self._time_offset_seconds: int = 0

    @overload
    def set_time(self, dt: datetime, /) -> None:
        """Set the current time using a datetime object."""
        ...

    @overload
    def set_time(self, t: time, /) -> None:
        """Set the time of day, keeping the current date."""
        ...

    @overload
    def set_time(self, preset: str, offset: timedelta = ..., /) -> None:
        """Set time based on a preset (sunrise/sunset) with optional offset."""
        ...

    def set_time(self, *args: Union[datetime, time, str, timedelta]) -> None:
        """Set the current time for the test environment.

        This method supports three different call patterns:

        1. set_time(datetime) - Set to a specific datetime
        2. set_time(time) - Set to a specific time today
        3. set_time(preset, offset) - Set relative to sunrise/sunset

        The time is in Europe/London timezone.

        Args:
            *args: Either (datetime,), (time,), or (str, timedelta).

        Example:
            # Set to specific datetime
            time_machine.set_time(datetime(2026, 1, 5, 7, 30))

            # Set to specific time today
            time_machine.set_time(time(7, 30))

            # Set to 30 minutes after sunrise
            time_machine.set_time("sunrise", timedelta(minutes=30))

            # Set to 1 hour before sunset
            time_machine.set_time("sunset", timedelta(hours=-1))

        Raises:
            TimeMachineError: If time manipulation fails.
            ValueError: If preset is not "sunrise" or "sunset", or if get_entity_state callback is not configured.
            TypeError: If invalid number or types of arguments provided.
        """
        # Parse arguments
        if len(args) == 0:
            raise TypeError("set_time() missing required positional argument")
        elif len(args) > 2:
            raise TypeError(f"set_time() takes at most 2 positional arguments ({len(args)} given)")

        arg1 = args[0]
        arg2 = args[1] if len(args) > 1 else None

        # Determine which overload was called and compute the target datetime
        if isinstance(arg1, datetime):
            target_dt = arg1
        elif isinstance(arg1, time):
            # Apply the time to today's date
            now = datetime.now()
            target_dt = datetime.combine(now.date(), arg1)
        elif isinstance(arg1, str):
            # Handle sunrise/sunset preset
            preset = arg1.lower()
            if preset not in ("sunrise", "sunset"):
                raise ValueError(f"Invalid preset '{arg1}'. Must be 'sunrise' or 'sunset'.")

            if self._get_entity_state is None:
                raise ValueError("Cannot use sunrise/sunset preset: get_entity_state callback not configured in TimeMachine")

            # Get sun.sun entity state
            sun_state = self._get_entity_state("sun.sun")
            if sun_state is None:
                raise TimeMachineError("Could not retrieve sun.sun entity state")

            # Extract the appropriate attribute
            attributes = sun_state.get("attributes", {})
            if preset == "sunrise":
                time_str = attributes.get("next_rising")
            else:  # sunset
                time_str = attributes.get("next_setting")

            if not time_str:
                raise TimeMachineError(f"Could not find {preset} time in sun.sun entity attributes")

            # Parse the ISO 8601 datetime string
            try:
                # Home Assistant returns ISO 8601 format with timezone
                # e.g., "2026-01-21T07:30:00+00:00"
                preset_dt = datetime.fromisoformat(time_str)
                # Remove timezone info to work with naive datetime
                preset_dt = preset_dt.replace(tzinfo=None)
            except (ValueError, AttributeError) as e:
                raise TimeMachineError(f"Failed to parse {preset} time '{time_str}': {e}")

            # Apply offset
            offset = arg2 if arg2 is not None else timedelta()
            if not isinstance(offset, timedelta):
                raise TypeError(f"Second argument for preset must be a timedelta, got {type(offset)}")
            target_dt = preset_dt + offset
        else:
            raise TypeError(f"Invalid argument type for set_time: {type(arg1)}")

        # Format datetime for libfaketime: "YYYY-MM-DD HH:MM:SS"
        time_str = target_dt.strftime("%Y-%m-%d %H:%M:%S")

        try:
            self._apply_faketime(time_str)
            self._fake_time = target_dt
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
