# Installation Guide

## Requirements

- Python 3.12 or later
- Docker Engine (running and accessible)
- Docker Compose V2
- A Home Assistant configuration repository

## Installation

### From PyPI (when published)

```bash
pip install ha_integration_test_harness
```

### From GitHub

```bash
pip install git+https://github.com/MarkTarry/HomeAssistant-Test-Harness.git
```

### For Development

Clone the repository and run the setup script:

```bash
git clone https://github.com/MarkTarry/HomeAssistant-Test-Harness.git
cd HomeAssistant-Test-Harness
./setup_dev_env.sh
```

This installs dependencies, sets up pre-commit hooks, and runs validation. See the [Development Guide](development.md) for more details.

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
