"""Unit tests for Orphek select entities."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.orphek.api import OrphekState
from custom_components.orphek.select import (
    MODE_OPTIONS,
    TEMP_UNIT_OPTIONS,
    OrphekModeSelect,
    OrphekTempUnitSelect,
)


@pytest.fixture
def mode_select(mock_coordinator, mock_entry, device_info):
    return OrphekModeSelect(mock_coordinator, mock_entry, device_info)


@pytest.fixture
def temp_unit_select(mock_coordinator, mock_entry, device_info):
    return OrphekTempUnitSelect(mock_coordinator, mock_entry, device_info)


class TestOrphekModeSelect:
    """Tests for the mode select entity."""

    def test_options(self, mode_select):
        assert mode_select.options == list(MODE_OPTIONS.values())
        assert "Program" in mode_select.options
        assert "Quick" in mode_select.options
        assert "Sun Moon Sync" in mode_select.options
        assert "Biorhythm" in mode_select.options

    def test_current_option_program(self, mode_select, mock_coordinator):
        mock_coordinator.data.mode = "program"
        assert mode_select.current_option == "Program"

    def test_current_option_sun_moon_sync(self, mode_select, mock_coordinator):
        mock_coordinator.data.mode = "sunMoonSync"
        assert mode_select.current_option == "Sun Moon Sync"

    def test_current_option_biorhythm(self, mode_select, mock_coordinator):
        mock_coordinator.data.mode = "biorhythm"
        assert mode_select.current_option == "Biorhythm"

    def test_current_option_quick(self, mode_select, mock_coordinator):
        mock_coordinator.data.mode = "quick"
        assert mode_select.current_option == "Quick"

    def test_current_option_none_data(self, mode_select, mock_coordinator):
        mock_coordinator.data = None
        assert mode_select.current_option is None

    def test_current_option_unknown_mode(self, mode_select, mock_coordinator):
        """Unknown mode falls back to raw value."""
        mock_coordinator.data.mode = "custom_mode"
        assert mode_select.current_option == "custom_mode"

    @pytest.mark.asyncio
    async def test_select_program(self, mode_select, mock_coordinator):
        await mode_select.async_select_option("Program")
        mock_coordinator.async_device_io.assert_called_once_with(
            mock_coordinator.device.set_mode, "program"
        )
        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_select_quick(self, mode_select, mock_coordinator):
        await mode_select.async_select_option("Quick")
        mock_coordinator.async_device_io.assert_called_once_with(
            mock_coordinator.device.set_mode, "quick"
        )

    @pytest.mark.asyncio
    async def test_select_sun_moon_sync(self, mode_select, mock_coordinator):
        await mode_select.async_select_option("Sun Moon Sync")
        mock_coordinator.async_device_io.assert_called_once_with(
            mock_coordinator.device.set_mode, "sunMoonSync"
        )

    @pytest.mark.asyncio
    async def test_select_biorhythm(self, mode_select, mock_coordinator):
        await mode_select.async_select_option("Biorhythm")
        mock_coordinator.async_device_io.assert_called_once_with(
            mock_coordinator.device.set_mode, "biorhythm"
        )

    def test_unique_id(self, mode_select):
        assert mode_select.unique_id == "bf00000000000000test_mode"

    def test_name(self, mode_select):
        assert mode_select.name == "Mode"


class TestOrphekTempUnitSelect:
    """Tests for the temperature unit select entity."""

    def test_options(self, temp_unit_select):
        assert temp_unit_select.options == list(TEMP_UNIT_OPTIONS.values())
        assert "Celsius (°C)" in temp_unit_select.options
        assert "Fahrenheit (°F)" in temp_unit_select.options

    def test_current_option_celsius(self, temp_unit_select, mock_coordinator):
        mock_coordinator.data.temp_unit = "c"
        assert temp_unit_select.current_option == "Celsius (°C)"

    def test_current_option_fahrenheit(self, temp_unit_select, mock_coordinator):
        mock_coordinator.data.temp_unit = "f"
        assert temp_unit_select.current_option == "Fahrenheit (°F)"

    def test_current_option_none_data(self, temp_unit_select, mock_coordinator):
        mock_coordinator.data = None
        assert temp_unit_select.current_option is None

    @pytest.mark.asyncio
    async def test_select_celsius(self, temp_unit_select, mock_coordinator):
        await temp_unit_select.async_select_option("Celsius (°C)")
        mock_coordinator.async_device_io.assert_called_once_with(
            mock_coordinator.device.set_temp_unit, "c"
        )
        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_select_fahrenheit(self, temp_unit_select, mock_coordinator):
        await temp_unit_select.async_select_option("Fahrenheit (°F)")
        mock_coordinator.async_device_io.assert_called_once_with(
            mock_coordinator.device.set_temp_unit, "f"
        )

    def test_unique_id(self, temp_unit_select):
        assert temp_unit_select.unique_id == "bf00000000000000test_temp_unit"

    def test_name(self, temp_unit_select):
        assert temp_unit_select.name == "Temperature unit"
