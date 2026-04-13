# Local Development & Troubleshooting Guide

## 1. Set Up a Local Home Assistant Dev Environment

### Option A: Home Assistant Container (quickest)

```bash
docker run -d \
  --name homeassistant \
  --restart=unless-stopped \
  -v $HOME/ha-config:/config \
  -v <path-to-repo>/custom_components:/config/custom_components \
  --network=host \
  ghcr.io/home-assistant/home-assistant:stable
```

Replace `<path-to-repo>` with your local checkout of this repository. In this example, `$HOME/ha-config` is your Home Assistant configuration directory, and the repository is expected to contain `custom_components/orphek`.

This mounts your working code directly into HA's config, so edits are reflected on restart.

### Option B: HA Core in a Python venv (best for debugging)

```bash
python3 -m venv ha-venv
source ha-venv/bin/activate
pip install homeassistant tinytuya pycryptodome

mkdir -p ha-config/custom_components
ln -s <path-to-repo>/custom_components/orphek \
      ha-config/custom_components/orphek

hass -c ha-config
```

HA will start on `http://localhost:8123`.

---

## 2. Enable Debug Logging

Add to `ha-config/configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.orphek: debug
    tinytuya: debug
```

Logs appear in the terminal, in **Settings → System → Logs**, and in `ha-config/home-assistant.log`.

---

## 3. Project Structure

```
custom_components/orphek/
├── __init__.py           # Integration setup / teardown
├── api.py                # Tuya local protocol client (tinytuya)
├── config_flow.py        # UI-based configuration flow
├── const.py              # Constants, Tuya DP mappings
├── coordinator.py        # DataUpdateCoordinator (30s polling)
├── light.py              # Light platform (brightness-only)
├── manifest.json         # Integration metadata
├── strings.json          # UI strings (source)
└── translations/
    └── en.json           # English translations
```

---

## 4. Protocol Overview

Orphek OR4-iCon LED Bars are Tuya-based devices communicating over the **Tuya local protocol v3.4** on **TCP port 6668**.

### Communication

The integration uses [tinytuya](https://github.com/jasonacox/tinytuya) for local LAN control. No cloud connection is required after initial setup.

Each device requires three credentials:
- **Device ID** — unique Tuya identifier (e.g. `bf87e570b50d5b6ca8ovgr`)
- **IP Address** — local network address
- **Local Key** — 16-char AES key for encrypting commands

### Tuya Datapoint (DP) Mapping

| DP  | Name       | Type | Range    | Description            |
|-----|------------|------|----------|------------------------|
| 20  | switch     | bool | —        | On/off                 |
| 22  | brightness | int  | 10–1000  | Brightness level       |

The integration maps Tuya's 10–1000 brightness range to Home Assistant's 1–255 range.

### Obtaining Local Keys

Local keys must be retrieved from the Tuya cloud. The recommended approach:

1. Pair the device with the **SmartLife** app (temporarily).
2. Create a project on the [Tuya IoT Platform](https://iot.tuya.com/).
3. Link your SmartLife account to the cloud project.
4. Use the cloud API or `tinytuya wizard` to retrieve the local key.
5. After obtaining the key, you can unpair from SmartLife — local control continues to work.

---

## 5. Key Troubleshooting Points

| Area | What to check |
|---|---|
| **Cannot connect** | Verify IP address, device ID, and local key are correct. Device must be on the same network/VLAN as HA. |
| **Connection drops** | The integration uses persistent sockets with automatic reconnection. Check `home-assistant.log` for `OrphekConnectionError` messages. |
| **Brightness out of range** | Tuya range is 10–1000. Values below 10 are clamped. HA shows 1–255. |
| **Device not responding** | Ensure the light is powered on. Try power-cycling it. Check that TCP port 6668 is reachable: `nc -zv <device-ip> 6668`. |
| **Local key changed** | If the device is re-paired with a Tuya-based app, the local key rotates. Re-fetch it and update the integration config. |
| **Polling interval** | State is polled every 30 seconds (configurable in `coordinator.py`). |

---

## 6. Running Tests

```bash
source ha-venv/bin/activate
python3 -m pytest tests/ -v
```

---

## 7. Live Editing & Reloading

After code changes:

1. **Quick reload**: HA UI → Settings → Integrations → orphek → ⋮ → **Reload**
2. **Full restart**: Stop and re-run `hass -c ha-config` (needed for `__init__.py` or `manifest.json` changes)

---

## 8. Interactive Debugging (Option B only)

```bash
pip install debugpy
python -m debugpy --listen 5678 --wait-for-client -m homeassistant -c ha-config
```

Then attach VS Code:

```json
{
  "name": "Attach to HA",
  "type": "debugpy",
  "request": "attach",
  "connect": { "host": "localhost", "port": 5678 }
}
```
