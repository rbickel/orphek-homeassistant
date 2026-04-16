"""L2 integration tests for the Orphek config flow.

Uses a real HomeAssistant instance (via pytest-homeassistant-custom-component)
with mocked device I/O and ATOP API, testing the config flow end-to-end through
HA's config entry machinery.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.orphek.const import DOMAIN

from .conftest import (
    MOCK_CLOUD_DEVICES,
    MOCK_CONFIG_DATA,
    MOCK_DEVICE_ID,
    MOCK_HOST,
    MOCK_LOCAL_KEY,
    MOCK_PRODUCT_ID,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_DISCOVERED_DEVICE = MagicMock()
MOCK_DISCOVERED_DEVICE.device_id = MOCK_DEVICE_ID
MOCK_DISCOVERED_DEVICE.ip = MOCK_HOST


def _make_atop_mock(logged_in: bool = True):
    """Build a mock OrphekAtopApi."""
    atop = MagicMock()
    atop.login.return_value = logged_in
    atop.session_id = "mock_session_id_abc" if logged_in else None
    atop.get_devices.return_value = MOCK_CLOUD_DEVICES
    atop.get_device_schema.return_value = {
        "product_id": MOCK_PRODUCT_ID,
        "category_code": "wf_ble_dj",
    }
    return atop


# ---------------------------------------------------------------------------
# Config flow: orphek_login step
# ---------------------------------------------------------------------------


class TestConfigFlowLogin:
    """Tests for the orphek_login config flow step."""

    async def test_show_form(self, hass: HomeAssistant) -> None:
        """First call shows the login form."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "orphek_login"

    async def test_login_failure(self, hass: HomeAssistant) -> None:
        """Invalid credentials show an error."""
        atop = _make_atop_mock(logged_in=False)

        with (
            patch(
                "custom_components.orphek.config_flow.OrphekAtopApi",
                return_value=atop,
            ),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": "user"}
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={
                    "email": "bad@example.com",
                    "password": "wrong",
                    "country_code": "1",
                },
            )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}

    async def test_single_device_creates_entry(
        self, hass: HomeAssistant
    ) -> None:
        """Login with one device discovered creates entry immediately."""
        atop = _make_atop_mock()

        with (
            patch(
                "custom_components.orphek.config_flow.OrphekAtopApi",
                return_value=atop,
            ),
            patch(
                "custom_components.orphek.config_flow.discover_orphek_devices",
                return_value=[MOCK_DISCOVERED_DEVICE],
            ),
            patch(
                "custom_components.orphek.config_flow.load_schema",
                return_value=None,
            ),
            patch(
                "custom_components.orphek.config_flow.list_known_products",
                return_value=[],
            ),
            patch(
                "custom_components.orphek.config_flow.save_schema",
            ),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": "user"}
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={
                    "email": "test@orphek.com",
                    "password": "testpass123",
                    "country_code": "1",
                },
            )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == f"Orphek ({MOCK_HOST})"
        assert result["data"]["device_id"] == MOCK_DEVICE_ID
        assert result["data"]["local_key"] == MOCK_LOCAL_KEY
        assert result["data"]["atop_email"] == "test@orphek.com"
        assert result["data"]["atop_session_id"] == "mock_session_id_abc"

    async def test_no_devices_found(self, hass: HomeAssistant) -> None:
        """Login succeeds but no devices on LAN → abort."""
        atop = _make_atop_mock()
        atop.get_devices.return_value = []

        with (
            patch(
                "custom_components.orphek.config_flow.OrphekAtopApi",
                return_value=atop,
            ),
            patch(
                "custom_components.orphek.config_flow.discover_orphek_devices",
                return_value=[],
            ),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": "user"}
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={
                    "email": "test@orphek.com",
                    "password": "testpass123",
                    "country_code": "1",
                },
            )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "no_devices_found"

    async def test_multiple_devices_show_picker(
        self, hass: HomeAssistant
    ) -> None:
        """Multiple devices → show device picker form."""
        second_device = MagicMock()
        second_device.device_id = "second_device_id_00"
        second_device.ip = "192.168.1.200"

        cloud_devices = MOCK_CLOUD_DEVICES + [
            {
                "devId": "second_device_id_00",
                "localKey": "key2key2key2key2",
                "ip": "192.168.1.200",
                "name": "Orphek #2",
                "productId": MOCK_PRODUCT_ID,
            }
        ]

        atop = _make_atop_mock()
        atop.get_devices.return_value = cloud_devices

        with (
            patch(
                "custom_components.orphek.config_flow.OrphekAtopApi",
                return_value=atop,
            ),
            patch(
                "custom_components.orphek.config_flow.discover_orphek_devices",
                return_value=[MOCK_DISCOVERED_DEVICE, second_device],
            ),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": "user"}
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={
                    "email": "test@orphek.com",
                    "password": "testpass123",
                    "country_code": "1",
                },
            )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "discover"

    async def test_duplicate_device_skipped(self, hass: HomeAssistant) -> None:
        """Already-configured device is skipped; result is abort if no new ones."""
        # Pre-add an existing entry
        existing = MockConfigEntry(
            domain=DOMAIN,
            unique_id=MOCK_DEVICE_ID,
            data=MOCK_CONFIG_DATA,
        )
        existing.add_to_hass(hass)

        atop = _make_atop_mock()

        with (
            patch(
                "custom_components.orphek.config_flow.OrphekAtopApi",
                return_value=atop,
            ),
            patch(
                "custom_components.orphek.config_flow.discover_orphek_devices",
                return_value=[MOCK_DISCOVERED_DEVICE],
            ),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": "user"}
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={
                    "email": "test@orphek.com",
                    "password": "testpass123",
                    "country_code": "1",
                },
            )

        assert result["type"] is FlowResultType.ABORT


