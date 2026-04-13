"""Product schema persistence for Orphek integration.

Schemas are keyed by **product_id** (Tuya product model), not by physical
device ID.  All devices of the same model share the same schema, so the
files in ``custom_components/orphek/devices/<product_id>.json`` can be
committed to the repository and will work for every user who owns that model.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Directory next to this file: custom_components/orphek/devices/
_DEVICES_DIR = Path(__file__).parent / "devices"


def _ensure_dir() -> Path:
    """Create the devices directory if it doesn't exist."""
    _DEVICES_DIR.mkdir(parents=True, exist_ok=True)
    return _DEVICES_DIR


def save_schema(schema: dict[str, Any]) -> Path:
    """Persist a product schema to disk, keyed by product_id.

    Returns the path to the saved file.
    """
    product_id = schema.get("product_id", "")
    if not product_id:
        raise ValueError("Schema must contain a non-empty 'product_id'")
    path = _ensure_dir() / f"{product_id}.json"
    path.write_text(json.dumps(schema, indent=2, sort_keys=True), encoding="utf-8")
    _LOGGER.info("Saved product schema to %s", path)
    return path


def load_schema(product_id: str) -> dict[str, Any] | None:
    """Load a previously saved product schema.

    Returns None if no schema file exists.
    """
    path = _DEVICES_DIR / f"{product_id}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as err:
        _LOGGER.warning("Failed to load schema from %s: %s", path, err)
        return None


def list_known_products() -> list[str]:
    """Return product IDs for which we have stored schemas."""
    if not _DEVICES_DIR.is_dir():
        return []
    return [p.stem for p in _DEVICES_DIR.glob("*.json")]


def get_dp_info(schema: dict[str, Any], dp_id: int | str) -> dict[str, Any] | None:
    """Look up a single DP definition in a schema.

    Returns a dict like::

        {"code": "mode", "mode": "rw", "type": "enum",
         "property": {"range": ["program", "quick", ...], "type": "enum"}}

    or None if the DP is not in the schema.
    """
    dps = schema.get("dps", {})
    return dps.get(str(dp_id))


def get_channel_range(schema: dict[str, Any], dp_id: int | str) -> tuple[int, int, int]:
    """Return (min, max, scale) for a value-type DP from the schema.

    Falls back to integration defaults if the DP is missing or not a value type.
    """
    from .const import CHANNEL_MAX, CHANNEL_MIN, CHANNEL_SCALE

    info = get_dp_info(schema, dp_id)
    if info and info.get("type") == "value":
        prop = info.get("property", {})
        return (
            prop.get("min", CHANNEL_MIN),
            prop.get("max", CHANNEL_MAX),
            10 ** prop.get("scale", 2),
        )
    return CHANNEL_MIN, CHANNEL_MAX, CHANNEL_SCALE


def get_enum_options(schema: dict[str, Any], dp_id: int | str) -> list[str]:
    """Return the list of allowed enum values for a DP.

    Returns an empty list if the DP is missing or not an enum type.
    """
    info = get_dp_info(schema, dp_id)
    if info and info.get("type") == "enum":
        return info.get("property", {}).get("range", [])
    return []


def is_writable(schema: dict[str, Any], dp_id: int | str) -> bool:
    """Check if a DP is writable according to the schema."""
    info = get_dp_info(schema, dp_id)
    if info is None:
        return False
    return info.get("mode", "") == "rw"
