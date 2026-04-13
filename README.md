# Orphek Aquarium LED Lighting Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Home Assistant custom integration for [Orphek](https://orphek.com/) iCon aquarium LED lights with local control via the Tuya protocol and cloud schedule/expansion data via the Orphek ATOP API.

## Supported & Tested Devices

| Device | Status |
|--------|--------|
| OR4 iCon LED Bar | ✅ Tested & working |
| OR3 iCon LED Bar | 🔲 Untested (should work — same Tuya protocol) |
| Atlantik iCon | 🔲 Untested — community contribution welcome |
| Natura iCon | 🔲 Untested — community contribution welcome |
| Osix Smart Controller | 🔲 Untested — community contribution welcome |

> **Contributions welcome!** If you own an Orphek iCon device not listed as tested, please open an issue with your device info so we can add support.

## Features

- **Local control** — direct communication via Tuya local protocol (no cloud required for on/off and brightness)
- **Multi-channel brightness** — individual control of all 6 LED channels
- **Mode selection** — Program, Quick, Sun Moon Sync, Biorhythm effects
- **Schedule display** — active program schedule and preset schedule
- **Expansion monitoring** — Jellyfish, Clouds, Acclimation, Lunar cycle, Biorhythm, Sun Moon Sync status
- **Temperature sensors** — device temperature in °C and °F
- **Quiet mode** — fan silent mode status
- **Auto-discovery** — finds Orphek devices on your LAN during setup
- **No developer account needed** — authenticates with your Orphek app email/password

## Installation

### HACS (Recommended)

1. Add this repository as a custom repository in HACS
2. Search for "Orphek" and install
3. Restart Home Assistant
4. Go to **Settings → Devices & Services → Add Integration → Orphek**

### Manual

1. Copy the `custom_components/orphek` folder into your `config/custom_components/` directory
2. Restart Home Assistant
3. Go to **Settings → Devices & Services → Add Integration → Orphek**

## Configuration

The integration is configured via the UI:

1. Choose **Orphek account (email/password)** as the setup method
2. Enter your Orphek app email, password, and country
3. The integration will auto-discover your device on the LAN and fetch the local encryption key

You can also set up manually if you already know the device ID, IP address, and local key.

## Entities

The integration creates the following entities for each device:

| Entity | Type | Description |
|--------|------|-------------|
| Light | `light` | Main light entity with brightness and effect (mode) control |
| Temperature | `sensor` | Device temperature (°C) |
| Temperature (°F) | `sensor` | Device temperature (°F) |
| Mode | `sensor` | Selected operating mode |
| Running mode | `sensor` | Currently active mode |
| Schedule | `sensor` | Active program schedule |
| Schedule preset | `sensor` | Default/preset schedule |
| Lunar interval | `sensor` | Lunar cycle interval (days) |
| Lunar max brightness | `sensor` | Lunar cycle max brightness (%) |
| Jellyfish | `binary_sensor` | Jellyfish expansion enabled |
| Clouds | `binary_sensor` | Clouds expansion enabled |
| Acclimation | `binary_sensor` | Acclimation expansion enabled |
| Lunar cycle | `binary_sensor` | Lunar cycle expansion enabled |
| Biorhythm | `binary_sensor` | Biorhythm expansion enabled |
| Sun moon sync | `binary_sensor` | Sun/moon sync expansion enabled |
| Quiet mode | `binary_sensor` | Fan quiet/silent mode enabled |
