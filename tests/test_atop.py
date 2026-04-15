"""Unit tests for the Orphek ATOP API client."""

from __future__ import annotations

import base64
import hashlib
import json
from unittest.mock import MagicMock, patch

import pytest

from custom_components.orphek.atop import (
    ATOP_ENDPOINTS,
    OrphekAtopApi,
    _aes_gcm_decrypt,
    _aes_gcm_encrypt,
    _enc_key,
    _mobile_hash,
    _sign,
)


# ---------------------------------------------------------------------------
# Helper crypto functions
# ---------------------------------------------------------------------------

class TestMobileHash:
    """Tests for _mobile_hash."""

    def test_known_input(self):
        h = hashlib.md5(b"hello").hexdigest()
        expected = h[8:16] + h[0:8] + h[24:32] + h[16:24]
        assert _mobile_hash("hello") == expected

    def test_empty_string(self):
        h = hashlib.md5(b"").hexdigest()
        expected = h[8:16] + h[0:8] + h[24:32] + h[16:24]
        assert _mobile_hash("") == expected

    def test_returns_32_chars(self):
        result = _mobile_hash("anything")
        assert len(result) == 32


class TestEncKey:
    """Tests for _enc_key."""

    def test_returns_16_bytes(self):
        key = _enc_key("some-request-id")
        assert isinstance(key, bytes)
        assert len(key) == 16

    def test_deterministic(self):
        assert _enc_key("req-1") == _enc_key("req-1")

    def test_different_ids_different_keys(self):
        assert _enc_key("req-1") != _enc_key("req-2")


class TestAesGcm:
    """Tests for AES-GCM encrypt/decrypt round-trip."""

    def test_round_trip(self):
        key = _enc_key("test-request-id")
        plaintext = b"Hello, Orphek!"
        encrypted = _aes_gcm_encrypt(plaintext, key)
        decrypted = _aes_gcm_decrypt(encrypted, key)
        assert decrypted == plaintext

    def test_encrypted_is_different_from_plaintext(self):
        key = _enc_key("rid")
        plaintext = b"secret data"
        assert _aes_gcm_encrypt(plaintext, key) != plaintext

    def test_encrypted_format(self):
        key = _enc_key("rid")
        encrypted = _aes_gcm_encrypt(b"data", key)
        # nonce(12) + ciphertext(4) + tag(16) = 32
        assert len(encrypted) == 12 + 4 + 16

    def test_wrong_key_fails(self):
        key1 = _enc_key("rid1")
        key2 = _enc_key("rid2")
        encrypted = _aes_gcm_encrypt(b"data", key1)
        with pytest.raises(Exception):
            _aes_gcm_decrypt(encrypted, key2)


class TestSign:
    """Tests for _sign."""

    def test_empty_params(self):
        sig = _sign({})
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA-256 hex

    def test_ignores_non_sign_params(self):
        sig1 = _sign({"a": "test"})
        sig2 = _sign({"a": "test", "randomKey": "value"})
        assert sig1 == sig2

    def test_includes_sign_params(self):
        sig1 = _sign({"a": "login"})
        sig2 = _sign({"a": "other"})
        assert sig1 != sig2

    def test_postData_is_hashed(self):
        """postData should go through _mobile_hash before signing."""
        sig1 = _sign({"a": "x", "postData": "data1"})
        sig2 = _sign({"a": "x", "postData": "data2"})
        assert sig1 != sig2


# ---------------------------------------------------------------------------
# OrphekAtopApi
# ---------------------------------------------------------------------------

class TestOrphekAtopApiInit:
    """Tests for OrphekAtopApi initialization."""

    def test_default_region(self):
        api = OrphekAtopApi()
        assert api._endpoint == ATOP_ENDPOINTS["eu"]

    def test_us_region(self):
        api = OrphekAtopApi(region="us")
        assert api._endpoint == ATOP_ENDPOINTS["us"]

    def test_unknown_region_falls_back_to_eu(self):
        api = OrphekAtopApi(region="xx")
        assert api._endpoint == ATOP_ENDPOINTS["eu"]

    def test_no_session_id(self):
        api = OrphekAtopApi()
        assert api.session_id is None


