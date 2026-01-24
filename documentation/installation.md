# Installation Guide

## Requirements

- Python 3.12 or later
- Docker Engine (running and accessible)
- Docker Compose V2
- A Home Assistant configuration repository

## Installation

### From GitHub

```bash
pip install git+https://github.com/MarkTarry/HomeAssistant-Test-Harness.git
```

## Verification

Verify the installation:

```bash
python -c "import ha_integration_test_harness; print(ha_integration_test_harness.__version__)"
```

## Configuration

No configuration is required. The plugin automatically:

- Registers pytest fixtures when installed
- Detects your repository root
- Mounts your configuration into Docker containers

## Next Steps

- Read the [Usage Guide](usage.md) to learn how to write tests
- Review [Available Fixtures](fixtures.md) to understand what's provided
- Check [Troubleshooting](troubleshooting.md) if you encounter issues
