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
    assigned URL and long-lived access token from the Docker container. The client
    is shared across all tests in the session (scope="session").

    Args:
        docker: The Docker container manager fixture.

    Returns:
        HomeAssistant: Client for Home Assistant API interactions.
    """
    base_url = docker.get_home_assistant_url()
    access_token = docker.read_container_file("homeassistant", "/shared_data/.ha_token")
    return HomeAssistant(base_url, access_token)


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


@pytest.fixture(scope="session")  # type: ignore[untyped-decorator]
def time_machine(docker: DockerComposeManager, home_assistant: HomeAssistant) -> TimeMachine:
    """Provide time machine for integration tests.

    This fixture creates a time machine that allows tests to advance time forward
    for deterministic testing of time-based automations.

    **IMPORTANT**: Time can only move forward, never backward. The fixture is
    session-scoped, meaning time persists across all tests in the session and
    cannot be reset. Tests that depend on specific time conditions must explicitly
    advance time to the desired state at the start of the test.

    Tests must explicitly request this fixture to use time manipulation.

    Args:
        docker: The Docker container manager fixture.
        home_assistant: The Home Assistant client fixture.

    Returns:
        TimeMachine: Manager for time manipulation operations.
    """
    machine = TimeMachine(
        apply_faketime=lambda content: docker.write_container_file("homeassistant", "/shared_data/.faketime", content),
        on_time_set=None,  # No token regeneration needed with long-lived token
        get_entity_state=lambda entity_id: home_assistant.get_state(entity_id),
    )
    return machine
    # No teardown: time cannot be reset and persists across tests in the session


@pytest.fixture(autouse=True)  # type: ignore[untyped-decorator]
def _cleanup_test_entities(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Auto-cleanup fixture that removes test entities after each test.

    This fixture automatically runs after every test function (autouse=True)
    and calls clean_up_test_entities() to remove any entities created via
    given_an_entity(). Tests don't need to explicitly request this fixture.

    Only activates cleanup if the test actually used the home_assistant fixture,
    avoiding unnecessary Docker container startup for tests that don't need it.

    Args:
        request: The pytest request object for conditional fixture access.

    Yields:
        None: This fixture doesn't provide any value to tests.
    """
    # Setup: nothing to do before the test
    yield

    # Teardown: only clean up if the test used home_assistant fixture
    if "home_assistant" in request.fixturenames:
        home_assistant: HomeAssistant = request.getfixturevalue("home_assistant")
        home_assistant.clean_up_test_entities()
