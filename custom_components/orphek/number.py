"""Number platform for Orphek integration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OrphekConfigEntry
from .const import (
    CHANNEL_MAX,
    CHANNEL_MIN,
    CHANNEL_SCALE,
    DP_CHANNELS,
    DP_CH1,
    DOMAIN,
)
from .coordinator import OrphekCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OrphekConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Orphek number entities from a config entry."""
    coordinator = entry.runtime_data
    device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)})
    async_add_entities([
        OrphekChannelNumber(coordinator, entry, device_info, dp)
        for dp in DP_CHANNELS
    ])


class OrphekChannelNumber(CoordinatorEntity[OrphekCoordinator], NumberEntity):
    """Number entity for an individual LED channel (DP 103-108)."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:led-on"
    _attr_native_min_value = CHANNEL_MIN / CHANNEL_SCALE  # 0.0
    _attr_native_max_value = CHANNEL_MAX / CHANNEL_SCALE  # 100.0
    _attr_native_step = 1.0 / CHANNEL_SCALE  # 0.01
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        coordinator: OrphekCoordinator,
        entry: OrphekConfigEntry,
        device_info: DeviceInfo,
        dp: int,
    ) -> None:
        super().__init__(coordinator)
        self._dp = dp
        ch_num = dp - DP_CH1 + 1
        self._attr_name = f"Channel {ch_num}"
        self._attr_unique_id = f"{entry.unique_id}_ch{ch_num}"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.channels.get(self._dp, 0)
        return raw / CHANNEL_SCALE

    async def async_set_native_value(self, value: float) -> None:
        """Set the channel value."""
        raw = max(CHANNEL_MIN, min(CHANNEL_MAX, round(value * CHANNEL_SCALE)))
        await self.coordinator.async_device_io(
            self.coordinator.device.set_channels, {self._dp: raw}
        )
        await self.coordinator.async_request_refresh()
