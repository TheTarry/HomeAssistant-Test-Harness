# Usage Guide

## Overview

The integration test harness provides a complete Docker-based test environment for Home Assistant and AppDaemon. Tests run against real instances, not mocks, ensuring your configuration works correctly.

## How It Works

### Auto-Discovery

When you run tests, the harness:

1. **Detects repository root**: Uses `git rev-parse --show-toplevel` to find your repository root
2. **Falls back gracefully**: If git is not available, uses current working directory
3. **Validates configuration**: Checks that `configuration.yaml` exists at the root
4. **Mounts repository**: Mounts the entire repository as `/config` in the Home Assistant container

**Note:** The harness works best when run from within a git repository, but will function without git.

### Container Lifecycle

- **Session-scoped**: Containers start once per test session and are shared across all tests
- **Automatic cleanup**: Containers are stopped and removed after all tests complete
- **Parallel-safe**: Dynamic port allocation allows multiple test runs concurrently

## Writing Tests

### Basic Test

```python
def test_entity_state(home_assistant):
    """Test setting and reading entity states."""
    home_assistant.set_state("input_boolean.test", "on")
    
    state = home_assistant.get_state("input_boolean.test")
    assert state["state"] == "on"
    
    # Cleanup
    home_assistant.remove_entity("input_boolean.test")
```

### Time-Based Test

```python
from datetime import datetime

def test_scheduled_automation(home_assistant, time_machine):
    """Test automation that triggers at specific time."""
    # Set time to 10:00 AM
    time_machine.set_time(datetime(2026, 1, 21, 10, 0))
    
    # Verify automation triggered
    home_assistant.assert_entity_state("light.morning", "on", timeout=5)
```

### Polling for State Changes

```python
def test_automation_with_delay(home_assistant):
    """Test automation that has a delay."""
    home_assistant.set_state("binary_sensor.motion", "on")
    
    # Poll until light turns on (or timeout after 30 seconds)
    home_assistant.assert_entity_state("light.living_room", "on", timeout=30)
```

## Best Practices

### Cleanup

Always clean up test entities to prevent state pollution:

```python
def test_with_cleanup(home_assistant):
    entity_id = "switch.test"
    home_assistant.set_state(entity_id, "on")
    
    # ... test logic ...
    
    # Cleanup
    home_assistant.remove_entity(entity_id)
```

### Factory Fixtures

Use factory patterns for creating multiple test entities:

```python
import pytest

@pytest.fixture
def create_entity(home_assistant):
    created = []
    
    def _create(entity_id, state):
        home_assistant.set_state(entity_id, state)
        created.append(entity_id)
        return entity_id
    
    yield _create
    
    # Automatic cleanup
    for entity_id in created:
        home_assistant.remove_entity(entity_id)

def test_multiple_entities(create_entity):
    light1 = create_entity("light.test1", "on")
    light2 = create_entity("light.test2", "off")
    # Entities automatically cleaned up after test
```

### Time Machine Isolation

Only request `time_machine` fixture in tests that need time manipulation:

```python
# Don't do this - time machine in every test
def test_normal(home_assistant, time_machine):
    pass

# Do this - only when needed
def test_time_based(home_assistant, time_machine):
    time_machine.set_time(...)
```

## Configuration Requirements

Your Home Assistant repository must contain:

- `configuration.yaml` at the root
- Valid Home Assistant configuration structure
- Any referenced files (automations, scripts, templates, etc.)

The harness mounts your entire repository, so all files are available to Home Assistant.

## Next Steps

- Review [Available Fixtures](fixtures.md) for complete API reference
- Check [Troubleshooting](troubleshooting.md) for common issues
