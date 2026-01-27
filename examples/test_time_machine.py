"""Example tests demonstrating TimeMachine usage."""

from datetime import datetime, time, timedelta

from ha_integration_test_harness import HomeAssistant, TimeMachine


def test_set_time_with_datetime(home_assistant: HomeAssistant, time_machine: TimeMachine) -> None:
    """Test setting time to a specific datetime."""
    # Set time to a specific datetime
    time_machine.set_time(datetime(2026, 6, 21, 12, 0, 0))

    # Verify time was set by checking sun position changes
    # The sun entity should reflect the new time
    sun_state = home_assistant.get_state("sun.sun")
    assert sun_state is not None
    assert "attributes" in sun_state


def test_set_time_with_time_of_day(home_assistant: HomeAssistant, time_machine: TimeMachine) -> None:
    """Test setting time to a specific time of day (today)."""
    # Set time to 7:30 AM today
    time_machine.set_time(time(7, 30))

    # Verify by checking sun state exists
    sun_state = home_assistant.get_state("sun.sun")
    assert sun_state is not None


def test_set_time_to_sunrise(home_assistant: HomeAssistant, time_machine: TimeMachine) -> None:
    """Test setting time to sunrise."""
    # Set time to sunrise
    time_machine.set_time("sunrise")

    # Verify sun state is accessible
    sun_state = home_assistant.get_state("sun.sun")
    assert sun_state is not None
    assert "attributes" in sun_state


def test_set_time_to_sunrise_with_offset(home_assistant: HomeAssistant, time_machine: TimeMachine) -> None:
    """Test setting time to 30 minutes after sunrise."""
    # Set time to 30 minutes after sunrise
    time_machine.set_time("sunrise", timedelta(minutes=30))

    # Verify sun state is accessible
    sun_state = home_assistant.get_state("sun.sun")
    assert sun_state is not None


def test_set_time_to_sunset(home_assistant: HomeAssistant, time_machine: TimeMachine) -> None:
    """Test setting time to sunset."""
    # Set time to sunset
    time_machine.set_time("sunset")

    # Verify sun state is accessible
    sun_state = home_assistant.get_state("sun.sun")
    assert sun_state is not None


def test_set_time_to_before_sunset(home_assistant: HomeAssistant, time_machine: TimeMachine) -> None:
    """Test setting time to 1 hour before sunset."""
    # Set time to 1 hour before sunset
    time_machine.set_time("sunset", timedelta(hours=-1))

    # Verify sun state is accessible
    sun_state = home_assistant.get_state("sun.sun")
    assert sun_state is not None


def test_advance_time_after_set_time(home_assistant: HomeAssistant, time_machine: TimeMachine) -> None:
    """Test advancing time after setting an initial time."""
    # Set initial time
    time_machine.set_time(datetime(2026, 1, 15, 10, 0))

    # Advance time by 1 hour
    time_machine.advance_time(3600)

    # Verify we can still interact with Home Assistant
    sun_state = home_assistant.get_state("sun.sun")
    assert sun_state is not None
