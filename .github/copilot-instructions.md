# GitHub Copilot Instructions

This repository provides a pytest plugin for integration testing Home Assistant and AppDaemon configurations using Docker containers.

## Repository Overview

This is a **Python package** that:

- Provides pytest fixtures for Home Assistant integration testing
- Manages Docker containers (Home Assistant + AppDaemon)
- Auto-discovers and mounts user's Home Assistant configuration
- Supports time manipulation for deterministic testing

## Key Files and Structure

### Package Source (`src/ha_integration_test_harness/`)

- **__init__.py**: Public API exports and version
- **conftest.py**: Pytest plugin that registers fixtures
- **docker_manager.py**: Docker Compose orchestration and container lifecycle
- **homeassistant_client.py**: Home Assistant API client with auto-retry
- **appdaemon_client.py**: AppDaemon API client (basic)
- **time_machine.py**: Time manipulation via libfaketime
- **exceptions.py**: Exception hierarchy
- **containers/**: Docker Compose configuration and setup scripts
  - **docker-compose.yaml**: Service definitions for HA and AppDaemon
  - **homeassistant/**: HA container setup scripts (onboarding, token generation)
  - **appdaemon/**: AppDaemon container setup scripts
  - **libfaketime/**: Time manipulation library installation

### Documentation (`documentation/`)

- **installation.md**: Installation instructions
- **usage.md**: How to write tests, auto-discovery explanation
- **fixtures.md**: Complete fixture API reference
- **troubleshooting.md**: Common issues and debugging
- **development.md**: Development setup, version bumping, release process

### Configuration Files

- **pyproject.toml**: Package metadata, pytest plugin entry-point, build config
- **LICENSE**: MIT license
- **.gitignore**: Python/Docker ignore patterns
- **.pre-commit-config.yaml**: Code quality hooks (black, isort, flake8, mypy, yamllint, markdownlint)
- **.markdownlint_style.rb**: Markdown linting rules

### Development Scripts

- **setup_dev_env.sh**: One-command setup (dependencies, pre-commit, validation)
- **run_checks.sh**: Complete validation suite (pre-commit, build, install test, examples)

### CI/CD (`.github/workflows/`)

- **ci.yaml**: Runs pre-commit hooks, builds package, validates imports
- **release.yaml**: Creates timestamped GitHub releases
- **copilot-setup-steps.yml**: Workspace setup automation

## Important Concepts

### Auto-Discovery Mechanism

The `DockerComposeManager` in [docker_manager.py](src/ha_integration_test_harness/docker_manager.py):

1. Checks `HOME_ASSISTANT_CONFIG_ROOT` environment variable for Home Assistant config directory
2. Checks `APPDAEMON_CONFIG_ROOT` environment variable for AppDaemon config directory
3. Falls back to `os.getcwd()` if environment variables not set
4. Validates `configuration.yaml` exists in Home Assistant root (raises error if missing)
5. Validates `apps/apps.yaml` exists in AppDaemon root (logs warning if missing, continues)
6. Sets `HA_CONFIG_ROOT` and `APPDAEMON_CONFIG_ROOT` environment variables for docker-compose
7. docker-compose.yaml mounts `${HA_CONFIG_ROOT}:/config` and `${APPDAEMON_CONFIG_ROOT}/apps:/conf/apps`

### Pytest Plugin Registration

The package registers as a pytest plugin via `pyproject.toml`:

```toml
[project.entry-points.pytest11]
ha_integration_test_harness = "ha_integration_test_harness.conftest"
```

This makes fixtures (`docker`, `home_assistant`, `app_daemon`, `time_machine`) automatically available to tests.

### Container Lifecycle

- **Session-scoped**: Containers start once, shared across all tests
- **Ephemeral ports**: Docker assigns random ports for parallel test support
- **Auto-cleanup**: Containers stopped and removed after test session
- **Diagnostic capture**: Logs captured on failure for debugging

## Code Style and Conventions

### Python

- **Line length**: 200 characters
- **Type hints**: Required for public APIs
- **Docstrings**: Google style for classes/methods
- **Imports**: Sorted via isort (black profile)
- **Formatting**: Black formatter

### Naming Conventions

- **Functions/methods**: snake_case
- **Classes**: PascalCase
- **Constants**: UPPER_SNAKE_CASE
- **Private methods**: Leading underscore (_method_name)

### Error Handling

- Use custom exceptions from [exceptions.py](src/ha_integration_test_harness/exceptions.py)
- `DockerError` for Docker/container failures
- `HomeAssistantClientError` for HA API failures
- `TimeMachineError` for time manipulation failures

## Development Workflow

### Initial Setup

```bash
./setup_dev_env.sh
```

This script:

- Installs all dependencies using `uv`
- Sets up pre-commit hooks
- Runs initial validation (can skip with `--skip-checks`)

### Making Changes

1. Make code changes
2. Run validation: `./run_checks.sh`
3. Commit (pre-commit hooks run automatically)
4. Test in a real HA repo: `uv pip install -e /path/to/harness`

### Validation Script (`run_checks.sh`)

Runs complete validation:

1. Pre-commit hooks (black, isort, flake8, mypy, yamllint, markdownlint)
2. Package build (`python -m build`)
3. Installation test (imports package and verifies version)
4. Example tests (`pytest examples/`)

### Version Bumping

Update version in **both**:

- `pyproject.toml`: `version = "0.2.0"`
- `src/ha_integration_test_harness/__init__.py`: `__version__ = "0.2.0"`

Follow semantic versioning:

- **Major**: Breaking changes to fixtures/API
- **Minor**: New features (backward compatible)
- **Patch**: Bug fixes

### Release Process

1. Bump version (see above)
2. Commit and push
3. GitHub Actions "Create Release" workflow
4. Generates timestamp tag (yyyy-mm-dd@HH-MM-ss)
5. Creates GitHub release with auto-generated notes

## Common Tasks

### Adding a New Fixture

1. Define in [conftest.py](src/ha_integration_test_harness/conftest.py)
2. Add docstring with Args/Returns/Yields
3. Export from [__init__.py](src/ha_integration_test_harness/__init__.py) if part of public API
4. Document in [documentation/fixtures.md](documentation/fixtures.md)
5. Add usage example in [documentation/usage.md](documentation/usage.md)

### Modifying Docker Configuration

1. Update [docker-compose.yaml](src/ha_integration_test_harness/containers/docker-compose.yaml)
2. Test manually: `export REPO_ROOT=/path/to/ha/config && docker compose up`
3. Update related setup scripts (homeassistant/entrypoint.sh, etc.)
4. Document changes if user-facing

### Adding Documentation

- Create new `.md` file in `documentation/` directory
- Link from [README.md](README.md)
- Follow existing structure and style
- Keep line length ≤ 200 characters

## Testing Strategy

- **No unit tests**: Package is thin wrapper around Docker/APIs
- **Example tests**: `examples/` directory contains runnable examples
- **Validation script**: `./run_checks.sh` runs all quality checks, builds package, and runs examples
- **Manual testing**: Install in editable mode in real HA config repos
- **CI validation**: Mirrors `run_checks.sh` - builds package, validates imports, runs pre-commit hooks

## Important Notes

1. **Package name consistency**: `ha_integration_test_harness` (underscore, not hyphen)
2. **Read-write mounts**: Configuration directories mounted as read-write (not :ro) for HA storage writes
3. **Error messages**: Include link to GitHub usage docs for configuration errors
4. **Documentation structure**: Keep docs in separate files, link from README
5. **Environment variables**: Support `HOME_ASSISTANT_CONFIG_ROOT` and `APPDAEMON_CONFIG_ROOT` for flexible config paths

## Best Practices

- **Minimal dependencies**: Only `requests` for runtime
- **Clear error messages**: Help users debug issues
- **Atomic operations**: File writes use temp file + move pattern
- **Environment-based configuration**: Use env vars for flexible directory paths
- **Type safety**: Use type hints throughout

## Resources

- **Home Assistant API**: <https://developers.home-assistant.io/docs/api/rest/>
- **Docker Compose**: <https://docs.docker.com/compose/>
- **Pytest Fixtures**: <https://docs.pytest.org/en/stable/fixture.html>
- **Pytest Plugins**: <https://docs.pytest.org/en/stable/how-to/writing_plugins.html>
