"""Example tests demonstrating automatic entity cleanup and persistent entities.

This file demonstrates two entity management patterns:

1. Per-test entities via given_an_entity():
   - Created during a test via home_assistant.given_an_entity()
   - Automatically cleaned up after each test
   - Useful for test-specific temporary entities
   - Helps avoid test pollution and cross-test coupling

2. Persistent session entities:
   - Defined in a YAML file (persistent_entities.yaml) referenced via pyproject.toml
   - Registered with Home Assistant during container startup
   - Available throughout the entire test session
   - Never automatically removed
   - Useful for simulating integration-created entities that tests depend on

To use persistent entities:
1. Create a YAML file with entity definitions (see persistent_entities.yaml)
2. Add to your pyproject.toml:
   [tool.pytest.ini_options]
   ha_persistent_entities_path = "path/to/entities.yaml"
"""

from ha_integration_test_harness import HomeAssistant


def test_given_an_entity_with_auto_cleanup(home_assistant: HomeAssistant) -> None:
    """Test that entities created via given_an_entity() are automatically cleaned up."""
    home_assistant.given_an_entity("switch.test_auto_cleanup", "on")

    state = home_assistant.get_state("switch.test_auto_cleanup")
    assert state is not None
    assert state["state"] == "on"

    # No manual cleanup needed - the fixture will handle it automatically!


def test_multiple_entities_with_auto_cleanup(home_assistant: HomeAssistant) -> None:
    """Test that multiple entities are all cleaned up automatically."""
    home_assistant.given_an_entity("switch.test_1", "on")
    home_assistant.given_an_entity("switch.test_2", "off")
    home_assistant.given_an_entity("sensor.test_sensor", "42", attributes={"unit_of_measurement": "°C"})

    assert home_assistant.get_state("switch.test_1")["state"] == "on"
    assert home_assistant.get_state("switch.test_2")["state"] == "off"
    sensor_state = home_assistant.get_state("sensor.test_sensor")
    assert sensor_state["state"] == "42"
    assert sensor_state["attributes"]["unit_of_measurement"] == "°C"

    # All entities will be automatically cleaned up after this test


def test_entity_update_tracked_correctly(home_assistant: HomeAssistant) -> None:
    """Test that updating an entity via given_an_entity() doesn't create duplicates."""
    home_assistant.given_an_entity("switch.test_update", "on")

    # Update the same entity — should update in place, not create a duplicate
    home_assistant.given_an_entity("switch.test_update", "off", attributes={"updated": "true"})

    state = home_assistant.get_state("switch.test_update")
    assert state["state"] == "off"
    assert state["attributes"]["updated"] == "true"

    # The entity should only be tracked once and cleaned up once


def test_mixing_given_an_entity_with_manual_cleanup(home_assistant: HomeAssistant) -> None:
    """Test that manual cleanup still works alongside auto-cleanup."""
    # Create a registered entity via given_an_entity (auto-cleanup)
    home_assistant.given_an_entity("switch.auto_cleanup", "on")

    # Inject a raw state via REST (manual cleanup required, entity is NOT registry-registered)
    home_assistant.set_state("sensor.manual_cleanup", "42")

    assert home_assistant.get_state("switch.auto_cleanup")["state"] == "on"
    assert home_assistant.get_state("sensor.manual_cleanup")["state"] == "42"

    # Manually clean up the REST-injected entity
    home_assistant.remove_entity("sensor.manual_cleanup")

    assert home_assistant.get_state("sensor.manual_cleanup") is None

    # The switch entity will be cleaned up automatically


def test_persistent_entities_available_with_expected_initial_state(home_assistant: HomeAssistant) -> None:
    """Test that persistent entities exist and have expected initial state.

    This test demonstrates that persistent entities (defined via the
    ha_persistent_entities_path configuration) are registered during
    container startup, available to all tests, and initialized to expected
    values from persistent_entities.yaml.
    """
    home_assistant.assert_entity_state("input_boolean.guest_mode", "off")
    home_assistant.assert_entity_state("input_number.target_temperature", "20.0")
    home_assistant.assert_entity_state("input_select.house_mode", "Home")
    home_assistant.assert_entity_state("counter.doorbell_presses", "0")
    home_assistant.assert_entity_state("light.living_room_lamp", "off")
    home_assistant.assert_entity_state("switch.garage_door", "off")

    guest_mode = home_assistant.get_state("input_boolean.guest_mode")
    assert guest_mode["attributes"]["icon"] == "mdi:account-group"

    temperature = home_assistant.get_state("input_number.target_temperature")
    assert float(temperature["attributes"]["min"]) == 10
    assert float(temperature["attributes"]["max"]) == 30

    house_mode = home_assistant.get_state("input_select.house_mode")
    assert "Home" in house_mode["attributes"]["options"]
    assert "Away" in house_mode["attributes"]["options"]


