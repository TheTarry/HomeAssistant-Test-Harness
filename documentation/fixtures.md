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
home_assistant.given_an_entity(entity_id: str, state: str, attributes: dict = None) -> None
home_assistant.clean_up_test_entities() -> None
home_assistant.regenerate_access_token() -> None
```

### home_assistant Usage

```python
def test_home_assistant(home_assistant):
    # Create entity with automatic cleanup
    home_assistant.given_an_entity("switch.test", "on")

    # Get entity state
    state = home_assistant.get_state("switch.test")
    assert state["state"] == "on"

    # Poll until condition is met (with timeout)
    home_assistant.assert_entity_state("timer.test", "idle", timeout=30)

    # Entity is automatically cleaned up after test
```

#### Alternative: Manual cleanup

```python
def test_manual_cleanup(home_assistant):
    # Set entity state (manual cleanup required)
    home_assistant.set_state("switch.test", "on")

    # Get entity state
    state = home_assistant.get_state("switch.test")
    assert state["state"] == "on"

    # Manual cleanup
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

Deletes an entity from Home Assistant. Use for manual test cleanup.

#### `given_an_entity(entity_id, state, attributes=None)`

Creates an entity for testing with **automatic cleanup**. The entity is tracked and automatically removed after the test function completes.

- **entity_id**: Entity ID (e.g., `"switch.test"`)
- **state**: State value (e.g., `"on"`, `"off"`, `"20.5"`)
- **attributes**: Optional dictionary of entity attributes

If called multiple times with the same `entity_id`, the entity is tracked only once (no duplicates).

**Example:**

```python
def test_automation(home_assistant):
    # Create entity with automatic cleanup
    home_assistant.given_an_entity("sensor.test", "42", {"unit_of_measurement": "°C"})

    # Test logic here
    assert home_assistant.get_state("sensor.test")["state"] == "42"

    # No cleanup needed - handled automatically!
```

#### `clean_up_test_entities()`

Removes all entities created via `given_an_entity()`. This method is called automatically by the test harness after each test function, so you typically don't need to call it manually.

If cleanup fails for some entities, all tracked entities are still removed from tracking, and errors are reported collectively.

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

## `time_machine` (session scope)

Manages time manipulation for deterministic testing of time-based automations.

**IMPORTANT LIMITATION**: Time can only move forward, never backward. The fixture is session-scoped, meaning time persists
across all tests in the session and cannot be reset to real time or an earlier point. This is a fundamental constraint of the Home Assistant container.

### time_machine API

```python
time_machine.fast_forward(delta: timedelta) -> None
time_machine.jump_to_next(month=None, day=None, day_of_month=None, hour=None, minute=None, second=None) -> None
time_machine.advance_to_preset(preset: str, offset: Optional[timedelta] = None) -> None
```

### time_machine Usage

```python
from datetime import timedelta

def test_time_manipulation(home_assistant, time_machine):
    # Advance time by 5 days
    time_machine.fast_forward(timedelta(days=5))

    # Jump to next Monday at 10:00 AM
    time_machine.jump_to_next(day="Monday", hour=10, minute=0)

    # Advance to 30 minutes after next sunrise
    time_machine.advance_to_preset("sunrise", timedelta(minutes=30))

    # Verify time-based automation triggered
    home_assistant.assert_entity_state("light.scheduled", "on")

    # NOTE: Time cannot be reset - it persists for the entire test session
```

### time_machine Methods

#### `fast_forward(delta: timedelta)`

Advances time forward by the specified timedelta. The advancement is cumulative - calling this method multiple times will continue advancing from the current fake time.

**Parameters:**

- **delta**: A timedelta object specifying the amount of time to advance. Supports weeks, days, hours, minutes, seconds, and microseconds.

**Examples:**

```python
# Advance by 1 day
time_machine.fast_forward(timedelta(days=1))

# Advance by 1 hour and 30 minutes
time_machine.fast_forward(timedelta(hours=1, minutes=30))

# Advance by 2 weeks, 3 days, and 4 hours
time_machine.fast_forward(timedelta(weeks=2, days=3, hours=4))

# Advance by 30 seconds
time_machine.fast_forward(timedelta(seconds=30))
```

