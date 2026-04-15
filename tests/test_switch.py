"""Unit tests for Orphek switch entities."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.orphek.api import OrphekState
from custom_components.orphek.switch import (
    OrphekHourSystemSwitch,
    OrphekNoAutoSwitchSwitch,
    OrphekQuietModeSwitch,
)


@pytest.fixture
def quiet_switch(mock_coordinator, mock_entry, device_info):
    return OrphekQuietModeSwitch(mock_coordinator, mock_entry, device_info)


@pytest.fixture
def hour_switch(mock_coordinator, mock_entry, device_info):
    return OrphekHourSystemSwitch(mock_coordinator, mock_entry, device_info)


@pytest.fixture
def auto_switch(mock_coordinator, mock_entry, device_info):
    return OrphekNoAutoSwitchSwitch(mock_coordinator, mock_entry, device_info)


class TestOrphekQuietModeSwitch:
    """Tests for the quiet mode switch entity."""

    def test_is_on_false(self, quiet_switch, mock_coordinator):
        mock_coordinator.data.quiet_mode = False
        assert quiet_switch.is_on is False

    def test_is_on_true(self, quiet_switch, mock_coordinator):
        mock_coordinator.data.quiet_mode = True
        assert quiet_switch.is_on is True

    def test_is_on_none_data(self, quiet_switch, mock_coordinator):
        mock_coordinator.data = None
        assert quiet_switch.is_on is None

    @pytest.mark.asyncio
    async def test_turn_on(self, quiet_switch, mock_coordinator):
        await quiet_switch.async_turn_on()
        mock_coordinator.async_device_io.assert_called_once_with(
            mock_coordinator.device.set_quiet_mode, True
        )
        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_off(self, quiet_switch, mock_coordinator):
        await quiet_switch.async_turn_off()
        mock_coordinator.async_device_io.assert_called_once_with(
            mock_coordinator.device.set_quiet_mode, False
        )
        mock_coordinator.async_request_refresh.assert_called_once()

    def test_unique_id(self, quiet_switch):
        assert quiet_switch.unique_id == "bf00000000000000test_quiet_mode"

    def test_name(self, quiet_switch):
        assert quiet_switch.name == "Quiet mode"


class TestOrphekHourSystemSwitch:
    """Tests for the 24-hour clock switch entity."""

    def test_is_on_false(self, hour_switch, mock_coordinator):
        mock_coordinator.data.hour_system = False
        assert hour_switch.is_on is False

    def test_is_on_true(self, hour_switch, mock_coordinator):
        mock_coordinator.data.hour_system = True
        assert hour_switch.is_on is True

    def test_is_on_none_data(self, hour_switch, mock_coordinator):
        mock_coordinator.data = None
        assert hour_switch.is_on is None

    @pytest.mark.asyncio
    async def test_turn_on(self, hour_switch, mock_coordinator):
        await hour_switch.async_turn_on()
        mock_coordinator.async_device_io.assert_called_once_with(
            mock_coordinator.device.set_hour_system, True
        )
        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_off(self, hour_switch, mock_coordinator):
        await hour_switch.async_turn_off()
        mock_coordinator.async_device_io.assert_called_once_with(
            mock_coordinator.device.set_hour_system, False
        )
        mock_coordinator.async_request_refresh.assert_called_once()

    def test_unique_id(self, hour_switch):
        assert hour_switch.unique_id == "bf00000000000000test_hour_system"

    def test_name(self, hour_switch):
        assert hour_switch.name == "24-hour clock"


class TestOrphekNoAutoSwitchSwitch:
    """Tests for the disable auto-recovery switch entity."""

    def test_is_on_false(self, auto_switch, mock_coordinator):
        mock_coordinator.data.no_auto_switch = False
        assert auto_switch.is_on is False

    def test_is_on_true(self, auto_switch, mock_coordinator):
        mock_coordinator.data.no_auto_switch = True
        assert auto_switch.is_on is True

    def test_is_on_none_data(self, auto_switch, mock_coordinator):
        mock_coordinator.data = None
        assert auto_switch.is_on is None

    @pytest.mark.asyncio
    async def test_turn_on(self, auto_switch, mock_coordinator):
        await auto_switch.async_turn_on()
        mock_coordinator.async_device_io.assert_called_once_with(
            mock_coordinator.device.set_no_auto_switch, True
        )
        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_off(self, auto_switch, mock_coordinator):
        await auto_switch.async_turn_off()
        mock_coordinator.async_device_io.assert_called_once_with(
            mock_coordinator.device.set_no_auto_switch, False
        )
        mock_coordinator.async_request_refresh.assert_called_once()

    def test_unique_id(self, auto_switch):
        assert auto_switch.unique_id == "bf00000000000000test_no_auto_switch"

    def test_name(self, auto_switch):
        assert auto_switch.name == "Disable auto-recovery"
