"""Home Assistant API client and authentication manager."""

import logging
import time
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, Union, overload

import requests

from .exceptions import HomeAssistantClientError

logger = logging.getLogger(__name__)
T = TypeVar("T")


class AuthManager:
    """Manages authentication tokens for Home Assistant API access.

    This class handles token lifecycle including initial token generation
    via refresh token exchange and token regeneration when tokens expire.
    """

    def __init__(self, base_url: str, refresh_token: str) -> None:
        """Initialize the authentication manager.

        Args:
            base_url: The base URL of the Home Assistant instance.
            refresh_token: The long-lived refresh token for obtaining access tokens.
        """
        self._base_url = base_url
        self._refresh_token = refresh_token
        self._access_token: Optional[str] = None

    def get_access_token(self) -> str:
        """Get the current access token, generating one if needed.

        Returns:
            The current valid access token.

        Raises:
            HomeAssistantClientError: If token generation fails.
        """
        if self._access_token is None:
            logger.debug("No access token cached, generating initial token")
            return self.regenerate_access_token()
        return self._access_token

    def regenerate_access_token(self) -> str:
        """Regenerate access token using the refresh token.

        This method exchanges the refresh token for a new access token by calling
        Home Assistant's /auth/token endpoint with grant_type=refresh_token.

        Returns:
            The new access token string.

        Raises:
            HomeAssistantClientError: If token regeneration fails.
        """
        logger.debug("Regenerating access token using refresh token")

        url = f"{self._base_url}/auth/token"
        try:
            response = requests.post(
                url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                    "client_id": "http://localhost",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()

            token_data = response.json()
            new_access_token: str = token_data.get("access_token")

            if not new_access_token:
                raise HomeAssistantClientError(f"No access_token in response from {url}: {token_data}")

            # Update cached token
            self._access_token = new_access_token
            logger.debug("Successfully regenerated access token")

            return new_access_token

        except requests.RequestException as e:
            raise HomeAssistantClientError(f"Failed to regenerate access token from {url}: {e}")


def _retry_on_auth_failure(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to automatically retry API calls with token regeneration on 401 errors.

    If a request receives a 401 Unauthorized response, this decorator will:
    1. Log the authentication failure with details
    2. Regenerate the access token using the refresh token
    3. Retry the request once with the new token

    If the retry also fails, the original error details are included in the exception.
    """

    @wraps(func)
    def wrapper(self: "HomeAssistant", *args: Any, **kwargs: Any) -> T:
        try:
            return func(self, *args, **kwargs)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                original_error = str(e)

                try:
                    self._auth_manager.regenerate_access_token()
                    return func(self, *args, **kwargs)
                except (requests.RequestException, HomeAssistantClientError) as retry_error:
                    raise HomeAssistantClientError(f"Failed to complete request after token regeneration. " f"Original 401 error: {original_error}. " f"Retry error: {retry_error}")
            raise

    return wrapper


class HomeAssistant:
    """Client for interacting with Home Assistant API.

    Provides methods for managing entity states and includes automatic
    authentication token management with retry logic.
    """

    def __init__(self, base_url: str, refresh_token: str) -> None:
        """Initialize the Home Assistant client.

        Args:
            base_url: The base URL of the Home Assistant instance.
            refresh_token: The long-lived refresh token for authentication.
        """
        self._base_url = base_url
        self._auth_manager = AuthManager(base_url, refresh_token)

    def regenerate_access_token(self) -> None:
        """Regenerate the access token.

        This is useful when time has been manipulated (e.g., in tests) and the
        existing access token has expired. Calling this method will obtain a
        fresh access token from Home Assistant.

        Raises:
            HomeAssistantClientError: If token regeneration fails.
        """
        self._auth_manager.regenerate_access_token()

    @_retry_on_auth_failure
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
            token = self._auth_manager.get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            body: dict[str, Any] = {"state": state}
            if attributes is not None:
                body["attributes"] = attributes
            response = requests.post(url, json=body, headers=headers)
            response.raise_for_status()
        except requests.HTTPError:
            # Re-raise HTTPError to allow decorator to handle 401
            raise
        except requests.RequestException as e:
            raise HomeAssistantClientError(f"Failed to set state for entity {entity_id} at {url}: {e}")

    @_retry_on_auth_failure
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
            token = self._auth_manager.get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(url, headers=headers)

            # 404 is acceptable - entity doesn't exist
            if response.status_code == 404:
                return None

            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
        except requests.HTTPError:
            # Re-raise HTTPError to allow decorator to handle 401
            raise
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

    @_retry_on_auth_failure
    def remove_entity(self, entity_id: str) -> None:
        """Remove an entity from Home Assistant.

        Args:
            entity_id: The entity ID to remove (e.g., 'light.living_room').

        Raises:
            HomeAssistantClientError: If the request fails due to network issues or API errors.
        """
        url = f"{self._base_url}/api/states/{entity_id}"
        try:
            token = self._auth_manager.get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.delete(url, headers=headers)
            # 404 is acceptable - entity doesn't exist, which is the desired outcome
            if response.status_code != 404:
                response.raise_for_status()
        except requests.HTTPError:
            # Re-raise HTTPError to allow decorator to handle 401
            raise
        except requests.RequestException as e:
            raise HomeAssistantClientError(f"Failed to remove entity {entity_id} from {url}: {e}")
