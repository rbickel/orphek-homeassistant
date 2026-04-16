"""Shared test fixtures for Orphek entity tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.orphek.api import OrphekDevice, OrphekState
from custom_components.orphek.const import (
    CONF_ATOP_COUNTRY_CODE,
    CONF_ATOP_EMAIL,
    CONF_ATOP_PASSWORD,
    CONF_ATOP_SESSION_ID,
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_LOCAL_KEY,
    CONF_PRODUCT_ID,
)
from custom_components.orphek.coordinator import OrphekCoordinator


# ---------------------------------------------------------------------------
# Canonical mock state — shared between L1 and L2/L3 tests
# ---------------------------------------------------------------------------

MOCK_DEVICE_ID = "bf00000000000000test"
MOCK_HOST = "192.168.1.100"
MOCK_LOCAL_KEY = "abcdef1234567890"
MOCK_PRODUCT_ID = "eh4tcr8zsdshvdrl"

MOCK_CONFIG_DATA = {
    CONF_HOST: MOCK_HOST,
    CONF_DEVICE_ID: MOCK_DEVICE_ID,
    CONF_LOCAL_KEY: MOCK_LOCAL_KEY,
    CONF_PRODUCT_ID: MOCK_PRODUCT_ID,
    CONF_ATOP_EMAIL: "test@orphek.com",
    CONF_ATOP_PASSWORD: "testpass123",
    CONF_ATOP_SESSION_ID: "mock_session_id_abc",
    CONF_ATOP_COUNTRY_CODE: "1",
}

MOCK_STATE = OrphekState(
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

MOCK_CLOUD_DPS = {
    "20": True,
    "103": 4100,
    "104": 4100,
    "105": 4100,
    "106": 4100,
    "107": 4100,
    "108": 4100,
    "110": "program",
}

MOCK_CLOUD_DEVICES = [
    {
        "devId": MOCK_DEVICE_ID,
        "localKey": MOCK_LOCAL_KEY,
        "ip": MOCK_HOST,
        "name": "Orphek OR4 Test",
        "productId": MOCK_PRODUCT_ID,
    }
]


def make_mock_state(**overrides) -> OrphekState:
    """Create a copy of MOCK_STATE with optional overrides."""
    import dataclasses

    return dataclasses.replace(MOCK_STATE, **overrides)


# ---------------------------------------------------------------------------
# L1 fixtures (unit tests — mock coordinator, no real hass)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_coordinator():
    """Create a mock OrphekCoordinator with a default OrphekState."""
    coord = MagicMock(spec=OrphekCoordinator)
    coord.data = make_mock_state()
    coord.device = MagicMock(spec=OrphekDevice)
    coord.async_device_io = AsyncMock()
    coord.async_request_refresh = AsyncMock()
    return coord


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.unique_id = MOCK_DEVICE_ID
    entry.title = f"Orphek ({MOCK_HOST})"
    entry.runtime_data = None  # will be set per test
    return entry


@pytest.fixture
def device_info():
    """Create a DeviceInfo dict."""
    from homeassistant.helpers.device_registry import DeviceInfo

    return DeviceInfo(identifiers={("orphek", MOCK_DEVICE_ID)})


# ---------------------------------------------------------------------------
# L2/L3 fixtures (real hass instance, mocked device layer)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in integration tests.

    This fixture is required by pytest-homeassistant-custom-component
    so that HA can discover integrations in the custom_components/ folder.
    Only needed for L2/L3 integration tests, not L1 unit tests.
    """
    yield
