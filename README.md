# Home Assistant Integration Test Harness

A pytest plugin for integration testing Home Assistant and AppDaemon configurations using Docker containers.

## Features

- **Docker-based test environment**: Fully isolated Home Assistant and AppDaemon instances
- **Pytest fixtures**: Session-scoped containers with automatic cleanup
- **Auto-discovery**: Automatically mounts your repository configuration
- **API clients**: Python clients for Home Assistant and AppDaemon APIs
- **Time manipulation**: Freeze and advance time for deterministic testing
- **Parallel test support**: Dynamic port allocation for concurrent test runs

## Quick Start

### Installation

```bash
pip install ha_integration_test_harness
```

### Requirements

- Python 3.12+
- Docker Engine
- Docker Compose V2
- Home Assistant configuration repository (works best with git)

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

1. Detects your repository root (via git or current directory)
2. Validates `configuration.yaml` exists
3. Mounts your entire repository as `/config` in Home Assistant container
4. Starts Home Assistant and AppDaemon in Docker
5. Provides fixtures for testing

## Documentation

- [Installation Guide](documentation/installation.md)
- [Usage Guide](documentation/usage.md)
- [Available Fixtures](documentation/fixtures.md)
- [Troubleshooting](documentation/troubleshooting.md)
- [Development Guide](documentation/development.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Links

- **Repository**: <https://github.com/MarkTarry/HomeAssistant-Test-Harness>
- **Issues**: <https://github.com/MarkTarry/HomeAssistant-Test-Harness/issues>
- **Changelog**: <https://github.com/MarkTarry/HomeAssistant-Test-Harness/releases>
