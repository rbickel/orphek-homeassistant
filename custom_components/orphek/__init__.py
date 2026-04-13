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
    CONF_ATOP_SESSION_ID,
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_LOCAL_KEY,
    DOMAIN,
)
from .coordinator import OrphekCoordinator
from .device_schema import load_schema, save_schema

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

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
    atop_session_id = entry.data.get(CONF_ATOP_SESSION_ID)
    atop_password = entry.data.get(CONF_ATOP_PASSWORD)

    if atop_email and (atop_session_id or atop_password):
        country_code = entry.data.get(CONF_ATOP_COUNTRY_CODE, "1")
        atop = OrphekAtopApi()

        # Prefer session ID if available (new auth method)
        if atop_session_id:
            atop.set_session_id(atop_session_id)
            _LOGGER.debug("Using stored session ID for ATOP authentication")
        elif atop_password:
            # Fall back to password login (backward compatibility)
            _LOGGER.warning(
                "Using password authentication; consider re-configuring to use session tokens"
            )
            logged_in = await hass.async_add_executor_job(
                atop.login, atop_email, atop_password, country_code
            )
            if not logged_in:
                _LOGGER.warning("ATOP cloud login failed; schedule data unavailable")
                atop = None

    # Load device schema (fetched during config flow)
    device_id = entry.data[CONF_DEVICE_ID]
    schema = await hass.async_add_executor_job(load_schema, device_id)
    if schema is None and atop is not None:
        # Schema missing — try to fetch it now
        try:
            schema = await hass.async_add_executor_job(
                atop.get_device_schema, device_id
            )
            if schema:
                await hass.async_add_executor_job(save_schema, device_id, schema)
        except Exception:
            _LOGGER.warning("Failed to fetch device schema for %s", device_id)

    coordinator = OrphekCoordinator(hass, device, atop=atop, schema=schema)
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
        # Close ATOP API session if it exists
        if coordinator.atop:
            await hass.async_add_executor_job(coordinator.atop.close)
    return unload_ok
