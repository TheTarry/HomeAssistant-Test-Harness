# Available Fixtures

The harness provides four pytest fixtures that are automatically available when the package is installed.

## `docker` (session scope)

Manages Docker container lifecycle for the entire test session.

### docker API

```python
docker.get_home_assistant_url() -> str
docker.get_appdaemon_url() -> str
docker.read_container_file(service: str, file_path: str) -> str
docker.write_container_file(service: str, file_path: str, content: str) -> None
docker.get_container_diagnostics() -> str
docker.containers_healthy() -> bool
```

### docker Usage

Most tests won't interact with `docker` directly. The `home_assistant` and `app_daemon` fixtures provide higher-level APIs.

```python
def test_with_docker(docker):
    # Get container diagnostics for debugging
    print(docker.get_container_diagnostics())
```

## `home_assistant` (session scope)

Home Assistant API client with automatic authentication and retry logic.

### home_assistant API

```python
home_assistant.set_state(entity_id: str, state: str, attributes: dict = None) -> None
home_assistant.get_state(entity_id: str) -> dict
home_assistant.assert_entity_state(entity_id: str, expected_state: str, timeout: int = 10) -> None
home_assistant.remove_entity(entity_id: str) -> None
home_assistant.regenerate_access_token() -> None
```

### home_assistant Usage

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

### home_assistant Methods

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

### app_daemon API

Currently provides basic initialization. Future versions will add methods for interacting with AppDaemon apps.

```python
def test_appdaemon(app_daemon):
    # Access base URL
    print(app_daemon.base_url)
```

## `time_machine` (function scope)

Manages time manipulation for deterministic testing of time-based automations.

### time_machine API

```python
time_machine.set_time(dt: datetime) -> None
time_machine.set_time(t: time) -> None
time_machine.set_time(preset: str, offset: timedelta = timedelta()) -> None
time_machine.advance_time(seconds: int) -> None
time_machine.reset_time() -> None
```

### time_machine Usage

```python
from datetime import datetime, time, timedelta

def test_time_manipulation(home_assistant, time_machine):
    # Freeze time at specific datetime
    time_machine.set_time(datetime(2026, 1, 21, 10, 30))

    # Set time to 7:30 AM today
    time_machine.set_time(time(7, 30))

    # Set time to 30 minutes after sunrise
    time_machine.set_time("sunrise", timedelta(minutes=30))

    # Set time to 1 hour before sunset
    time_machine.set_time("sunset", timedelta(hours=-1))

    # Advance time by 60 seconds
    time_machine.advance_time(60)

    # Verify time-based automation triggered
    home_assistant.assert_entity_state("light.scheduled", "on")

    # Time automatically resets after test
```

### time_machine Methods

#### `set_time(dt)`

Freezes time at specified datetime. All time-based automations see this time.

- **dt**: `datetime` object (timezone-aware or naive)

#### `set_time(t)`

Freezes time at specified time today. Combines the current date with the provided time.

- **t**: `time` object (e.g., `time(7, 30)` for 7:30 AM)

#### `set_time(preset, offset=timedelta())`

Sets time relative to sunrise or sunset. Uses the `sun.sun` entity from Home Assistant to determine sunrise/sunset times.

- **preset**: Either `"sunrise"` or `"sunset"`
- **offset**: Optional `timedelta` to add to the preset time (can be negative to go back)

Examples:

```python
# At sunrise
time_machine.set_time("sunrise")

# 30 minutes after sunrise
time_machine.set_time("sunrise", timedelta(minutes=30))

# 1 hour before sunset
time_machine.set_time("sunset", timedelta(hours=-1))
```

#### `advance_time(seconds)`

Advances time by specified number of seconds from current frozen time.

- **seconds**: Number of seconds to advance

#### `reset_time()`

Returns to real system time. Called automatically in fixture teardown.

### Limitations and Considerations

#### Time Can Only Move Forward

The `advance_time()` method only accepts non-negative values. To go back in time, use `set_time()` to jump to a specific earlier moment:

```python
# ✅ Supported - advance forward
time_machine.advance_time(60)  # Advance 60 seconds

# ❌ Not allowed - negative values
time_machine.advance_time(-60)  # Raises ValueError

# ✅ To go back, use set_time() instead
time_machine.set_time(datetime(2026, 1, 5, 10, 0))  # Jump to 10:00 AM
time_machine.advance_time(3600)  # Advance to 11:00 AM
time_machine.set_time(datetime(2026, 1, 5, 9, 0))   # Jump back to 9:00 AM
```

#### Second-Level Granularity

Time manipulation works at second-level precision. Sub-second accuracy is not supported:

```python
# ✅ Supported
time_machine.advance_time(60)  # 60 seconds

# ❌ Not meaningful (will advance 3 seconds, not 3.5)
time_machine.advance_time(3.5)  # Don't rely on fractional seconds
```

#### Timezone is Fixed

All tests use `Europe/London` timezone. You cannot change the timezone during a test.

#### Shared Clock Across Containers

Both Home Assistant and AppDaemon share the same fake clock. You cannot set different times for
each container.

#### State vs Time Persistence

The `docker`, `home_assistant`, and `app_daemon` fixtures are
session-scoped, so entity states persist across tests. The `time_machine` fixture is
function-scoped and automatically resets time after each test that uses it, but
entity states remain.

**Best practice:** Always set initial time at the start of tests that use time
manipulation, and reset relevant entity states if needed.

#### Real-Time Services May Behave Differently

Some Home Assistant integrations rely on real-time APIs (e.g., weather services, sun position
calculations). These may not respond correctly to fake time. Test external integrations with mock
data or acceptance tests.

### Example: Comprehensive Time-Based Test

```python
from datetime import datetime
from ha_integration_test_harness import HomeAssistant, TimeMachine

def test_heating_schedule(home_assistant: HomeAssistant, time_machine: TimeMachine):
    """Test that heating turns on at scheduled time and turns off after delay."""

    # Set time to Monday morning before heating schedule
    time_machine.set_time(datetime(2026, 1, 5, 6, 0))  # 6:00 AM

    # Verify heating is off
    state = home_assistant.get_state("climate.thermostat")
    assert state["attributes"]["hvac_action"] == "off"

    # Advance to heating schedule start (7:00 AM)
    time_machine.advance_time(3600)  # +1 hour

    # Verify heating turned on
    home_assistant.assert_entity_state("climate.thermostat", "heat", timeout=10)

    # Simulate someone leaving home
    home_assistant.set_state("person.homeowner", "not_home")

    # Verify heating turned off (automation should detect absence)
    home_assistant.assert_entity_state("climate.thermostat", "off", timeout=5)

    # Time is automatically reset to real time after this test completes
```

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
