"""Data update coordinator for Orphek lights."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OrphekDevice, OrphekState, OrphekApiError
from .atop import OrphekAtopApi
from .const import CONF_ATOP_SESSION_ID

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)
CLOUD_FETCH_INTERVAL = 10  # Fetch cloud DPS every N local polls (~5 minutes)


class OrphekCoordinator(DataUpdateCoordinator[OrphekState]):
    """Coordinator to manage data updates from an Orphek light."""

    def __init__(
        self,
        hass: HomeAssistant,
        device: OrphekDevice,
        atop: OrphekAtopApi | None = None,
        schema: dict | None = None,
        config_entry: ConfigEntry | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"Orphek {device.host}",
            update_interval=SCAN_INTERVAL,
        )
        self.device = device
        self._atop = atop
        self.schema = schema
        self._config_entry = config_entry
        self._last_sid: str | None = atop.session_id if atop else None
        self._poll_count = 0
        self._cloud_dps: dict = {}
        self._device_io_lock = asyncio.Lock()

    async def async_device_io(self, func, *args):
        """Serialize access to the shared local device transport."""
        async with self._device_io_lock:
            return await self.hass.async_add_executor_job(func, *args)

    async def _async_update_data(self) -> OrphekState:
        """Fetch data from the Orphek device (local + periodic cloud)."""
        try:
            state = await self.async_device_io(self.device.get_state)
        except OrphekApiError as err:
            raise UpdateFailed(
                f"Error communicating with Orphek device: {err}"
            ) from err

        # Periodically fetch cloud DPS for schedule/expansion data
        self._poll_count += 1
        if self._atop and (
            self._poll_count >= CLOUD_FETCH_INTERVAL or not self._cloud_dps
        ):
            self._poll_count = 0
            try:
                cloud_dps = await self.hass.async_add_executor_job(
                    self._atop.get_device_dps, self.device.device_id
                )
                if cloud_dps:
                    self._cloud_dps = cloud_dps

                # If atop auto-re-logged in, persist the new session ID
                new_sid = self._atop.session_id
                if (
                    new_sid
                    and new_sid != self._last_sid
                    and self._config_entry is not None
                ):
                    self._last_sid = new_sid
                    self.hass.config_entries.async_update_entry(
                        self._config_entry,
                        data={
                            **self._config_entry.data,
                            CONF_ATOP_SESSION_ID: new_sid,
                        },
                    )
                    _LOGGER.info("Persisted new ATOP session ID after re-login")
            except Exception:
                _LOGGER.debug("Cloud DPS fetch failed, using cached data")

        # Merge cloud data into local state
        if self._cloud_dps:
            OrphekDevice.update_state_from_cloud(state, self._cloud_dps)

        return state
