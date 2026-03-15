# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A pytest plugin (`ha_integration_test_harness`) for integration testing Home Assistant and AppDaemon
configurations using real Docker containers — no mocks. Tests run against a live HA instance managed
by the harness.

## Commands

```bash
# Initial setup (installs deps via uv, sets up pre-commit, creates .env)
./setup_dev_env.sh

# Full validation: pre-commit hooks + build + install test + example tests
./run_checks.sh

# Run example tests only
pytest examples/

# Run a single example test
pytest examples/test_basic_usage.py::test_entity_state_with_auto_cleanup

# Individual checks
black src/ && isort src/   # format
flake8 src/                 # lint
mypy src/                   # type check
python -m build             # build package
```

## Architecture

The package is a thin pytest plugin layered over Docker and the Home Assistant REST/WebSocket API:

```text
Tests (examples/) → Pytest plugin (conftest.py) → Client libraries → Docker containers
```

**Key components:**

- **[conftest.py](src/ha_integration_test_harness/conftest.py)** — Registers four session-scoped
  fixtures: `docker`, `home_assistant`, `app_daemon`, `time_machine`. Also registers a
  function-scoped `_cleanup_test_entities` auto-use fixture that removes tracked entities after each
  test.

- **[docker_manager.py](src/ha_integration_test_harness/docker_manager.py)** — Orchestrates Docker
  Compose. Auto-discovers HA config from `HOME_ASSISTANT_CONFIG_ROOT` env var or `home_assistant/`
  subdirectory. Validates `configuration.yaml` exists. Stages config, manages persistent entities
  via YAML overlay + `configuration.yaml` patching, handles ephemeral ports for parallel test
  support.

- **[homeassistant_client.py](src/ha_integration_test_harness/homeassistant_client.py)** — REST +
  WebSocket API client. Key methods: `set_state()`, `get_state()`, `remove_entity()`,
  `call_action()`, `assert_entity_state()` (polls until match or timeout), `given_an_entity()`
  (creates + tracks for auto-cleanup). WebSocket used for entity registry updates (areas, labels).

- **[time_machine.py](src/ha_integration_test_harness/time_machine.py)** — Manipulates time via
  libfaketime. **Time can only move forward, never backward.** Session-scoped — clock persists
  across all tests. Methods: `fast_forward(delta)`, `jump_to_next(...)`,
  `advance_to_preset("sunrise"|"sunset")`.

- **[exceptions.py](src/ha_integration_test_harness/exceptions.py)** — Custom hierarchy:
  `IntegrationTestError` → `DockerError`, `HomeAssistantClientError`, `AppDaemonClientError`,
  `TimeMachineError`, `PersistentEntityError`. Always raise from this hierarchy, never bare
  `Exception`.

- **[containers/](src/ha_integration_test_harness/containers/)** — Docker Compose service
  definitions and setup scripts. The shared volume at `/shared_data/` carries tokens and time state
  between containers. File-based health markers (`.homeassistant_ready`) signal startup completion.

## Testing Strategy

There are **no unit tests** — the package is a thin wrapper around Docker/APIs. All testing is done
via example tests in `examples/` against real containers. CI mirrors `./run_checks.sh`.

## Code Style

- Line length: 200 characters (Black + isort black profile)
- Type hints required on all public APIs
- Docstrings: Google style (`Args:`, `Returns:`, `Raises:`)
- Private methods/attributes use leading underscore

## Writing Tests

**Prefer `given_an_entity()` for auto-cleanup:**

```python
home_assistant.given_an_entity("sensor.test", "42", attributes={"unit_of_measurement": "°C"})
```

**Use `call_action()` for derived entities** (template sensors, lights backed by `input_boolean`) —
`set_state()` has no effect on derived entities since HA recomputes them from the source.

**Use `assert_entity_state()` with `timeout`** for async state transitions:

```python
home_assistant.assert_entity_state("light.living_room", "on", timeout=10)
home_assistant.assert_entity_state("sensor.temp", expected_attributes={"min": lambda v: float(v) >= 10})
```

**Time machine:** Only request the `time_machine` fixture in tests that actually need it. Always
advance to explicit conditions in each test — the clock does not reset. Every test that depends on
time must advance to its own desired starting point.

## Adding a New Fixture

1. Define in `conftest.py` with Google-style docstring
2. Export from `__init__.py`
3. Document in `documentation/fixtures.md`
4. Add usage example in `documentation/usage.md`

## Modifying Docker Configuration

1. Update [docker-compose.yaml](src/ha_integration_test_harness/containers/docker-compose.yaml)
2. Test manually: `export REPO_ROOT=/path/to/ha/config && docker compose up`
3. Update related setup scripts (`homeassistant/entrypoint.sh`, etc.)

## Documentation

Each topic lives in its own file under `documentation/`. New files must be linked from `README.md`.
Keep each file focused on one topic — split rather than grow a single file. Cross-link from related
files where useful.

Style: relative links between docs, fenced code blocks with explicit language tags, ≤200 char lines,
one blank line between each top-level heading and its content.

## Important Constraints

- **Package name**: Always `ha_integration_test_harness` (underscores, not hyphens)
- **Runtime dependencies**: Only `requests`, `python-dateutil`, `PyYAML`, `websocket-client` —
  avoid adding new ones without strong justification
- **Config mounts are read-write** (not `:ro`) — HA needs to write to its config directory
- **Error messages** for configuration problems must include the GitHub usage docs link for
  self-diagnosis
- **Atomic file writes**: Use temp-file-then-move for files that must not be seen in a partial state
