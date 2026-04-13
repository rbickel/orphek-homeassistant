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

    # Error code returned by the ATOP API when the session has expired
    SESSION_INVALID = "USER_SESSION_INVALID"

    def __init__(self, region: str = "eu") -> None:
        self._endpoint = ATOP_ENDPOINTS.get(region, ATOP_ENDPOINTS["eu"])
        self._session = requests.Session()
        self._sid: str | None = None
        self._email: str | None = None
        self._password: str | None = None
        self._country_code: str = "1"

    @property
    def session_id(self) -> str | None:
        """Return the current session ID."""
        return self._sid

    def set_session_id(self, session_id: str) -> None:
        """Set the session ID for authenticated requests.

        Use this to restore a previously obtained session instead of
        logging in again with email/password.
        """
        self._sid = session_id

    def close(self) -> None:
        """Close the HTTP session and cleanup resources."""
        if self._session:
            self._session.close()

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

        try:
            resp = self._session.post(self._endpoint, data=form, timeout=15)
            resp.raise_for_status()
            raw = resp.json()
        except requests.exceptions.RequestException as err:
            _LOGGER.error("ATOP API request failed: %s", err)
            return {"success": False, "errorMsg": str(err)}
        except ValueError as err:
            _LOGGER.error("Failed to parse ATOP API response as JSON: %s", err)
            return {"success": False, "errorMsg": "Invalid JSON response"}

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
        # Store credentials for transparent re-login on session expiry.
        # This is intentional: the ATOP API has no refresh-token mechanism,
        # so we keep the password in memory to re-authenticate automatically
        # when the session token expires (~90 days). The password is also
        # persisted in HA's config entry storage (standard HA practice, same
        # as the official Tuya, MQTT, SMTP integrations) to survive restarts.
        self._email = email
        self._password = password
        self._country_code = country_code
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

    def relogin(self) -> bool:
        """Re-authenticate using stored credentials.

        Returns True if login succeeds, False if credentials are missing
        or the login fails (e.g. password changed).
        """
        if not self._email or not self._password:
            _LOGGER.warning("Cannot re-login: no stored credentials")
            return False
        _LOGGER.info("Re-authenticating with stored ATOP credentials")
        return self.login(self._email, self._password, self._country_code)

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
            # Auto-relogin on session expiry
            if loc_resp.get("errorCode") == self.SESSION_INVALID and self.relogin():
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
            # Auto-relogin on session expiry
            if result.get("errorCode") == self.SESSION_INVALID and self.relogin():
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

    def get_device_schema(self, device_id: str) -> dict[str, Any] | None:
        """Fetch the full product schema for a device.

        Returns a normalised dict containing device metadata and DP definitions,
        or None on failure.  The response comes from
        ``thing.m.device.ref.info.my.list`` and is reshaped into::

            {
                "product_id": "eh4tcr8z...",
                "category": "dj",
                "category_code": "wf_ble_dj",
                "dps": {
                    "20": {"code": "switch_led", "mode": "rw", "type": "bool",
                           "property": {"type": "bool"}},
                    "110": {"code": "mode", "mode": "rw", "type": "enum",
                            "property": {"range": [...], "type": "enum"}},
                    ...
                }
            }
        """
        if not self._sid:
            _LOGGER.error("Not logged in")
            return None

        resp = self._request(
            "thing.m.device.ref.info.my.list",
            "1.0",
            {"devId": device_id},
            encrypt=False,
        )
        if not resp.get("success") or not resp.get("result"):
            # Auto-relogin on session expiry
            if resp.get("errorCode") == self.SESSION_INVALID and self.relogin():
                resp = self._request(
                    "thing.m.device.ref.info.my.list",
                    "1.0",
                    {"devId": device_id},
                    encrypt=False,
                )
            if not resp.get("success") or not resp.get("result"):
                _LOGGER.error(
                    "Failed to get device schema: %s",
                    resp.get("errorMsg", resp.get("errorCode")),
                )
                return None

        product = resp["result"][0]
        try:
            import json as _json

            raw_schema = _json.loads(product["schemaInfo"]["schema"])
        except (KeyError, TypeError, _json.JSONDecodeError) as err:
            _LOGGER.error("Failed to parse schema JSON: %s", err)
            return None

        dps: dict[str, dict[str, Any]] = {}
        for dp in raw_schema:
            dp_id = str(dp["id"])
            dps[dp_id] = {
                "code": dp.get("code", ""),
                "mode": dp.get("mode", ""),
                "type": dp.get("subType", ""),
                "property": dp.get("property", {}),
            }

        return {
            "product_id": product.get("id", ""),
            "category": product.get("category", ""),
            "category_code": product.get("categoryCode", ""),
            "dps": dps,
        }