class TestOrphekAtopApiLogin:
    """Tests for the login flow."""

    @patch.object(OrphekAtopApi, "_request")
    def test_login_success(self, mock_request):
        """Successful login sets sid and returns True."""
        mock_request.side_effect = [
            # Step 1: token create
            {"success": True, "result": {"token": "tok123"}},
            # Step 2: password login
            {"success": True, "result": {"sid": "session_abc"}},
        ]
        api = OrphekAtopApi()
        result = api.login("user@example.com", "password123", "1")

        assert result is True
        assert api.session_id == "session_abc"
        assert mock_request.call_count == 2

    @patch.object(OrphekAtopApi, "_request")
    def test_login_token_failure(self, mock_request):
        """Token creation failure returns False."""
        mock_request.return_value = {
            "success": False,
            "errorMsg": "RATE_LIMIT",
            "errorCode": "TOO_MANY_REQ",
        }
        api = OrphekAtopApi()
        assert api.login("user@example.com", "pass") is False
        assert api.session_id is None

    @patch.object(OrphekAtopApi, "_request")
    def test_login_password_failure(self, mock_request):
        """Password login failure returns False."""
        mock_request.side_effect = [
            {"success": True, "result": {"token": "tok"}},
            {"success": False, "errorMsg": "wrong password"},
        ]
        api = OrphekAtopApi()
        assert api.login("user@example.com", "wrong") is False
        assert api.session_id is None

    @patch.object(OrphekAtopApi, "_request")
    def test_login_password_hashed_as_md5(self, mock_request):
        """Password should be sent as an MD5 hash."""
        mock_request.side_effect = [
            {"success": True, "result": {"token": "tok"}},
            {"success": True, "result": {"sid": "s1"}},
        ]
        api = OrphekAtopApi()
        api.login("user@example.com", "mypassword", "1")

        # Check the second call (password login) post_data
        _, kwargs = mock_request.call_args_list[1]
        post_data = kwargs.get("post_data") or mock_request.call_args_list[1][0][2]
        expected_md5 = hashlib.md5(b"mypassword").hexdigest()
        assert post_data["passwd"] == expected_md5


class TestOrphekAtopApiGetDevices:
    """Tests for get_devices."""

    @patch.object(OrphekAtopApi, "_request")
    def test_not_logged_in(self, mock_request):
        """Returns empty list when not logged in."""
        api = OrphekAtopApi()
        assert api.get_devices() == []
        mock_request.assert_not_called()

    @patch.object(OrphekAtopApi, "_request")
    def test_get_devices_success(self, mock_request):
        """Fetches devices from all homes."""
        api = OrphekAtopApi()
        api._sid = "session123"

        mock_request.side_effect = [
            # locations
            {
                "success": True,
                "result": [
                    {"groupId": "100", "name": "Home"},
                    {"groupId": "200", "name": "Office"},
                ],
            },
            # devices in home 100
            {
                "success": True,
                "result": [{"devId": "dev1", "localKey": "key1"}],
            },
            # devices in home 200
            {
                "success": True,
                "result": [{"devId": "dev2", "localKey": "key2"}],
            },
        ]
        devices = api.get_devices()
        assert len(devices) == 2
        assert devices[0]["devId"] == "dev1"
        assert devices[1]["devId"] == "dev2"

    @patch.object(OrphekAtopApi, "_request")
    def test_get_devices_location_failure(self, mock_request):
        """Returns empty list when location fetch fails."""
        api = OrphekAtopApi()
        api._sid = "session123"
        mock_request.return_value = {"success": False, "errorMsg": "fail"}
        assert api.get_devices() == []

    @patch.object(OrphekAtopApi, "_request")
    def test_get_devices_no_locations(self, mock_request):
        """Returns empty list when no homes found."""
        api = OrphekAtopApi()
        api._sid = "session123"
        mock_request.return_value = {"success": True, "result": []}
        assert api.get_devices() == []

    @patch.object(OrphekAtopApi, "_request")
    def test_get_devices_partial_home_failure(self, mock_request):
        """Returns devices from successful homes even if one fails."""
        api = OrphekAtopApi()
        api._sid = "session123"
        mock_request.side_effect = [
            {"success": True, "result": [{"groupId": "100"}, {"groupId": "200"}]},
            {"success": True, "result": [{"devId": "dev1"}]},
            {"success": False, "errorCode": "ERR"},
        ]
        devices = api.get_devices()
        assert len(devices) == 1


class TestOrphekAtopApiGetDeviceLocalKey:
    """Tests for get_device_local_key."""

    @patch.object(OrphekAtopApi, "get_devices")
    def test_found(self, mock_get_devices):
        mock_get_devices.return_value = [
            {"devId": "dev1", "localKey": "key1"},
            {"devId": "dev2", "localKey": "key2"},
        ]
        api = OrphekAtopApi()
        api._sid = "s"
        assert api.get_device_local_key("dev2") == "key2"

    @patch.object(OrphekAtopApi, "get_devices")
    def test_not_found(self, mock_get_devices):
        mock_get_devices.return_value = [
            {"devId": "dev1", "localKey": "key1"},
        ]
        api = OrphekAtopApi()
        api._sid = "s"
        assert api.get_device_local_key("dev_unknown") is None


