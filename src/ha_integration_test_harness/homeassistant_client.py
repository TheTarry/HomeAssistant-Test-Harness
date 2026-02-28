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

    def set_state(self, entity_id: str, state: str, attributes: Optional[dict[str, Any]] = None) -> None:
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
    def assert_entity_state(self, entity_id: str, expected_state: str, timeout: int = 5, expected_attributes: None = None) -> None: ...

    @overload
    def assert_entity_state(self, entity_id: str, expected_state: Callable[[str], bool], timeout: int = 5, expected_attributes: None = None) -> None: ...

    @overload
    def assert_entity_state(self, entity_id: str, expected_state: None = None, timeout: int = 5, expected_attributes: Optional[dict[str, Any]] = None) -> None: ...

    def assert_entity_state(
        self,
        entity_id: str,
        expected_state: Union[str, Callable[[str], bool], None] = None,
        timeout: int = 5,
        expected_attributes: Optional[dict[str, Any]] = None,
    ) -> None:
        """Assert that an entity is in the expected state and/or has the expected attributes.

        Polls the entity state every second until all conditions are met or the timeout is reached.
        At least one of ``expected_state`` or ``expected_attributes`` must be provided.

        Args:
            entity_id: The entity ID to check (e.g., "light.foobar").
            expected_state: Either a string for exact match, or a callable that takes the current
                state string and returns True when satisfied. Pass None (or omit) to skip state checking.
            timeout: Maximum time to wait in seconds (default: 5).
            expected_attributes: Optional dictionary of attribute name to expected value. Each value
                may be an exact value (compared with ``==``) or a callable predicate that takes the
                actual attribute value and returns True when satisfied. Only the attributes listed here
                are checked; any additional attributes on the entity are ignored.

        Raises:
            ValueError: If neither ``expected_state`` nor ``expected_attributes`` is provided.
            AssertionError: If the entity is not found, or if state/attributes do not match within
                the timeout period.
        """
        if expected_state is None and expected_attributes is None:
            raise ValueError("At least one of expected_state or expected_attributes must be provided")

        start_time = time.time()
        last_state = None
        state_desc = "predicate function" if callable(expected_state) else f"'{expected_state}'"

        while True:
            state_response = self.get_state(entity_id)

            if state_response is None:
                raise AssertionError(f"Entity {entity_id} not found")

            if not isinstance(state_response, dict):
                raise AssertionError(f"Unexpected state response format for entity {entity_id}: {state_response}")

            # Extract the actual state value from the response
            current_state = state_response.get("state")
            if not isinstance(current_state, str):
                raise AssertionError(f"Entity {entity_id} has unexpected state value: {current_state}")

            # Check if state matches expectation
            state_matches = True
            if expected_state is not None:
                if callable(expected_state):
                    state_matches = expected_state(current_state)
                else:
                    state_matches = current_state == expected_state

            # Check if attributes match expectation
            attributes_match = True
            mismatched_attributes: dict[str, Any] = {}
            if expected_attributes is not None:
                current_attributes = state_response.get("attributes", {})
                for attr_name, attr_expected in expected_attributes.items():
                    attr_actual = current_attributes.get(attr_name)
                    if callable(attr_expected):
                        if not attr_expected(attr_actual):
                            attributes_match = False
                            mismatched_attributes[attr_name] = attr_actual
                    else:
                        if attr_actual != attr_expected:
                            attributes_match = False
                            mismatched_attributes[attr_name] = attr_actual

            if state_matches and attributes_match:
                if last_state is not None:
                    logger.debug(f"Entity {entity_id} reached expected conditions ({state_desc}) after {time.time() - start_time:.1f}s")
                return

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                failure_parts = []
                if expected_state is not None and not state_matches:
                    failure_parts.append(f"state did not match {state_desc} (current: '{current_state}')")
                if expected_attributes is not None and not attributes_match:
                    attr_details = ", ".join(f"'{k}': {v!r}" for k, v in mismatched_attributes.items())
                    failure_parts.append(f"attributes did not match (mismatched: {{{attr_details}}})")
                raise AssertionError(f"Entity {entity_id} did not reach expected conditions within {timeout}s. " + "; ".join(failure_parts))

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

    def call_action(self, domain: str, action: str, data: Optional[dict[str, Any]] = None) -> None:
        """Call a Home Assistant action (service).

        Args:
            domain: The domain of the action (e.g., 'light', 'switch', 'input_boolean').
            action: The action to call (e.g., 'turn_on', 'turn_off', 'toggle').
            data: Optional dictionary of action data (e.g., {'entity_id': 'light.living_room'}).

        Raises:
            HomeAssistantClientError: If the request fails due to network issues or API errors.
        """
        url = f"{self._base_url}/api/services/{domain}/{action}"
        try:
            headers = {"Authorization": f"Bearer {self._access_token}"}
            response = requests.post(url, json=data or {}, headers=headers)
            response.raise_for_status()
        except requests.RequestException as e:
            raise HomeAssistantClientError(f"Failed to call action {domain}.{action} at {url}: {e}")

    def given_an_entity(self, entity_id: str, state: str, attributes: Optional[dict[str, Any]] = None) -> None:
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
        It removes all tracked test entities. Successfully removed entities are
        cleared from tracking immediately, while failed removals remain tracked
        for potential retry.

        Raises:
            HomeAssistantClientError: If any entity removal fails.
        """
        errors = []
        successfully_removed = []

        for entity_id in list(self._created_entities):
            try:
                self.remove_entity(entity_id)
                successfully_removed.append(entity_id)
            except HomeAssistantClientError as e:
                errors.append(str(e))

        # Remove only successfully deleted entities from tracking
        for entity_id in successfully_removed:
            self._created_entities.discard(entity_id)

        # Raise if there were any errors
        if errors:
            raise HomeAssistantClientError(f"Failed to clean up {len(errors)} test entities:\n" + "\n".join(errors))
