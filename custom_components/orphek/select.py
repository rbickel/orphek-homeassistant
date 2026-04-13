"""Select platform for Orphek integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OrphekConfigEntry
from .const import DOMAIN, MODES_SELECTABLE
from .coordinator import OrphekCoordinator

# Human-readable labels for mode enum values
MODE_OPTIONS = {
    "program": "Program",
    "quick": "Quick",
    "sunMoonSync": "Sun Moon Sync",
    "biorhythm": "Biorhythm",
}

TEMP_UNIT_OPTIONS = {
    "c": "Celsius (°C)",
    "f": "Fahrenheit (°F)",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OrphekConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Orphek select entities from a config entry."""
    coordinator = entry.runtime_data
    device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)})
    async_add_entities([
        OrphekModeSelect(coordinator, entry, device_info),
        OrphekTempUnitSelect(coordinator, entry, device_info),
    ])


class OrphekModeSelect(CoordinatorEntity[OrphekCoordinator], SelectEntity):
    """Select entity for the Orphek operating mode (DP 110)."""

    _attr_has_entity_name = True
    _attr_name = "Mode"
    _attr_icon = "mdi:lightbulb-cog"
    _attr_options = list(MODE_OPTIONS.values())

    def __init__(
        self,
        coordinator: OrphekCoordinator,
        entry: OrphekConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_mode"
        self._attr_device_info = device_info

    @property
    def current_option(self) -> str | None:
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.mode
        return MODE_OPTIONS.get(raw, raw)

    async def async_select_option(self, option: str) -> None:
        """Set the operating mode."""
        # Reverse-map label to raw value
        raw = next(
            (k for k, v in MODE_OPTIONS.items() if v == option),
            option,
        )
        await self.coordinator.async_device_io(
            self.coordinator.device.set_mode, raw
        )
        await self.coordinator.async_request_refresh()


class OrphekTempUnitSelect(CoordinatorEntity[OrphekCoordinator], SelectEntity):
    """Select entity for temperature display unit (DP 125)."""

    _attr_has_entity_name = True
    _attr_name = "Temperature unit"
    _attr_icon = "mdi:thermometer"
    _attr_options = list(TEMP_UNIT_OPTIONS.values())

    def __init__(
        self,
        coordinator: OrphekCoordinator,
        entry: OrphekConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_temp_unit"
        self._attr_device_info = device_info

    @property
    def current_option(self) -> str | None:
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.temp_unit
        return TEMP_UNIT_OPTIONS.get(raw, raw)

    async def async_select_option(self, option: str) -> None:
        """Set the temperature unit."""
        raw = next(
            (k for k, v in TEMP_UNIT_OPTIONS.items() if v == option),
            option,
        )
        await self.coordinator.async_device_io(
            self.coordinator.device.set_temp_unit, raw
        )
        await self.coordinator.async_request_refresh()
