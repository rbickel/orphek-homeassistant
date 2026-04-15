"""L3 full integration tests for the Orphek integration.

These tests exercise the complete lifecycle through HA's public interfaces:
  - Set up the integration via config entries
  - Assert entity state via hass.states
  - Perform service calls via hass.services
  - Verify device commands reach the mocked device layer

All device I/O and network calls are mocked; only the HA core event loop
and entity/coordinator machinery are real.
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock, call, patch

import pytest
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.orphek.api import OrphekConnectionError, OrphekState
from custom_components.orphek.const import (
    CHANNEL_MAX,
    DP_CHANNELS,
    DOMAIN,
)

from .conftest import (
    MOCK_CLOUD_DPS,
    MOCK_CONFIG_DATA,
    MOCK_DEVICE_ID,
    MOCK_HOST,
    make_mock_state,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _setup_mocks(
    state: OrphekState | None = None,
    cloud_dps: dict | None = None,
):
    """Return context managers that mock device + ATOP + schema layers."""
    mock_device = MagicMock()
    mock_device.host = MOCK_HOST
    mock_device.device_id = MOCK_DEVICE_ID
    mock_device.test_connection.return_value = True
    mock_device.get_state.return_value = state or make_mock_state()
    mock_device.close.return_value = None

    mock_atop = MagicMock()
    mock_atop.session_id = "mock_session_id_abc"
    mock_atop._request.return_value = {"success": True}
    mock_atop.get_device_dps.return_value = cloud_dps if cloud_dps is not None else MOCK_CLOUD_DPS
    mock_atop.get_device_schema.return_value = None
    mock_atop.close.return_value = None
    mock_atop._email = None
    mock_atop._password = None
    mock_atop._country_code = "1"

    patches = (
        patch("custom_components.orphek.OrphekDevice", return_value=mock_device),
        patch("custom_components.orphek.OrphekAtopApi", return_value=mock_atop),
        patch("custom_components.orphek.load_schema", return_value=None),
        patch("custom_components.orphek.list_known_products", return_value=[]),
        patch("custom_components.orphek.save_schema"),
    )
    return mock_device, mock_atop, patches


async def _setup_integration(
    hass: HomeAssistant,
    state: OrphekState | None = None,
    cloud_dps: dict | None = None,
):
    """Set up the Orphek integration and return (entry, mock_device, mock_atop)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCK_DEVICE_ID,
        data=MOCK_CONFIG_DATA,
    )
    entry.add_to_hass(hass)

    mock_device, mock_atop, patches = _setup_mocks(state, cloud_dps)

    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    return entry, mock_device, mock_atop


def _find_entity(hass: HomeAssistant, domain: str, suffix: str = "") -> str:
    """Find an entity ID by domain (and optional unique_id suffix)."""
    for state in hass.states.async_all(domain):
        if suffix and suffix not in state.entity_id:
            continue
        return state.entity_id
    raise AssertionError(
        f"No {domain} entity found with suffix '{suffix}'. "
        f"Available: {[s.entity_id for s in hass.states.async_all(domain)]}"
    )


# ---------------------------------------------------------------------------
# Light entity integration
# ---------------------------------------------------------------------------


