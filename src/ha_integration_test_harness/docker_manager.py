"""Docker Compose manager for integration test environment."""

import json
import logging
import os
import re
import shlex
import subprocess
import uuid
from pathlib import Path
from typing import Optional

from .exceptions import DockerError

logger = logging.getLogger(__name__)


class DockerContainer:
    """Represents a Docker container in the test environment."""

    def __init__(
        self, service: str, name: str, container_id: str, url: str, local_port: int | None, mapped_port: int | None, status: str, health: str | None, exit_code: int | None, std_out: str, std_err: str
    ) -> None:
        """Initialize the Docker container representation.

        Args:
            service: The docker-compose service name associated with this container.
            name: The name of the container.
            container_id: The Docker container ID.
            url: The HTTP base URL for accessing the service running in the container.
            local_port: The local (host) port used to access the container, or ``None`` if not applicable.
            mapped_port: The container's internal port that is mapped to ``local_port``, or ``None`` if not applicable.
            status: The current container status (for example, ``"running"`` or ``"exited"``).
            health: The health status reported by Docker, or ``None`` if no health check is defined.
            exit_code: The container's exit code if it has stopped, or ``None`` if it is still running or not yet exited.
            std_out: The captured standard output from the container.
            std_err: The captured standard error output from the container.
        """
        self.service = service
        self.name = name
        self.container_id = container_id
        self.url = url
        self.local_port = local_port
        self.mapped_port = mapped_port
        self.status = status
        self.health = health
        self.exit_code = exit_code
        self.std_out = std_out
        self.std_err = std_err

    def __str__(self) -> str:
        """String representation of the Docker container."""
        info = [
            f"Service: {self.service}",
            f"Container: {self.name} (ID: {self.container_id})",
            f"URL: {self.url}",
            f"Local Port: {self.local_port}",
            f"Mapped Port: {self.mapped_port}",
            f"Status: {self.status}",
            f"Health: {self.health}",
            f"Exit Code: {self.exit_code}",
            f"Std Out:\n{self.std_out}",
            f"Std Err:\n{self.std_err}",
        ]
        return "\n".join(info)


