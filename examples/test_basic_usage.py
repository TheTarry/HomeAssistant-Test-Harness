"""Example tests demonstrating basic harness usage."""

from ha_integration_test_harness import HomeAssistant


def test_entity_state_with_manual_cleanup(home_assistant: HomeAssistant) -> None:
    """Test setting and getting entity states with manual cleanup."""
    # Set a state
    home_assistant.set_state("input_boolean.test_flag", "on")

    # Verify state
    state = home_assistant.get_state("input_boolean.test_flag")
    assert state["state"] == "on"

    # Manual cleanup required
    home_assistant.remove_entity("input_boolean.test_flag")


def test_entity_state_with_auto_cleanup(home_assistant: HomeAssistant) -> None:
    """Test setting and getting entity states with automatic cleanup."""
    # Use given_an_entity for automatic cleanup
    home_assistant.given_an_entity("input_boolean.test_flag_auto", "on")

    # Verify state
    state = home_assistant.get_state("input_boolean.test_flag_auto")
    assert state["state"] == "on"

    # No manual cleanup needed - entity will be automatically removed after test


def test_polling_for_state_change(home_assistant: HomeAssistant) -> None:
    """Test polling until a state changes."""
    # Given a timer entity (see configuration.yaml in the test config directory)

    # Poll until timer goes idle (with timeout)
    home_assistant.assert_entity_state("timer.test_timer", "idle", timeout=10)

    # Cleanup
    home_assistant.remove_entity("timer.test_timer")
