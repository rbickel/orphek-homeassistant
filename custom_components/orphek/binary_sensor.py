"""Binary sensor platform for Orphek integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
)
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
    """Set up Orphek binary sensor entities from a config entry."""
    coordinator = entry.runtime_data
    device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)})
    async_add_entities([
        OrphekBinarySensor(coordinator, entry, device_info, "jellyfish_enabled", "Jellyfish", "mdi:jellyfish"),
        OrphekBinarySensor(coordinator, entry, device_info, "clouds_enabled", "Clouds", "mdi:cloud"),
        OrphekBinarySensor(coordinator, entry, device_info, "acclimation_enabled", "Acclimation", "mdi:chart-timeline-variant"),
        OrphekBinarySensor(coordinator, entry, device_info, "lunar_enabled", "Lunar cycle", "mdi:moon-waning-crescent"),
        OrphekBinarySensor(coordinator, entry, device_info, "biorhythm_enabled", "Biorhythm", "mdi:sine-wave"),
        OrphekBinarySensor(coordinator, entry, device_info, "sun_moon_sync_enabled", "Sun moon sync", "mdi:weather-sunny"),
        OrphekBinarySensor(coordinator, entry, device_info, "quiet_mode", "Quiet mode", "mdi:fan-off"),
    ])


class OrphekBinarySensor(CoordinatorEntity[OrphekCoordinator], BinarySensorEntity):
    """A binary sensor for an Orphek on/off attribute."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OrphekCoordinator,
        entry: OrphekConfigEntry,
        device_info: DeviceInfo,
        state_key: str,
        name: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._state_key = state_key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.unique_id}_{state_key}"
        self._attr_device_info = device_info

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        state = self.coordinator.data
        # Handle nested expansion configs
        if self._state_key == "jellyfish_enabled":
            return state.jellyfish.enabled
        if self._state_key == "acclimation_enabled":
            return state.acclimation.enabled
        if self._state_key == "lunar_enabled":
            return state.lunar.enabled
        if self._state_key == "biorhythm_enabled":
            return state.biorhythm.enabled
        if self._state_key == "sun_moon_sync_enabled":
            return state.sun_moon_sync.enabled
        return getattr(state, self._state_key, None)
