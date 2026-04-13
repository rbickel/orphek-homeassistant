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
    CONF_PRODUCT_ID,
    DOMAIN,
)
from .coordinator import OrphekCoordinator
from .device_schema import load_schema, list_known_products, save_schema

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
    country_code = entry.data.get(CONF_ATOP_COUNTRY_CODE, "1")

    if atop_email and (atop_session_id or atop_password):
        atop = OrphekAtopApi()

        # Store credentials so atop.relogin() can work transparently
        if atop_password:
            atop._email = atop_email
            atop._password = atop_password
            atop._country_code = country_code

        session_ok = False

        # 1. Try the stored session ID first (fast, no login roundtrip)
        if atop_session_id:
            atop.set_session_id(atop_session_id)
            # Validate the session with a lightweight API call
            check = await hass.async_add_executor_job(
                atop._request, "thing.m.user.info.get", "1.0", None, None, False
            )
            if check.get("success"):
                session_ok = True
                _LOGGER.debug("Stored ATOP session is still valid")
            else:
                _LOGGER.info("Stored ATOP session expired, will re-authenticate")

        # 2. If session is invalid, re-login with stored password
        if not session_ok and atop_password:
            logged_in = await hass.async_add_executor_job(
                atop.login, atop_email, atop_password, country_code
            )
            if logged_in and atop.session_id:
                session_ok = True
                # Persist the fresh session ID so we skip login on next restart
                hass.config_entries.async_update_entry(
                    entry,
                    data={**entry.data, CONF_ATOP_SESSION_ID: atop.session_id},
                )
                _LOGGER.info("ATOP re-login successful, session ID updated")
            else:
                _LOGGER.warning("ATOP re-login failed")

        # 3. Last resort: trigger reauth flow so the user can re-enter credentials
        if not session_ok:
            _LOGGER.warning(
                "ATOP cloud authentication failed; "
                "schedule/expansion data unavailable. "
                "A re-authentication prompt will appear."
            )
            entry.async_start_reauth(hass)
            atop = None

    # Load product schema (keyed by product_id, not device_id)
    device_id = entry.data[CONF_DEVICE_ID]
    product_id = entry.data.get(CONF_PRODUCT_ID, "")
    schema: dict | None = None
    known_products = await hass.async_add_executor_job(list_known_products)

    if product_id:
        schema = await hass.async_add_executor_job(load_schema, product_id)

    if schema is None and atop is not None:
        # Schema missing — try to fetch it now
        try:
            schema = await hass.async_add_executor_job(
                atop.get_device_schema, device_id
            )
            if schema:
                fetched_pid = schema.get("product_id", "")
                if fetched_pid and fetched_pid not in known_products:
                    import json as _json

                    _LOGGER.warning(
                        "Discovered new Orphek product '%s' (category: %s). "
                        "Schema saved locally. Please report this to the "
                        "integration repository so it can be included for "
                        "other users. Full schema:\n%s",
                        fetched_pid,
                        schema.get("category_code", "unknown"),
                        _json.dumps(schema, indent=2),
                    )
                await hass.async_add_executor_job(save_schema, schema)
        except Exception:
            _LOGGER.warning("Failed to fetch product schema for %s", device_id)

    coordinator = OrphekCoordinator(
        hass, device, atop=atop, schema=schema, config_entry=entry
    )
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
        if coordinator._atop:
            await hass.async_add_executor_job(coordinator._atop.close)
    return unload_ok
