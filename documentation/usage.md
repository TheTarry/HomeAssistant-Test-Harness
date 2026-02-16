# Usage Guide

## Overview

The integration test harness provides a complete Docker-based test environment for Home Assistant and AppDaemon. Tests run against real instances, not mocks, ensuring your configuration works correctly.

## Installation

See [Installation Guide](installation.md) for details.

## How It Works

### Auto-Discovery

When you run tests, the harness:

1. **Checks environment variables**: Looks for `HOME_ASSISTANT_CONFIG_ROOT` (Home Assistant) and `APPDAEMON_CONFIG_ROOT` (AppDaemon)
2. **Falls back to subdirectories**: If environment variables are not set, looks for `home_assistant/` and `appdaemon/` subdirectories in the current working directory
3. **Validates configuration**:
   - Checks that `configuration.yaml` exists in the Home Assistant root (raises error if missing)
   - Checks that `apps/apps.yaml` exists in the AppDaemon root (logs warning if missing)
4. **Mounts directories**: Mounts the directories as `/config` in the Home Assistant container and `/conf/apps` in the AppDaemon container

**Note:** You can run tests from any directory by using either:

**Option 1 - Use default directory structure** (recommended):

```text
my-project/
├── home_assistant/          # Home Assistant configuration
│   └── configuration.yaml
├── appdaemon/              # AppDaemon configuration
│   └── apps/
│       └── apps.yaml
└── tests/                  # Your test files
    └── test_integration.py
```

**Option 2 - Set environment variables explicitly**:

```bash
export HOME_ASSISTANT_CONFIG_ROOT=/path/to/homeassistant/config
export APPDAEMON_CONFIG_ROOT=/path/to/appdaemon/config
pytest
```

If neither environment variables are set nor the default subdirectories exist, configuration validation will fail.

### Container Lifecycle

- **Session-scoped**: Containers start once per test session and are shared across all tests
- **Automatic cleanup**: Containers are stopped and removed after all tests complete
- **Parallel-safe**: Dynamic port allocation allows multiple test runs concurrently

## Test Environment Architecture

Integration tests use a Docker Compose environment to run isolated instances of Home Assistant and AppDaemon.

### Container Architecture

```plaintext
┌─────────────────────────────────────────────────────────────┐
│  Test Suite (pytest)                                        │
│  ├── Uses harness package (DockerComposeManager,            │
│  │   HomeAssistant, AppDaemon, TimeMachine)                 │
│  └── Interacts via HTTP APIs                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Docker Compose Environment                                 │
│  ┌────────────────────────┐   ┌──────────────────────────┐  │
│  │  Home Assistant        │   │  AppDaemon               │  │
│  │  Port: 8123 (ephemeral)│   │  Port: 5050 (ephemeral)  │  │
│  │  ├── Configuration     │   │  ├── Apps                │  │
│  │  │   (from repo)       │   │  │   (from repo)         │  │
│  │  ├── Automations       │   │  ├── Connected to HA     │  │
│  │  ├── Scripts           │   │  └── API enabled         │  │
│  │  └── Templates         │   │                          │  │
│  └────────────────────────┘   └──────────────────────────┘  │
│             │                              │                │
│             └──────────┬───────────────────┘                │
│                        ▼                                    │
│              ┌──────────────────┐                           │
│              │  Shared Volume   │                           │
│              │  - Auth token    │                           │
│              │  - Ready flags   │                           │
│              └──────────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

### Startup Sequence

The `docker-compose.yaml` orchestrates container startup with dependencies and health checks:

1. **Home Assistant starts** (`containers/homeassistant/entrypoint.sh`):
  - Copies repository configuration into `/config`
  - Starts Home Assistant server
  - Completes onboarding (creates test user)
  - Generates long-lived access token
  - Writes token to shared volume (`/shared_data/.ha_token`)
  - Creates ready flag (`/shared_data/.homeassistant_ready`)

2. **AppDaemon starts** (after HA is healthy) (`containers/appdaemon/entrypoint.sh`):
  - Waits for HA token file
  - Reads HA long-lived access token from shared volume
  - Generates `appdaemon.yaml` from template with token
  - Starts AppDaemon server
  - Waits for initialization to complete
  - Creates ready flag (`/shared_data/.appdaemon_ready`)

3. **Docker Compose health checks**:
  - Home Assistant: checks for `.homeassistant_ready` flag
  - AppDaemon: checks for `.appdaemon_ready` flag
  - `docker compose up --wait` blocks until both are healthy

### Parallel Test Execution

The environment supports **parallel test runs** via Docker Compose project names:

- Each test session gets a unique project ID (`uuid.uuid4().hex`)
- Containers are named `<project_id>-<service>-1` (e.g., `a1b2c3d4-homeassistant-1`)
- Ports are dynamically assigned (ephemeral mapping)
- Volumes are project-scoped (isolated state per run)

This design allows multiple developers or CI jobs to run tests simultaneously without conflicts.

## Writing Tests

### Basic Test

```python
def test_entity_state(home_assistant):
    """Test setting and reading entity states with automatic cleanup."""
    home_assistant.given_an_entity("input_boolean.test", "on")

    state = home_assistant.get_state("input_boolean.test")
    assert state["state"] == "on"

    # Entity is automatically cleaned up after test
