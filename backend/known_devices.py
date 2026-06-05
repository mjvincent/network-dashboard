import os
from pathlib import Path


REPO_KNOWN_DEVICES = Path(__file__).resolve().parents[1] / "config" / "known_devices.yml"
REPO_EXAMPLE_DEVICES = Path(__file__).resolve().parents[1] / "config" / "known_devices.example.yml"


def parse_scalar(value):
    value = value.strip()
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def parse_key_value(line):
    if ":" not in line:
        raise ValueError(f"Expected key/value line, got: {line}")
    key, value = line.split(":", 1)
    return key.strip(), parse_scalar(value)


def parse_devices(path):
    devices = []
    current = None
    in_devices = False

    for raw_line in path.read_text().splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()

        if stripped == "devices:":
            in_devices = True
            continue
        if not in_devices:
            continue

        if stripped.startswith("- "):
            if current:
                devices.append(current)
            current = {}
            remainder = stripped[2:].strip()
            if remainder:
                key, value = parse_key_value(remainder)
                current[key] = value
            continue

        if current is None:
            continue

        key, value = parse_key_value(stripped)
        current[key] = value

    if current:
        devices.append(current)

    return devices


def get_known_devices_path():
    configured = os.getenv("KNOWN_DEVICES_PATH")
    if configured:
        configured_path = Path(configured)
        if configured_path.exists():
            return configured_path
        example_path = configured_path.with_name("known_devices.example.yml")
        if example_path.exists():
            return example_path
    if REPO_KNOWN_DEVICES.exists():
        return REPO_KNOWN_DEVICES
    return REPO_EXAMPLE_DEVICES


def load_known_devices():
    path = get_known_devices_path()
    if not path.exists():
        return []

    devices = []
    for device in parse_devices(path):
        ip = str(device.get("ip", "")).strip()
        if not ip:
            continue
        devices.append({
            "ip": ip,
            "hostname": str(device.get("name") or device.get("hostname") or ""),
            "mac": str(device.get("mac") or ""),
            "vendor": str(device.get("vendor") or "Unknown"),
            "role": str(device.get("role") or "device"),
            "location": str(device.get("location") or "unknown"),
            "criticality": str(device.get("criticality") or "standard"),
            "source": "known",
            "status": "known",
            "last_seen": None,
        })

    return devices
