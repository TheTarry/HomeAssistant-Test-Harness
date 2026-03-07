---
applyTo: "src/ha_integration_test_harness/**/*.py"
---

# Python Source Instructions

## Code Style

- **Line length**: 200 characters
- **Formatter**: Black
- **Import sorting**: isort (black profile)
- **Type hints**: Required on all public APIs (functions, methods, class attributes)
- **Docstrings**: Google style — summary line, then `Args:`, `Returns:`, `Yields:`, `Raises:` sections as appropriate

## Naming Conventions

Follow [PEP 8](https://peps.python.org/pep-0008/#naming-conventions) naming conventions.
Private methods and attributes use a leading underscore (e.g., `_apply_faketime`).

## Error Handling

Always raise from the custom exception hierarchy in `exceptions.py` — never raise bare `Exception`:

- `DockerError` — Docker/container lifecycle failures
- `HomeAssistantClientError` — Home Assistant REST API failures
- `TimeMachineError` — time manipulation failures

Wrap third-party exceptions (e.g., `requests.RequestException`) in the appropriate custom exception and include enough context to identify the failing entity/URL.

## Key Implementation Patterns

- **Atomic file writes**: Use a temp-file-then-move pattern for any file that must not be seen in a partial state.
- **Minimal runtime dependencies**: Only `requests` and `python-dateutil` are runtime dependencies. Do not add new runtime dependencies without a compelling reason.
- **Package name consistency**: Always use `ha_integration_test_harness` (underscores, not hyphens) in imports and references.
- **Environment-based configuration**: Prefer environment variables (`HOME_ASSISTANT_CONFIG_ROOT`, `APPDAEMON_CONFIG_ROOT`) over hard-coded paths.
- **Error messages**: Include the GitHub usage docs link in error messages for configuration problems so users can self-diagnose.

## Adding a New Fixture

1. Define the fixture in `conftest.py` with a complete Google-style docstring.
2. Export it from `__init__.py` if it is part of the public API.
3. Document it in `documentation/fixtures.md`.
4. Add a usage example in `documentation/usage.md`.

## Time Manipulation Constraint

**Time can only move forward, never backward.** The `time_machine` fixture is session-scoped and persists across all tests.
There is no `reset_time()` method. Document this constraint clearly in any code that touches time state.
