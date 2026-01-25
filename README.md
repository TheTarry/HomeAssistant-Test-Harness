# Home Assistant Integration Test Harness

A pytest plugin for integration testing Home Assistant and AppDaemon configurations using Docker containers.

[![Continuous Integration](https://github.com/TheTarry/HomeAssistant-Test-Harness/actions/workflows/ci.yaml/badge.svg)](https://github.com/TheTarry/HomeAssistant-Test-Harness/actions/workflows/ci.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Features

- **Docker-based test environment**: Fully isolated Home Assistant and AppDaemon instances
- **Pytest fixtures**: Session-scoped containers with automatic cleanup
- **Flexible configuration**: Uses environment variables or current directory
- **API clients**: Python clients for Home Assistant and AppDaemon APIs
- **Time manipulation**: Freeze and advance time for deterministic testing
- **Parallel test support**: Dynamic port allocation for concurrent test runs

## Quick Start

### Installation

Since this is a pytest plugin for testing, install it as a **dev dependency** in your Home Assistant configuration repository.

Add to your `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "ha-integration-test-harness @ git+https://github.com/TheTarry/HomeAssistant-Test-Harness.git",
]
```

Then install:

```bash
pip install -e ".[dev]"
```

See the [Installation Guide](documentation/installation.md) for alternative methods.

### Requirements

- Python 3.12+
- Docker Engine
- Docker Compose V2
- Home Assistant configuration directory with `configuration.yaml`

### Write a Test

```python
def test_automation(home_assistant):
    """Test that an automation works correctly."""
    # Set entity state
    home_assistant.set_state("input_boolean.test_mode", "on")

    # Trigger automation
    home_assistant.set_state("binary_sensor.motion", "on")

    # Assert expected outcome (polls with timeout)
    home_assistant.assert_entity_state("light.living_room", "on", timeout=10)
```

### Run Tests

```bash
pytest
```

The plugin automatically:

1. Detects your Home Assistant configuration directory (via `HOME_ASSISTANT_CONFIG_ROOT` env var or current directory)
2. Detects your AppDaemon configuration directory (via `APPDAEMON_CONFIG_ROOT` env var or current directory)
3. Validates `configuration.yaml` exists in Home Assistant directory
4. Validates `apps/apps.yaml` exists in AppDaemon directory (warning only)
5. Mounts configuration directories into Docker containers
6. Starts Home Assistant and AppDaemon
7. Provides fixtures for testing

## Documentation

- [Installation Guide](documentation/installation.md)
- [Usage Guide](documentation/usage.md)
- [Available Fixtures](documentation/fixtures.md)
- [Troubleshooting](documentation/troubleshooting.md)
- [Development Guide](documentation/development.md)

## Links

- **Repository**: <https://github.com/TheTarry/HomeAssistant-Test-Harness>
- **Issues**: <https://github.com/TheTarry/HomeAssistant-Test-Harness/issues>
- **Changelog**: <https://github.com/TheTarry/HomeAssistant-Test-Harness/releases>

## Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:

- Setting up the development environment
- Code standards and style guide
- Running tests and validation
- Submitting pull requests

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

## Security

For security issues, please see our [Security Policy](SECURITY.md) for responsible disclosure guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
