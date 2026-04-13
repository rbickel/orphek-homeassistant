"""Config flow for Orphek integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .api import OrphekDevice
from .atop import OrphekAtopApi
from .const import (
    CONF_ATOP_COUNTRY_CODE,
    CONF_ATOP_EMAIL,
    CONF_ATOP_SESSION_ID,
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_LOCAL_KEY,
    COUNTRIES,
    DOMAIN,
)
from .discovery import discover_orphek_devices

_LOGGER = logging.getLogger(__name__)

STEP_ORPHEK_LOGIN_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required("country_code", default="1"): vol.In(COUNTRIES),
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
        self._discovered_devices: list[dict[str, Any]] = []
        self._atop_email: str = ""
        self._atop_session_id: str = ""
        self._atop_country_code: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step — go straight to Orphek login."""
        return await self.async_step_orphek_login()

    async def async_step_orphek_login(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle Orphek email/password login and auto-discover devices."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]
            country_code = user_input.get("country_code", "1")

            atop = OrphekAtopApi()
            logged_in = await self.hass.async_add_executor_job(
                atop.login, email, password, country_code
            )

            if not logged_in:
                errors["base"] = "invalid_auth"
            else:
                # Save session ID for authenticated API calls
                session_id = atop.session_id
                if not session_id:
                    errors["base"] = "invalid_auth"
                    _LOGGER.error("Login succeeded but no session ID returned")
                else:
                    # Discover devices on LAN
                    lan_devices = await self.hass.async_add_executor_job(
                        discover_orphek_devices
                    )

                    # Fetch all cloud devices to get local keys
                    cloud_devices = await self.hass.async_add_executor_job(
                        atop.get_devices
                    )
                    cloud_map = {
                        d.get("devId"): d for d in cloud_devices if d.get("devId")
                    }

                    existing = {
                        entry.unique_id for entry in self._async_current_entries()
                    }
                    self._discovered_devices = []

                    for dev in lan_devices:
                        if dev.device_id in existing:
                            continue
                        cloud_dev = cloud_map.get(dev.device_id)
                        if cloud_dev and cloud_dev.get("localKey"):
                            self._discovered_devices.append(
                                {
                                    "device_id": dev.device_id,
                                    "ip": dev.ip,
                                    "local_key": cloud_dev["localKey"],
                                }
                            )

                    # Also add cloud-only devices (not on LAN yet)
                    lan_ids = {d.device_id for d in lan_devices}
                    for dev_id, cloud_dev in cloud_map.items():
                        if dev_id not in existing and dev_id not in lan_ids:
                            ip = cloud_dev.get("ip", "")
                            if ip and cloud_dev.get("localKey"):
                                self._discovered_devices.append(
                                    {
                                        "device_id": dev_id,
                                        "ip": ip,
                                        "local_key": cloud_dev["localKey"],
                                    }
                                )

                    if not self._discovered_devices:
                        return self.async_abort(reason="no_devices_found")

                    # Save session ID and credentials for the device picker step
                    self._atop_email = email
                    self._atop_session_id = session_id
                    self._atop_country_code = country_code

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
                                CONF_ATOP_EMAIL: email,
                                CONF_ATOP_SESSION_ID: session_id,
                                CONF_ATOP_COUNTRY_CODE: country_code,
                            },
                        )

                    # Multiple devices available — show picker for a single device
                    device_options = {
                        dev["device_id"]: f"{dev['ip']} ({dev['device_id'][:8]}...)"
                        for dev in self._discovered_devices
                    }
                    return self.async_show_form(
                        step_id="pick_device",
                        data_schema=vol.Schema(
                            {
                                vol.Required("devices"): vol.In(device_options),
                            }
                        ),
                    )

        return self.async_show_form(
            step_id="orphek_login",
            data_schema=STEP_ORPHEK_LOGIN_SCHEMA,
            errors=errors,
        )

    async def async_step_pick_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle device selection when multiple devices are found."""
        if user_input is not None:
            selected = user_input.get("devices", [])
            selected_device_found = False
            for dev in self._discovered_devices:
                if dev["device_id"] in selected:
                    selected_device_found = True
                    if not await _test_device(
                        self.hass, dev["ip"], dev["device_id"], dev["local_key"]
                    ):
                        continue

                    await self.async_set_unique_id(dev["device_id"])
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"Orphek ({dev['ip']})",
                        data={
                            CONF_HOST: dev["ip"],
                            CONF_DEVICE_ID: dev["device_id"],
                            CONF_LOCAL_KEY: dev["local_key"],
                            CONF_ATOP_EMAIL: self._atop_email,
                            CONF_ATOP_SESSION_ID: self._atop_session_id,
                            CONF_ATOP_COUNTRY_CODE: self._atop_country_code,
                        },
                    )

            if selected_device_found:
                return self.async_abort(reason="cannot_connect")

        return self.async_abort(reason="no_devices_selected")
