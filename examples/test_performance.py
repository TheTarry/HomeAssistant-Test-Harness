"""Performance tests for given_an_entity() — entity creation should be fast.

Root cause of the issue being tested:

  ws_create_entity in the ha_test_harness custom integration calls
  ``await hass.async_block_till_done()`` after registering each entity.
  In minimal HA configurations this completes quickly, but in configurations
  that carry many integrations and automations the call drains the entire HA
  event loop — waiting for ALL pending tasks across the whole instance to finish.
  The result is that every call to given_an_entity() can block for tens of
  seconds or several minutes in production-like configs.

  The fix replaces async_block_till_done() with asyncio.sleep(0), which yields
  once to let the entity's own state-machine write propagate without waiting for
  unrelated tasks.

How the test reproduces the issue in a minimal config:

  configuration.yaml contains an automation ('perf_test_event_loop_probe') with a
  1-second delay that triggers whenever one of the reserved sensor.perf_test_* entities
  changes state.  This places a sleeping asyncio task in the HA event loop.

  async_block_till_done() gathers ALL pending asyncio tasks, including sleeping ones,
  so it blocks for the full 1-second delay on every entity creation.

  asyncio.sleep(0) yields control once and returns immediately; the automation
  continues in the background without blocking the response.

  Creating 5 entities back-to-back therefore takes:
    Bug  (async_block_till_done):  5 × ~1 s  = ~5 s  — exceeds the 2.5 s limit
    Fix  (asyncio.sleep(0)):       5 × ~0.1 s = ~0.5 s — well within the limit
"""

import time

from ha_integration_test_harness import HomeAssistant

# The automation in configuration.yaml triggers on exactly these entity IDs.
# Do not reuse these names in other tests.
_PERF_ENTITIES = [f"sensor.perf_test_{i}" for i in range(5)]

# Maximum acceptable total wall-clock time for creating _PERF_ENTITIES back-to-back
# on the warm path (platform already loaded).
#
# Chosen so that a single automation delay (1 s) per entity comfortably exceeds the
# limit (5 s expected vs 2.5 s allowed), while generous WebSocket + HA overhead
# (~0.1 s per entity) stays well below it.
_MAX_TOTAL_S = 2.5


def test_given_an_entity_warm_path_is_fast(home_assistant: HomeAssistant) -> None:
    """Entity creation should not block on unrelated HA event-loop tasks.

    The ha_test_harness integration must yield control once (asyncio.sleep(0))
    after registering a new entity, NOT drain the entire event loop with
    hass.async_block_till_done().

    Mechanism:
      configuration.yaml includes an automation ('perf_test_event_loop_probe')
      with a 1-second delay that fires whenever a sensor.perf_test_* entity
      changes state.  With async_block_till_done(), each entity creation blocks
      until the automation's sleeping task completes (~1 s).  With
      asyncio.sleep(0), creation returns immediately and the automation runs in
      the background.

    A failure here means ws_create_entity is still using async_block_till_done().
    """
    # Prime the sensor platform — cold path (may include platform_ready wait).
    # Uses a distinct entity ID so the perf automation does not fire here.
    home_assistant.given_an_entity("sensor.perf_prime", "0")

    # Warm path: time 5 back-to-back creations.
    # Each triggers the 1-second automation delay via configuration.yaml.
    start = time.monotonic()
    for entity_id in _PERF_ENTITIES:
        home_assistant.given_an_entity(entity_id, "42")
    elapsed = time.monotonic() - start

    assert elapsed < _MAX_TOTAL_S, (
        f"Creating {len(_PERF_ENTITIES)} entities took {elapsed:.2f}s "
        f"(limit: {_MAX_TOTAL_S}s). "
        f"ws_create_entity appears to be awaiting hass.async_block_till_done(), "
        f"which blocks until the 'perf_test_event_loop_probe' automation's 1-second "
        f"delay completes on every entity creation. "
        f"Fix: replace async_block_till_done() with asyncio.sleep(0) in "
        f"custom_components/ha_test_harness/__init__.py."
    )
