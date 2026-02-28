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


def test_call_action_turn_on_light(home_assistant: HomeAssistant) -> None:
    """Test calling a turn_on action on a template light backed by an input_boolean.

    This demonstrates the correct approach for entities whose state is derived
    from another entity. Calling set_state() on the light would have no effect
    because Home Assistant recomputes the light's state from the backing
    input_boolean. Instead, call_action() triggers the light's turn_on script
    which updates the underlying input_boolean.
    """
    # Verify initial state is off (set by persistent_entities.yaml)
    home_assistant.assert_entity_state("light.study_light", "off")

    # Turn on the light via action - this updates the backing input_boolean
    home_assistant.call_action("light", "turn_on", {"entity_id": "light.study_light"})

    # Verify the light turned on
    home_assistant.assert_entity_state("light.study_light", "on", timeout=5)

    # Restore initial state so subsequent tests start with the light off
    # (light.study_light is a persistent entity and won't be auto-cleaned up)
    home_assistant.call_action("light", "turn_off", {"entity_id": "light.study_light"})
    home_assistant.assert_entity_state("light.study_light", "off", timeout=5)


def test_polling_for_state_change(home_assistant: HomeAssistant) -> None:
    """Test polling until a state changes."""
    # Given a timer entity (see configuration.yaml in the test config directory)

    # Poll until timer goes idle (with timeout)
    home_assistant.assert_entity_state("timer.test_timer", "idle", timeout=10)

    # Cleanup
    home_assistant.remove_entity("timer.test_timer")


def test_assert_entity_state_with_exact_attribute_match(home_assistant: HomeAssistant) -> None:
    """Test assert_entity_state with exact attribute matching.

    Demonstrates use-cases 2 (state + attribute) and 3 (attribute only):
    - Assert state and a specific attribute match simultaneously.
    - Assert only an attribute, without checking state.
    """
    # Use-case 2: assert state AND attribute together
    home_assistant.assert_entity_state("input_boolean.guest_mode", "off", expected_attributes={"icon": "mdi:account-group"})

    # Use-case 3: assert attribute only (no state check)
    home_assistant.assert_entity_state("input_select.house_mode", expected_attributes={"icon": "mdi:home"})

    # Use-case 5: assert multiple attributes at once
    home_assistant.assert_entity_state(
        "input_number.target_temperature",
        expected_attributes={"unit_of_measurement": "°C", "icon": "mdi:thermometer"},
    )


def test_assert_entity_state_with_predicate_attribute(home_assistant: HomeAssistant) -> None:
    """Test assert_entity_state with lambda predicate for attribute values.

    Demonstrates use-case 4: assert an attribute using a lambda function
    instead of an exact value, enabling range or type checks.
    """
    # Use-case 4: use a lambda to assert the attribute value satisfies a condition
    home_assistant.assert_entity_state(
        "input_number.target_temperature",
        expected_attributes={
            "min": lambda v: float(v) >= 10,
            "max": lambda v: float(v) <= 30,
        },
    )
