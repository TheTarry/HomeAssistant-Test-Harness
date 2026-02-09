"""Home Assistant API client."""

import logging
import time
from typing import Any, Callable, Optional, Union, overload

import requests

from .exceptions import HomeAssistantClientError

logger = logging.getLogger(__name__)


class HomeAssistant:
    """Client for interacting with Home Assistant API.

    Provides methods for managing entity states using a long-lived access token
    for authentication.
    """

    def __init__(self, base_url: str, access_token: str) -> None:
        """Initialize the Home Assistant client.

        Args:
            base_url: The base URL of the Home Assistant instance.
            access_token: The long-lived access token for authentication.
        """
        self._base_url = base_url
        self._access_token = access_token
        self._created_entities: set[str] = set()

    def set_state(self, entity_id: str, state: str, attributes: Optional[dict[str, str]] = None) -> None:
        """Set the state and/or attributes of a Home Assistant entity.

        Args:
            entity_id: The entity ID to set the state for (e.g., 'light.living_room').
            state: The state value to set for the entity.
            attributes: Optional dictionary of attributes to set for the entity.

        Raises:
            HomeAssistantClientError: If the request fails due to network issues or API errors.
        """
        url = f"{self._base_url}/api/states/{entity_id}"
        try:
            headers = {"Authorization": f"Bearer {self._access_token}"}
            body: dict[str, Any] = {"state": state}
            if attributes is not None:
                body["attributes"] = attributes
            response = requests.post(url, json=body, headers=headers)
            response.raise_for_status()
        except requests.RequestException as e:
            raise HomeAssistantClientError(f"Failed to set state for entity {entity_id} at {url}: {e}")

    def get_state(self, entity_id: str) -> Optional[dict[str, Any]]:
        """Get the state of an entity from Home Assistant.

        Args:
            entity_id: The entity ID to query (e.g., "light.foobar").

        Returns:
            The state dictionary of the entity, or None if not found (404 response).

        Raises:
            HomeAssistantClientError: If the request fails due to network issues or API errors.
        """
        url = f"{self._base_url}/api/states/{entity_id}"
        try:
            headers = {"Authorization": f"Bearer {self._access_token}"}
            response = requests.get(url, headers=headers)

            # 404 is acceptable - entity doesn't exist
            if response.status_code == 404:
                return None

            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
        except requests.RequestException as e:
            raise HomeAssistantClientError(f"Failed to get state for entity {entity_id} from {url}: {e}")

    @overload
    def assert_entity_state(self, entity_id: str, expected_state: str, timeout: int = 5) -> None: ...

    @overload
    def assert_entity_state(self, entity_id: str, expected_state: Callable[[str], bool], timeout: int = 5) -> None: ...

    def assert_entity_state(self, entity_id: str, expected_state: Union[str, Callable[[str], bool]], timeout: int = 5) -> None:
        """Assert that an entity is in the expected state.

        Polls the entity state every second until it matches the expected state
        or the timeout is reached.

        Args:
            entity_id: The entity ID to check (e.g., "light.foobar").
            expected_state: Either a string for exact match, or a callable that
                takes the current state string and returns True when satisfied.
            timeout: Maximum time to wait in seconds (default: 5).

        Raises:
            AssertionError: If the entity's state does not match the expected state
                within the timeout period, or if the entity is not found.
        """
        start_time = time.time()
        last_state = None
        expectation_desc = "predicate function" if callable(expected_state) else f"'{expected_state}'"

        while True:
            state_response = self.get_state(entity_id)

            if state_response is None:
                raise AssertionError(f"Entity {entity_id} not found")

            # Extract the actual state value from the response
            if isinstance(state_response, dict):
                current_state = state_response.get("state")
                if not isinstance(current_state, str):
                    raise AssertionError(f"Entity {entity_id} has unexpected state value: {current_state}")
            else:
                raise AssertionError(f"Unexpected state response format for entity {entity_id}: {state_response}")

            # Check if state matches expectation
            if callable(expected_state):
                # Call the predicate function
                matches = expected_state(current_state)
            else:
                # Exact match
                matches = current_state == expected_state

            if matches:
                if last_state is not None and (callable(expected_state) or last_state != expected_state):
                    logger.debug(f"Entity {entity_id} reached expected state ({expectation_desc}) after {time.time() - start_time:.1f}s")
                return

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                raise AssertionError(f"Entity {entity_id} did not reach expected state ({expectation_desc}) within {timeout}s. " f"Current state: '{current_state}'")

            last_state = current_state
            time.sleep(1)

    def remove_entity(self, entity_id: str) -> None:
        """Remove an entity from Home Assistant.

        Args:
            entity_id: The entity ID to remove (e.g., 'light.living_room').

        Raises:
            HomeAssistantClientError: If the request fails due to network issues or API errors.
        """
        url = f"{self._base_url}/api/states/{entity_id}"
        try:
            headers = {"Authorization": f"Bearer {self._access_token}"}
            response = requests.delete(url, headers=headers)
            # 404 is acceptable - entity doesn't exist, which is the desired outcome
            if response.status_code != 404:
                response.raise_for_status()
        except requests.RequestException as e:
            raise HomeAssistantClientError(f"Failed to remove entity {entity_id} from {url}: {e}")

    def given_an_entity(self, entity_id: str, state: str, attributes: Optional[dict[str, str]] = None) -> None:
        """Create an entity for testing purposes with automatic cleanup.

        This method creates a test entity using set_state() and automatically tracks it
        for cleanup at the end of the test function. If called multiple times with the
        same entity_id, it is tracked only once.

        Args:
            entity_id: The entity ID to create (e.g., 'light.living_room').
            state: The state value to set for the entity.
            attributes: Optional dictionary of attributes to set for the entity.

        Raises:
            HomeAssistantClientError: If the request fails due to network issues or API errors.
        """
        self.set_state(entity_id, state, attributes)
        self._created_entities.add(entity_id)

    def clean_up_test_entities(self) -> None:
        """Remove all entities created via given_an_entity().

        This method is called automatically after each test function completes.
        It removes all tracked test entities and clears the tracking set.

        Raises:
            HomeAssistantClientError: If any entity removal fails.
        """
        errors = []
        for entity_id in self._created_entities:
            try:
                self.remove_entity(entity_id)
            except HomeAssistantClientError as e:
                errors.append(str(e))

        # Clear the set regardless of errors
        self._created_entities.clear()

        # Raise if there were any errors
        if errors:
            raise HomeAssistantClientError(f"Failed to clean up {len(errors)} test entities:\n" + "\n".join(errors))
