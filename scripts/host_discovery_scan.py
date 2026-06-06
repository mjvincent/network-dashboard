#!/usr/bin/env python3
"""Discover LAN devices from the host network namespace and import them."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import ipaddress
import json
import platform
import re
import subprocess
import urllib.error
import urllib.request


ARP_PATTERN = re.compile(r"\((?P<ip>[^)]+)\) at (?P<mac>[0-9a-f:]{11,17}|incomplete)", re.IGNORECASE)


def ping_host(ip: str, timeout_ms: int) -> None:
    timeout_seconds = max(1, round(timeout_ms / 1000))
    system = platform.system()
    if system == "Linux":
        command = ["ping", "-c", "1", "-W", str(timeout_seconds), ip]
    elif system == "Darwin":
        command = ["ping", "-c", "1", "-W", str(timeout_ms), ip]
    else:
        command = ["ping", "-c", "1", ip]

    subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def arp_table() -> list[dict[str, str]]:
    result = subprocess.run(["arp", "-an"], capture_output=True, text=True, check=True)
    devices = []
    for line in result.stdout.splitlines():
        match = ARP_PATTERN.search(line)
        if not match:
            continue
        mac = match.group("mac").lower()
        if mac == "incomplete":
            continue
        devices.append({
            "ip": match.group("ip"),
            "hostname": "",
            "mac": mac,
            "vendor": "Unknown",
        })
    return devices


def scan(network_range: str, timeout_ms: int, workers: int, ping_sweep: bool) -> list[dict[str, str]]:
    network = ipaddress.ip_network(network_range, strict=False)
    if ping_sweep:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            list(executor.map(lambda ip: ping_host(str(ip), timeout_ms), network.hosts()))

    devices_by_ip = {}
    for device in arp_table():
        try:
            ip = ipaddress.ip_address(device["ip"])
        except ValueError:
            continue
        if ip in network and ip not in {network.network_address, network.broadcast_address}:
            if device["mac"] == "ff:ff:ff:ff:ff:ff":
                continue
            devices_by_ip[device["ip"]] = device

    return sorted(devices_by_ip.values(), key=lambda device: ipaddress.ip_address(device["ip"]))


def import_devices(api_url: str, network_range: str, devices: list[dict[str, str]]) -> dict:
    payload = {
        "network_range": network_range,
        "source": "host-scan",
        "devices": devices,
    }
    request = urllib.request.Request(
        api_url.rstrip("/") + "/discovery/import",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run host-side LAN discovery and import results.")
    parser.add_argument("--network-range", default="192.168.68.0/24")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--timeout-ms", type=int, default=200)
    parser.add_argument("--workers", type=int, default=64)
    parser.add_argument("--ping-sweep", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    devices = scan(args.network_range, args.timeout_ms, args.workers, args.ping_sweep)
    print(json.dumps({"network_range": args.network_range, "devices": devices}, indent=2))

    if args.dry_run:
        return

    try:
        result = import_devices(args.api_url, args.network_range, devices)
    except urllib.error.URLError as exc:
        raise SystemExit(f"Failed to import discovery results: {exc}") from exc

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
