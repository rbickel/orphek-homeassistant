"""Config flow for Orphek integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant

from .api import OrphekDevice, OrphekConnectionError
from .cloud import TuyaCloudApi
from .const import (
    CONF_API_KEY,
    CONF_API_REGION,
    CONF_API_SECRET,
    CONF_CLOUD_CREDENTIALS,
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_LOCAL_KEY,
    DOMAIN,
)
from .discovery import discover_orphek_devices

_LOGGER = logging.getLogger(__name__)

STEP_METHOD_SCHEMA = vol.Schema(
    {
        vol.Required("method", default="cloud"): vol.In(
            {"cloud": "Auto-discover (recommended)", "manual": "Manual setup"}
        ),
    }
)

STEP_CLOUD_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_API_SECRET): str,
        vol.Required(CONF_API_REGION, default="eu"): vol.In(
            {"eu": "Europe", "us": "Americas", "cn": "China", "in": "India"}
        ),
    }
)

STEP_MANUAL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_DEVICE_ID): str,
        vol.Required(CONF_LOCAL_KEY): str,
    }
)


async def _test_device(hass: HomeAssistant, host: str, device_id: str, local_key: str) -> bool:
    """Test connection to a device."""
    device = OrphekDevice(device_id=device_id, host=host, local_key=local_key)
    try:
        return await hass.async_add_executor_job(device.test_connection)
    finally:
        device.close()


class OrphekConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Orphek."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._cloud_api: TuyaCloudApi | None = None
        self._discovered_devices: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step — choose setup method."""
        if user_input is not None:
            if user_input["method"] == "cloud":
                return await self.async_step_cloud()
            return await self.async_step_manual()

        return self.async_show_form(step_id="user", data_schema=STEP_METHOD_SCHEMA)

    async def async_step_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle cloud credentials step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api = TuyaCloudApi(
                user_input[CONF_API_KEY],
                user_input[CONF_API_SECRET],
                user_input[CONF_API_REGION],
            )

            valid = await self.hass.async_add_executor_job(api.test_credentials)
            if not valid:
                errors["base"] = "invalid_api_credentials"
            else:
                self._cloud_api = api
                # Save cloud credentials for later use (key refresh etc.)
                self.hass.data.setdefault(DOMAIN, {})[CONF_CLOUD_CREDENTIALS] = {
                    CONF_API_KEY: user_input[CONF_API_KEY],
                    CONF_API_SECRET: user_input[CONF_API_SECRET],
                    CONF_API_REGION: user_input[CONF_API_REGION],
                }
                return await self.async_step_discover()

        return self.async_show_form(
            step_id="cloud",
            data_schema=STEP_CLOUD_SCHEMA,
            errors=errors,
        )

    async def async_step_discover(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Discover Orphek devices on LAN and fetch their local keys."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # User selected devices to add
            selected = user_input.get("devices", [])
            if not selected:
                errors["base"] = "no_devices_selected"
            else:
                # Add the first device; remaining ones get added in the next iteration
                for dev in self._discovered_devices:
                    if dev["device_id"] in selected:
                        await self.async_set_unique_id(dev["device_id"])
                        self._abort_if_unique_id_configured()
                        return self.async_create_entry(
                            title=f"Orphek ({dev['ip']})",
                            data={
                                CONF_HOST: dev["ip"],
                                CONF_DEVICE_ID: dev["device_id"],
                                CONF_LOCAL_KEY: dev["local_key"],
                            },
                        )

        # Discover devices on LAN
        lan_devices = await self.hass.async_add_executor_job(discover_orphek_devices)
        _LOGGER.debug("LAN discovery found %d Orphek devices", len(lan_devices))

        if not lan_devices:
            return self.async_abort(reason="no_devices_found")

        # Fetch local keys from cloud for each discovered device
        self._discovered_devices = []
        for dev in lan_devices:
            # Skip already configured devices
            existing = {
                entry.unique_id
                for entry in self._async_current_entries()
            }
            if dev.device_id in existing:
                continue

            local_key = await self.hass.async_add_executor_job(
                self._cloud_api.get_device_local_key, dev.device_id
            )
            if local_key:
                self._discovered_devices.append(
                    {
                        "device_id": dev.device_id,
                        "ip": dev.ip,
                        "local_key": local_key,
                    }
                )

        if not self._discovered_devices:
            return self.async_abort(reason="no_new_devices")

        # If only one device, add it directly
        if len(self._discovered_devices) == 1:
            dev = self._discovered_devices[0]
            await self.async_set_unique_id(dev["device_id"])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Orphek ({dev['ip']})",
                data={
                    CONF_HOST: dev["ip"],
                    CONF_DEVICE_ID: dev["device_id"],
                    CONF_LOCAL_KEY: dev["local_key"],
                },
            )

        # Multiple devices — let user pick
        device_options = {
            dev["device_id"]: f"{dev['ip']} ({dev['device_id'][:8]}...)"
            for dev in self._discovered_devices
        }
        return self.async_show_form(
            step_id="discover",
            data_schema=vol.Schema(
                {
                    vol.Required("devices"): vol.All(
                        [vol.In(device_options)],
                        vol.Length(min=1),
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual device entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            local_key = user_input[CONF_LOCAL_KEY].strip()

            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            self._abort_if_unique_id_configured()

            connected = await _test_device(
                self.hass,
                user_input[CONF_HOST],
                user_input[CONF_DEVICE_ID],
                local_key,
            )
            if not connected:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"Orphek ({user_input[CONF_HOST]})",
                    data={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_DEVICE_ID: user_input[CONF_DEVICE_ID],
                        CONF_LOCAL_KEY: local_key,
                    },
                )

        return self.async_show_form(
            step_id="manual",
            data_schema=STEP_MANUAL_SCHEMA,
            errors=errors,
        )
