"""Pytest configuration and fixtures for integration tests."""

import logging
from typing import Any, Generator

import pytest

from .appdaemon_client import AppDaemon
from .docker_manager import DockerComposeManager
from .homeassistant_client import HomeAssistant
from .time_machine import TimeMachine

logger = logging.getLogger(__name__)

# Session-level flag to capture diagnostics only once
_diagnostics_captured = False


def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[Any]) -> None:
    """Pytest hook to detect test failures and mark for diagnostics capture."""
    if call.when == "call" and call.excinfo is not None:
        # Test failed - mark in session stash
        if not hasattr(item.session, "_test_failure_detected"):
            item.session._test_failure_detected = True


@pytest.fixture(scope="session")  # type: ignore[untyped-decorator]
def docker(request: pytest.FixtureRequest) -> Generator[DockerComposeManager, None, None]:
    """Provide Docker Compose manager for integration tests.

    This fixture creates and starts Docker containers for Home Assistant and AppDaemon,
    managing their lifecycle for the entire test session (scope="session") to avoid
    the overhead of repeatedly starting and stopping containers.

    The containers are automatically cleaned up after all tests in the session complete.

    Yields:
        DockerComposeManager: Manager for Docker container lifecycle and file operations.
    """
    global _diagnostics_captured
    manager = DockerComposeManager()
    try:
        manager.start()
        logger.info("Docker containers started successfully")
        yield manager
    except Exception:
        logger.warning(f"Container startup failed\n{manager.get_container_diagnostics()}")
        _diagnostics_captured = True
        raise
    finally:
        # Capture diagnostics if any failures detected
        test_failures = request.session.testsfailed > 0
        hook_failures = getattr(request.session, "_test_failure_detected", False)
        container_failure = not manager.containers_healthy()

        if (test_failures or hook_failures or container_failure) and not _diagnostics_captured:
            logger.warning(manager.get_container_diagnostics())
            _diagnostics_captured = True

        logger.info("Tearing down Docker containers")
        manager.stop()


@pytest.fixture(scope="session")  # type: ignore[untyped-decorator]
def home_assistant(docker: DockerComposeManager) -> HomeAssistant:
    """Provide Home Assistant API client for integration tests.

    This fixture creates a Home Assistant client configured with the dynamically
    assigned URL and refresh token from the Docker container. The client is shared
    across all tests in the session (scope="session").

    Args:
        docker: The Docker container manager fixture.

    Returns:
        HomeAssistant: Client for Home Assistant API interactions.
    """
    base_url = docker.get_home_assistant_url()
    refresh_token = docker.read_container_file("homeassistant", "/shared_data/.ha_refresh_token")
    return HomeAssistant(base_url, refresh_token)


@pytest.fixture(scope="session")  # type: ignore[untyped-decorator]
def app_daemon(docker: DockerComposeManager) -> AppDaemon:
    """Provide AppDaemon API client for integration tests.

    This fixture creates an AppDaemon client configured with the dynamically
    assigned URL from the Docker container. The client is shared across all tests
    in the session (scope="session").

    Args:
        docker: The Docker container manager fixture.

    Returns:
        AppDaemon: Client for AppDaemon API interactions.
    """
    base_url = docker.get_appdaemon_url()
    return AppDaemon(base_url)


@pytest.fixture(scope="function")  # type: ignore[untyped-decorator]
def time_machine(docker: DockerComposeManager, home_assistant: HomeAssistant) -> Generator[TimeMachine, None, None]:
    """Provide time machine for integration tests.

    This fixture creates a time machine that allows tests to freeze time
    or advance time for deterministic testing of time-based automations.
    The time is automatically reset to real time after each test (scope="function").

    Tests must explicitly request this fixture to use time manipulation.

    Args:
        docker: The Docker container manager fixture.
        home_assistant: The Home Assistant client fixture.

    Yields:
        TimeMachine: Manager for time manipulation operations.
    """
    machine = TimeMachine(
        apply_faketime=lambda content: docker.write_container_file("homeassistant", "/shared_data/.faketime", content),
        on_time_set=lambda: home_assistant.regenerate_access_token(),
        get_entity_state=lambda entity_id: home_assistant.get_state(entity_id),
    )
    yield machine
    # Teardown: reset time to real time for next test
    machine.reset_time()
