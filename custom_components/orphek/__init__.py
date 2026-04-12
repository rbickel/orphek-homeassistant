"""The Orphek integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import OrphekDevice
from .const import CONF_DEVICE_ID, CONF_HOST, CONF_LOCAL_KEY, DOMAIN
from .coordinator import OrphekCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.LIGHT]

type OrphekConfigEntry = ConfigEntry[OrphekCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: OrphekConfigEntry) -> bool:
    """Set up Orphek from a config entry."""
    device = OrphekDevice(
        device_id=entry.data[CONF_DEVICE_ID],
        host=entry.data[CONF_HOST],
        local_key=entry.data[CONF_LOCAL_KEY],
    )
    coordinator = OrphekCoordinator(hass, device)
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
