# Orphek Aquarium LED Lighting Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Home Assistant custom integration for [Orphek](https://orphek.com/) iCon aquarium LED lights.

## Supported Devices

- Atlantik iCon
- Natura iCon
- OR3 / OR4 iCon LED Bars
- Osix Smart Controllers

## Features

- Multi-channel brightness control
- Day/Night mode support
- Device auto-discovery (planned)

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

The integration is configured via the UI. You will need the IP address of your Orphek light on your local network.
