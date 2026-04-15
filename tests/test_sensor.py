"""Unit tests for Orphek sensor entities."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.orphek.api import OrphekState, ScheduleSlot
from custom_components.orphek.sensor import (
    OrphekLunarIntervalSensor,
    OrphekLunarMaxBrightnessSensor,
    OrphekModeRunningSensor,
    OrphekSchedulePresetSensor,
    OrphekScheduleSensor,
    OrphekTemperatureCelsiusSensor,
    OrphekTemperatureFahrenheitSensor,
    _format_schedule,
)


class TestFormatSchedule:
    """Tests for the _format_schedule helper."""

    def test_single_slot(self):
        slots = [ScheduleSlot(hour=8, minute=30, channels=[10, 20, 30, 40, 50, 60])]
        result = _format_schedule(slots)
        assert result == "08:30 [10/20/30/40/50/60]%"

    def test_multiple_slots(self):
        slots = [
            ScheduleSlot(hour=6, minute=0, channels=[0, 0, 0, 0, 0, 0]),
            ScheduleSlot(hour=12, minute=0, channels=[50, 50, 50, 50, 50, 50]),
        ]
        result = _format_schedule(slots)
        assert "06:00" in result
        assert "12:00" in result
        assert ", " in result

    def test_empty(self):
        assert _format_schedule([]) == ""


class TestOrphekTemperatureCelsiusSensor:
    """Tests for temperature °C sensor."""

    def test_value(self, mock_coordinator, mock_entry, device_info):
        sensor = OrphekTemperatureCelsiusSensor(mock_coordinator, mock_entry, device_info)
        mock_coordinator.data.temperature_c = 28
        assert sensor.native_value == 28

    def test_none_temp(self, mock_coordinator, mock_entry, device_info):
        sensor = OrphekTemperatureCelsiusSensor(mock_coordinator, mock_entry, device_info)
        mock_coordinator.data.temperature_c = None
        assert sensor.native_value is None

    def test_none_data(self, mock_coordinator, mock_entry, device_info):
        sensor = OrphekTemperatureCelsiusSensor(mock_coordinator, mock_entry, device_info)
        mock_coordinator.data = None
        assert sensor.native_value is None

    def test_unique_id(self, mock_coordinator, mock_entry, device_info):
        sensor = OrphekTemperatureCelsiusSensor(mock_coordinator, mock_entry, device_info)
        assert sensor.unique_id == "bf00000000000000test_temperature"


class TestOrphekTemperatureFahrenheitSensor:
    """Tests for temperature °F sensor."""

    def test_value(self, mock_coordinator, mock_entry, device_info):
        sensor = OrphekTemperatureFahrenheitSensor(mock_coordinator, mock_entry, device_info)
        mock_coordinator.data.temperature_f = 82
        assert sensor.native_value == 82

    def test_none(self, mock_coordinator, mock_entry, device_info):
        sensor = OrphekTemperatureFahrenheitSensor(mock_coordinator, mock_entry, device_info)
        mock_coordinator.data = None
        assert sensor.native_value is None


class TestOrphekModeRunningSensor:
    """Tests for running mode sensor."""

    def test_running_mode(self, mock_coordinator, mock_entry, device_info):
        sensor = OrphekModeRunningSensor(mock_coordinator, mock_entry, device_info)
        mock_coordinator.data.mode_running = "quick"
        assert sensor.native_value == "quick"

    def test_fallback_to_mode(self, mock_coordinator, mock_entry, device_info):
        sensor = OrphekModeRunningSensor(mock_coordinator, mock_entry, device_info)
        mock_coordinator.data.mode_running = ""
        mock_coordinator.data.mode = "program"
        assert sensor.native_value == "program"

    def test_none_data(self, mock_coordinator, mock_entry, device_info):
        sensor = OrphekModeRunningSensor(mock_coordinator, mock_entry, device_info)
        mock_coordinator.data = None
        assert sensor.native_value is None

    def test_unique_id(self, mock_coordinator, mock_entry, device_info):
        sensor = OrphekModeRunningSensor(mock_coordinator, mock_entry, device_info)
        assert sensor.unique_id == "bf00000000000000test_mode_running"


class TestOrphekScheduleSensor:
    """Tests for the schedule sensor."""

    def test_with_slots(self, mock_coordinator, mock_entry, device_info):
        sensor = OrphekScheduleSensor(mock_coordinator, mock_entry, device_info)
        mock_coordinator.data.schedule = [
            ScheduleSlot(hour=8, minute=0, channels=[50, 50, 50, 50, 50, 50])
        ]
        assert "08:00" in sensor.native_value

    def test_no_schedule(self, mock_coordinator, mock_entry, device_info):
        sensor = OrphekScheduleSensor(mock_coordinator, mock_entry, device_info)
        mock_coordinator.data.schedule = []
        assert sensor.native_value == "No schedule"

    def test_none_data(self, mock_coordinator, mock_entry, device_info):
        sensor = OrphekScheduleSensor(mock_coordinator, mock_entry, device_info)
        mock_coordinator.data = None
        assert sensor.native_value is None


class TestOrphekSchedulePresetSensor:
    """Tests for the schedule preset sensor."""

    def test_with_slots(self, mock_coordinator, mock_entry, device_info):
        sensor = OrphekSchedulePresetSensor(mock_coordinator, mock_entry, device_info)
        mock_coordinator.data.schedule_preset = [
            ScheduleSlot(hour=6, minute=30, channels=[30, 30, 30, 30, 30, 30])
        ]
        assert "06:30" in sensor.native_value

    def test_no_schedule(self, mock_coordinator, mock_entry, device_info):
        sensor = OrphekSchedulePresetSensor(mock_coordinator, mock_entry, device_info)
        mock_coordinator.data.schedule_preset = []
        assert sensor.native_value == "No schedule"


class TestOrphekLunarIntervalSensor:
    """Tests for the lunar interval sensor."""

    def test_value(self, mock_coordinator, mock_entry, device_info):
        sensor = OrphekLunarIntervalSensor(mock_coordinator, mock_entry, device_info)
        mock_coordinator.data.lunar.interval_days = 28
        assert sensor.native_value == 28

    def test_none_data(self, mock_coordinator, mock_entry, device_info):
        sensor = OrphekLunarIntervalSensor(mock_coordinator, mock_entry, device_info)
        mock_coordinator.data = None
        assert sensor.native_value is None


class TestOrphekLunarMaxBrightnessSensor:
    """Tests for the lunar max brightness sensor."""

    def test_value(self, mock_coordinator, mock_entry, device_info):
        sensor = OrphekLunarMaxBrightnessSensor(mock_coordinator, mock_entry, device_info)
        mock_coordinator.data.lunar.max_brightness = 0.52
        assert sensor.native_value == pytest.approx(0.52)

    def test_none_data(self, mock_coordinator, mock_entry, device_info):
        sensor = OrphekLunarMaxBrightnessSensor(mock_coordinator, mock_entry, device_info)
        mock_coordinator.data = None
        assert sensor.native_value is None