# ---------------------------------------------------------------------------
# Config flow: discover (device picker) step
# ---------------------------------------------------------------------------


class TestConfigFlowDiscover:
    """Tests for the discover step when multiple devices are found."""

    async def _init_flow_to_discover(self, hass: HomeAssistant, atop, devices, cloud_devices):
        """Helper: drive the flow to the discover step."""
        atop.get_devices.return_value = cloud_devices

        with (
            patch(
                "custom_components.orphek.config_flow.OrphekAtopApi",
                return_value=atop,
            ),
            patch(
                "custom_components.orphek.config_flow.discover_orphek_devices",
                return_value=devices,
            ),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": "user"}
            )
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={
                    "email": "test@orphek.com",
                    "password": "testpass123",
                    "country_code": "1",
                },
            )
        return result

    async def test_select_device_creates_entry(self, hass: HomeAssistant) -> None:
        """Selecting a device from the picker creates a config entry."""
        second_device = MagicMock()
        second_device.device_id = "second_device_id_00"
        second_device.ip = "192.168.1.200"

        cloud_devices = MOCK_CLOUD_DEVICES + [
            {
                "devId": "second_device_id_00",
                "localKey": "key2key2key2key2",
                "ip": "192.168.1.200",
            }
        ]

        atop = _make_atop_mock()
        result = await self._init_flow_to_discover(
            hass, atop, [MOCK_DISCOVERED_DEVICE, second_device], cloud_devices
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "discover"

        # Now select the first device
        with (
            patch(
                "custom_components.orphek.config_flow._test_device",
                return_value=True,
            ),
            patch(
                "custom_components.orphek.config_flow.load_schema",
                return_value=None,
            ),
            patch(
                "custom_components.orphek.config_flow.list_known_products",
                return_value=[],
            ),
            patch(
                "custom_components.orphek.config_flow.save_schema",
            ),
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={"devices": MOCK_DEVICE_ID},
            )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"]["device_id"] == MOCK_DEVICE_ID

    async def test_select_device_connection_failed(self, hass: HomeAssistant) -> None:
        """Connection failure shows an error on the picker form."""
        second_device = MagicMock()
        second_device.device_id = "second_device_id_00"
        second_device.ip = "192.168.1.200"

        cloud_devices = MOCK_CLOUD_DEVICES + [
            {
                "devId": "second_device_id_00",
                "localKey": "key2key2key2key2",
                "ip": "192.168.1.200",
            }
        ]

        atop = _make_atop_mock()
        result = await self._init_flow_to_discover(
            hass, atop, [MOCK_DISCOVERED_DEVICE, second_device], cloud_devices
        )

        with patch(
            "custom_components.orphek.config_flow._test_device",
            return_value=False,
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={"devices": MOCK_DEVICE_ID},
            )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


# ---------------------------------------------------------------------------
# Config flow: reauth
# ---------------------------------------------------------------------------


class TestConfigFlowReauth:
    """Tests for the re-authentication flow."""

    async def test_reauth_success(self, hass: HomeAssistant) -> None:
        """Successful reauth updates the config entry and reloads."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=MOCK_DEVICE_ID,
            data=MOCK_CONFIG_DATA,
        )
        entry.add_to_hass(hass)

        result = await entry.start_reauth_flow(hass)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

        new_atop = MagicMock()
        new_atop.login.return_value = True
        new_atop.session_id = "fresh_session_xyz"

        with patch(
            "custom_components.orphek.config_flow.OrphekAtopApi",
            return_value=new_atop,
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={
                    "email": "test@orphek.com",
                    "password": "newpass456",
                },
            )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reauth_successful"
        assert entry.data["atop_session_id"] == "fresh_session_xyz"

    async def test_reauth_invalid_credentials(self, hass: HomeAssistant) -> None:
        """Failed reauth shows error."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=MOCK_DEVICE_ID,
            data=MOCK_CONFIG_DATA,
        )
        entry.add_to_hass(hass)

        result = await entry.start_reauth_flow(hass)

        bad_atop = MagicMock()
        bad_atop.login.return_value = False

        with patch(
            "custom_components.orphek.config_flow.OrphekAtopApi",
            return_value=bad_atop,
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={
                    "email": "test@orphek.com",
                    "password": "wrongpass",
                },
            )

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}
