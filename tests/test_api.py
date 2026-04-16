"""Unit tests for the Orphek API client (local Tuya protocol + parsers)."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

import pytest

from custom_components.orphek.api import (
    AcclimationConfig,
    BiorhythmConfig,
    JellyfishConfig,
    LunarConfig,
    OrphekApiError,
    OrphekConnectionError,
    OrphekDevice,
    OrphekState,
    ScheduleSlot,
    SunMoonSyncConfig,
    _parse_acclimation,
    _parse_biorhythm,
    _parse_expansion_enabled,
    _parse_jellyfish,
    _parse_lunar,
    _parse_schedule,
    _parse_sun_moon_sync,
)
from custom_components.orphek.const import (
    CHANNEL_MAX,
    CHANNEL_MIN,
    DP_CH1,
    DP_CH2,
    DP_CH3,
    DP_CH4,
    DP_CH5,
    DP_CH6,
    DP_CHANNELS,
    DP_HOUR_SYSTEM,
    DP_MODE,
    DP_NO_AUTO_SWITCH,
    DP_QUIET_MODE,
    DP_SWITCH,
    DP_TEMP_UNIT,
)


# ---------------------------------------------------------------------------
# OrphekState
# ---------------------------------------------------------------------------

class TestOrphekState:
    """Tests for OrphekState dataclass."""

    def test_default_values(self):
        state = OrphekState()
        assert state.is_on is False
        assert state.channels == {}
        assert state.mode == ""
        assert state.temperature_c is None
        assert state.brightness == 0

    def test_brightness_is_max_channel(self):
        state = OrphekState(channels={103: 10, 104: 80, 105: 50})
        assert state.brightness == 80

    def test_brightness_all_zero(self):
        state = OrphekState(channels={103: 0, 104: 0})
        assert state.brightness == 0

    def test_brightness_empty_channels(self):
        state = OrphekState()
        assert state.brightness == 0


# ---------------------------------------------------------------------------
# Schedule parsing
# ---------------------------------------------------------------------------

class TestParseSchedule:
    """Tests for _parse_schedule."""

    def test_single_slot(self):
        # Hour=8, Min=30, channels=[10,20,30,40,50,60]
        data = bytes([8, 30, 10, 20, 30, 40, 50, 60])
        # Pad to end with 0xFF
        data += b"\xff" * 8
        b64 = base64.b64encode(data).decode()
        slots = _parse_schedule(b64)
        assert len(slots) == 1
        assert slots[0].hour == 8
        assert slots[0].minute == 30
        assert slots[0].channels == [10, 20, 30, 40, 50, 60]

    def test_multiple_slots(self):
        slot1 = bytes([6, 0, 10, 10, 10, 10, 10, 10])
        slot2 = bytes([12, 30, 50, 50, 50, 50, 50, 50])
        slot3 = bytes([18, 0, 20, 20, 20, 20, 20, 20])
        data = slot1 + slot2 + slot3 + b"\xff" * 8
        b64 = base64.b64encode(data).decode()
        slots = _parse_schedule(b64)
        assert len(slots) == 3
        assert slots[1].hour == 12
        assert slots[1].minute == 30

    def test_with_header(self):
        header = bytes([0x01, 0x02])
        slot = bytes([9, 15, 80, 70, 60, 50, 40, 30])
        data = header + slot + b"\xff" * 8
        b64 = base64.b64encode(data).decode()
        slots = _parse_schedule(b64, has_header=True)
        assert len(slots) == 1
        assert slots[0].hour == 9

    def test_empty_schedule(self):
        data = b"\xff" * 16
        b64 = base64.b64encode(data).decode()
        assert _parse_schedule(b64) == []

    def test_invalid_base64(self):
        assert _parse_schedule("not_valid_base64!!!") == []

    def test_empty_string(self):
        assert _parse_schedule("") == []

    def test_too_short_data(self):
        data = bytes([8, 30, 10])  # less than 8 bytes
        b64 = base64.b64encode(data).decode()
        assert _parse_schedule(b64) == []


# ---------------------------------------------------------------------------
# Expansion parsers
# ---------------------------------------------------------------------------

class TestParseExpansionEnabled:
    """Tests for _parse_expansion_enabled."""

    def test_enabled(self):
        b64 = base64.b64encode(bytes([1, 0, 0])).decode()
        assert _parse_expansion_enabled(b64) is True

    def test_disabled(self):
        b64 = base64.b64encode(bytes([0, 0, 0])).decode()
        assert _parse_expansion_enabled(b64) is False

    def test_empty(self):
        b64 = base64.b64encode(b"").decode()
        assert _parse_expansion_enabled(b64) is False

    def test_invalid(self):
        assert _parse_expansion_enabled("!!!") is False


class TestParseJellyfish:
    """Tests for _parse_jellyfish."""

    def test_full_data(self):
        # [enabled=1, speed=5, ?, ?, ?, brightness=80]
        data = bytes([1, 5, 0, 0, 0, 80])
        b64 = base64.b64encode(data).decode()
        jf = _parse_jellyfish(b64)
        assert jf.enabled is True
        assert jf.speed == 5
        assert jf.brightness == 80

    def test_disabled(self):
        data = bytes([0, 3, 0, 0, 0, 50])
        b64 = base64.b64encode(data).decode()
        jf = _parse_jellyfish(b64)
        assert jf.enabled is False

    def test_minimal_data(self):
        data = bytes([1])
        b64 = base64.b64encode(data).decode()
        jf = _parse_jellyfish(b64)
        assert jf.enabled is True
        assert jf.speed == 0
        assert jf.brightness == 0

    def test_invalid(self):
        jf = _parse_jellyfish("bad_data!!!")
        assert jf.enabled is False


class TestParseAcclimation:
    """Tests for _parse_acclimation."""

    def test_full_data(self):
        # [enabled=1, duration=14, start=30, target=100, ?, ?]
        data = bytes([1, 14, 30, 100, 0, 0])
        b64 = base64.b64encode(data).decode()
        acc = _parse_acclimation(b64)
        assert acc.enabled is True
        assert acc.duration_days == 14
        assert acc.start_pct == 30
        assert acc.target_pct == 100

    def test_disabled(self):
        data = bytes([0, 7, 50, 80])
        b64 = base64.b64encode(data).decode()
        acc = _parse_acclimation(b64)
        assert acc.enabled is False

    def test_invalid(self):
        acc = _parse_acclimation("!!!")
        assert acc.enabled is False
        assert acc.duration_days == 0


class TestParseLunar:
    """Tests for _parse_lunar."""

    def test_full_data(self):
        # [enabled=1, ?, ?, interval=28, ?, ?, ?, ?, max_brightness=52, ch1=10, ch2=20]
        data = bytes([1, 0, 0, 28, 0, 0, 0, 0, 52, 10, 20])
        b64 = base64.b64encode(data).decode()
        lunar = _parse_lunar(b64)
        assert lunar.enabled is True
        assert lunar.interval_days == 28
        assert lunar.max_brightness == pytest.approx(0.52)
        assert lunar.channel_maxes == [10, 20]

    def test_max_brightness_scaling(self):
        """Raw byte 100 should be 1.0%."""
        data = bytes([1, 0, 0, 14, 0, 0, 0, 0, 100])
        b64 = base64.b64encode(data).decode()
        lunar = _parse_lunar(b64)
        assert lunar.max_brightness == pytest.approx(1.0)

    def test_max_brightness_zero(self):
        data = bytes([1, 0, 0, 7, 0, 0, 0, 0, 0])
        b64 = base64.b64encode(data).decode()
        lunar = _parse_lunar(b64)
        assert lunar.max_brightness == pytest.approx(0.0)

    def test_disabled(self):
        data = bytes([0, 0, 0, 28, 0, 0, 0, 0, 52])
        b64 = base64.b64encode(data).decode()
        lunar = _parse_lunar(b64)
        assert lunar.enabled is False

    def test_invalid(self):
        lunar = _parse_lunar("!!!")
        assert lunar.enabled is False


class TestParseBiorhythm:
    """Tests for _parse_biorhythm."""

    def test_with_slots(self):
        # [enabled=1, ?, ?, weekday_mask=0b1111111, num_slots=2,
        #  slot1: flag=1, h=8, m=0, ch1-6=10..60
        #  slot2: flag=1, h=20, m=0, ch1-6=5..30]
        data = bytes([
            1, 0, 0, 0x7F, 2,
            1, 8, 0, 10, 20, 30, 40, 50, 60,
            1, 20, 0, 5, 10, 15, 20, 25, 30,
        ])
        b64 = base64.b64encode(data).decode()
        bio = _parse_biorhythm(b64)
        assert bio.enabled is True
        assert bio.weekday_mask == 0x7F
        assert len(bio.slots) == 2
        assert bio.slots[0].hour == 8
        assert bio.slots[1].hour == 20
        assert bio.slots[0].channels == [10, 20, 30, 40, 50, 60]

    def test_no_slots(self):
        data = bytes([1, 0, 0, 0x1F, 0])
        b64 = base64.b64encode(data).decode()
        bio = _parse_biorhythm(b64)
        assert bio.enabled is True
        assert bio.slots == []

    def test_minimal(self):
        data = bytes([0])
        b64 = base64.b64encode(data).decode()
        bio = _parse_biorhythm(b64)
        assert bio.enabled is False

    def test_invalid(self):
        bio = _parse_biorhythm("!!!")
        assert bio.enabled is False


class TestParseSunMoonSync:
    """Tests for _parse_sun_moon_sync."""

    def test_full_data(self):
        # [enabled=1, ?, ?, sunrise_h=6, sunrise_m=30, sunset_h=18, sunset_m=45, ...]
        data = bytes([1, 0, 0, 6, 30, 18, 45, 0])
        b64 = base64.b64encode(data).decode()
        sms = _parse_sun_moon_sync(b64)
        assert sms.enabled is True
        assert sms.sunrise_hour == 6
        assert sms.sunrise_minute == 30
        assert sms.sunset_hour == 18
        assert sms.sunset_minute == 45

    def test_disabled(self):
        data = bytes([0, 0, 0, 6, 30, 18, 45])
        b64 = base64.b64encode(data).decode()
        sms = _parse_sun_moon_sync(b64)
        assert sms.enabled is False

    def test_invalid(self):
        sms = _parse_sun_moon_sync("!!!")
        assert sms.enabled is False


# ---------------------------------------------------------------------------
# OrphekDevice
# ---------------------------------------------------------------------------

class TestOrphekDeviceInit:
    """Tests for OrphekDevice initialization."""

    def test_properties(self):
        dev = OrphekDevice("dev123", "192.168.1.1", "localkey")
        assert dev.device_id == "dev123"
        assert dev.host == "192.168.1.1"

    def test_no_device_on_init(self):
        dev = OrphekDevice("d", "h", "k")
        assert dev._device is None


class TestOrphekDeviceTestConnection:
    """Tests for OrphekDevice.test_connection."""

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_success(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_dev.status.return_value = {"dps": {"20": True}}
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        assert dev.test_connection() is True

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_no_dps_key(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_dev.status.return_value = {"error": "timeout"}
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        assert dev.test_connection() is False

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_none_response(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_dev.status.return_value = None
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        assert dev.test_connection() is False

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_exception(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_dev.status.side_effect = ConnectionError("timeout")
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        assert dev.test_connection() is False


class TestOrphekDeviceGetState:
    """Tests for OrphekDevice.get_state."""

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_basic_state(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_dev.status.return_value = {
            "dps": {
                "20": True,
                "101": 28,
                "103": 80,
                "104": 60,
                "105": 40,
                "106": 20,
                "107": 10,
                "108": 5,
                "110": "program",
                "122": "program",
                "123": False,
                "124": 82,
                "125": "c",
            }
        }
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        state = dev.get_state()

        assert state.is_on is True
        assert state.channels[103] == 80
        assert state.channels[108] == 5
        assert state.mode == "program"
        assert state.mode_running == "program"
        assert state.temperature_c == 28
        assert state.temperature_f == 82
        assert state.quiet_mode is False
        assert state.brightness == 80

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_none_response_raises(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_dev.status.return_value = None
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        with pytest.raises(OrphekConnectionError):
            dev.get_state()
        # Device should be reset
        assert dev._device is None

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_exception_raises(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_dev.status.side_effect = Exception("broken")
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        with pytest.raises(OrphekConnectionError):
            dev.get_state()

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_missing_dps_raises(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_dev.status.return_value = {"error": "no dps"}
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        with pytest.raises(OrphekConnectionError):
            dev.get_state()


class TestOrphekDeviceParseDps:
    """Tests for the static _parse_dps method."""

    def test_minimal_dps(self):
        state = OrphekDevice._parse_dps({"20": True})
        assert state.is_on is True
        assert state.channels[103] == 0  # default

    def test_quiet_mode(self):
        state = OrphekDevice._parse_dps({"123": True})
        assert state.quiet_mode is True

    def test_no_auto_switch(self):
        state = OrphekDevice._parse_dps({"120": True})
        assert state.no_auto_switch is True

    def test_hour_system(self):
        state = OrphekDevice._parse_dps({"119": True})
        assert state.hour_system is True

    def test_fault(self):
        state = OrphekDevice._parse_dps({"102": 3})
        assert state.fault == 3

    def test_schedule_parsed(self):
        slot = bytes([10, 0, 50, 50, 50, 50, 50, 50]) + b"\xff" * 8
        b64 = base64.b64encode(slot).decode()
        state = OrphekDevice._parse_dps({"111": b64})
        assert len(state.schedule) == 1
        assert state.schedule[0].hour == 10

    def test_expansion_parsed(self):
        jf_data = base64.b64encode(bytes([1, 3, 0, 0, 0, 90])).decode()
        state = OrphekDevice._parse_dps({"114": jf_data})
        assert state.jellyfish.enabled is True
        assert state.jellyfish.speed == 3

    def test_clouds_enabled(self):
        clouds_data = base64.b64encode(bytes([1, 0])).decode()
        state = OrphekDevice._parse_dps({"115": clouds_data})
        assert state.clouds_enabled is True


class TestOrphekDeviceSetPower:
    """Tests for OrphekDevice.set_power."""

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_turn_on(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        dev.set_power(True)
        mock_dev.set_value.assert_called_once_with(DP_SWITCH, True)

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_turn_off(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        dev.set_power(False)
        mock_dev.set_value.assert_called_once_with(DP_SWITCH, False)

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_error_resets_device(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_dev.set_value.side_effect = Exception("fail")
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        with pytest.raises(OrphekConnectionError):
            dev.set_power(True)
        assert dev._device is None


class TestOrphekDeviceSetBrightness:
    """Tests for OrphekDevice.set_brightness."""

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_scales_channels(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_dev.status.return_value = {
            "dps": {"103": "10000", "104": "5000", "105": "0", "106": "0", "107": "0", "108": "0"}
        }
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        dev.set_brightness(5000)

        call_args = mock_dev.set_multiple_values.call_args[0][0]
        assert call_args[DP_SWITCH] is True
        assert call_args[DP_CH1] == 5000   # 10000 * 0.5
        assert call_args[DP_CH2] == 2500   # 5000 * 0.5

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_clamps_to_max(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_dev.status.return_value = {
            "dps": {"103": "8000", "104": "0", "105": "0", "106": "0", "107": "0", "108": "0"}
        }
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        dev.set_brightness(20000)  # over CHANNEL_MAX

        call_args = mock_dev.set_multiple_values.call_args[0][0]
        assert all(
            CHANNEL_MIN <= call_args[dp] <= CHANNEL_MAX
            for dp in DP_CHANNELS
        )

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_all_zero_channels(self, mock_device_cls):
        """When all channels are 0, set_brightness sets all to target."""
        mock_dev = MagicMock()
        mock_dev.status.return_value = {
            "dps": {"103": "0", "104": "0", "105": "0", "106": "0", "107": "0", "108": "0"}
        }
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        dev.set_brightness(5000)

        call_args = mock_dev.set_multiple_values.call_args[0][0]
        for dp in DP_CHANNELS:
            assert call_args[dp] == 5000


class TestOrphekDeviceSetChannels:
    """Tests for OrphekDevice.set_channels."""

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_sets_values(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        dev.set_channels({DP_CH1: 80, DP_CH3: 60})

        call_args = mock_dev.set_multiple_values.call_args[0][0]
        assert call_args[DP_CH1] == 80
        assert call_args[DP_CH3] == 60

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_clamps_values(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        dev.set_channels({DP_CH1: 15000, DP_CH2: -10})

        call_args = mock_dev.set_multiple_values.call_args[0][0]
        assert call_args[DP_CH1] == CHANNEL_MAX
        assert call_args[DP_CH2] == CHANNEL_MIN

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_ignores_invalid_dps(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        dev.set_channels({999: 50})  # not a valid channel DP

        mock_dev.set_multiple_values.assert_not_called()

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_error_resets_device(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_dev.set_multiple_values.side_effect = Exception("fail")
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        with pytest.raises(OrphekConnectionError):
            dev.set_channels({DP_CH1: 50})
        assert dev._device is None


class TestOrphekDeviceSetMode:
    """Tests for OrphekDevice.set_mode."""

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_sets_mode(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        dev.set_mode("quick")
        mock_dev.set_value.assert_called_once_with(DP_MODE, "quick")


class TestOrphekDeviceSetQuietMode:
    """Tests for OrphekDevice.set_quiet_mode."""

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_enable(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        dev.set_quiet_mode(True)
        mock_dev.set_value.assert_called_once_with(DP_QUIET_MODE, True)

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_disable(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        dev.set_quiet_mode(False)
        mock_dev.set_value.assert_called_once_with(DP_QUIET_MODE, False)


class TestOrphekDeviceSetTempUnit:
    """Tests for OrphekDevice.set_temp_unit."""

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_set_celsius(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        dev.set_temp_unit("c")
        mock_dev.set_value.assert_called_once_with(DP_TEMP_UNIT, "c")

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_set_fahrenheit(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        dev.set_temp_unit("f")
        mock_dev.set_value.assert_called_once_with(DP_TEMP_UNIT, "f")

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_error_resets_device(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_dev.set_value.side_effect = Exception("fail")
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        with pytest.raises(OrphekConnectionError):
            dev.set_temp_unit("f")
        assert dev._device is None


class TestOrphekDeviceSetHourSystem:
    """Tests for OrphekDevice.set_hour_system."""

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_set_24h(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        dev.set_hour_system(True)
        mock_dev.set_value.assert_called_once_with(DP_HOUR_SYSTEM, True)

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_set_12h(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        dev.set_hour_system(False)
        mock_dev.set_value.assert_called_once_with(DP_HOUR_SYSTEM, False)


class TestOrphekDeviceSetNoAutoSwitch:
    """Tests for OrphekDevice.set_no_auto_switch."""

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_enable(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        dev.set_no_auto_switch(True)
        mock_dev.set_value.assert_called_once_with(DP_NO_AUTO_SWITCH, True)

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_disable(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        dev.set_no_auto_switch(False)
        mock_dev.set_value.assert_called_once_with(DP_NO_AUTO_SWITCH, False)


class TestOrphekDeviceClose:
    """Tests for OrphekDevice.close."""

    @patch("custom_components.orphek.api.tinytuya.Device")
    def test_close_resets_device(self, mock_device_cls):
        mock_dev = MagicMock()
        mock_device_cls.return_value = mock_dev

        dev = OrphekDevice("d", "h", "k")
        dev._get_device()  # create device
        assert dev._device is not None
        dev.close()
        assert dev._device is None
        mock_dev.close.assert_called_once()

    def test_close_when_no_device(self):
        dev = OrphekDevice("d", "h", "k")
        dev.close()  # should not raise
        assert dev._device is None


# ---------------------------------------------------------------------------
# update_state_from_cloud
# ---------------------------------------------------------------------------

class TestUpdateStateFromCloud:
    """Tests for OrphekDevice.update_state_from_cloud."""

    def test_updates_channels(self):
        state = OrphekState(channels={103: 0, 104: 0, 105: 0, 106: 0, 107: 0, 108: 0})
        OrphekDevice.update_state_from_cloud(state, {"103": 80, "104": 60})
        assert state.channels[103] == 80
        assert state.channels[104] == 60

    def test_updates_schedule(self):
        slot = bytes([10, 30, 50, 50, 50, 50, 50, 50]) + b"\xff" * 8
        b64 = base64.b64encode(slot).decode()
        state = OrphekState()
        OrphekDevice.update_state_from_cloud(state, {"111": b64})
        assert len(state.schedule) == 1
        assert state.schedule[0].hour == 10

    def test_updates_expansions(self):
        jf_data = base64.b64encode(bytes([1, 5, 0, 0, 0, 70])).decode()
        clouds_data = base64.b64encode(bytes([1])).decode()
        state = OrphekState()
        OrphekDevice.update_state_from_cloud(
            state, {"114": jf_data, "115": clouds_data}
        )
        assert state.jellyfish.enabled is True
        assert state.jellyfish.speed == 5
        assert state.clouds_enabled is True

    def test_updates_temp_f_when_local_missing(self):
        state = OrphekState(temperature_f=None)
        OrphekDevice.update_state_from_cloud(state, {"124": 82})
        assert state.temperature_f == 82

    def test_does_not_overwrite_local_temp_f(self):
        state = OrphekState(temperature_f=80)
        OrphekDevice.update_state_from_cloud(state, {"124": 82})
        assert state.temperature_f == 80  # local value preserved

    def test_empty_cloud_dps(self):
        state = OrphekState(is_on=True, channels={103: 50})
        OrphekDevice.update_state_from_cloud(state, {})
        assert state.channels[103] == 50  # unchanged

    def test_returns_state(self):
        state = OrphekState()
        result = OrphekDevice.update_state_from_cloud(state, {})
        assert result is state