class TestLightIntegration:
    """Full lifecycle tests for the Orphek light entity."""

    async def test_light_state_on(self, hass: HomeAssistant) -> None:
        """Light reports ON when device is on."""
        await _setup_integration(hass)
        entity_id = _find_entity(hass, "light")
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == STATE_ON

    async def test_light_state_off(self, hass: HomeAssistant) -> None:
        """Light reports OFF when device is off."""
        await _setup_integration(hass, make_mock_state(is_on=False))
        entity_id = _find_entity(hass, "light")
        state = hass.states.get(entity_id)
        assert state.state == STATE_OFF

    async def test_light_turn_on_service(self, hass: HomeAssistant) -> None:
        """Calling light.turn_on sends set_power(True) to device."""
        _, mock_device, _ = await _setup_integration(
            hass, make_mock_state(is_on=False)
        )
        entity_id = _find_entity(hass, "light")

        await hass.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )

        mock_device.set_power.assert_called_with(True)

    async def test_light_turn_off_service(self, hass: HomeAssistant) -> None:
        """Calling light.turn_off sends set_power(False) to device."""
        _, mock_device, _ = await _setup_integration(hass)
        entity_id = _find_entity(hass, "light")

        await hass.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )

        mock_device.set_power.assert_called_with(False)

    async def test_light_brightness_service(self, hass: HomeAssistant) -> None:
        """Setting brightness scales and passes to set_brightness."""
        _, mock_device, _ = await _setup_integration(hass)
        entity_id = _find_entity(hass, "light")

        await hass.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: entity_id, "brightness": 128},
            blocking=True,
        )

        # Verify set_brightness was called (not set_power)
        mock_device.set_brightness.assert_called_once()
        arg = mock_device.set_brightness.call_args[0][0]
        # 128/255 * 10000 ≈ 5020
        assert 4900 <= arg <= 5100

    async def test_light_effect_service(self, hass: HomeAssistant) -> None:
        """Setting an effect calls set_mode on the device."""
        _, mock_device, _ = await _setup_integration(hass)
        entity_id = _find_entity(hass, "light")

        await hass.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: entity_id, "effect": "Quick"},
            blocking=True,
        )

        mock_device.set_mode.assert_called_with("quick")

    async def test_light_brightness_attribute(self, hass: HomeAssistant) -> None:
        """Brightness attribute reflects channel max scaled to 0-255."""
        await _setup_integration(hass)
        entity_id = _find_entity(hass, "light")
        state = hass.states.get(entity_id)
        brightness = state.attributes.get("brightness")
        assert brightness is not None
        # Channels are 4100 each → max=4100 → 4100*255/10000 = 104.55 → ceil = 105
        expected = max(1, math.ceil(4100 * 255 / CHANNEL_MAX))
        assert brightness == expected


# ---------------------------------------------------------------------------
# Sensor entity integration
# ---------------------------------------------------------------------------


class TestSensorIntegration:
    """Full lifecycle tests for Orphek sensor entities."""

    async def test_temperature_sensor(self, hass: HomeAssistant) -> None:
        """Temperature sensor reports correct value."""
        await _setup_integration(hass, make_mock_state(temperature_c=32))
        # Find temperature sensor
        for state in hass.states.async_all("sensor"):
            if "temperature" in state.entity_id and "fahrenheit" not in state.entity_id and "unit" not in state.entity_id:
                assert state.state == "32"
                return
        pytest.fail("Temperature sensor not found")

    async def test_mode_running_sensor(self, hass: HomeAssistant) -> None:
        """Mode running sensor reports the current mode."""
        await _setup_integration(
            hass, make_mock_state(mode_running="jellyfish")
        )
        for state in hass.states.async_all("sensor"):
            if "mode" in state.entity_id:
                assert state.state == "jellyfish"
                return
        pytest.fail("Mode running sensor not found")


# ---------------------------------------------------------------------------
# Switch entity integration
# ---------------------------------------------------------------------------


class TestSwitchIntegration:
    """Full lifecycle tests for Orphek switch entities."""

    async def test_quiet_mode_switch_state(self, hass: HomeAssistant) -> None:
        """Quiet mode switch reflects device state."""
        await _setup_integration(hass, make_mock_state(quiet_mode=True))
        quiet = None
        for state in hass.states.async_all("switch"):
            if "quiet" in state.entity_id:
                quiet = state
                break
        assert quiet is not None
        assert quiet.state == STATE_ON

    async def test_quiet_mode_turn_on(self, hass: HomeAssistant) -> None:
        """Turning on quiet mode calls set_quiet_mode(True)."""
        _, mock_device, _ = await _setup_integration(hass)
        quiet_id = None
        for state in hass.states.async_all("switch"):
            if "quiet" in state.entity_id:
                quiet_id = state.entity_id
                break
        assert quiet_id is not None

        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: quiet_id},
            blocking=True,
        )

        mock_device.set_quiet_mode.assert_called_with(True)

    async def test_quiet_mode_turn_off(self, hass: HomeAssistant) -> None:
        """Turning off quiet mode calls set_quiet_mode(False)."""
        _, mock_device, _ = await _setup_integration(
            hass, make_mock_state(quiet_mode=True)
        )
        quiet_id = None
        for state in hass.states.async_all("switch"):
            if "quiet" in state.entity_id:
                quiet_id = state.entity_id
                break

        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: quiet_id},
            blocking=True,
        )

        mock_device.set_quiet_mode.assert_called_with(False)

    async def test_hour_system_switch(self, hass: HomeAssistant) -> None:
        """Hour system switch reflects state and sends commands."""
        _, mock_device, _ = await _setup_integration(hass)
        hour_id = None
        for state in hass.states.async_all("switch"):
            if "hour" in state.entity_id or "24" in state.entity_id or "clock" in state.entity_id:
                hour_id = state.entity_id
                break
        assert hour_id is not None

        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: hour_id},
            blocking=True,
        )

        mock_device.set_hour_system.assert_called_with(True)