class TestOrphekAtopApiGetDeviceDps:
    """Tests for get_device_dps."""

    @patch.object(OrphekAtopApi, "_request")
    def test_not_logged_in(self, mock_request):
        api = OrphekAtopApi()
        assert api.get_device_dps("dev1") == {}

    @patch.object(OrphekAtopApi, "_request")
    def test_success(self, mock_request):
        api = OrphekAtopApi()
        api._sid = "s"
        mock_request.return_value = {
            "success": True,
            "result": {"20": True, "103": 50},
        }
        dps = api.get_device_dps("dev1")
        assert dps == {"20": True, "103": 50}

    @patch.object(OrphekAtopApi, "_request")
    def test_failure(self, mock_request):
        api = OrphekAtopApi()
        api._sid = "s"
        mock_request.return_value = {"success": False, "errorMsg": "fail"}
        assert api.get_device_dps("dev1") == {}


class TestOrphekAtopApiRequest:
    """Tests for the internal _request method (with network mocked)."""

    @patch("custom_components.orphek.atop.requests.Session")
    def test_unencrypted_request(self, mock_session_cls):
        """Unencrypted request returns raw JSON."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "success": True,
            "result": {"key": "val"},
        }
        mock_session = MagicMock()
        mock_session.post.return_value = mock_resp
        mock_session_cls.return_value = mock_session

        api = OrphekAtopApi()
        result = api._request("test.api", "1.0", {"foo": "bar"}, encrypt=False)

        assert result == {"success": True, "result": {"key": "val"}}
        mock_session.post.assert_called_once()

    @patch("custom_components.orphek.atop.requests.Session")
    def test_encrypted_request_decrypts_result(self, mock_session_cls):
        """Encrypted request decrypts the result field."""
        # Create an encrypted response payload
        from custom_components.orphek.atop import _enc_key as real_enc_key

        api = OrphekAtopApi()
        # We need to know the request_id to encrypt. We'll patch uuid4.
        with patch("custom_components.orphek.atop.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value = MagicMock(
                __str__=lambda self: "fixed-uuid-1234"
            )
            key = real_enc_key("fixed-uuid-1234")
            encrypted_result = _aes_gcm_encrypt(
                json.dumps({"decrypted": True}).encode(), key
            )

            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "success": True,
                "result": base64.b64encode(encrypted_result).decode(),
            }
            mock_session = MagicMock()
            mock_session.post.return_value = mock_resp
            api._session = mock_session

            result = api._request("test.api", "1.0", {"data": "x"}, encrypt=True)
            assert result == {"decrypted": True}

    @patch("custom_components.orphek.atop.requests.Session")
    def test_sid_included_when_set(self, mock_session_cls):
        """Session ID is included in request params when set."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"success": True, "result": None}
        mock_session = MagicMock()
        mock_session.post.return_value = mock_resp
        mock_session_cls.return_value = mock_session

        api = OrphekAtopApi()
        api._sid = "my_session"
        api._request("test.api", "1.0", encrypt=False)

        call_kwargs = mock_session.post.call_args
        form_data = call_kwargs[1].get("data") or call_kwargs[0][1] if len(call_kwargs[0]) > 1 else call_kwargs[1]["data"]
        assert form_data["sid"] == "my_session"


# ---------------------------------------------------------------------------
# get_device_schema
# ---------------------------------------------------------------------------