```

### Time-Based Test

```python
def test_scheduled_automation(home_assistant, time_machine):
    """Test automation that triggers at specific time."""
    # Jump to next Monday at 10:00 AM
    time_machine.jump_to_next(day="Monday", hour=10, minute=0)

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

The harness provides **automatic cleanup** for test entities via `given_an_entity()`:

```python
def test_with_auto_cleanup(home_assistant):
    """Entities created with given_an_entity are automatically cleaned up."""
    home_assistant.given_an_entity("switch.test", "on")

    # ... test logic ...

    # No cleanup needed - handled automatically!
```

**Manual cleanup** is still supported for cases where you need explicit control:

```python
def test_with_manual_cleanup(home_assistant):
    """Manual cleanup when needed."""
    entity_id = "switch.test"
    home_assistant.set_state(entity_id, "on")

    # ... test logic ...

    # Manual cleanup
    home_assistant.remove_entity(entity_id)
```

**When to use each approach:**

- **Use `given_an_entity()`** (automatic): For most test entities that should be cleaned up after the test
- **Use `set_state()` + `remove_entity()`** (manual): When you need explicit control over cleanup timing or want to test entity removal behavior

### Factory Fixtures

Use factory patterns for creating multiple test entities with automatic cleanup:

```python
import pytest

@pytest.fixture
def create_entity(home_assistant):
    """Factory fixture with automatic cleanup via given_an_entity."""
    def _create(entity_id, state, **attributes):
        home_assistant.given_an_entity(entity_id, state, attributes)
        return entity_id

    return _create

def test_multiple_entities(create_entity):
    light1 = create_entity("light.test1", "on", brightness=255)
    light2 = create_entity("light.test2", "off")
    # Entities automatically cleaned up after test
```

**Alternative with manual tracking** (for advanced use cases):

```python
import pytest

@pytest.fixture
def create_entity_manual(home_assistant):
    """Factory fixture with manual cleanup tracking."""
    created = []

    def _create(entity_id, state):
        home_assistant.set_state(entity_id, state)
        created.append(entity_id)
        return entity_id

    yield _create

    # Manual cleanup
    for entity_id in created:
        home_assistant.remove_entity(entity_id)

def test_multiple_entities(create_entity_manual):
    light1 = create_entity_manual("light.test1", "on")
    light2 = create_entity_manual("light.test2", "off")
    # Entities cleaned up by fixture teardown
```

### Time Machine Isolation

Only request `time_machine` fixture in tests that need time manipulation:

```python
from datetime import timedelta

# Don't do this - time machine in every test
def test_normal(home_assistant, time_machine):
    pass

# Do this - only when needed
def test_time_based(home_assistant, time_machine):
    # Always explicitly set initial time conditions
    time_machine.fast_forward(timedelta(days=1))
    # ... test logic ...
```

**Important:** The `time_machine` fixture is session-scoped, so time persists across all tests and cannot be reset. Each test using time manipulation should
explicitly set its initial time state.

## Configuration Requirements

Your Home Assistant repository must contain:

- `configuration.yaml` at the root
- Valid Home Assistant configuration structure
- Any referenced files (automations, scripts, templates, etc.)

The harness mounts your entire repository, so all files are available to Home Assistant.

## Next Steps

- Review [Available Fixtures](fixtures.md) for complete API reference
- Check [Troubleshooting](troubleshooting.md) for common issues