# ---------------------------------------------------------------------------
# Number entity integration (channel control)
# ---------------------------------------------------------------------------


class TestNumberIntegration:
    """Full lifecycle tests for Orphek channel number entities."""

    async def test_channel_numbers_registered(self, hass: HomeAssistant) -> None:
        """Six channel number entities are created."""
        await _setup_integration(hass)
        numbers = hass.states.async_all("number")
        channel_numbers = [s for s in numbers if "channel" in s.entity_id or "ch" in s.entity_id]
        assert len(channel_numbers) == 6

    async def test_channel_value_reflects_state(self, hass: HomeAssistant) -> None:
        """Channel number entities reflect the device state (raw / 100)."""
        custom_channels = {103: 5000, 104: 3000, 105: 1000, 106: 0, 107: 0, 108: 0}
        # Cloud DPS must match to avoid cloud merge overwriting local values
        cloud_dps = {str(k): v for k, v in custom_channels.items()}
        await _setup_integration(
            hass,
            make_mock_state(channels=custom_channels),
            cloud_dps=cloud_dps,
        )
        numbers = hass.states.async_all("number")
        channel_states = sorted(
            [s for s in numbers if "channel" in s.entity_id or "ch" in s.entity_id],
            key=lambda s: s.entity_id,
        )
        # The first channel is 5000/100 = 50.0
        values = [float(s.state) for s in channel_states]
        assert 50.0 in values
        assert 30.0 in values

    async def test_set_channel_value(self, hass: HomeAssistant) -> None:
        """Setting a number value calls set_channels on the device."""
        _, mock_device, _ = await _setup_integration(hass)
        numbers = hass.states.async_all("number")
        channel_entities = sorted(
            [s for s in numbers if "channel" in s.entity_id or "ch" in s.entity_id],
            key=lambda s: s.entity_id,
        )
        assert len(channel_entities) > 0
        entity_id = channel_entities[0].entity_id

        await hass.services.async_call(
            NUMBER_DOMAIN,
            "set_value",
            {ATTR_ENTITY_ID: entity_id, "value": 75.0},
            blocking=True,
        )

        mock_device.set_channels.assert_called_once()
        # 75.0 * 100 = 7500
        args = mock_device.set_channels.call_args[0][0]
        assert any(v == 7500 for v in args.values())


# ---------------------------------------------------------------------------
# Select entity integration (mode & temp unit)
# ---------------------------------------------------------------------------