**Raises:**

- `ValueError`: If delta is negative (time can only move forward)
- `TimeMachineError`: If time manipulation fails

#### `jump_to_next(month=None, day=None, day_of_month=None, hour=None, minute=None, second=None)`

Jumps to the next occurrence of specified calendar constraints. Constraints are applied in a specific order:

1. **Month**: Advance to next occurrence of specified month
2. **Day of month**: Set the day of the month (may advance to next month if needed)
3. **Weekday**: Advance to next occurrence of specified weekday
4. **Time**: Set hour/minute/second (preserving unspecified components)

All parameters are optional. Unspecified time components (hour/minute/second) preserve their values from the current fake time.

**Parameters:**

- **month**: Month name ("Jan"/"January") or 3-char abbreviation (case-insensitive)
- **day**: Weekday name ("Mon"/"Monday") or 3-char abbreviation (case-insensitive)
- **day_of_month**: Day of the month (1-31). Applied after month, before weekday
- **hour**: Hour of day (0-23). Preserves current hour if omitted
- **minute**: Minute (0-59). Preserves current minute if omitted
- **second**: Second (0-59). Preserves current second if omitted

**Examples:**

```python
# Jump to next Monday at current time
time_machine.jump_to_next(day="Monday")

# Jump to next February, preserving current day and time
time_machine.jump_to_next(month="Feb")

# Jump to 1st of next month
time_machine.jump_to_next(day_of_month=1)

# Complex: From Jan 31 14:30:00, jump to next Monday in February at 10:00:00
# Result: Feb 3 10:00:00 (1st of Feb is Sat, next Mon is 3rd, time set to 10:00)
time_machine.jump_to_next(month="Feb", day="Monday", hour=10)
```

**Constraint Resolution Order Example:**

From **Tue Jan 31 14:30:00**, calling:

```python
time_machine.jump_to_next(day_of_month=1, day="Monday", hour=10)
```

**Step-by-step execution:**

1. Set to **1st of next month** → **Feb 1 14:30:00** (Feb 1 is Saturday)
2. Advance to **next Monday** → **Feb 3 14:30:00**
3. Set **hour to 10** → **Feb 3 10:30:00** (minutes/seconds preserved)

**Another example** - From **Tue Jan 31 14:30:00**, calling:

```python
time_machine.jump_to_next(month="Feb", day_of_month=1, day="Monday")
```

**Step-by-step execution:**

1. Jump to **February** → **Feb 28 14:30:00** (or Feb 29 in leap year, same day-of-month as current)
2. Set to **1st** → **Mar 1 14:30:00** (Feb 1 is in the past, so next occurrence is March 1)
3. Advance to **next Monday** → **Mar 3 14:30:00** (if Mar 1 is Saturday)

**Raises:**

- `ValueError`: If month/day names are invalid or numeric values out of range
- `TimeMachineError`: If result would not be in the future or manipulation fails

#### `advance_to_preset(preset, offset=None)`

Advances time to the next sunrise or sunset, with optional offset. Uses the `sun.sun` entity from Home Assistant to determine sunrise/sunset times.

**Parameters:**

- **preset**: Either "sunrise" or "sunset" (case-insensitive)
- **offset**: Optional `timedelta` to add to the preset time (can be negative for "before")

**Examples:**

```python
# Advance to next sunrise
time_machine.advance_to_preset("sunrise")

# Advance to 30 minutes after next sunrise
time_machine.advance_to_preset("sunrise", timedelta(minutes=30))

# Advance to 1 hour before next sunset
time_machine.advance_to_preset("sunset", timedelta(hours=-1))
```

**Raises:**

- `ValueError`: If get_entity_state callback is not configured or preset is invalid
- `TimeMachineError`: If entity fetch fails, parsing fails, or result would not be in future

### Limitations and Considerations

#### Time Can Only Move Forward (Critical Limitation)

**You CANNOT move time backward or reset time to real time.** This is a fundamental constraint of the Home Assistant container.

