"""API client for Orphek OR4-iCon LED Bar using Tuya local protocol."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import tinytuya

from .const import (
    BRIGHTNESS_MAX,
    BRIGHTNESS_MIN,
    DP_BRIGHTNESS,
    DP_SWITCH,
    TUYA_VERSION,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class OrphekState:
    """Current state of an Orphek light."""

    is_on: bool = False
    brightness: int = 0  # 0-1000


class OrphekApiError(Exception):
    """Error communicating with the Orphek device."""


class OrphekConnectionError(OrphekApiError):
    """Error connecting to the Orphek device."""


class OrphekDevice:
    """Controls an Orphek OR4-iCon LED Bar via Tuya local protocol."""

    def __init__(self, device_id: str, host: str, local_key: str) -> None:
        self._device_id = device_id
        self._host = host
        self._local_key = local_key
        self._device: tinytuya.Device | None = None

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def host(self) -> str:
        return self._host

    def _get_device(self) -> tinytuya.Device:
        if self._device is None:
            self._device = tinytuya.Device(
                self._device_id, self._host, self._local_key, version=TUYA_VERSION
            )
            self._device.set_socketPersistent(True)
            self._device.set_socketRetryLimit(3)
            self._device.set_socketTimeout(5)
        return self._device

    def close(self) -> None:
        """Close the connection."""
        if self._device is not None:
            try:
                self._device.set_socketPersistent(False)
                self._device.close()
            except Exception:
                pass
            self._device = None

    def test_connection(self) -> bool:
        """Test if the device is reachable and responds."""
        try:
            status = self._get_device().status()
            ok = status is not None and "dps" in (status or {})
            if not ok:
                _LOGGER.error("Device %s returned unexpected status: %s", self._host, status)
            return ok
        except Exception as err:
            _LOGGER.error("Connection test failed for %s: %s", self._host, err)
            return False

    def get_state(self) -> OrphekState:
        """Get the current light state."""
        try:
            result = self._get_device().status()
        except Exception as err:
            self._device = None
            raise OrphekConnectionError(
                f"Error communicating with {self._host}: {err}"
            ) from err

        if result is None or "dps" not in result:
            self._device = None
            raise OrphekConnectionError(f"No response from {self._host}")

        dps = result["dps"]
        return OrphekState(
            is_on=bool(dps.get(str(DP_SWITCH), False)),
            brightness=int(dps.get(str(DP_BRIGHTNESS), 0)),
        )

    def set_power(self, on: bool) -> None:
        """Turn the light on or off."""
        try:
            self._get_device().set_value(DP_SWITCH, on)
        except Exception as err:
            self._device = None
            raise OrphekConnectionError(
                f"Error sending command to {self._host}: {err}"
            ) from err

    def set_brightness(self, brightness: int) -> None:
        """Set brightness (10-1000). Also turns on the light."""
        brightness = max(BRIGHTNESS_MIN, min(BRIGHTNESS_MAX, brightness))
        try:
            dev = self._get_device()
            dev.set_multiple_values({DP_SWITCH: True, DP_BRIGHTNESS: brightness})
        except Exception as err:
            self._device = None
            raise OrphekConnectionError(
                f"Error sending command to {self._host}: {err}"
            ) from err
