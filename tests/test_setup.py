"""L2 integration tests for async_setup_entry / async_unload_entry.

Uses a real HomeAssistant instance with mocked device I/O and ATOP API.
Validates entry setup, coordinator initialization, entity registration,
and clean unload.
"""

from __future__ import annotations

import contextlib
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.orphek.api import (
    OrphekConnectionError,
    OrphekState,
)
from custom_components.orphek.const import DOMAIN

from .conftest import (
    MOCK_CLOUD_DPS,
    MOCK_CONFIG_DATA,
    MOCK_DEVICE_ID,
    MOCK_HOST,
    make_mock_state,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _patch_all(
    state: OrphekState | None = None,
    valid_session: bool = True,
    cloud_dps: dict | None = None,
    device_side_effect: Exception | None = None,
):
    """Single context manager that mocks device + ATOP + schema layers.

    Yields (mock_device, mock_atop).
    """
    mock_device = MagicMock()
    mock_device.host = MOCK_HOST
    mock_device.device_id = MOCK_DEVICE_ID
    mock_device.test_connection.return_value = True
    if device_side_effect:
        mock_device.get_state.side_effect = device_side_effect
    else:
        mock_device.get_state.return_value = state or make_mock_state()
    mock_device.close.return_value = None

    mock_atop = MagicMock()
    mock_atop.session_id = "mock_session_id_abc"
    mock_atop.get_device_dps.return_value = cloud_dps or MOCK_CLOUD_DPS
    mock_atop.get_device_schema.return_value = None
    mock_atop.close.return_value = None
    mock_atop._email = None
    mock_atop._password = None
    mock_atop._country_code = "1"
    if valid_session:
        mock_atop._request.return_value = {"success": True}
    else:
        mock_atop._request.return_value = {"success": False}
        mock_atop.login.return_value = True

    with (
        patch("custom_components.orphek.OrphekDevice", return_value=mock_device),
        patch("custom_components.orphek.OrphekAtopApi", return_value=mock_atop),
        patch("custom_components.orphek.load_schema", return_value=None),
        patch("custom_components.orphek.list_known_products", return_value=[]),
        patch("custom_components.orphek.save_schema"),
    ):
        yield mock_device, mock_atop


@contextlib.contextmanager
def _patch_device_only(state: OrphekState | None = None):
    """Patch only the device and schema layers (no ATOP)."""
    mock_device = MagicMock()
    mock_device.host = MOCK_HOST
    mock_device.device_id = MOCK_DEVICE_ID
    mock_device.test_connection.return_value = True
    mock_device.get_state.return_value = state or make_mock_state()
    mock_device.close.return_value = None

    with (
        patch("custom_components.orphek.OrphekDevice", return_value=mock_device),
        patch("custom_components.orphek.load_schema", return_value=None),
        patch("custom_components.orphek.list_known_products", return_value=[]),
        patch("custom_components.orphek.save_schema"),
    ):
        yield mock_device


# ---------------------------------------------------------------------------
# Setup tests
# ---------------------------------------------------------------------------


class TestSetupEntry:
    """Tests for async_setup_entry."""

    async def test_successful_setup(self, hass: HomeAssistant) -> None:
        """Entry loads and reaches LOADED state with all platforms."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=MOCK_DEVICE_ID,
            data=MOCK_CONFIG_DATA,
        )
        entry.add_to_hass(hass)

        with _patch_all():
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.LOADED
        assert entry.runtime_data is not None

    async def test_setup_creates_entities(self, hass: HomeAssistant) -> None:
        """Entry setup registers at least the light, sensor, and switch entities."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=MOCK_DEVICE_ID,
            data=MOCK_CONFIG_DATA,
        )
        entry.add_to_hass(hass)

        with _patch_all():
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

        states = hass.states.async_all()
        entity_domains = {s.domain for s in states}
        assert "light" in entity_domains
        assert "sensor" in entity_domains
        assert "switch" in entity_domains
        assert "number" in entity_domains
        assert "select" in entity_domains
        assert "binary_sensor" in entity_domains

    async def test_setup_without_atop(self, hass: HomeAssistant) -> None:
        """Entry without ATOP credentials still loads (local-only mode)."""
        data_no_atop = {
            "device_id": MOCK_DEVICE_ID,
            "host": MOCK_HOST,
            "local_key": "abcdef1234567890",
            "product_id": "",
        }

        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=MOCK_DEVICE_ID,
            data=data_no_atop,
        )
        entry.add_to_hass(hass)

        with _patch_device_only():
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.LOADED

    async def test_setup_device_offline(self, hass: HomeAssistant) -> None:
        """Device offline during first refresh -> entry is SETUP_RETRY."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=MOCK_DEVICE_ID,
            data=MOCK_CONFIG_DATA,
        )
        entry.add_to_hass(hass)

        with _patch_all(device_side_effect=OrphekConnectionError("offline")):
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.SETUP_RETRY

    async def test_setup_expired_session_relogins(
        self, hass: HomeAssistant
    ) -> None:
        """Expired ATOP session triggers re-login with stored password."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=MOCK_DEVICE_ID,
            data=MOCK_CONFIG_DATA,
        )
        entry.add_to_hass(hass)

        with _patch_all(valid_session=False) as (_, mock_atop):
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.LOADED
        mock_atop.login.assert_called_once()


# ---------------------------------------------------------------------------
# Unload tests
# ---------------------------------------------------------------------------


class TestUnloadEntry:
    """Tests for async_unload_entry."""

    async def test_unload_success(self, hass: HomeAssistant) -> None:
        """Unloading entry closes device and ATOP connections."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=MOCK_DEVICE_ID,
            data=MOCK_CONFIG_DATA,
        )
        entry.add_to_hass(hass)

        with _patch_all() as (mock_device, mock_atop):
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
            assert entry.state is ConfigEntryState.LOADED

            await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.NOT_LOADED
        mock_device.close.assert_called_once()

    async def test_unload_and_reload(self, hass: HomeAssistant) -> None:
        """Entry can be unloaded and reloaded cleanly."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=MOCK_DEVICE_ID,
            data=MOCK_CONFIG_DATA,
        )
        entry.add_to_hass(hass)

        with _patch_all():
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
            assert entry.state is ConfigEntryState.LOADED

            await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()
            assert entry.state is ConfigEntryState.NOT_LOADED

            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
            assert entry.state is ConfigEntryState.LOADED