```python
# ✅ Supported - advance forward
time_machine.fast_forward(timedelta(days=1))

# ✅ Supported - jump to next occurrence (always in future)
time_machine.jump_to_next(day="Monday")

# ❌ NOT SUPPORTED - cannot move time backward
# Once time has advanced, it CANNOT go back

# ❌ This will raise an error:
time_machine.fast_forward(timedelta(days=-1))  # Negative values not allowed

# ❌ There is NO way to reset time to real time or an earlier point
# No reset_time() method exists
```

#### Session-Scoped Fixture Means Persistent Time

The `time_machine` fixture is **session-scoped**, meaning time persists across all tests in the session. Tests must explicitly advance time to their desired starting conditions.

**Best practice:** Each test that uses time manipulation should explicitly set its initial time state:

```python
def test_morning_automation(home_assistant, time_machine):
    # Explicitly advance to desired starting time
    time_machine.jump_to_next(day="Monday", hour=7)

    # ... test logic ...

def test_evening_automation(home_assistant, time_machine):
    # This test runs AFTER test_morning_automation, so time is already
    # Monday 7:XX. We need to explicitly advance to evening:
    time_machine.jump_to_next(hour=19)  # 7 PM

    # ... test logic ...
```

#### Second-Level Granularity

Time manipulation works at second-level precision. Sub-second accuracy is not supported:

```python
# ✅ Supported
time_machine.fast_forward(timedelta(seconds=60))

# ⚠️ Fractional seconds are truncated
time_machine.fast_forward(timedelta(seconds=3, milliseconds=500))  # Can only advance by whole seconds
```

#### Timezone is Fixed

All tests use `Europe/London` timezone. You cannot change the timezone during a test.

#### Shared Clock Across Containers

Both Home Assistant and AppDaemon share the same fake clock. You cannot set different times for
each container.

#### State Persistence Across Tests

The `docker`, `home_assistant`, and `app_daemon` fixtures are session-scoped, so entity states persist across tests. The `time_machine` fixture is also session-scoped,
so time persists and cannot be reset.

**Best practice:** Always explicitly set initial time at the start of tests that use time manipulation. Reset relevant entity states if needed:

```python
def test_automation_sequence(home_assistant, time_machine):
    # Set initial conditions
    time_machine.jump_to_next(day="Monday", hour=6, minute=0, second=0) # Start from known time
    home_assistant.set_state("input_boolean.test_mode", "off")

    # ... test logic ...
```

#### Real-Time Services May Behave Differently

Some Home Assistant integrations rely on real-time APIs (e.g., weather services, sun position
calculations). These may not respond correctly with a fake time set.

```python
from ha_integration_test_harness import HomeAssistant, TimeMachine

def test_heating_schedule(home_assistant: HomeAssistant, time_machine: TimeMachine):
    """Test that heating turns on at scheduled time and turns off after delay."""

    # Advance to Monday morning before heating schedule (6:00 AM)
    time_machine.jump_to_next(day="Monday", hour=6, minute=0, second=0)

    # Verify heating is off
    state = home_assistant.get_state("climate.thermostat")
    assert state["attributes"]["hvac_action"] == "off"

    # Advance to heating schedule start (7:00 AM)
    time_machine.fast_forward(timedelta(hours=1))

    # Verify heating turned on
    home_assistant.assert_entity_state("climate.thermostat", "heat", timeout=10)

    # Simulate someone leaving home
    home_assistant.set_state("person.homeowner", "not_home")

    # Verify heating turned off (automation should detect absence)
    home_assistant.assert_entity_state("climate.thermostat", "off", timeout=5)

    # NOTE: Time remains at Monday 7:00 AM for subsequent test
```

All fixtures (`docker`, `home_assistant`, `app_daemon`, `time_machine`) are session-scoped:

- Created once when first test requests them
- Shared across all tests in the session
- Torn down after all tests complete
- Provides fast test execution (containers start once)
- **Time and entity states persist across tests**

**Important:** Because time persists and cannot be reset, time-dependent test scenarios should always explicitly set their initial time conditions.

## Next Steps

- Read [Troubleshooting](troubleshooting.md) for common issues
- See [Development Guide](development.md) for contributing
