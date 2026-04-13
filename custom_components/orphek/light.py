"""Light platform for Orphek integration."""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OrphekConfigEntry
from .const import (
    CHANNEL_MAX,
    CHANNEL_MIN,
    DP_CH1,
    DOMAIN,
)
from .coordinator import OrphekCoordinator

# Map user-friendly effect names to DP 110 mode values
EFFECT_LIST = ["Program", "Quick", "Sun Moon Sync", "Biorhythm"]
_EFFECT_TO_MODE = {
    "Program": "program",
    "Quick": "quick",
    "Sun Moon Sync": "sunMoonSync",
    "Biorhythm": "biorhythm",
}
_MODE_TO_EFFECT = {v: k for k, v in _EFFECT_TO_MODE.items()}


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
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = EFFECT_LIST

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
        channel_val = self.coordinator.data.brightness
        return max(1, math.ceil(channel_val * 255 / CHANNEL_MAX)) if channel_val > 0 else 0

    @property
    def effect(self) -> str | None:
        if self.coordinator.data is None:
            return None
        mode = self.coordinator.data.mode
        return _MODE_TO_EFFECT.get(mode, mode)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose individual channel levels."""
        if self.coordinator.data is None:
            return {}
        state = self.coordinator.data
        attrs: dict[str, Any] = {}

        # Channel levels
        for dp in sorted(state.channels):
            ch_num = dp - DP_CH1 + 1
            attrs[f"ch{ch_num}"] = state.channels[dp]

        return attrs

    async def async_turn_on(self, **kwargs: Any) -> None:
        if ATTR_EFFECT in kwargs:
            effect = kwargs[ATTR_EFFECT]
            mode = _EFFECT_TO_MODE.get(effect, effect)
            await self.coordinator.async_device_io(
                self.coordinator.device.set_mode, mode
            )
        elif ATTR_BRIGHTNESS in kwargs:
            ha_brightness = kwargs[ATTR_BRIGHTNESS]
            channel_brightness = max(
                CHANNEL_MIN,
                round(ha_brightness * CHANNEL_MAX / 255),
            )
            await self.coordinator.async_device_io(
                self.coordinator.device.set_brightness, channel_brightness
            )
        else:
            await self.coordinator.async_device_io(
                self.coordinator.device.set_power, True
            )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_device_io(
            self.coordinator.device.set_power, False
        )
        await self.coordinator.async_request_refresh()
