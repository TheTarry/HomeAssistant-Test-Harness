"""Example tests demonstrating automatic entity cleanup."""

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
    home_assistant.given_an_entity("input_boolean.test_update", "off", attributes={"updated": True})

    # Verify the entity has the updated state
    state = home_assistant.get_state("input_boolean.test_update")
    assert state["state"] == "off"
    assert state["attributes"]["updated"] is True

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
