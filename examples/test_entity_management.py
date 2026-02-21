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
    # Create a test entity using the new method
    home_assistant.given_an_entity("input_boolean.test_auto_cleanup", "on", attributes={"friendly_name": "Test Auto Cleanup"})

    # Verify the entity exists
    state = home_assistant.get_state("input_boolean.test_auto_cleanup")
    assert state is not None
    assert state["state"] == "on"
    assert state["attributes"]["friendly_name"] == "Test Auto Cleanup"

    # No manual cleanup needed - the fixture will handle it automatically!


def test_multiple_entities_with_auto_cleanup(home_assistant: HomeAssistant) -> None:
    """Test that multiple entities are all cleaned up automatically."""
    # Create multiple test entities
    home_assistant.given_an_entity("input_boolean.test_1", "on")
    home_assistant.given_an_entity("input_boolean.test_2", "off")
    home_assistant.given_an_entity("sensor.test_sensor", "42", attributes={"unit_of_measurement": "°C"})

    # Verify all entities exist
    assert home_assistant.get_state("input_boolean.test_1")["state"] == "on"
    assert home_assistant.get_state("input_boolean.test_2")["state"] == "off"
    sensor_state = home_assistant.get_state("sensor.test_sensor")
    assert sensor_state["state"] == "42"
    assert sensor_state["attributes"]["unit_of_measurement"] == "°C"

    # All entities will be automatically cleaned up after this test


def test_entity_update_tracked_correctly(home_assistant: HomeAssistant) -> None:
    """Test that updating an entity via given_an_entity() doesn't create duplicates."""
    # Create an entity
    home_assistant.given_an_entity("input_boolean.test_update", "on")

    # Update the same entity
    home_assistant.given_an_entity("input_boolean.test_update", "off", attributes={"updated": "true"})

    # Verify the entity has the updated state
    state = home_assistant.get_state("input_boolean.test_update")
    assert state["state"] == "off"
    assert state["attributes"]["updated"] == "true"

    # The entity should only be tracked once and cleaned up once


def test_mixing_given_an_entity_with_manual_cleanup(home_assistant: HomeAssistant) -> None:
    """Test that manual cleanup still works alongside auto-cleanup."""
    # Create an entity with auto-cleanup
    home_assistant.given_an_entity("input_boolean.auto_cleanup", "on")

    # Create an entity with manual cleanup
    home_assistant.set_state("input_boolean.manual_cleanup", "on")

    # Verify both entities exist
    assert home_assistant.get_state("input_boolean.auto_cleanup")["state"] == "on"
    assert home_assistant.get_state("input_boolean.manual_cleanup")["state"] == "on"

    # Manually clean up the manual entity
    home_assistant.remove_entity("input_boolean.manual_cleanup")

    # Verify manual entity is gone
    assert home_assistant.get_state("input_boolean.manual_cleanup") is None

    # The auto_cleanup entity will be cleaned up automatically


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

    guest_mode = home_assistant.get_state("input_boolean.guest_mode")
    assert guest_mode["attributes"]["icon"] == "mdi:account-group"

    temperature = home_assistant.get_state("input_number.target_temperature")
    assert float(temperature["attributes"]["min"]) == 10
    assert float(temperature["attributes"]["max"]) == 30

    house_mode = home_assistant.get_state("input_select.house_mode")
    assert "Home" in house_mode["attributes"]["options"]
    assert "Away" in house_mode["attributes"]["options"]