class DockerComposeManager:
    """Manages Docker Compose test environment lifecycle.

    This class handles all Docker operations for the integration test environment,
    including starting/stopping containers, port discovery, and file I/O operations
    with running containers.

    The environment includes:
    - Home Assistant on localhost:<dynamic-port>
    - AppDaemon on localhost:<dynamic-port>

    Docker assigns ephemeral ports automatically to enable parallel test runs.
    """

    def __init__(self) -> None:
        """Initialize the Docker Compose manager.

        Sets up paths and generates a unique run ID for container isolation.
        The environment is not started automatically; call start() to launch it.

        Raises:
            DockerError: If configuration.yaml is not found in the detected repository root.
        """
        self._run_id = uuid.uuid4().hex

        # Detect repository root using git, with fallback to current working directory
        self._repo_root = self._detect_repo_root()

        # Validate that configuration.yaml exists in the repository root
        config_file = self._repo_root / "configuration.yaml"
        if not config_file.exists():
            raise DockerError(
                f"configuration.yaml not found at {config_file}. "
                "Tests must be run from a Home Assistant configuration repository. "
                "See: https://github.com/MarkTarry/HomeAssistant-Test-Harness#usage"
            )

        # Set up containers directory path
        self._containers_dir = Path(__file__).parent / "containers"

        if not self._containers_dir.exists():
            raise DockerError(f"Containers directory not found: {self._containers_dir}")

        compose_file = self._containers_dir / "docker-compose.yaml"
        if not compose_file.exists():
            raise DockerError(f"docker-compose.yaml not found: {compose_file}")

        # Container lifecycle state
        self._containers: dict[str, DockerContainer] = {}

    def _detect_repo_root(self) -> Path:
        """Detect the repository root directory.

        Attempts to use git to find the repository root. If git is not available
        or not in a git repository, falls back to the current working directory.

        Returns:
            Path: The detected repository root directory.
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True,
            )
            repo_root = Path(result.stdout.strip())
            logger.debug(f"Detected git repository root: {repo_root}")
            return repo_root
        except (FileNotFoundError, subprocess.CalledProcessError):
            # Git not available or not in a git repo, fall back to current directory
            repo_root = Path(os.getcwd())
            logger.debug(f"Git not available, using current directory as root: {repo_root}")
            return repo_root

    def start(self) -> None:
        """Start the Docker Compose test environment.

        Executes 'docker compose up -d --wait' which:
        - Starts Home Assistant on localhost:8123
        - Waits for Home Assistant to be healthy (via healthcheck)
        - Generates authentication token and AppDaemon config
        - Starts AppDaemon on localhost:5050
        - Waits for AppDaemon to be healthy (via healthcheck)

        Raises:
            DockerError: If the docker compose command fails or if the services
                fail to start properly.
        """
        logger.debug("Starting docker-compose test environment...")
        try:
            # Set REPO_ROOT environment variable for docker-compose to mount the repository
            env = os.environ.copy()
            env["REPO_ROOT"] = str(self._repo_root)

            subprocess.run(
                ["docker", "compose", "-p", self._run_id, "up", "-d", "--wait"],
                cwd=self._containers_dir,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )

            # Start monitoring containers
            self._containers = self._refresh_container_details()
            logger.debug("Docker-compose environment started successfully:")
            for container in self._containers.values():
                logger.debug(f"  - {container.service}: {container.name} (ID: {container.container_id}) - Status: {container.status}, Health: {container.health}")

        except subprocess.CalledProcessError as e:
            # Pull as much info as we can on the containers - even though they likely failed to start
            self._containers = self._refresh_container_details()

            error_msg = f"Failed to start docker-compose environment (project: {self._run_id}): {e}"
            if e.stderr:
                error_msg += f"\nStderr:\n{e.stderr}"
            if e.stdout:
                error_msg += f"\nStdout:\n{e.stdout}"

            raise DockerError(error_msg)
        except FileNotFoundError:
            raise DockerError("'docker' command not found. Ensure Docker is installed and available in PATH.")

    def stop(self) -> None:
        """Stop the Docker Compose test environment.

        Executes 'docker compose down -v' which:
        - Stops all running containers
        - Removes containers and volumes
        - Cleans up resources

        This method is safe to call multiple times; subsequent calls are
        no-ops if the environment is already stopped.

        Note:
            Any exceptions during shutdown are logged but not raised, ensuring
            cleanup can complete even if the environment is in an unexpected state.
        """
        if not self._containers:
            logger.debug("Containers already stopped, skipping")
            return

        logger.debug("Stopping docker-compose test environment...")
        try:
            subprocess.run(
                ["docker", "compose", "-p", self._run_id, "down", "-v"],
                cwd=self._containers_dir,
                check=True,
                capture_output=True,
                text=True,
            )
            logger.debug("Docker-compose environment stopped successfully")
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to stop docker-compose environment (project: {self._run_id}): {e}"
            if e.stderr:
                error_msg += f"\nStderr:\n{e.stderr}"
            if e.stdout:
                error_msg += f"\nStdout:\n{e.stdout}"
            logger.warning(error_msg)
        except FileNotFoundError:
            logger.warning("'docker' command not found. Ensure Docker is installed and available in PATH.")
        finally:
            self._containers.clear()

    def get_container_diagnostics(self) -> str:
        """Dump logs from all containers for diagnostic purposes.

        Returns:
            A string containing container status and logs for debugging.
        """
        logs = ["========== CONTAINER DIAGNOSTICS =========="]
        try:
            self._containers = self._refresh_container_details()
            for container in self._containers.values():
                logs.append(f"{container}")
        except Exception as e:
            logs.append(f"** ERROR ** Failed to dump container diagnostics: {e}")

        logs.append("========== END DIAGNOSTICS ==========")
        return "\n".join(logs)

    def containers_healthy(self) -> bool:
        """Check if all containers are healthy.

        Returns:
            True if all containers are running and healthy, False otherwise.
        """
        if not self._containers:
            return False

        try:
            result = subprocess.run(
                ["docker", "compose", "-p", self._run_id, "ps", "--format", "json"],
                cwd=self._containers_dir,
                capture_output=True,
                text=True,
                check=True,
            )

            # Docker compose returns one JSON object per line, not a JSON array
            containers = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    containers.append(json.loads(line))

            for container in containers:
                state = container.get("State", "").lower()
                health = container.get("Health", "").lower()

                # Container is unhealthy if not running or health check failing
                if state != "running" or (health and health != "healthy"):
                    logger.warning(f"Container {container.get('Name')} is unhealthy: state={state}, health={health}")
                    return False

            return True

        except (subprocess.CalledProcessError, json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to check container health: {e}")
            return False

    def get_home_assistant_url(self) -> str:
        """Get the Home Assistant URL with dynamically assigned port.

        Returns:
            The full URL to Home Assistant (e.g., "http://localhost:49153").

        Raises:
            DockerError: If the port mapping cannot be determined.
        """
        container = self._get_container("homeassistant")
        if not container:
            raise DockerError("Home Assistant container not found")
        return container.url

    def get_appdaemon_url(self) -> str:
        """Get the AppDaemon URL with dynamically assigned port.

        Returns:
            The full URL to AppDaemon (e.g., "http://localhost:49154").

        Raises:
            DockerError: If the port mapping cannot be determined.
        """
        container = self._get_container("appdaemon")
        if not container:
            raise DockerError("AppDaemon container not found")
        return container.url

    def read_container_file(self, service: str, file_path: str) -> str:
        """Read a file from a running container.

        Args:
            service: The service name (e.g., "homeassistant", "appdaemon").
            file_path: The absolute path to the file inside the container.

        Returns:
            The contents of the file as a string.

        Raises:
            DockerError: If the file cannot be read from the container.
        """
        container = self._get_container(service)
        if not container:
            raise DockerError(f"No container found for service {service}")

        logger.debug(f"Reading file {file_path} from container {container.name}")
        try:
            result = subprocess.run(
                ["docker", "exec", container.name, "cat", file_path],
                capture_output=True,
                text=True,
                check=True,
            )
            content = result.stdout.strip()

            if not content:
                raise DockerError(f"File {file_path} in container {container.name} is empty")

            logger.debug(f"Successfully read file {file_path} from container {container.name}")
            return content

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to read file {file_path} from container {container.name}: {e}"
            if e.stderr:
                error_msg += f"\nStderr: {e.stderr}"
            raise DockerError(error_msg)
        except FileNotFoundError:
            raise DockerError("'docker' command not found. Ensure Docker is installed and available in PATH.")

    def write_container_file(self, service: str, file_path: str, content: str) -> None:
        """Write content to a file in a running container.

        Uses atomic write operation (write to temp file, then move) to prevent
        partial reads during file updates.

        This method is a no-op if containers are not running, making it safe to
        call during teardown or in error states.

        Args:
            service: The service name (e.g., "homeassistant", "appdaemon").
            file_path: The absolute path to the file inside the container.
            content: The content to write to the file.

        Raises:
            DockerError: If the file cannot be written to the container.
        """
        if not self._containers or service not in self._containers:
            logger.debug(f"Skipping write to {file_path}: {service} container not available")
            return

        container = self._get_container(service)
        if not container:
            raise DockerError(f"No container found for service {service}")

        logger.debug(f"Writing file {file_path} to container {container.name}")
        try:
            # Atomic write: write to temp file via stdin, then move
            # Using stdin piping to avoid shell injection vulnerabilities
            # Shell-escape paths to prevent injection via file path parameters
            temp_path = f"{file_path}.tmp"
            escaped_temp_path = shlex.quote(temp_path)
            escaped_file_path = shlex.quote(file_path)
            subprocess.run(
                ["docker", "exec", "-i", container.name, "sh", "-c", f"cat > {escaped_temp_path} && mv {escaped_temp_path} {escaped_file_path}"],
                input=content,
                check=True,
                capture_output=True,
                text=True,
            )
            logger.debug(f"Successfully wrote file {file_path} to container {container.name}")
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to write file {file_path} to container {container.name}: {e}"
            if e.stderr:
                error_msg += f"\nStderr: {e.stderr}"
            raise DockerError(error_msg)
        except FileNotFoundError:
            raise DockerError("'docker' command not found. Ensure Docker is installed and available in PATH.")

    def _refresh_container_details(self) -> dict[str, DockerContainer]:
        """Retrieve details of all running containers in the Docker Compose project.

        Returns:
            A list of DockerContainer objects representing each running container.
        """
        containers = {}
        try:
            result = subprocess.run(
                ["docker", "compose", "-p", self._run_id, "ps", "-a", "--format", "json"],
                cwd=self._containers_dir,
                capture_output=True,
                text=True,
                check=True,
            )

            # Docker compose returns one JSON object per line, not a JSON array
            container_details = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    container_details.append(json.loads(line))

            for details in container_details:
                container_id = details.get("ID")
                service = details.get("Service")

                local_port = None
                mapped_port = None
                ports = details.get("Ports", "")
                if ports:
                    # Match pattern: <host>:<host_port>-><container_port>/<protocol>
                    # E.g. '0.0.0.0:64865->5050/tcp, [::]:64865->5050/tcp'
                    match = re.search(r":(\d+)->(\d+)/", ports)
                    if match:
                        mapped_port = int(match.group(1))
                        local_port = int(match.group(2))

                # Get container logs (no tail limit for stopped/failed containers)
                logs_result = subprocess.run(
                    ["docker", "logs", "--tail=100", container_id],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )

                containers[service] = DockerContainer(
                    service=service,
                    name=details.get("Name"),
                    container_id=container_id,
                    url=f"http://localhost:{mapped_port}" if mapped_port else "",
                    local_port=local_port,
                    mapped_port=mapped_port,
                    status=details.get("Status"),
                    health=details.get("Health"),
                    exit_code=details.get("ExitCode"),
                    std_out=logs_result.stdout or "<<empty>>",
                    std_err=logs_result.stderr or "<<empty>>",
                )

            return containers

        except (subprocess.CalledProcessError, json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to get container details: {e}")
            return {}

    def _get_container(self, service: str) -> Optional[DockerContainer]:
        """Get the DockerContainer object for a given service.

        Args:
            service: The service name (e.g., "homeassistant", "appdaemon").

        Returns:
            DockerContainer: The corresponding DockerContainer object or None if not found.
        """
        return self._containers.get(service, None)
