"""Shared test fixtures for Orphek entity tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.orphek.api import OrphekDevice, OrphekState
from custom_components.orphek.coordinator import OrphekCoordinator


@pytest.fixture
def mock_coordinator():
    """Create a mock OrphekCoordinator with a default OrphekState."""
    coord = MagicMock(spec=OrphekCoordinator)
    coord.data = OrphekState(
        is_on=True,
        channels={103: 4100, 104: 4100, 105: 4100, 106: 4100, 107: 4100, 108: 4100},
        mode="program",
        mode_running="program",
        temperature_c=28,
        temperature_f=82,
        temp_unit="c",
        quiet_mode=False,
        no_auto_switch=False,
        hour_system=False,
    )
    coord.device = MagicMock(spec=OrphekDevice)
    coord.async_device_io = AsyncMock()
    coord.async_request_refresh = AsyncMock()
    return coord


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.unique_id = "test_device_123"
    entry.title = "Orphek (192.168.1.100)"
    entry.runtime_data = None  # will be set per test
    return entry


@pytest.fixture
def device_info():
    """Create a DeviceInfo dict."""
    from homeassistant.helpers.device_registry import DeviceInfo
    return DeviceInfo(identifiers={("orphek", "test_device_123")})
