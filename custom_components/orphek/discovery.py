"""LAN discovery for Orphek (Tuya) devices."""

from __future__ import annotations

import json
import logging
import socket
from dataclasses import dataclass

import tinytuya

_LOGGER = logging.getLogger(__name__)

ORPHEK_PRODUCT_KEY = "eh4tcr8zsdshvdrl"
BROADCAST_PORT = 6667
LISTEN_TIMEOUT = 8


@dataclass
class DiscoveredDevice:
    """A Tuya device discovered on the LAN."""

    device_id: str
    ip: str
    product_key: str
    version: str


def discover_orphek_devices(timeout: int = LISTEN_TIMEOUT) -> list[DiscoveredDevice]:
    """Listen for Tuya UDP broadcasts and return Orphek devices."""
    devices: dict[str, DiscoveredDevice] = {}

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", BROADCAST_PORT))
        sock.settimeout(timeout)
    except OSError as err:
        _LOGGER.error("Cannot bind UDP port %d for discovery: %s", BROADCAST_PORT, err)
        return []

    import time

    start = time.monotonic()
    try:
        while time.monotonic() - start < timeout:
            try:
                data, addr = sock.recvfrom(4096)
                ip = addr[0]
                if ip in devices:
                    continue
                result = tinytuya.decrypt_udp(data)
                info = json.loads(result)
                product_key = info.get("productKey", "")
                device_id = info.get("gwId", "")
                version = info.get("version", "3.4")

                if product_key == ORPHEK_PRODUCT_KEY and device_id:
                    devices[ip] = DiscoveredDevice(
                        device_id=device_id,
                        ip=ip,
                        product_key=product_key,
                        version=version,
                    )
                    _LOGGER.debug("Discovered Orphek device %s at %s", device_id, ip)
            except socket.timeout:
                break
            except Exception:
                continue
    finally:
        sock.close()

    return list(devices.values())