class TestSelectIntegration:
    """Full lifecycle tests for Orphek select entities."""

    async def test_mode_reflects_state(self, hass: HomeAssistant) -> None:
        """Mode select entity shows the current mode."""
        await _setup_integration(hass, make_mock_state(mode="quick"))
        for state in hass.states.async_all("select"):
            if "mode" in state.entity_id and "temp" not in state.entity_id:
                assert state.state == "Quick"
                return
        pytest.fail("Mode select entity not found")

    async def test_set_mode(self, hass: HomeAssistant) -> None:
        """Selecting a mode calls set_mode on the device."""
        _, mock_device, _ = await _setup_integration(hass)
        mode_id = None
        for state in hass.states.async_all("select"):
            if "mode" in state.entity_id and "temp" not in state.entity_id:
                mode_id = state.entity_id
                break
        assert mode_id is not None

        await hass.services.async_call(
            SELECT_DOMAIN,
            "select_option",
            {ATTR_ENTITY_ID: mode_id, "option": "Biorhythm"},
            blocking=True,
        )

        mock_device.set_mode.assert_called_with("biorhythm")

    async def test_temp_unit_reflects_state(self, hass: HomeAssistant) -> None:
        """Temperature unit select shows the current unit."""
        await _setup_integration(hass, make_mock_state(temp_unit="f"))
        for state in hass.states.async_all("select"):
            if "temp" in state.entity_id and "unit" in state.entity_id:
                assert "Fahrenheit" in state.state
                return
        pytest.fail("Temp unit select entity not found")


# ---------------------------------------------------------------------------
# Binary sensor integration (expansion modes)
# ---------------------------------------------------------------------------


class TestBinarySensorIntegration:
    """Full lifecycle tests for Orphek binary sensor entities."""

    async def test_binary_sensors_registered(self, hass: HomeAssistant) -> None:
        """Six binary sensor entities are created (one per expansion)."""
        await _setup_integration(hass)
        binary_sensors = hass.states.async_all("binary_sensor")
        assert len(binary_sensors) == 6

    async def test_binary_sensor_reflects_expansion_state(
        self, hass: HomeAssistant
    ) -> None:
        """Binary sensors reflect expansion enabled/disabled state."""
        from custom_components.orphek.api import JellyfishConfig

        state = make_mock_state()
        state.jellyfish = JellyfishConfig(enabled=True, speed=5, brightness=80)
        await _setup_integration(hass, state)

        for bs in hass.states.async_all("binary_sensor"):
            if "jellyfish" in bs.entity_id:
                assert bs.state == STATE_ON
                return
        pytest.fail("Jellyfish binary sensor not found")


# ---------------------------------------------------------------------------
# Coordinator integration (data refresh cycle)
# ---------------------------------------------------------------------------


class TestCoordinatorIntegration:
    """Tests for coordinator-level behaviour within a real HA instance."""

    async def test_device_goes_unavailable(self, hass: HomeAssistant) -> None:
        """When device raises ConnectionError, entities go unavailable."""
        entry, mock_device, _ = await _setup_integration(hass)

        # Now make device fail
        mock_device.get_state.side_effect = OrphekConnectionError("timeout")

        coordinator = entry.runtime_data
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        entity_id = _find_entity(hass, "light")
        state = hass.states.get(entity_id)
        assert state.state == "unavailable"

    async def test_state_update_propagates(self, hass: HomeAssistant) -> None:
        """New device state propagates to entity attributes after refresh."""
        entry, mock_device, mock_atop = await _setup_integration(hass)

        # Update both device mock AND cloud DPS to return new channel values
        new_channels = {103: 8000, 104: 6000, 105: 4000, 106: 2000, 107: 1000, 108: 500}
        new_state = make_mock_state(
            is_on=True,
            channels=new_channels,
            temperature_c=35,
        )
        mock_device.get_state.return_value = new_state
        new_cloud = {str(k): v for k, v in new_channels.items()}
        mock_atop.get_device_dps.return_value = new_cloud

        coordinator = entry.runtime_data
        # Also update the cached cloud DPS so the merge doesn't revert values
        coordinator._cloud_dps = new_cloud
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # Verify light brightness updated
        entity_id = _find_entity(hass, "light")
        state = hass.states.get(entity_id)
        brightness = state.attributes.get("brightness")
        expected = max(1, math.ceil(8000 * 255 / CHANNEL_MAX))
        assert brightness == expected

    async def test_cloud_dps_fetched_on_first_poll(
        self, hass: HomeAssistant
    ) -> None:
        """ATOP cloud DPS is fetched during setup (first coordinator refresh)."""
        _, _, mock_atop = await _setup_integration(hass)
        mock_atop.get_device_dps.assert_called()
