"""Tuya IoT Platform API client for fetching device local keys."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any

import requests

_LOGGER = logging.getLogger(__name__)

TUYA_ENDPOINTS = {
    "eu": "https://openapi.tuyaeu.com",
    "us": "https://openapi.tuyaus.com",
    "cn": "https://openapi.tuyacn.com",
    "in": "https://openapi.tuyain.com",
}


class TuyaCloudApi:
    """Tuya IoT Platform API client."""

    def __init__(self, api_key: str, api_secret: str, region: str = "eu") -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = TUYA_ENDPOINTS.get(region, TUYA_ENDPOINTS["eu"])
        self._access_token: str | None = None
        self._token_expiry: float = 0
        self._session = requests.Session()

    def _sign(self, method: str, path: str, access_token: str = "") -> tuple[str, str]:
        """Generate Tuya API request signature."""
        t = str(int(time.time() * 1000))
        content_hash = hashlib.sha256(b"").hexdigest()
        string_to_sign = f"{method}\n{content_hash}\n\n{path}"
        str_to_sign = self._api_key + access_token + t + string_to_sign
        sign = hmac.new(
            self._api_secret.encode(),
            str_to_sign.encode(),
            hashlib.sha256,
        ).hexdigest().upper()
        return t, sign

    def _get_token(self) -> str | None:
        """Get or refresh the access token."""
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token

        path = "/v1.0/token?grant_type=1"
        t, sign = self._sign("GET", path)
        headers = {
            "client_id": self._api_key,
            "sign": sign,
            "t": t,
            "sign_method": "HMAC-SHA256",
        }
        try:
            r = self._session.get(f"{self._base_url}{path}", headers=headers, timeout=10)
            data = r.json()
        except Exception as err:
            _LOGGER.error("Failed to get Tuya token: %s", err)
            return None

        if data.get("success"):
            result = data["result"]
            self._access_token = result["access_token"]
            self._token_expiry = time.time() + result.get("expire_time", 7200) - 60
            return self._access_token

        _LOGGER.error("Tuya token request failed: %s", data.get("msg"))
        return None

    def _api_get(self, path: str) -> dict[str, Any] | None:
        """Make an authenticated GET request."""
        token = self._get_token()
        if not token:
            return None

        t, sign = self._sign("GET", path, token)
        headers = {
            "client_id": self._api_key,
            "access_token": token,
            "sign": sign,
            "t": t,
            "sign_method": "HMAC-SHA256",
        }
        try:
            r = self._session.get(f"{self._base_url}{path}", headers=headers, timeout=10)
            return r.json()
        except Exception as err:
            _LOGGER.error("Tuya API request failed: %s", err)
            return None

    def get_user_devices(self, uid: str) -> list[dict[str, Any]]:
        """Get all devices for a user, including local keys."""
        data = self._api_get(f"/v1.0/users/{uid}/devices")
        if data and data.get("success"):
            return data.get("result", [])
        _LOGGER.error("Failed to fetch devices: %s", data)
        return []

    def get_device(self, device_id: str) -> dict[str, Any] | None:
        """Get a single device's details including local key."""
        data = self._api_get(f"/v1.0/devices/{device_id}")
        if data and data.get("success"):
            return data.get("result")
        return None

    def get_device_local_key(self, device_id: str) -> str | None:
        """Fetch a single device's local key."""
        device = self.get_device(device_id)
        if device:
            return device.get("local_key")
        return None

    def test_credentials(self) -> bool:
        """Test if the API credentials are valid."""
        return self._get_token() is not None

    def get_uid_from_devices(self) -> str | None:
        """Get the UID by listing linked app accounts."""
        data = self._api_get("/v1.0/token/uids")
        if data and data.get("success"):
            uids = data.get("result", [])
            if uids:
                return uids[0]
        return None
