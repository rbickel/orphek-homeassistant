"""Data update coordinator for Orphek lights."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OrphekLight, OrphekState, OrphekApiError

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)


class OrphekCoordinator(DataUpdateCoordinator[OrphekState]):
    """Coordinator to manage data updates from an Orphek light."""

    def __init__(self, hass: HomeAssistant, api: OrphekLight) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"Orphek {api.host}",
            update_interval=SCAN_INTERVAL,
        )
        self.api = api

    async def _async_update_data(self) -> OrphekState:
        """Fetch data from the Orphek device."""
        try:
            return await self.api.get_state()
        except OrphekApiError as err:
            raise UpdateFailed(f"Error communicating with Orphek device: {err}") from err
