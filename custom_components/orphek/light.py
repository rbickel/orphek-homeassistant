"""Light platform for Orphek integration."""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OrphekConfigEntry
from .const import BRIGHTNESS_MAX, BRIGHTNESS_MIN, DOMAIN
from .coordinator import OrphekCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OrphekConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Orphek light entities from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities([OrphekLight(coordinator, entry)])


class OrphekLight(CoordinatorEntity[OrphekCoordinator], LightEntity):
    """Represents an Orphek OR4-iCon LED Bar."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(
        self,
        coordinator: OrphekCoordinator,
        entry: OrphekConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = entry.unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title,
            manufacturer="Orphek",
            model="OR4-iCon LED Bar",
        )

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.is_on

    @property
    def brightness(self) -> int | None:
        if self.coordinator.data is None or not self.coordinator.data.is_on:
            return None
        tuya_val = self.coordinator.data.brightness
        return max(1, math.ceil(tuya_val * 255 / BRIGHTNESS_MAX))

    async def async_turn_on(self, **kwargs: Any) -> None:
        if ATTR_BRIGHTNESS in kwargs:
            ha_brightness = kwargs[ATTR_BRIGHTNESS]
            tuya_brightness = max(
                BRIGHTNESS_MIN,
                round(ha_brightness * BRIGHTNESS_MAX / 255),
            )
            await self.hass.async_add_executor_job(
                self.coordinator.device.set_brightness, tuya_brightness
            )
        else:
            await self.hass.async_add_executor_job(
                self.coordinator.device.set_power, True
            )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.hass.async_add_executor_job(
            self.coordinator.device.set_power, False
        )
        await self.coordinator.async_request_refresh()
