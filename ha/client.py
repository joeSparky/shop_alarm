import os
import time
from typing import Any

import requests


DEFAULT_HA_URL = "http://192.168.12.201:8123"


class HomeAssistantClient:
    """Small REST client used by the shop alarm tests and tools."""

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("HA_URL", DEFAULT_HA_URL)).rstrip("/")
        self.token = token or os.getenv("HA_TOKEN")
        self.timeout = timeout

        if not self.token:
            raise ValueError("Home Assistant token is required. Set HA_TOKEN or pass token=.")

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            }
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self.session.request(
            method,
            f"{self.base_url}{path}",
            timeout=self.timeout,
            **kwargs,
        )
        response.raise_for_status()

        if not response.content:
            return None

        return response.json()

    def api_status(self) -> str:
        """Return Home Assistant's API status message."""
        data = self._request("GET", "/api/")
        return data["message"]

    def get_state(self, entity_id: str) -> dict[str, Any]:
        """Return the complete state object for one Home Assistant entity."""
        return self._request("GET", f"/api/states/{entity_id}")

    def state(self, entity_id: str) -> str:
        """Return only an entity's state string."""
        return self.get_state(entity_id)["state"]

    def wait_for_state(
        self,
        entity_id: str,
        expected_state: str,
        timeout: float = 30.0,
        poll_interval: float = 0.25,
    ) -> dict[str, Any]:
        """Wait until an entity reaches expected_state, then return its state object.

        Raises TimeoutError if the requested state is not observed before timeout.
        """
        deadline = time.monotonic() + timeout
        last_state: str | None = None

        while True:
            state_object = self.get_state(entity_id)
            last_state = state_object["state"]

            if last_state == expected_state:
                return state_object

            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Timed out after {timeout:g}s waiting for {entity_id} "
                    f"to become {expected_state!r}; last state was {last_state!r}."
                )

            time.sleep(poll_interval)

    def call_service(
        self,
        domain: str,
        service: str,
        data: dict[str, Any] | None = None,
    ) -> Any:
        """Call a Home Assistant service and return its REST response."""
        return self._request(
            "POST",
            f"/api/services/{domain}/{service}",
            json=data or {},
        )

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "HomeAssistantClient":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()
