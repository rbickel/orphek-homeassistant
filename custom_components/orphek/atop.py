"""Orphek ATOP API client for email/password authentication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from typing import Any

import requests

_LOGGER = logging.getLogger(__name__)

# Orphek app embedded credentials (from com.orphek.android APK)
_PKG_NAME = "com.orphek.android"
_CERT_HASH = (
    "E8:DF:A0:21:BC:79:50:A5:4A:63:F8:60:93:4C:58:01:"
    "82:3B:0C:85:7D:DD:0A:0A:2F:7F:A0:98:6B:0A:1E:50"
)
_BMP_SECRET = "73c5k4qmn7r9sc4yfwthqd893wq75yrj"
_APP_SECRET = "kstwthkthxndmytp5anqq3t5p9fkcggm"
_APP_ID = "wmnju8gm5myqd3a3pa5e"
_CH_KEY = "724832ce"
_TTID = "orphekandroid"
_APP_VERSION = "1.0.6"

_SIGNING_KEY = f"{_PKG_NAME}_{_CERT_HASH}_{_BMP_SECRET}_{_APP_SECRET}"

_SIGN_PARAMS = frozenset({
    "a", "v", "lat", "lon", "lang", "deviceId", "appVersion", "ttid",
    "isH5", "h5Token", "os", "clientId", "postData", "time", "requestId",
    "et", "n4h5", "sid", "chKey", "sp",
})

ATOP_ENDPOINTS = {
    "eu": "https://a1.tuyaeu.com/api.json",
    "us": "https://a1.tuyaus.com/api.json",
    "cn": "https://a1.tuyacn.com/api.json",
    "in": "https://a1.tuyain.com/api.json",
}


def _mobile_hash(data: str) -> str:
    """Compute Tuya mobile hash: MD5 hex with swapped segments."""
    h = hashlib.md5(data.encode()).hexdigest()
    return h[8:16] + h[0:8] + h[24:32] + h[16:24]


def _enc_key(request_id: str) -> bytes:
    """Derive AES-128 encryption key from request ID."""
    h = hmac.new(
        request_id.encode(), _SIGNING_KEY.encode(), hashlib.sha256
    ).hexdigest()
    return h[:16].encode()


def _aes_gcm_encrypt(plaintext: bytes, key: bytes) -> bytes:
    """AES-128-GCM encrypt, output = nonce(12) + ciphertext + tag(16)."""
    try:
        from Cryptodome.Cipher import AES
    except ImportError:
        from Crypto.Cipher import AES

    nonce = os.urandom(12)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ct, tag = cipher.encrypt_and_digest(plaintext)
    return nonce + ct + tag


def _aes_gcm_decrypt(data: bytes, key: bytes) -> bytes:
    """AES-128-GCM decrypt, input = nonce(12) + ciphertext + tag(16)."""
    try:
        from Cryptodome.Cipher import AES
    except ImportError:
        from Crypto.Cipher import AES

    nonce = data[:12]
    ciphertext = data[12:-16]
    tag = data[-16:]
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag)


def _sign(params: dict[str, str]) -> str:
    """Compute HMAC-SHA256 signature for request parameters."""
    parts = []
    for key in sorted(params):
        if key in _SIGN_PARAMS and params.get(key):
            val = _mobile_hash(params[key]) if key == "postData" else params[key]
            parts.append(f"{key}={val}")
    sign_str = "||".join(parts)
    return hmac.new(
        _SIGNING_KEY.encode(), sign_str.encode(), hashlib.sha256
    ).hexdigest()


class OrphekAtopApi:
    """Client for the Orphek ATOP mobile API."""

    def __init__(self, region: str = "eu") -> None:
        self._endpoint = ATOP_ENDPOINTS.get(region, ATOP_ENDPOINTS["eu"])
        self._session = requests.Session()
        self._sid: str | None = None

    @property
    def session_id(self) -> str | None:
        """Return the current session ID."""
        return self._sid

    def _request(
        self,
        api: str,
        version: str,
        post_data: dict | None = None,
        extra_params: dict[str, str] | None = None,
        encrypt: bool = True,
    ) -> dict[str, Any]:
        """Make an ATOP request.

        Args:
            api: API name (e.g. 'thing.m.user.email.token.create').
            version: API version.
            post_data: POST data dict (will be JSON-serialized).
            extra_params: Additional form parameters (e.g. gid).
            encrypt: If True, use et=3 AES-GCM encryption for post data
                     and decrypt response. If False, send plain JSON.
        """
        request_id = str(uuid.uuid4())
        ts = str(int(time.time()))

        params: dict[str, str] = {
            "a": api,
            "v": version,
            "clientId": _APP_ID,
            "time": ts,
            "lang": "en",
            "os": "Android",
            "ttid": _TTID,
            "appVersion": _APP_VERSION,
            "chKey": _CH_KEY,
            "requestId": request_id,
        }
        if encrypt:
            params["et"] = "3"
        if self._sid:
            params["sid"] = self._sid
        if extra_params:
            params.update(extra_params)

        sign_params = dict(params)

        if post_data is not None:
            post_json = json.dumps(post_data, separators=(",", ":"))
            if encrypt:
                key = _enc_key(request_id)
                encrypted = _aes_gcm_encrypt(post_json.encode(), key)
                sign_params["postData"] = base64.b64encode(encrypted).decode()
            else:
                sign_params["postData"] = post_json

        sig = _sign(sign_params)

        form: dict[str, str] = dict(params)
        form["sign"] = sig
        if "postData" in sign_params:
            form["postData"] = sign_params["postData"]

        resp = self._session.post(self._endpoint, data=form, timeout=15)
        raw = resp.json()

        if encrypt and "result" in raw and raw["result"]:
            try:
                key = _enc_key(request_id)
                decrypted = _aes_gcm_decrypt(
                    base64.b64decode(raw["result"]), key
                )
                return json.loads(decrypted)
            except Exception:
                _LOGGER.debug("Could not decrypt response, returning raw")
                return raw
        return raw

    def login(self, email: str, password: str, country_code: str = "1") -> bool:
        """Authenticate with Orphek email and password.

        Returns True on success. Sets self._sid.
        """
        # Step 1: Get login token
        token_resp = self._request(
            "thing.m.user.email.token.create",
            "1.0",
            {"countryCode": country_code, "email": email},
        )

        if not token_resp.get("success"):
            _LOGGER.error(
                "Token creation failed: %s",
                token_resp.get("errorMsg", token_resp.get("errorCode")),
            )
            return False

        result = token_resp["result"]
        token = result["token"]

        # Step 2: Hash password (MD5). Transport is already AES-GCM encrypted.
        password_md5 = hashlib.md5(password.encode()).hexdigest()

        # Step 3: Login
        login_resp = self._request(
            "thing.m.user.email.password.login",
            "3.0",
            {
                "countryCode": country_code,
                "email": email,
                "passwd": password_md5,
                "options": '{"group": 1}',
                "token": token,
                "ifencrypt": 0,
            },
        )

        if not login_resp.get("success"):
            _LOGGER.error(
                "Login failed: %s",
                login_resp.get("errorMsg", login_resp.get("errorCode")),
            )
            return False

        self._sid = login_resp["result"].get("sid")
        _LOGGER.info("Orphek ATOP login successful")
        return True

    def get_devices(self) -> list[dict[str, Any]]:
        """Get all devices across all homes for the logged-in user."""
        if not self._sid:
            _LOGGER.error("Not logged in")
            return []

        # Get homes/locations to find gids
        loc_resp = self._request(
            "thing.m.location.list", "2.1", {}, encrypt=False,
        )
        if not loc_resp.get("success"):
            _LOGGER.error(
                "Failed to get locations: %s",
                loc_resp.get("errorMsg", loc_resp.get("errorCode")),
            )
            return []

        locations = loc_resp.get("result", [])
        if not locations:
            _LOGGER.warning("No homes found for this account")
            return []

        # Get devices from each home
        all_devices: list[dict[str, Any]] = []
        for loc in locations:
            gid = str(loc.get("groupId") or loc.get("gid", ""))
            if not gid:
                continue
            resp = self._request(
                "thing.m.my.group.device.list",
                "1.0",
                extra_params={"gid": gid},
                encrypt=False,
            )
            if resp.get("success"):
                all_devices.extend(resp.get("result", []))
            else:
                _LOGGER.warning(
                    "Failed to get devices for home %s: %s",
                    gid,
                    resp.get("errorCode"),
                )

        return all_devices

    def get_device_local_key(self, device_id: str) -> str | None:
        """Get the local key for a specific device."""
        devices = self.get_devices()
        for dev in devices:
            if dev.get("devId") == device_id:
                return dev.get("localKey")
        return None

    def get_device_dps(self, device_id: str) -> dict[str, Any]:
        """Get all DP values for a device from the cloud.

        Returns a dict of DP id (str) -> value. Uses unencrypted request
        because the encrypted response decryption doesn't work for this API.
        """
        if not self._sid:
            _LOGGER.error("Not logged in")
            return {}

        result = self._request(
            "tuya.m.device.dp.get",
            "1.0",
            {"devId": device_id},
            encrypt=False,
        )

        if not result.get("success"):
            _LOGGER.error(
                "Failed to get device DPS: %s",
                result.get("errorMsg", result.get("errorCode")),
            )
            return {}

        return result.get("result", {})
