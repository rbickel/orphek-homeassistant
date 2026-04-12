"""Light platform for Orphek integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OrphekConfigEntry
from .const import DOMAIN
from .coordinator import OrphekCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OrphekConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Orphek light entities from a config entry."""
    coordinator = entry.runtime_data

    entities: list[OrphekChannelLight] = []
    if coordinator.data and coordinator.data.channels:
        for channel in coordinator.data.channels:
            entities.append(
                OrphekChannelLight(coordinator, entry, channel.channel_id)
            )

    async_add_entities(entities)


class OrphekChannelLight(CoordinatorEntity[OrphekCoordinator], LightEntity):
    """Represents a single channel of an Orphek light."""

    _attr_has_entity_name = True
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(
        self,
        coordinator: OrphekCoordinator,
        entry: OrphekConfigEntry,
        channel_id: int,
    ) -> None:
        super().__init__(coordinator)
        self._channel_id = channel_id
        self._attr_unique_id = f"{entry.entry_id}_channel_{channel_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Orphek",
        )
        self._update_attrs()

    @property
    def _channel(self):
        """Get the current channel state from coordinator data."""
        if self.coordinator.data:
            for ch in self.coordinator.data.channels:
                if ch.channel_id == self._channel_id:
                    return ch
        return None

    def _update_attrs(self) -> None:
        """Update entity attributes from coordinator data."""
        channel = self._channel
        if channel:
            self._attr_name = channel.name
            # Map 0-1000 → 0-255
            self._attr_brightness = round(channel.brightness * 255 / 1000)
            self._attr_is_on = channel.brightness > 0

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_attrs()
        super()._handle_coordinator_update()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the channel."""
        if ATTR_BRIGHTNESS in kwargs:
            # Map 0-255 → 0-1000
            brightness_1000 = round(kwargs[ATTR_BRIGHTNESS] * 1000 / 255)
        else:
            brightness_1000 = 1000

        await self.coordinator.api.set_channel_brightness(
            self._channel_id, brightness_1000
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the channel."""
        await self.coordinator.api.set_channel_brightness(self._channel_id, 0)
        await self.coordinator.async_request_refresh()
