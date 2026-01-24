"""Example tests demonstrating basic harness usage."""

from ha_integration_test_harness import HomeAssistant


def test_entity_state(home_assistant: HomeAssistant) -> None:
    """Test setting and getting entity states."""
    # Set a state
    home_assistant.set_state("input_boolean.test_flag", "on")

    # Verify state
    state = home_assistant.get_state("input_boolean.test_flag")
    assert state["state"] == "on"

    # Cleanup
    home_assistant.remove_entity("input_boolean.test_flag")


def test_polling_for_state_change(home_assistant: HomeAssistant) -> None:
    """Test polling until a state changes."""
    # Create a timer
    home_assistant.set_state("timer.test_timer", "active", {"duration": "00:00:05"})

    # Poll until timer goes idle (with timeout)
    home_assistant.assert_entity_state("timer.test_timer", "idle", timeout=10)

    # Cleanup
    home_assistant.remove_entity("timer.test_timer")
