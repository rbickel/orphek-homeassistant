"""API client for Orphek OR4-iCon LED Bar using Tuya local protocol."""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass, field

import tinytuya

from .const import (
    CHANNEL_MAX,
    CHANNEL_MIN,
    DP_ACCLIMATION,
    DP_BIORHYTHM,
    DP_CHANNELS,
    DP_CH1,
    DP_CLOUDS,
    DP_FAULT,
    DP_HOUR_SYSTEM,
    DP_JELLYFISH,
    DP_LUNAR,
    DP_MODE,
    DP_MODE_RUNNING,
    DP_NO_AUTO_SWITCH,
    DP_PROGRAM_MODE,
    DP_PROGRAM_PRESET,
    DP_QUIET_MODE,
    DP_SUN_MOON_SYNC,
    DP_SWITCH,
    DP_TEMPERATURE_C,
    DP_TEMP_F,
    DP_TEMP_UNIT,
    TUYA_VERSION,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ScheduleSlot:
    """A single time-slot in a program schedule."""

    hour: int
    minute: int
    channels: list[int]  # 6 values, each 0-100


@dataclass
class JellyfishConfig:
    """Jellyfish expansion config."""

    enabled: bool = False
    speed: int = 0
    brightness: int = 0


@dataclass
class AcclimationConfig:
    """Acclimation expansion config."""

    enabled: bool = False
    duration_days: int = 0
    start_pct: int = 0
    target_pct: int = 0


@dataclass
class LunarConfig:
    """Lunar cycle expansion config."""

    enabled: bool = False
    interval_days: int = 0
    max_brightness: float = 0.0
    channel_maxes: list[int] = field(default_factory=list)


@dataclass
class BiorhythmConfig:
    """Biorhythm expansion config."""

    enabled: bool = False
    weekday_mask: int = 0  # 7-bit bitmask (bit 0 = Monday, etc.)
    slots: list[ScheduleSlot] = field(default_factory=list)


@dataclass
class SunMoonSyncConfig:
    """Sun/Moon sync expansion config."""

    enabled: bool = False
    sunrise_hour: int = 0
    sunrise_minute: int = 0
    sunset_hour: int = 0
    sunset_minute: int = 0


@dataclass
class OrphekState:
    """Full state of an Orphek light."""

    is_on: bool = False
    channels: dict[int, int] = field(default_factory=dict)  # DP 103-108, each 0-100
    mode: str = ""          # DP 110: program, quick, sunMoonSync, biorhythm
    mode_running: str = ""  # DP 122: actual running mode
    temperature_c: int | None = None    # DP 101
    temperature_f: int | None = None    # DP 124
    temp_unit: str = "c"    # DP 125: 'c' or 'f'
    fault: int = 0          # DP 102: fault bitmap
    quiet_mode: bool = False  # DP 123
    no_auto_switch: bool = False  # DP 120
    hour_system: bool = False  # DP 119: True = 24h, False = 12h

    # Schedule (parsed from DP 111)
    schedule: list[ScheduleSlot] = field(default_factory=list)
    # Preset schedule (parsed from DP 112)
    schedule_preset: list[ScheduleSlot] = field(default_factory=list)

    # Parsed expansion configs
    jellyfish: JellyfishConfig = field(default_factory=JellyfishConfig)
    clouds_enabled: bool = False
    acclimation: AcclimationConfig = field(default_factory=AcclimationConfig)
    lunar: LunarConfig = field(default_factory=LunarConfig)
    biorhythm: BiorhythmConfig = field(default_factory=BiorhythmConfig)
    sun_moon_sync: SunMoonSyncConfig = field(default_factory=SunMoonSyncConfig)

    @property
    def brightness(self) -> int:
        """Effective brightness = max channel value (0-100)."""
        return max(self.channels.values()) if self.channels else 0


class OrphekApiError(Exception):
    """Error communicating with the Orphek device."""


class OrphekConnectionError(OrphekApiError):
    """Error connecting to the Orphek device."""


def _parse_schedule(raw_b64: str, has_header: bool = False) -> list[ScheduleSlot]:
    """Parse a base64-encoded program schedule.

    Format: 8 bytes per slot [hour, minute, ch1, ch2, ch3, ch4, ch5, ch6].
    Padded with 0xFF. Optional 2-byte header (DP 112).
    """
    try:
        data = base64.b64decode(raw_b64)
    except Exception:
        return []
    i = 2 if has_header else 0
    slots: list[ScheduleSlot] = []
    while i + 7 < len(data):
        h, m = data[i], data[i + 1]
        if h == 0xFF:
            break
        chs = list(data[i + 2 : i + 8])
        slots.append(ScheduleSlot(hour=h, minute=m, channels=chs))
        i += 8
    return slots


def _parse_expansion_enabled(raw_b64: str) -> bool:
    """Check if an expansion mode is enabled (first byte)."""
    try:
        data = base64.b64decode(raw_b64)
        return bool(data[0]) if data else False
    except Exception:
        return False


def _parse_jellyfish(raw_b64: str) -> JellyfishConfig:
    """Parse jellyfish config: [enabled, speed, ?, ?, ?, brightness]."""
    try:
        data = base64.b64decode(raw_b64)
        return JellyfishConfig(
            enabled=bool(data[0]),
            speed=data[1] if len(data) > 1 else 0,
            brightness=data[5] if len(data) > 5 else 0,
        )
    except Exception:
        return JellyfishConfig()


def _parse_acclimation(raw_b64: str) -> AcclimationConfig:
    """Parse acclimation config: [enabled, duration_days, start_pct, target_pct, ?, ?]."""
    try:
        data = base64.b64decode(raw_b64)
        return AcclimationConfig(
            enabled=bool(data[0]),
            duration_days=data[1] if len(data) > 1 else 0,
            start_pct=data[2] if len(data) > 2 else 0,
            target_pct=data[3] if len(data) > 3 else 0,
        )
    except Exception:
        return AcclimationConfig()


def _parse_lunar(raw_b64: str) -> LunarConfig:
    """Parse lunar config: [enabled, ?, ?, interval_days, ?, ?, ?, ?, max_brightness, ch1-ch5 maxes].

    max_brightness raw byte is scaled by 100 (e.g. 52 = 0.52%).
    """
    try:
        data = base64.b64decode(raw_b64)
        return LunarConfig(
            enabled=bool(data[0]),
            interval_days=data[3] if len(data) > 3 else 0,
            max_brightness=data[8] / 100.0 if len(data) > 8 else 0.0,
            channel_maxes=list(data[9:]) if len(data) > 9 else [],
        )
    except Exception:
        return LunarConfig()


def _parse_biorhythm(raw_b64: str) -> BiorhythmConfig:
    """Parse biorhythm: [enabled, ?, ?, weekday_mask, num_slots, then per slot: flag, h, m, ch1-ch6]."""
    try:
        data = base64.b64decode(raw_b64)
        if len(data) < 5:
            return BiorhythmConfig(enabled=bool(data[0]) if data else False)
        config = BiorhythmConfig(
            enabled=bool(data[0]),
            weekday_mask=data[3],
        )
        num_slots = data[4]
        i = 5
        for _ in range(num_slots):
            if i + 8 >= len(data):
                break
            # flag, hour, minute, ch1-ch6
            h, m = data[i + 1], data[i + 2]
            chs = list(data[i + 3 : i + 9])
            config.slots.append(ScheduleSlot(hour=h, minute=m, channels=chs))
            i += 9
        return config
    except Exception:
        return BiorhythmConfig()


def _parse_sun_moon_sync(raw_b64: str) -> SunMoonSyncConfig:
    """Parse sun/moon sync: [enabled, ?, ?, sunrise_h, sunrise_m, sunset_h, sunset_m, ...]."""
    try:
        data = base64.b64decode(raw_b64)
        return SunMoonSyncConfig(
            enabled=bool(data[0]),
            sunrise_hour=data[3] if len(data) > 3 else 0,
            sunrise_minute=data[4] if len(data) > 4 else 0,
            sunset_hour=data[5] if len(data) > 5 else 0,
            sunset_minute=data[6] if len(data) > 6 else 0,
        )
    except Exception:
        return SunMoonSyncConfig()


class OrphekDevice:
    """Controls an Orphek OR4-iCon LED Bar via Tuya local protocol."""

    def __init__(self, device_id: str, host: str, local_key: str) -> None:
        self._device_id = device_id
        self._host = host
        self._local_key = local_key
        self._device: tinytuya.Device | None = None

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def host(self) -> str:
        return self._host

    def _get_device(self) -> tinytuya.Device:
        if self._device is None:
            self._device = tinytuya.Device(
                self._device_id, self._host, self._local_key, version=TUYA_VERSION
            )
            self._device.set_socketPersistent(True)
            self._device.set_socketRetryLimit(3)
            self._device.set_socketTimeout(5)
        return self._device

    def close(self) -> None:
        """Close the connection."""
        if self._device is not None:
            try:
                self._device.set_socketPersistent(False)
                self._device.close()
            except Exception:
                pass
            self._device = None

    def test_connection(self) -> bool:
        """Test if the device is reachable and responds."""
        try:
            status = self._get_device().status()
            ok = status is not None and "dps" in (status or {})
            if not ok:
                _LOGGER.error("Device %s returned unexpected status: %s", self._host, status)
            return ok
        except Exception as err:
            _LOGGER.error("Connection test failed for %s: %s", self._host, err)
            return False

    def get_state(self) -> OrphekState:
        """Get the current light state from local protocol.

        Returns basic state (power, channels, mode, temperature).
        Schedule and expansion data require cloud DPS (see update_state_from_cloud).
        """
        try:
            result = self._get_device().status()
        except Exception as err:
            self._device = None
            raise OrphekConnectionError(
                f"Error communicating with {self._host}: {err}"
            ) from err

        if result is None or "dps" not in result:
            self._device = None
            raise OrphekConnectionError(f"No response from {self._host}")

        return self._parse_dps(result["dps"])

    @staticmethod
    def _parse_dps(dps: dict) -> OrphekState:
        """Parse a DPS dict into an OrphekState."""

        def _get_dps_value(dp: int, default=None):
            """Return a DPS value for either string or integer DP keys."""
            if str(dp) in dps:
                return dps[str(dp)]
            if dp in dps:
                return dps[dp]
            return default

        channels = {dp: int(_get_dps_value(dp, 0)) for dp in DP_CHANNELS}

        # Parse schedules
        dp111 = _get_dps_value(DP_PROGRAM_MODE, "")
        dp112 = _get_dps_value(DP_PROGRAM_PRESET, "")
        schedule = _parse_schedule(dp111) if dp111 else []
        schedule_preset = _parse_schedule(dp112, has_header=True) if dp112 else []

        # Parse expansion enabled states
        dp114 = _get_dps_value(DP_JELLYFISH, "")
        dp115 = _get_dps_value(DP_CLOUDS, "")
        dp116 = _get_dps_value(DP_ACCLIMATION, "")
        dp117 = _get_dps_value(DP_LUNAR, "")
        dp126 = _get_dps_value(DP_BIORHYTHM, "")
        dp127 = _get_dps_value(DP_SUN_MOON_SYNC, "")

        temp_c = _get_dps_value(DP_TEMPERATURE_C)
        temp_f = _get_dps_value(DP_TEMP_F)

        return OrphekState(
            is_on=bool(_get_dps_value(DP_SWITCH, False)),
            channels=channels,
            mode=str(_get_dps_value(DP_MODE, "")),
            mode_running=str(_get_dps_value(DP_MODE_RUNNING, "")),
            temperature_c=int(temp_c) if temp_c is not None else None,
            temperature_f=int(temp_f) if temp_f is not None else None,
            temp_unit=str(_get_dps_value(DP_TEMP_UNIT, "c")),
            fault=int(_get_dps_value(DP_FAULT, 0)),
            quiet_mode=bool(_get_dps_value(DP_QUIET_MODE, False)),
            no_auto_switch=bool(_get_dps_value(DP_NO_AUTO_SWITCH, False)),
            hour_system=bool(_get_dps_value(DP_HOUR_SYSTEM, False)),
            schedule=schedule,
            schedule_preset=schedule_preset,
            jellyfish=_parse_jellyfish(dp114) if dp114 else JellyfishConfig(),
            clouds_enabled=_parse_expansion_enabled(dp115),
            acclimation=_parse_acclimation(dp116) if dp116 else AcclimationConfig(),
            lunar=_parse_lunar(dp117) if dp117 else LunarConfig(),
            biorhythm=_parse_biorhythm(dp126) if dp126 else BiorhythmConfig(),
            sun_moon_sync=_parse_sun_moon_sync(dp127) if dp127 else SunMoonSyncConfig(),
        )

    @staticmethod
    def update_state_from_cloud(state: OrphekState, cloud_dps: dict) -> OrphekState:
        """Merge cloud DPS into an existing state.

        Cloud DPS provides schedule/expansion data not available locally.
        Local values (channels, mode, power) are preferred when already set.
        """
        # Update channels and basic state from cloud if local has zeros
        # (local is authoritative when device is responding)
        for dp in DP_CHANNELS:
            cloud_val = cloud_dps.get(str(dp))
            if cloud_val is not None:
                state.channels[dp] = int(cloud_val)

        # Update fields only available from cloud
        dp111 = cloud_dps.get(str(DP_PROGRAM_MODE), "")
        dp112 = cloud_dps.get(str(DP_PROGRAM_PRESET), "")
        if dp111:
            state.schedule = _parse_schedule(dp111)
        if dp112:
            state.schedule_preset = _parse_schedule(dp112, has_header=True)

        dp114 = cloud_dps.get(str(DP_JELLYFISH), "")
        dp115 = cloud_dps.get(str(DP_CLOUDS), "")
        dp116 = cloud_dps.get(str(DP_ACCLIMATION), "")
        dp117 = cloud_dps.get(str(DP_LUNAR), "")
        dp126 = cloud_dps.get(str(DP_BIORHYTHM), "")
        dp127 = cloud_dps.get(str(DP_SUN_MOON_SYNC), "")

        if dp114:
            state.jellyfish = _parse_jellyfish(dp114)
        if dp115:
            state.clouds_enabled = _parse_expansion_enabled(dp115)
        if dp116:
            state.acclimation = _parse_acclimation(dp116)
        if dp117:
            state.lunar = _parse_lunar(dp117)
        if dp126:
            state.biorhythm = _parse_biorhythm(dp126)
        if dp127:
            state.sun_moon_sync = _parse_sun_moon_sync(dp127)

        # Temperature from cloud if not available locally
        temp_f = cloud_dps.get(str(DP_TEMP_F))
        if temp_f is not None and state.temperature_f is None:
            state.temperature_f = int(temp_f)

        return state

    def set_power(self, on: bool) -> None:
        """Turn the light on or off."""
        try:
            self._get_device().set_value(DP_SWITCH, on)
        except Exception as err:
            self._device = None
            raise OrphekConnectionError(
                f"Error sending command to {self._host}: {err}"
            ) from err

    def set_brightness(self, brightness: int) -> None:
        """Set brightness by scaling all channels proportionally.

        brightness: target max channel value (0-10000, scale=2).
        """
        brightness = max(CHANNEL_MIN, min(CHANNEL_MAX, brightness))
        try:
            dev = self._get_device()
            status = dev.status()
            dps = (status or {}).get("dps", {})
            current = {dp: int(dps.get(str(dp), 0)) for dp in DP_CHANNELS}
            current_max = max(current.values()) if current else 0

            values: dict[int | str, bool | int] = {DP_SWITCH: True}
            if current_max > 0 and brightness > 0:
                scale = brightness / current_max
                for dp in DP_CHANNELS:
                    values[dp] = max(CHANNEL_MIN, min(CHANNEL_MAX, round(current[dp] * scale)))
            else:
                for dp in DP_CHANNELS:
                    values[dp] = brightness
            dev.set_multiple_values(values)
        except Exception as err:
            self._device = None
            raise OrphekConnectionError(
                f"Error sending command to {self._host}: {err}"
            ) from err

    def set_channels(self, channel_values: dict[int, int]) -> None:
        """Set individual channel values. Keys are DP numbers (103-108)."""
        try:
            values: dict[int | str, int] = {}
            for dp, val in channel_values.items():
                if dp in DP_CHANNELS:
                    values[dp] = max(CHANNEL_MIN, min(CHANNEL_MAX, val))
            if values:
                self._get_device().set_multiple_values(values)
        except Exception as err:
            self._device = None
            raise OrphekConnectionError(
                f"Error sending command to {self._host}: {err}"
            ) from err

    def set_mode(self, mode: str) -> None:
        """Set the operating mode (program, quick, sunMoonSync, biorhythm)."""
        try:
            self._get_device().set_value(DP_MODE, mode)
        except Exception as err:
            self._device = None
            raise OrphekConnectionError(
                f"Error sending command to {self._host}: {err}"
            ) from err

    def set_quiet_mode(self, quiet: bool) -> None:
        """Set quiet/silent fan mode."""
        try:
            self._get_device().set_value(DP_QUIET_MODE, quiet)
        except Exception as err:
            self._device = None
            raise OrphekConnectionError(
                f"Error sending command to {self._host}: {err}"
            ) from err

    def set_temp_unit(self, unit: str) -> None:
        """Set temperature display unit ('c' or 'f')."""
        try:
            self._get_device().set_value(DP_TEMP_UNIT, unit)
        except Exception as err:
            self._device = None
            raise OrphekConnectionError(
                f"Error sending command to {self._host}: {err}"
            ) from err

    def set_hour_system(self, is_24h: bool) -> None:
        """Set hour system (True = 24h, False = 12h)."""
        try:
            self._get_device().set_value(DP_HOUR_SYSTEM, is_24h)
        except Exception as err:
            self._device = None
            raise OrphekConnectionError(
                f"Error sending command to {self._host}: {err}"
            ) from err

    def set_no_auto_switch(self, disabled: bool) -> None:
        """Set no-auto-switch / disable auto-recovery."""
        try:
            self._get_device().set_value(DP_NO_AUTO_SWITCH, disabled)
        except Exception as err:
            self._device = None
            raise OrphekConnectionError(
                f"Error sending command to {self._host}: {err}"
            ) from err
