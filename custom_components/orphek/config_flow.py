"""Config flow for Orphek integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant

from .api import OrphekDevice, OrphekConnectionError
from .const import CONF_DEVICE_ID, CONF_HOST, CONF_LOCAL_KEY, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_DEVICE_ID): str,
        vol.Required(CONF_LOCAL_KEY): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    """Validate the user input allows us to connect."""
    device = OrphekDevice(
        device_id=data[CONF_DEVICE_ID],
        host=data[CONF_HOST],
        local_key=data[CONF_LOCAL_KEY],
    )
    try:
        connected = await hass.async_add_executor_job(device.test_connection)
        if not connected:
            raise OrphekConnectionError("Cannot connect to device")
    finally:
        device.close()
    return {"title": f"Orphek ({data[CONF_HOST]})"}


class OrphekConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Orphek."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
            except OrphekConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
