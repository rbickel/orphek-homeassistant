"""The Orphek integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import OrphekDevice
from .atop import OrphekAtopApi
from .const import (
    CONF_ATOP_COUNTRY_CODE,
    CONF_ATOP_EMAIL,
    CONF_ATOP_PASSWORD,
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_LOCAL_KEY,
    DOMAIN,
)
from .coordinator import OrphekCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.LIGHT, Platform.SENSOR]

type OrphekConfigEntry = ConfigEntry[OrphekCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: OrphekConfigEntry) -> bool:
    """Set up Orphek from a config entry."""
    device = OrphekDevice(
        device_id=entry.data[CONF_DEVICE_ID],
        host=entry.data[CONF_HOST],
        local_key=entry.data[CONF_LOCAL_KEY],
    )

    # Set up ATOP cloud client for schedule/expansion data if credentials available
    atop: OrphekAtopApi | None = None
    atop_email = entry.data.get(CONF_ATOP_EMAIL)
    atop_password = entry.data.get(CONF_ATOP_PASSWORD)
    if atop_email and atop_password:
        country_code = entry.data.get(CONF_ATOP_COUNTRY_CODE, "1")
        atop = OrphekAtopApi()
        logged_in = await hass.async_add_executor_job(
            atop.login, atop_email, atop_password, country_code
        )
        if not logged_in:
            _LOGGER.warning("ATOP cloud login failed; schedule data unavailable")
            atop = None

    coordinator = OrphekCoordinator(hass, device, atop=atop)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: OrphekConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: OrphekCoordinator = entry.runtime_data
        coordinator.device.close()
    return unload_ok
