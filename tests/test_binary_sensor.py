"""Unit tests for Orphek binary sensor entities."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.orphek.api import (
    AcclimationConfig,
    BiorhythmConfig,
    JellyfishConfig,
    LunarConfig,
    OrphekState,
    SunMoonSyncConfig,
)
from custom_components.orphek.binary_sensor import OrphekBinarySensor


@pytest.fixture
def make_binary_sensor(mock_coordinator, mock_entry, device_info):
    """Factory to create an OrphekBinarySensor with a given state_key."""
    def _make(state_key, name="Test", icon="mdi:test"):
        return OrphekBinarySensor(
            mock_coordinator, mock_entry, device_info, state_key, name, icon
        )
    return _make


class TestOrphekBinarySensorJellyfish:
    """Tests for jellyfish binary sensor."""

    def test_enabled(self, make_binary_sensor, mock_coordinator):
        mock_coordinator.data.jellyfish = JellyfishConfig(enabled=True)
        sensor = make_binary_sensor("jellyfish_enabled", "Jellyfish")
        assert sensor.is_on is True

    def test_disabled(self, make_binary_sensor, mock_coordinator):
        mock_coordinator.data.jellyfish = JellyfishConfig(enabled=False)
        sensor = make_binary_sensor("jellyfish_enabled", "Jellyfish")
        assert sensor.is_on is False

    def test_none_data(self, make_binary_sensor, mock_coordinator):
        mock_coordinator.data = None
        sensor = make_binary_sensor("jellyfish_enabled", "Jellyfish")
        assert sensor.is_on is None


class TestOrphekBinarySensorClouds:
    """Tests for clouds binary sensor."""

    def test_enabled(self, make_binary_sensor, mock_coordinator):
        mock_coordinator.data.clouds_enabled = True
        sensor = make_binary_sensor("clouds_enabled", "Clouds")
        assert sensor.is_on is True

    def test_disabled(self, make_binary_sensor, mock_coordinator):
        mock_coordinator.data.clouds_enabled = False
        sensor = make_binary_sensor("clouds_enabled", "Clouds")
        assert sensor.is_on is False


class TestOrphekBinarySensorAcclimation:
    """Tests for acclimation binary sensor."""

    def test_enabled(self, make_binary_sensor, mock_coordinator):
        mock_coordinator.data.acclimation = AcclimationConfig(enabled=True)
        sensor = make_binary_sensor("acclimation_enabled", "Acclimation")
        assert sensor.is_on is True

    def test_disabled(self, make_binary_sensor, mock_coordinator):
        mock_coordinator.data.acclimation = AcclimationConfig(enabled=False)
        sensor = make_binary_sensor("acclimation_enabled", "Acclimation")
        assert sensor.is_on is False


class TestOrphekBinarySensorLunar:
    """Tests for lunar cycle binary sensor."""

    def test_enabled(self, make_binary_sensor, mock_coordinator):
        mock_coordinator.data.lunar = LunarConfig(enabled=True)
        sensor = make_binary_sensor("lunar_enabled", "Lunar")
        assert sensor.is_on is True

    def test_disabled(self, make_binary_sensor, mock_coordinator):
        mock_coordinator.data.lunar = LunarConfig(enabled=False)
        sensor = make_binary_sensor("lunar_enabled", "Lunar")
        assert sensor.is_on is False


class TestOrphekBinarySensorBiorhythm:
    """Tests for biorhythm binary sensor."""

    def test_enabled(self, make_binary_sensor, mock_coordinator):
        mock_coordinator.data.biorhythm = BiorhythmConfig(enabled=True)
        sensor = make_binary_sensor("biorhythm_enabled", "Biorhythm")
        assert sensor.is_on is True

    def test_disabled(self, make_binary_sensor, mock_coordinator):
        mock_coordinator.data.biorhythm = BiorhythmConfig(enabled=False)
        sensor = make_binary_sensor("biorhythm_enabled", "Biorhythm")
        assert sensor.is_on is False


class TestOrphekBinarySensorSunMoonSync:
    """Tests for sun moon sync binary sensor."""

    def test_enabled(self, make_binary_sensor, mock_coordinator):
        mock_coordinator.data.sun_moon_sync = SunMoonSyncConfig(enabled=True)
        sensor = make_binary_sensor("sun_moon_sync_enabled", "Sun Moon Sync")
        assert sensor.is_on is True

    def test_disabled(self, make_binary_sensor, mock_coordinator):
        mock_coordinator.data.sun_moon_sync = SunMoonSyncConfig(enabled=False)
        sensor = make_binary_sensor("sun_moon_sync_enabled", "Sun Moon Sync")
        assert sensor.is_on is False


class TestOrphekBinarySensorUniqueId:
    """Tests for binary sensor unique IDs."""

    def test_unique_id_format(self, make_binary_sensor):
        sensor = make_binary_sensor("jellyfish_enabled", "Jellyfish")
        assert sensor.unique_id == "bf00000000000000test_jellyfish_enabled"

    def test_different_keys_different_ids(self, make_binary_sensor):
        s1 = make_binary_sensor("jellyfish_enabled", "Jellyfish")
        s2 = make_binary_sensor("clouds_enabled", "Clouds")
        assert s1.unique_id != s2.unique_id
