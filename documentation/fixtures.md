# Available Fixtures

The harness provides four pytest fixtures that are automatically available when the package is installed.

## `docker` (session scope)

Manages Docker container lifecycle for the entire test session.

### API

```python
docker.get_home_assistant_url() -> str
docker.get_appdaemon_url() -> str
docker.read_container_file(service: str, file_path: str) -> str
docker.write_container_file(service: str, file_path: str, content: str) -> None
docker.get_container_diagnostics() -> str
docker.containers_healthy() -> bool
```

### Usage

Most tests won't interact with `docker` directly. The `home_assistant` and `app_daemon` fixtures provide higher-level APIs.

```python
def test_with_docker(docker):
    # Get container diagnostics for debugging
    print(docker.get_container_diagnostics())
```

## `home_assistant` (session scope)

Home Assistant API client with automatic authentication and retry logic.

### API

```python
home_assistant.set_state(entity_id: str, state: str, attributes: dict = None) -> None
home_assistant.get_state(entity_id: str) -> dict
home_assistant.assert_entity_state(entity_id: str, expected_state: str, timeout: int = 10) -> None
home_assistant.remove_entity(entity_id: str) -> None
home_assistant.regenerate_access_token() -> None
```

### Usage

```python
def test_home_assistant(home_assistant):
    # Set entity state
    home_assistant.set_state("switch.test", "on")
    
    # Get entity state
    state = home_assistant.get_state("switch.test")
    assert state["state"] == "on"
    
    # Poll until condition is met (with timeout)
    home_assistant.assert_entity_state("timer.test", "idle", timeout=30)
    
    # Clean up
    home_assistant.remove_entity("switch.test")
```

### Methods

#### `set_state(entity_id, state, attributes=None)`

Sets the state of an entity. Creates the entity if it doesn't exist.

- **entity_id**: Entity ID (e.g., `"switch.test"`)
- **state**: State value (e.g., `"on"`, `"off"`, `"20.5"`)
- **attributes**: Optional dictionary of entity attributes

#### `get_state(entity_id)`

Returns entity state as a dictionary with `state`, `attributes`, `last_changed`, etc.

#### `assert_entity_state(entity_id, expected_state, timeout=10)`

Polls entity state until it matches expected value or timeout expires. Raises `AssertionError` if timeout occurs.

- **timeout**: Maximum seconds to wait (default: 10)

#### `remove_entity(entity_id)`

Deletes an entity from Home Assistant. Use for test cleanup.

#### `regenerate_access_token()`

Generates a new access token. Called automatically after time manipulation.

## `app_daemon` (session scope)

AppDaemon API client.

### API

Currently provides basic initialization. Future versions will add methods for interacting with AppDaemon apps.

```python
def test_appdaemon(app_daemon):
    # Access base URL
    print(app_daemon.base_url)
```

## `time_machine` (function scope)

Manages time manipulation for deterministic testing of time-based automations.

### API

```python
time_machine.set_time(dt: datetime) -> None
time_machine.advance_time(seconds: int) -> None
time_machine.reset_time() -> None
```

### Usage

```python
from datetime import datetime

def test_time_manipulation(home_assistant, time_machine):
    # Freeze time at specific moment
    time_machine.set_time(datetime(2026, 1, 21, 10, 30))
    
    # Advance time by 60 seconds
    time_machine.advance_time(60)
    
    # Verify time-based automation triggered
    home_assistant.assert_entity_state("light.scheduled", "on")
    
    # Time automatically resets after test
```

### Methods

#### `set_time(dt)`

Freezes time at specified datetime. All time-based automations see this time.

- **dt**: `datetime` object (timezone-aware or naive)

#### `advance_time(seconds)`

Advances time by specified number of seconds from current frozen time.

- **seconds**: Number of seconds to advance

#### `reset_time()`

Returns to real system time. Called automatically in fixture teardown.

## Fixture Scopes

### Session Scope

`docker`, `home_assistant`, `app_daemon` are session-scoped:

- Created once when first test requests them
- Shared across all tests in the session
- Torn down after all tests complete
- Provides fast test execution (containers start once)

### Function Scope

`time_machine` is function-scoped:

- Created fresh for each test that requests it
- Automatically resets time after each test
- Isolates time manipulation between tests

## Next Steps

- Read [Troubleshooting](troubleshooting.md) for common issues
- See [Development Guide](development.md) for contributing