def test_label_based_automation(home_assistant: HomeAssistant) -> None:
    """Test that a label-based automation turns on a light assigned the target label.

    An automation in configuration.yaml fires when input_button.label_automation_trigger
    is pressed and turns on all entities carrying the 'test_label_target' label.

    This test assigns that label to light.living_room_lamp, presses the button,
    and verifies the light turns on.  The label is automatically restored to its
    original value (no labels) after the test function completes.
    """
    # Assign the target label to the persistent light entity
    home_assistant.given_entity_has("light.living_room_lamp", labels=["test_label_target"])

    # Ensure the light starts off before triggering the automation
    home_assistant.assert_entity_state("light.living_room_lamp", "off")

    # Press the button — triggers the automation that uses label-based targeting
    home_assistant.call_action("input_button", "press", {"entity_id": "input_button.label_automation_trigger"})

    # The automation should turn on the light that carries the label
    home_assistant.assert_entity_state("light.living_room_lamp", "on", timeout=10)

    # Restore light state for subsequent tests (persistent entity — not auto-cleaned up)
    home_assistant.call_action("light", "turn_off", {"entity_id": "light.living_room_lamp"})
    home_assistant.assert_entity_state("light.living_room_lamp", "off", timeout=5)


def test_given_an_entity_then_remove_entity(home_assistant: HomeAssistant) -> None:
    """Test that an entity created via given_an_entity() can be explicitly removed.

    Entities created via given_an_entity() are registered in the HA entity registry.
    Calling remove_entity() removes them from both the state machine and the registry.
    """
    home_assistant.given_an_entity("sensor.test_removable", "42", attributes={"unit_of_measurement": "°C"})

    # Confirm entity is visible
    home_assistant.assert_entity_state("sensor.test_removable", "42")

    # Explicitly remove the entity
    home_assistant.remove_entity("sensor.test_removable")

    # Entity should be gone from the state machine
    assert home_assistant.get_state("sensor.test_removable") is None


def test_given_an_entity_then_assign_area_and_label(home_assistant: HomeAssistant) -> None:
    """Test that an entity created via given_an_entity() supports area and label assignment.

    Because given_an_entity() registers entities in the HA entity registry (with a
    unique_id), they can be targeted by given_entity_has() in the same test — a
    combination that was not possible with the previous REST-based entity creation.
    """
    home_assistant.given_an_entity("light.test_area_label", "off")

    # Assign an area and a label to the newly created entity
    home_assistant.given_entity_has("light.test_area_label", area="test_room", labels=["test_light"])

    # Entity state should still be readable after registry updates
    home_assistant.assert_entity_state("light.test_area_label", "off")


def test_area_based_automation(home_assistant: HomeAssistant) -> None:
    """Test that an area-based automation turns on a light assigned to the target area.

    An automation in configuration.yaml fires when input_button.area_automation_trigger
    is pressed and turns on all lights in the 'living_room' area.

    This test assigns the 'living_room' area to light.living_room_lamp, presses the
    button, and verifies the light turns on.  The area assignment is automatically
    restored to its original value (no area) after the test function completes.
    """
    # Assign the light to the 'living_room' area
    home_assistant.given_entity_has("light.living_room_lamp", area="living_room")

    # Ensure the light starts off before triggering the automation
    home_assistant.assert_entity_state("light.living_room_lamp", "off")

    # Press the button — triggers the automation that uses area-based targeting
    home_assistant.call_action("input_button", "press", {"entity_id": "input_button.area_automation_trigger"})

    # The automation should turn on the light that belongs to the area
    home_assistant.assert_entity_state("light.living_room_lamp", "on", timeout=10)

    # Restore light state for subsequent tests (persistent entity — not auto-cleaned up)
    home_assistant.call_action("light", "turn_off", {"entity_id": "light.living_room_lamp"})
    home_assistant.assert_entity_state("light.living_room_lamp", "off", timeout=5)
