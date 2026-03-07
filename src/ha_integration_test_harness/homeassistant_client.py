"""Home Assistant API client."""

import json
import logging
import time
from typing import Any, Callable, Optional, Union, overload
from urllib.parse import urlparse, urlunparse

import requests
import websocket

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
        self._entity_original_labels: dict[str, list[str]] = {}

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
    def assert_entity_state(self, entity_id: str, expected_state: str, expected_attributes: Optional[dict[str, Any]] = None, timeout: int = 5) -> None: ...

    @overload
    def assert_entity_state(self, entity_id: str, expected_state: Callable[[str], bool], expected_attributes: Optional[dict[str, Any]] = None, timeout: int = 5) -> None: ...

    @overload
    def assert_entity_state(self, entity_id: str, expected_state: None = None, expected_attributes: Optional[dict[str, Any]] = None, timeout: int = 5) -> None: ...

    def assert_entity_state(
        self,
        entity_id: str,
        expected_state: Union[str, Callable[[str], bool], None] = None,
        expected_attributes: Optional[dict[str, Any]] = None,
        timeout: int = 5,
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
                    if expected_state is not None:
                        condition_desc = f"state {state_desc}"
                        if expected_attributes is not None:
                            condition_desc += " and expected attributes"
                    elif expected_attributes is not None:
                        attr_keys = ", ".join(sorted(expected_attributes.keys()))
                        condition_desc = f"expected attributes ({attr_keys})"
                    else:
                        condition_desc = "expected conditions"
                    logger.debug(f"Entity {entity_id} reached {condition_desc} after {time.time() - start_time:.1f}s")
                return

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                failure_parts = []
                if expected_state is not None and not state_matches:
                    failure_parts.append(f"state did not match {state_desc} (current: '{current_state}')")
                if expected_attributes is not None and not attributes_match:
                    attr_details = []
                    for k, v in mismatched_attributes.items():
                        expected_val = expected_attributes[k]
                        if callable(expected_val):
                            attr_details.append(f"'{k}': predicate not satisfied (actual: {v!r})")
                        else:
                            attr_details.append(f"'{k}': expected {expected_val!r}, got {v!r}")
                    failure_parts.append(f"attributes did not match ({'; '.join(attr_details)})")
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

    def _ws_send_receive(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Authenticate over the WebSocket API and send a single command, returning the response.

        Opens a new WebSocket connection for each call, performs the HA authentication
        handshake, sends ``payload``, and returns the result message.

        Args:
            payload: The command payload to send. Must include an ``"id"`` field.

        Returns:
            The response message dict returned by Home Assistant.

        Raises:
            HomeAssistantClientError: If the connection, authentication, or command fails.
        """
        ws_parsed = urlparse(self._base_url)
        ws_scheme = "wss" if ws_parsed.scheme == "https" else "ws"
        ws_url = urlunparse(ws_parsed._replace(scheme=ws_scheme, path="/api/websocket"))
        ws = websocket.WebSocket()
        try:
            ws.connect(ws_url, timeout=10)

            # Receive auth_required
            auth_required = json.loads(ws.recv())
            if auth_required.get("type") != "auth_required":
                raise HomeAssistantClientError(f"Unexpected WebSocket message during handshake: {auth_required}")

            # Send auth
            ws.send(json.dumps({"type": "auth", "access_token": self._access_token}))

            # Receive auth_ok
            auth_result = json.loads(ws.recv())
            if auth_result.get("type") != "auth_ok":
                raise HomeAssistantClientError(f"WebSocket authentication failed: {auth_result}")

            # Send command and receive response
            ws.send(json.dumps(payload))
            response: dict[str, Any] = json.loads(ws.recv())
            return response
        except websocket.WebSocketException as e:
            raise HomeAssistantClientError(f"WebSocket error communicating with Home Assistant at {ws_url}: {e}")
        finally:
            ws.close()

    def _get_entity_labels(self, entity_id: str) -> list[str]:
        """Fetch the current labels assigned to an entity via the entity registry.

        Args:
            entity_id: The entity ID to query (e.g., 'light.living_room').

        Returns:
            A list of label IDs currently assigned to the entity.

        Raises:
            HomeAssistantClientError: If the entity registry entry cannot be retrieved.
        """
        response = self._ws_send_receive({"id": 1, "type": "config/entity_registry/get", "entity_id": entity_id})
        # id=1 is safe: _ws_send_receive opens a fresh connection per call, so there is no ID collision.
        if not response.get("success"):
            raise HomeAssistantClientError(f"Failed to get entity registry entry for {entity_id}: {response}")
        labels: list[str] = response.get("result", {}).get("labels", [])
        return labels

    def _set_entity_labels(self, entity_id: str, labels: list[str]) -> None:
        """Overwrite the labels on an entity via the entity registry.

        Args:
            entity_id: The entity ID to update (e.g., 'light.living_room').
            labels: The complete list of label IDs to assign to the entity.
                Any pre-existing labels not in this list are removed.

        Raises:
            HomeAssistantClientError: If the entity registry update fails.
        """
        response = self._ws_send_receive({"id": 1, "type": "config/entity_registry/update", "entity_id": entity_id, "labels": labels})
        # id=1 is safe: _ws_send_receive opens a fresh connection per call, so there is no ID collision.
        if not response.get("success"):
            raise HomeAssistantClientError(f"Failed to update labels for {entity_id}: {response}")

    def given_entity_has_labels(self, entity_id: str, labels: list[str]) -> None:
        """Assign labels to an entity for testing purposes, with automatic rollback.

        Saves the entity's current labels before modification so they can be restored
        at the end of the test. If called multiple times for the same ``entity_id``,
        only the labels captured on the first call are saved for restoration (preserving
        the state before any test modification).

        This method always **overwrites** any pre-existing labels on the entity with
        the provided list.

        Args:
            entity_id: The entity ID to label (e.g., 'light.living_room').
            labels: List of label IDs to assign to the entity. Overwrites any
                pre-existing labels.

        Raises:
            HomeAssistantClientError: If the entity registry cannot be read or updated.
        """
        if entity_id not in self._entity_original_labels:
            self._entity_original_labels[entity_id] = self._get_entity_labels(entity_id)
        self._set_entity_labels(entity_id, labels)

    def restore_entity_labels(self) -> None:
        """Restore all entity labels modified by given_entity_has_labels() to their original values.

        This method is called automatically after each test function completes.
        It restores labels for all entities modified via given_entity_has_labels().
        Successfully restored entities are cleared from tracking immediately, while
        failed restorations remain tracked.

        Raises:
            HomeAssistantClientError: If any label restoration fails.
        """
        errors = []
        successfully_restored = []

        for entity_id, original_labels in list(self._entity_original_labels.items()):
            try:
                self._set_entity_labels(entity_id, original_labels)
                successfully_restored.append(entity_id)
            except HomeAssistantClientError as e:
                errors.append(str(e))

        for entity_id in successfully_restored:
            del self._entity_original_labels[entity_id]

        if errors:
            raise HomeAssistantClientError(f"Failed to restore labels for {len(errors)} entities:\n" + "\n".join(errors))

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
