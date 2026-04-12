"""API client for Orphek iCon aquarium lights."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


@dataclass
class OrphekDeviceInfo:
    """Represents basic Orphek device information."""

    model: str = "Unknown"
    firmware_version: str = "Unknown"
    mac_address: str = ""
    name: str = "Orphek Light"


@dataclass
class OrphekChannelState:
    """State of a single light channel."""

    channel_id: int = 0
    name: str = ""
    brightness: int = 0  # 0-1000 (0.0% - 100.0%)


@dataclass
class OrphekState:
    """Combined state of an Orphek light."""

    is_on: bool = False
    channels: list[OrphekChannelState] = field(default_factory=list)


class OrphekApiError(Exception):
    """Error communicating with the Orphek device."""


class OrphekConnectionError(OrphekApiError):
    """Error connecting to the Orphek device."""


class OrphekLight:
    """API client for a single Orphek iCon light."""

    def __init__(self, host: str, port: int = 8080) -> None:
        self._host = host
        self._port = port
        self._session: aiohttp.ClientSession | None = None
        self._device_info: OrphekDeviceInfo | None = None

    @property
    def host(self) -> str:
        return self._host

    @property
    def base_url(self) -> str:
        return f"http://{self._host}:{self._port}"

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def test_connection(self) -> bool:
        """Test if the device is reachable."""
        try:
            await self.get_device_info()
            return True
        except OrphekApiError:
            return False

    async def get_device_info(self) -> OrphekDeviceInfo:
        """Retrieve device information."""
        # TODO: Implement actual API call once protocol is known
        # Placeholder — replace with real HTTP/UDP call
        raise NotImplementedError("API protocol not yet implemented")

    async def get_state(self) -> OrphekState:
        """Get the current light state."""
        # TODO: Implement actual API call
        raise NotImplementedError("API protocol not yet implemented")

    async def set_channel_brightness(self, channel_id: int, brightness: int) -> None:
        """Set brightness for a specific channel (0-1000)."""
        # TODO: Implement actual API call
        raise NotImplementedError("API protocol not yet implemented")

    async def set_power(self, on: bool) -> None:
        """Turn the light on or off."""
        # TODO: Implement actual API call
        raise NotImplementedError("API protocol not yet implemented")

    async def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Make an API request to the device."""
        session = await self._ensure_session()
        url = f"{self.base_url}{path}"

        try:
            async with asyncio.timeout(10):
                async with session.request(method, url, **kwargs) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        except asyncio.TimeoutError as err:
            raise OrphekConnectionError(
                f"Timeout connecting to {self._host}"
            ) from err
        except aiohttp.ClientError as err:
            raise OrphekConnectionError(
                f"Error connecting to {self._host}: {err}"
            ) from err
