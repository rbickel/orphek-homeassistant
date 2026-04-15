"""Unit tests for Orphek number entities (channel controls)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.orphek.api import OrphekState
from custom_components.orphek.const import (
    CHANNEL_MAX,
    CHANNEL_MIN,
    CHANNEL_SCALE,
    DP_CH1,
    DP_CH2,
    DP_CH6,
    DP_CHANNELS,
)
from custom_components.orphek.number import OrphekChannelNumber


@pytest.fixture
def channel1_number(mock_coordinator, mock_entry, device_info):
    return OrphekChannelNumber(mock_coordinator, mock_entry, device_info, DP_CH1)


@pytest.fixture
def channel6_number(mock_coordinator, mock_entry, device_info):
    return OrphekChannelNumber(mock_coordinator, mock_entry, device_info, DP_CH6)


class TestOrphekChannelNumberProperties:
    """Tests for channel number entity read properties."""

    def test_native_value_conversion(self, channel1_number, mock_coordinator):
        """Raw 4100 should display as 41.0%."""
        mock_coordinator.data.channels[DP_CH1] = 4100
        assert channel1_number.native_value == pytest.approx(41.0)

    def test_native_value_zero(self, channel1_number, mock_coordinator):
        mock_coordinator.data.channels[DP_CH1] = 0
        assert channel1_number.native_value == pytest.approx(0.0)

    def test_native_value_max(self, channel1_number, mock_coordinator):
        mock_coordinator.data.channels[DP_CH1] = 10000
        assert channel1_number.native_value == pytest.approx(100.0)

    def test_native_value_precision(self, channel1_number, mock_coordinator):
        """Raw 5050 should display as 50.50%."""
        mock_coordinator.data.channels[DP_CH1] = 5050
        assert channel1_number.native_value == pytest.approx(50.50)

    def test_native_value_none_data(self, channel1_number, mock_coordinator):
        mock_coordinator.data = None
        assert channel1_number.native_value is None

    def test_min_max_step(self, channel1_number):
        assert channel1_number.native_min_value == pytest.approx(0.0)
        assert channel1_number.native_max_value == pytest.approx(100.0)
        assert channel1_number.native_step == pytest.approx(0.01)

    def test_unit(self, channel1_number):
        assert channel1_number.native_unit_of_measurement == "%"

    def test_channel_naming(self, channel1_number, channel6_number):
        assert channel1_number.name == "Channel 1"
        assert channel6_number.name == "Channel 6"

    def test_unique_ids(self, channel1_number, channel6_number):
        assert channel1_number.unique_id == "bf00000000000000test_ch1"
        assert channel6_number.unique_id == "bf00000000000000test_ch6"


class TestOrphekChannelNumberActions:
    """Tests for channel number entity write actions."""

    @pytest.mark.asyncio
    async def test_set_value(self, channel1_number, mock_coordinator):
        """Setting 50.0% should send raw value 5000."""
        await channel1_number.async_set_native_value(50.0)
        mock_coordinator.async_device_io.assert_called_once_with(
            mock_coordinator.device.set_channels, {DP_CH1: 5000}
        )
        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_zero(self, channel1_number, mock_coordinator):
        await channel1_number.async_set_native_value(0.0)
        mock_coordinator.async_device_io.assert_called_once_with(
            mock_coordinator.device.set_channels, {DP_CH1: 0}
        )

    @pytest.mark.asyncio
    async def test_set_max(self, channel1_number, mock_coordinator):
        await channel1_number.async_set_native_value(100.0)
        mock_coordinator.async_device_io.assert_called_once_with(
            mock_coordinator.device.set_channels, {DP_CH1: 10000}
        )

    @pytest.mark.asyncio
    async def test_set_fractional(self, channel1_number, mock_coordinator):
        """Setting 41.00% should send raw value 4100."""
        await channel1_number.async_set_native_value(41.00)
        mock_coordinator.async_device_io.assert_called_once_with(
            mock_coordinator.device.set_channels, {DP_CH1: 4100}
        )

    @pytest.mark.asyncio
    async def test_clamps_over_max(self, channel1_number, mock_coordinator):
        """Values over 100% should be clamped to CHANNEL_MAX."""
        await channel1_number.async_set_native_value(150.0)
        call_args = mock_coordinator.async_device_io.call_args[0]
        assert call_args[1][DP_CH1] == CHANNEL_MAX

    @pytest.mark.asyncio
    async def test_clamps_under_min(self, channel1_number, mock_coordinator):
        """Negative values should be clamped to CHANNEL_MIN."""
        await channel1_number.async_set_native_value(-5.0)
        call_args = mock_coordinator.async_device_io.call_args[0]
        assert call_args[1][DP_CH1] == CHANNEL_MIN

    @pytest.mark.asyncio
    async def test_set_channel6(self, channel6_number, mock_coordinator):
        """Channel 6 writes to DP_CH6."""
        await channel6_number.async_set_native_value(75.0)
        mock_coordinator.async_device_io.assert_called_once_with(
            mock_coordinator.device.set_channels, {DP_CH6: 7500}
        )


class TestAllChannelsCreated:
    """Verify all 6 channels are created with correct unique IDs."""

    def test_six_channels(self, mock_coordinator, mock_entry, device_info):
        entities = [
            OrphekChannelNumber(mock_coordinator, mock_entry, device_info, dp)
            for dp in DP_CHANNELS
        ]
        assert len(entities) == 6
        names = [e.name for e in entities]
        assert names == [
            "Channel 1", "Channel 2", "Channel 3",
            "Channel 4", "Channel 5", "Channel 6",
        ]
        unique_ids = [e.unique_id for e in entities]
        assert unique_ids == [
            "bf00000000000000test_ch1", "bf00000000000000test_ch2", "bf00000000000000test_ch3",
            "bf00000000000000test_ch4", "bf00000000000000test_ch5", "bf00000000000000test_ch6",
        ]
