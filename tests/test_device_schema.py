"""Unit tests for the Orphek device schema persistence module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from custom_components.orphek.device_schema import (
    _DEVICES_DIR,
    get_channel_range,
    get_dp_info,
    get_enum_options,
    is_writable,
    list_known_products,
    load_schema,
    save_schema,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_SCHEMA = {
    "product_id": "eh4tcr8zsdshvdrl",
    "category": "dj",
    "category_code": "wf_ble_dj",
    "dps": {
        "20": {
            "code": "switch_led",
            "mode": "rw",
            "type": "bool",
            "property": {"type": "bool"},
        },
        "22": {
            "code": "bright_value",
            "mode": "rw",
            "type": "value",
            "property": {
                "type": "value",
                "min": 10,
                "max": 1000,
                "scale": 0,
                "step": 1,
                "unit": "",
            },
        },
        "101": {
            "code": "temp",
            "mode": "ro",
            "type": "value",
            "property": {
                "type": "value",
                "min": 0,
                "max": 100,
                "scale": 0,
                "step": 1,
                "unit": "℃",
            },
        },
        "103": {
            "code": "ch1",
            "mode": "rw",
            "type": "value",
            "property": {
                "type": "value",
                "min": 0,
                "max": 10000,
                "scale": 2,
                "step": 1,
                "unit": "%",
            },
        },
        "110": {
            "code": "mode",
            "mode": "rw",
            "type": "enum",
            "property": {
                "type": "enum",
                "range": ["program", "quick", "sun_moon_sync", "biorhythm"],
            },
        },
        "121": {
            "code": "model",
            "mode": "ro",
            "type": "enum",
            "property": {"type": "enum", "range": ["6-1"]},
        },
    },
}


@pytest.fixture
def tmp_devices_dir(tmp_path, monkeypatch):
    """Redirect the devices directory to a temporary path."""
    fake_dir = tmp_path / "devices"
    monkeypatch.setattr(
        "custom_components.orphek.device_schema._DEVICES_DIR", fake_dir
    )
    return fake_dir


# ---------------------------------------------------------------------------
# save_schema
# ---------------------------------------------------------------------------

class TestSaveSchema:
    def test_creates_directory_and_file(self, tmp_devices_dir):
        assert not tmp_devices_dir.exists()
        path = save_schema(SAMPLE_SCHEMA)
        assert tmp_devices_dir.is_dir()
        assert path.is_file()
        assert path.name == "eh4tcr8zsdshvdrl.json"

    def test_content_is_valid_json(self, tmp_devices_dir):
        save_schema(SAMPLE_SCHEMA)
        content = json.loads((tmp_devices_dir / "eh4tcr8zsdshvdrl.json").read_text())
        assert content["product_id"] == "eh4tcr8zsdshvdrl"
        assert "dps" in content

    def test_overwrites_existing(self, tmp_devices_dir):
        save_schema({"product_id": "p1", "dps": {}})
        save_schema({"product_id": "p1", "dps": {"1": {}}})
        content = json.loads((tmp_devices_dir / "p1.json").read_text())
        assert "1" in content["dps"]

    def test_returns_path(self, tmp_devices_dir):
        result = save_schema(SAMPLE_SCHEMA)
        assert isinstance(result, Path)
        assert result.stem == "eh4tcr8zsdshvdrl"

    def test_raises_on_empty_product_id(self, tmp_devices_dir):
        with pytest.raises(ValueError):
            save_schema({"product_id": "", "dps": {}})

    def test_raises_on_missing_product_id(self, tmp_devices_dir):
        with pytest.raises(ValueError):
            save_schema({"dps": {}})


# ---------------------------------------------------------------------------
# load_schema
# ---------------------------------------------------------------------------

class TestLoadSchema:
    def test_returns_none_when_missing(self, tmp_devices_dir):
        assert load_schema("nonexistent") is None

    def test_returns_saved_schema(self, tmp_devices_dir):
        save_schema(SAMPLE_SCHEMA)
        loaded = load_schema("eh4tcr8zsdshvdrl")
        assert loaded is not None
        assert loaded["product_id"] == SAMPLE_SCHEMA["product_id"]
        assert loaded["dps"]["103"]["code"] == "ch1"

    def test_returns_none_on_corrupt_json(self, tmp_devices_dir):
        tmp_devices_dir.mkdir(parents=True, exist_ok=True)
        (tmp_devices_dir / "bad.json").write_text("not json", encoding="utf-8")
        assert load_schema("bad") is None


# ---------------------------------------------------------------------------
# list_known_devices
# ---------------------------------------------------------------------------

class TestListKnownProducts:
    def test_empty_when_no_dir(self, tmp_devices_dir):
        assert list_known_products() == []

    def test_returns_product_ids(self, tmp_devices_dir):
        save_schema({"product_id": "prod_a", "dps": {}})
        save_schema({"product_id": "prod_b", "dps": {}})
        result = list_known_products()
        assert sorted(result) == ["prod_a", "prod_b"]

    def test_ignores_non_json(self, tmp_devices_dir):
        tmp_devices_dir.mkdir(parents=True, exist_ok=True)
        (tmp_devices_dir / "readme.txt").write_text("hi")
        save_schema(SAMPLE_SCHEMA)
        assert list_known_products() == ["eh4tcr8zsdshvdrl"]


# ---------------------------------------------------------------------------
# get_dp_info
# ---------------------------------------------------------------------------

class TestGetDpInfo:
    def test_existing_dp_by_int(self):
        info = get_dp_info(SAMPLE_SCHEMA, 20)
        assert info is not None
        assert info["code"] == "switch_led"

    def test_existing_dp_by_str(self):
        info = get_dp_info(SAMPLE_SCHEMA, "110")
        assert info is not None
        assert info["type"] == "enum"

    def test_missing_dp(self):
        assert get_dp_info(SAMPLE_SCHEMA, 999) is None

    def test_empty_schema(self):
        assert get_dp_info({}, 20) is None

    def test_schema_without_dps_key(self):
        assert get_dp_info({"product_id": "x"}, 20) is None


# ---------------------------------------------------------------------------
# get_channel_range
# ---------------------------------------------------------------------------

class TestGetChannelRange:
    def test_value_dp(self):
        min_val, max_val, scale = get_channel_range(SAMPLE_SCHEMA, 103)
        assert min_val == 0
        assert max_val == 10000
        assert scale == 100  # 10**2

    def test_brightness_dp(self):
        min_val, max_val, scale = get_channel_range(SAMPLE_SCHEMA, 22)
        assert min_val == 10
        assert max_val == 1000
        assert scale == 1  # 10**0

    def test_non_value_dp_returns_defaults(self):
        min_val, max_val, scale = get_channel_range(SAMPLE_SCHEMA, 110)
        from custom_components.orphek.const import CHANNEL_MAX, CHANNEL_MIN, CHANNEL_SCALE
        assert min_val == CHANNEL_MIN
        assert max_val == CHANNEL_MAX
        assert scale == CHANNEL_SCALE

    def test_missing_dp_returns_defaults(self):
        min_val, max_val, scale = get_channel_range(SAMPLE_SCHEMA, 999)
        from custom_components.orphek.const import CHANNEL_MAX, CHANNEL_MIN, CHANNEL_SCALE
        assert min_val == CHANNEL_MIN
        assert max_val == CHANNEL_MAX
        assert scale == CHANNEL_SCALE


# ---------------------------------------------------------------------------
# get_enum_options
# ---------------------------------------------------------------------------

class TestGetEnumOptions:
    def test_enum_dp(self):
        options = get_enum_options(SAMPLE_SCHEMA, 110)
        assert options == ["program", "quick", "sun_moon_sync", "biorhythm"]

    def test_non_enum_dp(self):
        assert get_enum_options(SAMPLE_SCHEMA, 20) == []

    def test_missing_dp(self):
        assert get_enum_options(SAMPLE_SCHEMA, 999) == []

    def test_enum_without_range(self):
        schema = {
            "dps": {
                "50": {
                    "code": "test",
                    "mode": "rw",
                    "type": "enum",
                    "property": {"type": "enum"},
                }
            }
        }
        assert get_enum_options(schema, 50) == []


# ---------------------------------------------------------------------------
# is_writable
# ---------------------------------------------------------------------------

class TestIsWritable:
    def test_rw_dp(self):
        assert is_writable(SAMPLE_SCHEMA, 20) is True
        assert is_writable(SAMPLE_SCHEMA, 103) is True
        assert is_writable(SAMPLE_SCHEMA, 110) is True

    def test_ro_dp(self):
        assert is_writable(SAMPLE_SCHEMA, 101) is False
        assert is_writable(SAMPLE_SCHEMA, 121) is False

    def test_missing_dp(self):
        assert is_writable(SAMPLE_SCHEMA, 999) is False

    def test_empty_schema(self):
        assert is_writable({}, 20) is False