class TestGetDeviceSchema:
    """Tests for get_device_schema()."""

    SCHEMA_API_RESULT = [
        {
            "id": "eh4tcr8zsdshvdrl",
            "category": "dj",
            "categoryCode": "wf_ble_dj",
            "schemaInfo": {
                "schema": json.dumps(
                    [
                        {
                            "id": 20,
                            "code": "switch_led",
                            "mode": "rw",
                            "subType": "bool",
                            "property": {"type": "bool"},
                        },
                        {
                            "id": 110,
                            "code": "mode",
                            "mode": "rw",
                            "subType": "enum",
                            "property": {
                                "type": "enum",
                                "range": ["program", "quick"],
                            },
                        },
                        {
                            "id": 103,
                            "code": "ch1",
                            "mode": "rw",
                            "subType": "value",
                            "property": {
                                "type": "value",
                                "min": 0,
                                "max": 10000,
                                "scale": 2,
                            },
                        },
                    ]
                )
            },
        }
    ]

    def _make_api(self):
        api = OrphekAtopApi()
        api._sid = "test_session"
        api._session = MagicMock()
        return api

    def test_returns_normalised_schema(self):
        api = self._make_api()
        api._session.post.return_value.json.return_value = {
            "success": True,
            "result": self.SCHEMA_API_RESULT,
        }

        result = api.get_device_schema("dev123")

        assert result is not None
        assert result["product_id"] == "eh4tcr8zsdshvdrl"
        assert result["category"] == "dj"
        assert result["category_code"] == "wf_ble_dj"
        assert "20" in result["dps"]
        assert result["dps"]["20"]["code"] == "switch_led"
        assert result["dps"]["20"]["mode"] == "rw"
        assert result["dps"]["20"]["type"] == "bool"
        assert result["dps"]["110"]["type"] == "enum"
        assert result["dps"]["103"]["property"]["max"] == 10000

    def test_returns_none_when_not_logged_in(self):
        api = OrphekAtopApi()  # no session
        assert api.get_device_schema("dev123") is None

    def test_returns_none_on_api_failure(self):
        api = self._make_api()
        api._session.post.return_value.json.return_value = {
            "success": False,
            "errorMsg": "device not found",
        }
        assert api.get_device_schema("dev123") is None

    def test_returns_none_on_empty_result(self):
        api = self._make_api()
        api._session.post.return_value.json.return_value = {
            "success": True,
            "result": [],
        }
        assert api.get_device_schema("dev123") is None

    def test_returns_none_on_bad_schema_json(self):
        api = self._make_api()
        bad_result = [
            {
                "id": "prod1",
                "category": "dj",
                "categoryCode": "wf_ble_dj",
                "schemaInfo": {"schema": "not valid json{{{"},
            }
        ]
        api._session.post.return_value.json.return_value = {
            "success": True,
            "result": bad_result,
        }
        assert api.get_device_schema("dev123") is None

    def test_returns_none_on_missing_schema_key(self):
        api = self._make_api()
        bad_result = [{"id": "prod1", "category": "dj", "categoryCode": "wf_ble_dj"}]
        api._session.post.return_value.json.return_value = {
            "success": True,
            "result": bad_result,
        }
        assert api.get_device_schema("dev123") is None


# ---------------------------------------------------------------------------
# relogin / session expiry
# ---------------------------------------------------------------------------

class TestRelogin:
    """Tests for automatic re-authentication."""

    def test_relogin_with_stored_credentials(self):
        api = OrphekAtopApi()
        api._email = "user@example.com"
        api._password = "secret"
        api._country_code = "41"
        with patch.object(api, "login", return_value=True) as mock_login:
            assert api.relogin() is True
            mock_login.assert_called_once_with("user@example.com", "secret", "41")

    def test_relogin_fails_without_credentials(self):
        api = OrphekAtopApi()
        assert api.relogin() is False

    def test_relogin_fails_when_login_fails(self):
        api = OrphekAtopApi()
        api._email = "user@example.com"
        api._password = "wrong"
        api._country_code = "1"
        with patch.object(api, "login", return_value=False) as mock_login:
            assert api.relogin() is False

    def test_login_stores_credentials(self):
        api = OrphekAtopApi()
        api._session = MagicMock()
        # Mock both token and login requests
        api._session.post.return_value.json.side_effect = [
            {"success": True, "result": {"token": "tok"}},
            {"success": True, "result": {"sid": "new_sid"}},
        ]
        api.login("test@example.com", "pass123", "41")
        assert api._email == "test@example.com"
        assert api._password == "pass123"
        assert api._country_code == "41"

    def test_session_invalid_constant(self):
        assert OrphekAtopApi.SESSION_INVALID == "USER_SESSION_INVALID"

    def test_get_device_dps_retries_on_session_invalid(self):
        api = OrphekAtopApi()
        api._sid = "expired"
        api._email = "u@e.com"
        api._password = "p"
        api._country_code = "1"

        call_count = 0
        def mock_request(action, version, post_data=None, extra_params=None, encrypt=True):
            nonlocal call_count
            if action == "tuya.m.device.dp.get":
                call_count += 1
                if call_count == 1:
                    return {"success": False, "errorCode": "USER_SESSION_INVALID"}
                return {"success": True, "result": {"110": "program"}}
            return {"success": True, "result": {}}

        with patch.object(api, "_request", side_effect=mock_request):
            with patch.object(api, "relogin", return_value=True):
                result = api.get_device_dps("dev1")
                assert result == {"110": "program"}
