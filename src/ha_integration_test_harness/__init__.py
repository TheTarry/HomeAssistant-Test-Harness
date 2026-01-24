"""Home Assistant Integration Test Harness.

A pytest plugin providing fixtures and utilities for integration testing
Home Assistant and AppDaemon configurations in Docker containers.

Public Classes:
    DockerComposeManager: Manages Docker container lifecycle and file I/O.
    HomeAssistant: Client for Home Assistant API interactions.
    AppDaemon: Client for AppDaemon API interactions.
    TimeMachine: Manages time manipulation for deterministic testing.
    ContainerInfo: Information about a running Docker container.

Exceptions:
    IntegrationTestError: Base exception for all harness errors.
    DockerError: Docker operation failures.
    HomeAssistantError: Home Assistant operations and API call failures.
    AppDaemonError: AppDaemon operations and API call failures.
    TimeChangeError: Time manipulation failures.

Pytest Fixtures (auto-registered):
    docker: DockerComposeManager for container lifecycle (session scope)
    home_assistant: HomeAssistant API client (session scope)
    app_daemon: AppDaemon API client (session scope)
    time_machine: TimeMachine for time manipulation (function scope)
"""

from .appdaemon_client import AppDaemon
from .docker_manager import DockerComposeManager, DockerContainer
from .exceptions import (
    AppDaemonClientError,
    DockerError,
    HomeAssistantClientError,
    IntegrationTestError,
    TimeMachineError,
)
from .homeassistant_client import HomeAssistant
from .time_machine import TimeMachine

__version__ = "0.1.0"

__all__ = [
    "AppDaemon",
    "AppDaemonClientError",
    "DockerComposeManager",
    "DockerContainer",
    "DockerError",
    "HomeAssistant",
    "HomeAssistantClientError",
    "IntegrationTestError",
    "TimeMachine",
    "TimeMachineError",
]
