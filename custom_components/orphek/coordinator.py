"""Data update coordinator for Orphek lights."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OrphekDevice, OrphekState, OrphekApiError
from .atop import OrphekAtopApi

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
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"Orphek {device.host}",
            update_interval=SCAN_INTERVAL,
        )
        self.device = device
        self._atop = atop
        self._poll_count = 0
        self._cloud_dps: dict = {}

    async def _async_update_data(self) -> OrphekState:
        """Fetch data from the Orphek device (local + periodic cloud)."""
        try:
            state = await self.hass.async_add_executor_job(self.device.get_state)
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
            except Exception:
                _LOGGER.debug("Cloud DPS fetch failed, using cached data")

        # Merge cloud data into local state
        if self._cloud_dps:
            OrphekDevice.update_state_from_cloud(state, self._cloud_dps)

        return state
