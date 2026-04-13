"""Switch platform for Orphek integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OrphekConfigEntry
from .const import DOMAIN
from .coordinator import OrphekCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OrphekConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Orphek switch entities from a config entry."""
    coordinator = entry.runtime_data
    device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)})
    async_add_entities([
        OrphekQuietModeSwitch(coordinator, entry, device_info),
        OrphekHourSystemSwitch(coordinator, entry, device_info),
        OrphekNoAutoSwitchSwitch(coordinator, entry, device_info),
    ])


class OrphekQuietModeSwitch(CoordinatorEntity[OrphekCoordinator], SwitchEntity):
    """Switch for quiet/silent fan mode (DP 123)."""

    _attr_has_entity_name = True
    _attr_name = "Quiet mode"
    _attr_icon = "mdi:fan-off"

    def __init__(
        self,
        coordinator: OrphekCoordinator,
        entry: OrphekConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_quiet_mode"
        self._attr_device_info = device_info

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.quiet_mode

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_device_io(
            self.coordinator.device.set_quiet_mode, True
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_device_io(
            self.coordinator.device.set_quiet_mode, False
        )
        await self.coordinator.async_request_refresh()


class OrphekHourSystemSwitch(CoordinatorEntity[OrphekCoordinator], SwitchEntity):
    """Switch for 24-hour clock mode (DP 119)."""

    _attr_has_entity_name = True
    _attr_name = "24-hour clock"
    _attr_icon = "mdi:clock-outline"

    def __init__(
        self,
        coordinator: OrphekCoordinator,
        entry: OrphekConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_hour_system"
        self._attr_device_info = device_info

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.hour_system

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_device_io(
            self.coordinator.device.set_hour_system, True
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_device_io(
            self.coordinator.device.set_hour_system, False
        )
        await self.coordinator.async_request_refresh()


class OrphekNoAutoSwitchSwitch(CoordinatorEntity[OrphekCoordinator], SwitchEntity):
    """Switch for disabling auto-recovery (DP 120)."""

    _attr_has_entity_name = True
    _attr_name = "Disable auto-recovery"
    _attr_icon = "mdi:sync-off"

    def __init__(
        self,
        coordinator: OrphekCoordinator,
        entry: OrphekConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_no_auto_switch"
        self._attr_device_info = device_info

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.no_auto_switch

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_device_io(
            self.coordinator.device.set_no_auto_switch, True
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_device_io(
            self.coordinator.device.set_no_auto_switch, False
        )
        await self.coordinator.async_request_refresh()
