"""Sensor platform for Orphek integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OrphekConfigEntry
from .api import ScheduleSlot
from .const import DOMAIN
from .coordinator import OrphekCoordinator


def _format_schedule(slots: list[ScheduleSlot]) -> str:
    """Format schedule slots into a human-readable string."""
    parts = []
    for slot in slots:
        ch_str = "/".join(str(c) for c in slot.channels)
        parts.append(f"{slot.hour:02d}:{slot.minute:02d} [{ch_str}]%")
    return ", ".join(parts)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OrphekConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Orphek sensor entities from a config entry."""
    coordinator = entry.runtime_data
    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry.unique_id)},
    )
    async_add_entities([
        OrphekTemperatureCelsiusSensor(coordinator, entry, device_info),
        OrphekTemperatureFahrenheitSensor(coordinator, entry, device_info),
        OrphekModeRunningSensor(coordinator, entry, device_info),
        OrphekScheduleSensor(coordinator, entry, device_info),
        OrphekSchedulePresetSensor(coordinator, entry, device_info),
        OrphekLunarIntervalSensor(coordinator, entry, device_info),
        OrphekLunarMaxBrightnessSensor(coordinator, entry, device_info),
    ])


class OrphekTemperatureCelsiusSensor(CoordinatorEntity[OrphekCoordinator], SensorEntity):
    """Temperature sensor (°C) for the Orphek light."""

    _attr_has_entity_name = True
    _attr_name = "Temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        coordinator: OrphekCoordinator,
        entry: OrphekConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_temperature"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.temperature_c


class OrphekTemperatureFahrenheitSensor(CoordinatorEntity[OrphekCoordinator], SensorEntity):
    """Temperature sensor (°F) for the Orphek light."""

    _attr_has_entity_name = True
    _attr_name = "Temperature (°F)"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT

    def __init__(
        self,
        coordinator: OrphekCoordinator,
        entry: OrphekConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_temperature_f"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.temperature_f


class OrphekModeRunningSensor(CoordinatorEntity[OrphekCoordinator], SensorEntity):
    """Running mode sensor for the Orphek light."""

    _attr_has_entity_name = True
    _attr_name = "Running mode"
    _attr_icon = "mdi:lightbulb-auto"

    def __init__(
        self,
        coordinator: OrphekCoordinator,
        entry: OrphekConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_mode_running"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.mode_running or self.coordinator.data.mode


class OrphekScheduleSensor(CoordinatorEntity[OrphekCoordinator], SensorEntity):
    """Active program schedule sensor."""

    _attr_has_entity_name = True
    _attr_name = "Schedule"
    _attr_icon = "mdi:calendar-clock"

    def __init__(
        self,
        coordinator: OrphekCoordinator,
        entry: OrphekConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_schedule"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        slots = self.coordinator.data.schedule
        return _format_schedule(slots) if slots else "No schedule"

    @property
    def extra_state_attributes(self) -> dict | None:
        if self.coordinator.data is None:
            return None
        slots = self.coordinator.data.schedule
        return {
            "slots": [
                {
                    "hour": s.hour,
                    "minute": s.minute,
                    "channels": s.channels,
                }
                for s in slots
            ]
        }


class OrphekSchedulePresetSensor(CoordinatorEntity[OrphekCoordinator], SensorEntity):
    """Preset program schedule sensor."""

    _attr_has_entity_name = True
    _attr_name = "Schedule preset"
    _attr_icon = "mdi:calendar-star"

    def __init__(
        self,
        coordinator: OrphekCoordinator,
        entry: OrphekConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_schedule_preset"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        slots = self.coordinator.data.schedule_preset
        return _format_schedule(slots) if slots else "No schedule"


class OrphekLunarIntervalSensor(CoordinatorEntity[OrphekCoordinator], SensorEntity):
    """Lunar cycle interval sensor."""

    _attr_has_entity_name = True
    _attr_name = "Lunar interval"
    _attr_icon = "mdi:moon-waning-crescent"
    _attr_native_unit_of_measurement = "days"

    def __init__(
        self,
        coordinator: OrphekCoordinator,
        entry: OrphekConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_lunar_interval"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.lunar.interval_days


class OrphekLunarMaxBrightnessSensor(CoordinatorEntity[OrphekCoordinator], SensorEntity):
    """Lunar cycle max brightness sensor."""

    _attr_has_entity_name = True
    _attr_name = "Lunar max brightness"
    _attr_icon = "mdi:moon-full"
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(
        self,
        coordinator: OrphekCoordinator,
        entry: OrphekConfigEntry,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_lunar_max_brightness"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.lunar.max_brightness
