"""Time manipulation utilities for integration tests."""

import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from dateutil.relativedelta import relativedelta

from .exceptions import TimeMachineError

logger = logging.getLogger(__name__)

# Month name to number mapping (case-insensitive)
MONTH_NAMES = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

# Day name to weekday mapping (case-insensitive, Monday=0)
DAY_NAMES = {
    "mon": 0,
    "monday": 0,
    "tue": 1,
    "tuesday": 1,
    "wed": 2,
    "wednesday": 2,
    "thu": 3,
    "thursday": 3,
    "fri": 4,
    "friday": 4,
    "sat": 5,
    "saturday": 5,
    "sun": 6,
    "sunday": 6,
}


class TimeMachine:
    """Manages time manipulation for integration tests using libfaketime.

    This class enables deterministic testing of time-based automations by allowing
    tests to advance time forward in the containerized Home Assistant environment.

    **IMPORTANT LIMITATION**: Time can only move forward, never backward. Once time
    has been advanced, it cannot be reset to an earlier point. This is a fundamental
    constraint of the libfaketime implementation used by the containers.

    The TimeMachine is session-scoped, meaning time persists across all tests in a
    test session. Tests that depend on specific time conditions must explicitly
    advance time to the desired state at the start of the test.
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
        self._fake_time: datetime = datetime.now()

    def _set_time(self, target_dt: datetime, log_message: str, error_message_prefix: str) -> None:
        """Apply time change to faketime and update internal state.

        This helper method encapsulates the common pattern of formatting the datetime,
        applying faketime, updating internal state, logging, and invoking callbacks.

        Args:
            target_dt: Target datetime to set.
            log_message: Complete log message to emit (should include formatted time).
            error_message_prefix: Error message prefix (exception details will be appended).

        Raises:
            TimeMachineError: If time manipulation fails.
        """
        # Format datetime for libfaketime: "@YYYY-MM-DD HH:MM:SS"
        time_str = target_dt.strftime("@%Y-%m-%d %H:%M:%S")

        try:
            self._apply_faketime(time_str)
            self._fake_time = target_dt
            logger.debug(log_message)

            # Invoke callback if provided (e.g., to regenerate access tokens)
            if self._on_time_set is not None:
                self._on_time_set()
        except Exception as e:
            raise TimeMachineError(f"{error_message_prefix}: {e}")

    def fast_forward(self, delta: timedelta) -> None:
        """Advance time forward by the specified timedelta.

        This method advances time by a relative offset. The advancement is cumulative -
        calling this method multiple times will continue advancing from the current fake time.

        Args:
            delta: A timedelta object specifying the amount of time to advance.
                   Supports weeks, days, hours, minutes, seconds, and microseconds.

        Example:
            # Advance by 1 day
            time_machine.fast_forward(timedelta(days=1))

            # Advance by 1 hour and 30 minutes
            time_machine.fast_forward(timedelta(hours=1, minutes=30))

            # Advance by 2 weeks, 3 days, and 4 hours
            time_machine.fast_forward(timedelta(weeks=2, days=3, hours=4))

            # Advance by 30 seconds
            time_machine.fast_forward(timedelta(seconds=30))

        Raises:
            ValueError: If delta is negative (time can only move forward).
            TimeMachineError: If time manipulation fails.
        """
        # Validate delta is non-negative
        if delta.total_seconds() < 0:
            raise ValueError(f"Cannot advance time backwards: delta={delta}. Time can only move forward.")

        # Calculate target time
        try:
            target_dt = self._fake_time + delta
        except (ValueError, OverflowError) as e:
            raise TimeMachineError(f"Failed to calculate target time: {e}")

        # Apply time change
        time_str = target_dt.strftime("%Y-%m-%d %H:%M:%S")
        self._set_time(
            target_dt,
            log_message=f"Advanced time by {delta} -> {time_str}",
            error_message_prefix=f"Failed to advance time to {time_str}",
        )

    def jump_to_next(
        self,
        month: Optional[str] = None,
        day: Optional[str] = None,
        day_of_month: Optional[int] = None,
        hour: Optional[int] = None,
        minute: Optional[int] = None,
        second: Optional[int] = None,
    ) -> None:
        """Jump to the next occurrence of specified calendar constraints.

        This method advances time to the next datetime matching the specified constraints.
        Constraints are applied in a specific order to ensure predictable behavior:

        1. Month: Advance to the next occurrence of the specified month
        2. Day of month: Set the day of the month (may advance to next month if needed)
        3. Weekday: Advance to the next occurrence of the specified weekday
        4. Time: Set hour/minute/second (preserving unspecified components)

        All parameters are optional. Unspecified time components (hour/minute/second)
        preserve their values from the current fake time.

        Args:
            month: Month name ("Jan"/"January") or 3-char abbreviation (case-insensitive).
            day: Weekday name ("Mon"/"Monday") or 3-char abbreviation (case-insensitive).
            day_of_month: Day of the month (1-31). Applied after month, before weekday.
            hour: Hour of day (0-23). Preserves current hour if omitted.
            minute: Minute (0-59). Preserves current minute if omitted.
            second: Second (0-59). Preserves current second if omitted.

        Example:
            # Jump to next Monday at current time
            time_machine.jump_to_next(day="Monday")

            # Jump to next February, preserving current day and time
            time_machine.jump_to_next(month="Feb")

            # Jump to 1st of next month (or current month if before the 1st)
            time_machine.jump_to_next(day_of_month=1)

            # Complex: From Jan 31 14:30:00, jump to next Monday in February at 10:00:00
            # Result: Feb 3 10:00:00 (1st of Feb is Sat, next Mon is 3rd, time set to 10:00)
            time_machine.jump_to_next(month="Feb", day="Monday", hour=10)

            # Constraint sequence example: From Tue Jan 31 14:30:00
            # jump_to_next(day_of_month=1, day="Monday")
            # Step 1: Set to Feb 1 14:30:00 (day_of_month=1, but Feb 1 is Saturday)
            # Step 2: Advance to next Monday -> Feb 3 14:30:00

        Raises:
            ValueError: If month/day names are invalid or numeric values out of range.
            TimeMachineError: If time manipulation fails.
        """
        target_dt = self._fake_time

        # Step 1: Apply month constraint if specified
        if month is not None:
            month_lower = month.lower()
            if month_lower not in MONTH_NAMES:
                raise ValueError(f"Invalid month name '{month}'. Use full name or 3-char abbreviation (e.g., 'Jan', 'January').")

            target_month = MONTH_NAMES[month_lower]

            # If target month is same as current, we're already there
            # If target month is earlier in year, advance to next year
            if target_month <= target_dt.month:
                # Advance to next year
                target_dt = target_dt + relativedelta(years=1, month=target_month)
            else:
                # Same year
                target_dt = target_dt.replace(month=target_month)

        # Step 2: Apply day_of_month constraint if specified
        if day_of_month is not None:
            if not 1 <= day_of_month <= 31:
                raise ValueError(f"Invalid day_of_month '{day_of_month}'. Must be between 1 and 31.")

            try:
                # Try to set the day in current month
                candidate_dt = target_dt.replace(day=day_of_month)

                # If this is not in the future, advance to next month
                if candidate_dt <= self._fake_time:
                    # Move to next month and try again
                    target_dt = target_dt + relativedelta(months=1)
                    # Handle month-end edge cases (e.g., day=31 in February)
                    try:
                        target_dt = target_dt.replace(day=day_of_month)
                    except ValueError:
                        # Day doesn't exist in target month, use last day of month
                        target_dt = target_dt + relativedelta(day=31)  # relativedelta day=31 gives last day
                else:
                    target_dt = candidate_dt
            except ValueError:
                # Day doesn't exist in current month, advance to next month
                target_dt = target_dt + relativedelta(months=1, day=day_of_month)

        # Step 3: Apply weekday constraint if specified
        if day is not None:
            day_lower = day.lower()
            if day_lower not in DAY_NAMES:
                raise ValueError(f"Invalid day name '{day}'. Use full name or 3-char abbreviation (e.g., 'Mon', 'Monday').")

            target_weekday = DAY_NAMES[day_lower]
            current_weekday = target_dt.weekday()

            # Calculate days until target weekday
            days_ahead = (target_weekday - current_weekday) % 7

            # If days_ahead is 0 and we're on the target weekday already,
            # check if this would still be in the future
            if days_ahead == 0:
                if target_dt <= self._fake_time:
                    # Need to advance a full week
                    days_ahead = 7

            if days_ahead > 0:
                target_dt = target_dt + timedelta(days=days_ahead)

        # Step 4: Apply time constraints (hour/minute/second) if specified
        if hour is not None:
            if not 0 <= hour <= 23:
                raise ValueError(f"Invalid hour '{hour}'. Must be between 0 and 23.")
            target_dt = target_dt.replace(hour=hour)

        if minute is not None:
            if not 0 <= minute <= 59:
                raise ValueError(f"Invalid minute '{minute}'. Must be between 0 and 59.")
            target_dt = target_dt.replace(minute=minute)

        if second is not None:
            if not 0 <= second <= 59:
                raise ValueError(f"Invalid second '{second}'. Must be between 0 and 59.")
            target_dt = target_dt.replace(second=second)

        # Check if time constraints resulted in a time that's not in the future
        # If so, advance to the next valid occurrence at the specified time
        if target_dt <= self._fake_time:
            if day is not None:
                # Preserve the requested weekday by advancing a full week
                target_dt = target_dt + timedelta(days=7)
            else:
                # No weekday constraint: just move to the next day
                target_dt = target_dt + timedelta(days=1)

        # Apply time change
        time_str = target_dt.strftime("%Y-%m-%d %H:%M:%S")
        self._set_time(
            target_dt,
            log_message=f"Jumped to next occurrence matching constraints -> {time_str}",
            error_message_prefix=f"Failed to jump to {time_str}",
        )

    def advance_to_preset(self, preset: str, offset: Optional[timedelta] = None) -> None:
        """Advance time to the next sunrise or sunset, with optional offset.

        This method queries the Home Assistant sun.sun entity to get the next occurrence
        of sunrise or sunset, applies an optional offset, and advances time to that point.

        Args:
            preset: Either "sunrise" or "sunset" (case-insensitive).
            offset: Optional timedelta to add to the preset time (can be negative for "before").

        Example:
            # Advance to next sunrise
            time_machine.advance_to_preset("sunrise")

            # Advance to 30 minutes after next sunrise
            time_machine.advance_to_preset("sunrise", timedelta(minutes=30))

            # Advance to 1 hour before next sunset
            time_machine.advance_to_preset("sunset", timedelta(hours=-1))

        Raises:
            ValueError: If get_entity_state callback is not configured or preset is invalid.
            TimeMachineError: If entity fetch fails, parsing fails, or result would not be in future.
        """
        # Validate callback is configured
        if self._get_entity_state is None:
            raise ValueError("Cannot use advance_to_preset: get_entity_state callback not configured in TimeMachine. " "This callback is required to fetch sunrise/sunset times from Home Assistant.")

        # Validate preset
        preset_lower = preset.lower()
        if preset_lower not in ("sunrise", "sunset"):
            raise ValueError(f"Invalid preset '{preset}'. Must be 'sunrise' or 'sunset'.")

        # Fetch sun.sun entity state
        sun_state = self._get_entity_state("sun.sun")
        if sun_state is None:
            raise TimeMachineError("Could not retrieve sun.sun entity state from Home Assistant.")

        # Extract the appropriate attribute
        attributes = sun_state.get("attributes", {})
        if preset_lower == "sunrise":
            time_str_from_entity = attributes.get("next_rising")
        else:  # sunset
            time_str_from_entity = attributes.get("next_setting")

        if not time_str_from_entity:
            raise TimeMachineError(f"Could not find {preset_lower} time in sun.sun entity attributes. " f"Available attributes: {list(attributes.keys())}")

        # Parse the ISO 8601 datetime string
        try:
            # Home Assistant returns ISO 8601 format with timezone
            # e.g., "2026-01-21T07:30:00+00:00"
            preset_dt = datetime.fromisoformat(time_str_from_entity)
            # Remove timezone info to work with naive datetime
            preset_dt = preset_dt.replace(tzinfo=None)
        except (ValueError, AttributeError) as e:
            raise TimeMachineError(f"Failed to parse {preset_lower} time '{time_str_from_entity}': {e}")

        # Apply offset if provided
        offset_applied = offset if offset is not None else timedelta()
        target_dt = preset_dt + offset_applied

        # Validate that we're moving forward in time
        if target_dt <= self._fake_time:
            raise TimeMachineError(
                f"Cannot advance to {preset_lower}: calculated target time would not be in the future.\n"
                f"  Current fake time: {self._fake_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"  Preset ({preset_lower}): {preset_dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"  Offset applied: {offset_applied}\n"
                f"  Target time: {target_dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Time can only move forward. The sun.sun entity's next_{('rising' if preset_lower == 'sunrise' else 'setting')} "
                f"may be stale or the offset may be too negative."
            )

        # Apply time change
        time_str = target_dt.strftime("%Y-%m-%d %H:%M:%S")
        self._set_time(
            target_dt,
            log_message=f"Advanced to {preset_lower} with offset {offset_applied} -> {time_str}",
            error_message_prefix=f"Failed to advance to {preset_lower} at {time_str}",
        )
