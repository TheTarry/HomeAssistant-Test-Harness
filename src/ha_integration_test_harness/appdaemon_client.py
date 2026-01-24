"""AppDaemon API client."""

import logging

logger = logging.getLogger(__name__)


class AppDaemon:
    """Client for interacting with AppDaemon API.

    This is currently a placeholder class for future AppDaemon API interactions.
    """

    def __init__(self, base_url: str) -> None:
        """Initialize the AppDaemon client.

        Args:
            base_url: The base URL of the AppDaemon instance.
        """
        self._base_url = base_url
        logger.debug(f"AppDaemon client initialized with URL: {base_url}")
