"""Smoke tests for Orphek integration."""

import json
from pathlib import Path

import pytest


def test_manifest_valid():
    """Test that manifest.json is valid and has required fields."""
    manifest_path = Path(__file__).parent.parent / "custom_components" / "orphek" / "manifest.json"

    assert manifest_path.exists(), "manifest.json not found"

    with open(manifest_path) as f:
        manifest = json.load(f)

    # Check required fields
    assert "domain" in manifest
    assert "name" in manifest
    assert "version" in manifest
    assert "requirements" in manifest

    # Verify domain
    assert manifest["domain"] == "orphek"

    # Verify version format (should be semver-like)
    version_parts = manifest["version"].split(".")
    assert len(version_parts) >= 2, "Version should have at least major.minor"


def test_integration_imports():
    """Test that core integration modules can be imported."""
    # Import main module
    from custom_components.orphek import DOMAIN, PLATFORMS

    assert DOMAIN == "orphek"
    assert PLATFORMS is not None
    assert len(PLATFORMS) > 0


def test_config_flow_imports():
    """Test that config flow can be imported."""
    from custom_components.orphek.config_flow import OrphekConfigFlow

    assert OrphekConfigFlow is not None
    assert hasattr(OrphekConfigFlow, "async_step_user")


def test_const_imports():
    """Test that constants are defined."""
    from custom_components.orphek.const import (
        CONF_ATOP_EMAIL,
        CONF_ATOP_SESSION_ID,
        CONF_DEVICE_ID,
        CONF_HOST,
        CONF_LOCAL_KEY,
        DOMAIN,
    )

    assert DOMAIN == "orphek"
    assert CONF_DEVICE_ID is not None
    assert CONF_HOST is not None
    assert CONF_LOCAL_KEY is not None
    assert CONF_ATOP_EMAIL is not None
    assert CONF_ATOP_SESSION_ID is not None


def test_atop_api_class():
    """Test that ATOP API class can be instantiated."""
    from custom_components.orphek.atop import OrphekAtopApi

    # Create API instance
    api = OrphekAtopApi()

    # Verify it has required methods
    assert hasattr(api, "login")
    assert hasattr(api, "get_devices")
    assert hasattr(api, "set_session_id")
    assert hasattr(api, "session_id")


def test_device_api_class():
    """Test that device API class can be instantiated."""
    from custom_components.orphek.api import OrphekDevice

    # Verify class exists and has required methods
    assert hasattr(OrphekDevice, "test_connection")
    assert hasattr(OrphekDevice, "get_state")
    assert hasattr(OrphekDevice, "set_brightness")
