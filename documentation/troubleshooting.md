# Troubleshooting

## Common Issues

### Configuration Not Found

**Error:**

```text
DockerError: configuration.yaml not found at /path/to/config/configuration.yaml.
Tests must be run from a Home Assistant configuration directory.
Set HOME_ASSISTANT_CONFIG_ROOT environment variable to specify the location.
See: https://github.com/TheTarry/HomeAssistant-Test-Harness#usage
```

**Cause:** Tests cannot find your Home Assistant `configuration.yaml` file.

**Solution:**

1. Ensure you're running tests from your Home Assistant configuration directory, or
2. Set the environment variable to point to your configuration:

   ```bash
   export HOME_ASSISTANT_CONFIG_ROOT=/path/to/homeassistant/config
   ```

3. Verify `configuration.yaml` exists at the root of that directory

### Docker Not Available

**Error:**

```text
DockerError: 'docker' command not found. Ensure Docker is installed and available in PATH.
```

**Cause:** Docker is not installed or not in the system PATH.

**Solution:**

1. Install Docker Desktop (Windows/Mac) or Docker Engine (Linux)
2. Ensure Docker daemon is running
3. Verify with: `docker --version`
4. Ensure your user has Docker permissions (Linux: add to docker group)

### Container Startup Failures

**Error:**

```text
Failed to start docker-compose environment (project: abc123)
```

**Cause:** Docker containers failed to start or health checks failed.

**Solution:**

1. Check Docker container logs in test output
2. Verify port 8123 and 5050 are available (or dynamic ports work)
3. Check Home Assistant configuration is valid
4. Try running containers manually: `cd src/ha_integration_test_harness/containers && docker compose up`

### Port Conflicts

**Symptoms:** Containers fail to start, port binding errors in logs.

**Cause:** Ports 8123 or 5050 are already in use (if not using dynamic ports).

**Solution:**

The harness uses ephemeral ports by default, so this should be rare. If you encounter port conflicts:

1. Stop other containers: `docker ps` and `docker stop <container>`
2. Check what's using the port: `netstat -an | grep 8123`
3. The harness should automatically use different ports for parallel runs

### Shell Script Line Ending Errors (Windows)

**Error:**

```text
/entrypoint.sh: line 2: set: -: invalid option
/entrypoint.sh: line 3: $'\r': command not found
/bin/bash: /entrypoint.sh: /bin/bash^M: bad interpreter: No such file or directory
```

**Cause:** Shell scripts have Windows line endings (CRLF) instead of Unix line endings (LF). This happens when the package is installed from git on Windows systems prior to v0.1.1.

**Solution:**

1. **Upgrade to v0.1.1 or later:** The package now includes `.gitattributes` that enforces Unix line endings for shell scripts:

   ```toml
   # In your pyproject.toml
   [project.optional-dependencies]
   dev = [
       "ha-integration-test-harness @ git+https://github.com/TheTarry/HomeAssistant-Test-Harness.git@v0.1.1"
   ]
   ```

2. **For versions prior to v0.1.1:** If you must use an older version, you can manually fix line endings after installation (not recommended):

   ```bash
   # Find the installed package location
   python -c "import ha_integration_test_harness; print(ha_integration_test_harness.__file__)"
   # Navigate to that directory and convert scripts
   find . -name "*.sh" -exec dos2unix {} \;
   ```

3. **For development:** If you've cloned the repository on Windows, the `.gitattributes` file (added in v0.1.1) will automatically normalize line endings. Re-clone the repository or run:

   ```bash
   git rm --cached -r .
   git reset --hard
   ```

### Fixtures Not Found

**Error:**

```text
fixture 'home_assistant' not found
```

**Cause:** The pytest plugin is not registered or the package is not installed correctly.

**Solution:**

1. Verify the package is in your dev dependencies:

   ```toml
   # pyproject.toml
   [project.optional-dependencies]
   dev = [
       "ha-integration-test-harness @ git+https://github.com/TheTarry/HomeAssistant-Test-Harness.git",
   ]
   ```

2. Reinstall dev dependencies: `pip install -e ".[dev]"`

3. Verify installation: `python -c "import ha_integration_test_harness"`

4. Check pytest sees the plugin: `pytest --fixtures | grep home_assistant`

### Time Manipulation Not Working

**Symptoms:** Time-based automations don't trigger at expected times.

**Cause:** LibFaketime not installed in container or not configured correctly.

**Solution:**

1. Check container logs for libfaketime installation messages
2. Verify `/shared_data/.faketime` file exists in container
3. Ensure `time_machine` fixture is requested in your test
4. Check that you called `time_machine.set_time()` before expecting time-based behavior

### Tests Hang or Timeout

**Symptoms:** Tests hang indefinitely or timeout after long wait.

**Cause:** Various issues including:

- Home Assistant not starting properly
- Health checks not passing
- Polling for state that never changes

**Solution:**

1. Check timeout values in `assert_entity_state()` calls
2. Review container diagnostics in test output
3. Run with pytest verbose mode: `pytest -v`
4. Check Home Assistant logs in container

### Permission Denied (Linux)

**Error:**

```text
Permission denied while trying to connect to the Docker daemon socket
```

**Cause:** User doesn't have permission to access Docker.

**Solution:**

```bash
sudo usermod -aG docker $USER
# Log out and log back in
```

## Debugging Tips

### View Container Logs

Containers are automatically stopped after tests, but logs are captured. Check test output for diagnostic information.

### Run Containers Manually

Navigate to the containers directory and run manually:

```bash
export HA_CONFIG_ROOT=/path/to/homeassistant/config
export APPDAEMON_CONFIG_ROOT=/path/to/appdaemon/config
cd src/ha_integration_test_harness/containers
docker compose up
```

### Pytest Verbose Mode

Run tests with verbose output:

```bash
pytest -v -s
```

The `-s` flag shows print statements and logging output.

### Enable Debug Logging

Add to your test or conftest.py:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Getting Help

If you encounter issues not covered here:

1. Check [GitHub Issues](https://github.com/TheTarry/HomeAssistant-Test-Harness/issues)
2. Open a new issue with:
  - Full error message
  - Test code that reproduces the issue
  - Container diagnostics from test output
  - Docker and Python versions
