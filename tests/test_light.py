"""Unit tests for Orphek light entity."""

from __future__ import annotations

import math

import pytest

from custom_components.orphek.const import CHANNEL_MAX, CHANNEL_MIN
from custom_components.orphek.light import (
    EFFECT_LIST,
    OrphekLight,
    _EFFECT_TO_MODE,
    _MODE_TO_EFFECT,
)


@pytest.fixture
def light_entity(mock_coordinator, mock_entry):
    """Create an OrphekLight entity for testing."""
    return OrphekLight(mock_coordinator, mock_entry)


class TestOrphekLightProperties:
    """Tests for light entity read properties."""

    def test_is_on(self, light_entity, mock_coordinator):
        assert light_entity.is_on is True
        mock_coordinator.data.is_on = False
        assert light_entity.is_on is False

    def test_is_on_none_data(self, light_entity, mock_coordinator):
        mock_coordinator.data = None
        assert light_entity.is_on is None

    def test_brightness_conversion(self, light_entity, mock_coordinator):
        """Brightness converts from 0-10000 channel range to 0-255 HA range."""
        mock_coordinator.data.channels = {103: 10000, 104: 5000, 105: 0, 106: 0, 107: 0, 108: 0}
        # brightness = max channel = 10000
        expected = max(1, math.ceil(10000 * 255 / CHANNEL_MAX))
        assert light_entity.brightness == expected
        assert light_entity.brightness == 255

    def test_brightness_half(self, light_entity, mock_coordinator):
        mock_coordinator.data.channels = {103: 5000, 104: 5000, 105: 0, 106: 0, 107: 0, 108: 0}
        expected = max(1, math.ceil(5000 * 255 / CHANNEL_MAX))
        assert light_entity.brightness == expected
        assert light_entity.brightness == 128  # ceil(127.5)

    def test_brightness_zero(self, light_entity, mock_coordinator):
        mock_coordinator.data.channels = {103: 0, 104: 0, 105: 0, 106: 0, 107: 0, 108: 0}
        assert light_entity.brightness == 0

    def test_brightness_none_when_off(self, light_entity, mock_coordinator):
        mock_coordinator.data.is_on = False
        assert light_entity.brightness is None

    def test_brightness_none_when_no_data(self, light_entity, mock_coordinator):
        mock_coordinator.data = None
        assert light_entity.brightness is None

    def test_effect(self, light_entity, mock_coordinator):
        mock_coordinator.data.mode = "program"
        assert light_entity.effect == "Program"
        mock_coordinator.data.mode = "sunMoonSync"
        assert light_entity.effect == "Sun Moon Sync"

    def test_effect_none_data(self, light_entity, mock_coordinator):
        mock_coordinator.data = None
        assert light_entity.effect is None

    def test_effect_list(self, light_entity):
        assert light_entity.effect_list == EFFECT_LIST
        assert len(EFFECT_LIST) == 4

    def test_extra_state_attributes(self, light_entity, mock_coordinator):
        mock_coordinator.data.channels = {103: 4100, 104: 3000, 105: 2000, 106: 1000, 107: 500, 108: 0}
        attrs = light_entity.extra_state_attributes
        assert attrs["ch1"] == 4100
        assert attrs["ch6"] == 0

    def test_extra_state_attributes_none(self, light_entity, mock_coordinator):
        mock_coordinator.data = None
        assert light_entity.extra_state_attributes == {}

    def test_unique_id(self, light_entity):
        assert light_entity.unique_id == "bf00000000000000test"


class TestOrphekLightActions:
    """Tests for light entity write actions."""

    @pytest.mark.asyncio
    async def test_turn_on_power(self, light_entity, mock_coordinator):
        await light_entity.async_turn_on()
        mock_coordinator.async_device_io.assert_called_once_with(
            mock_coordinator.device.set_power, True
        )
        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_on_brightness(self, light_entity, mock_coordinator):
        await light_entity.async_turn_on(brightness=128)
        expected_channel = max(CHANNEL_MIN, round(128 * CHANNEL_MAX / 255))
        mock_coordinator.async_device_io.assert_called_once_with(
            mock_coordinator.device.set_brightness, expected_channel
        )

    @pytest.mark.asyncio
    async def test_turn_on_effect(self, light_entity, mock_coordinator):
        await light_entity.async_turn_on(effect="Quick")
        mock_coordinator.async_device_io.assert_called_once_with(
            mock_coordinator.device.set_mode, "quick"
        )

    @pytest.mark.asyncio
    async def test_turn_off(self, light_entity, mock_coordinator):
        await light_entity.async_turn_off()
        mock_coordinator.async_device_io.assert_called_once_with(
            mock_coordinator.device.set_power, False
        )
        mock_coordinator.async_request_refresh.assert_called_once()


class TestEffectMappings:
    """Tests for effect/mode mapping dicts."""

    def test_all_effects_map_to_modes(self):
        for effect in EFFECT_LIST:
            assert effect in _EFFECT_TO_MODE

    def test_round_trip(self):
        for effect, mode in _EFFECT_TO_MODE.items():
            assert _MODE_TO_EFFECT[mode] == effect
