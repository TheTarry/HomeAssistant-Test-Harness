---
applyTo: "examples/**/*.py"
---

# Test Instructions

## Test Structure

Tests live in `examples/` and run against real Docker-hosted Home Assistant and AppDaemon instances — there are no mocks.

All four fixtures (`docker`, `home_assistant`, `app_daemon`, `time_machine`) are **session-scoped**: they are created once and shared across the entire test session.
Entity states and the fake clock persist between tests.

## Entity Management

- **Prefer `given_an_entity()`** for test entities that should be cleaned up automatically after the test function returns.
- **Use `set_state()` + `remove_entity()`** only when you need explicit control over cleanup timing or are testing entity removal behaviour.
- **Prefer `call_action()` over `set_state()`** for entities whose state is derived from another entity
  (e.g., a template `light` backed by an `input_boolean`). Calling `set_state()` on a derived entity
  has no effect because Home Assistant recomputes its value from the source entity.

```python
# ✅ Automatic cleanup
home_assistant.given_an_entity("sensor.test", "42", attributes={"unit_of_measurement": "°C"})

# ✅ Controlling a derived entity
home_assistant.call_action("light", "turn_on", {"entity_id": "light.living_room"})

# ⚠️ Manual cleanup required
home_assistant.set_state("input_boolean.test_flag", "on")
home_assistant.remove_entity("input_boolean.test_flag")
```

## Time Machine Usage

Only request the `time_machine` fixture in tests that actually need time manipulation.

**Critical constraint: time can only move forward.** The fixture is session-scoped, so the clock does not reset between tests.
Every test that depends on specific time conditions must explicitly advance time to its desired starting point.

### Available Methods

```python
time_machine.fast_forward(delta: timedelta)
# Advance by a relative offset. Raises ValueError for negative deltas.

time_machine.jump_to_next(month=None, day=None, day_of_month=None, hour=None, minute=None, second=None)
# Jump to next occurrence matching calendar constraints.
# Constraint order: month → day_of_month → weekday → hour/minute/second
# Unspecified time components (hour/minute/second) are preserved from current fake time.

time_machine.advance_to_preset(preset: str, offset: Optional[timedelta] = None)
# Advance to next "sunrise" or "sunset" (from sun.sun entity), with optional offset.
```

### Examples

```python
from datetime import timedelta

def test_morning_automation(home_assistant, time_machine):
    # Always set initial time conditions explicitly
    time_machine.jump_to_next(day="Monday", hour=7, minute=0, second=0)
    home_assistant.assert_entity_state("light.morning", "on", timeout=5)

def test_evening_automation(home_assistant, time_machine):
    # Time is already past Monday 07:00 from the previous test — advance further forward
    time_machine.jump_to_next(hour=19)
    home_assistant.assert_entity_state("light.evening", "on", timeout=5)

def test_sunrise_automation(home_assistant, time_machine):
    time_machine.jump_to_next(hour=3)  # advance to 3 AM (before typical sunrise)
    time_machine.advance_to_preset("sunrise", timedelta(minutes=1))
    home_assistant.assert_entity_state("light.outdoor", "on", timeout=10)
```

## Assertions

Use `assert_entity_state()` (with `timeout`) rather than bare `assert state["state"] == ...` to handle asynchronous state transitions:

```python
# ✅ Poll until state matches (or timeout)
home_assistant.assert_entity_state("light.living_room", "on", timeout=10)

# ✅ Assert attributes alongside state
home_assistant.assert_entity_state(
    "climate.thermostat",
    "heat",
    expected_attributes={"hvac_action": "heating"},
    timeout=10,
)

# ✅ Lambda predicate for flexible value checks
home_assistant.assert_entity_state(
    "sensor.temperature",
    expected_attributes={"min": lambda v: float(v) >= 10},
)
```
