import asyncio
import os
import sqlite3
import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Response
from influxdb_client import InfluxDBClient
from pydantic import BaseModel
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, Info, generate_latest

from registry import DeviceRegistry
from scanner import NetworkScanner, UnreliableScanResult

load_dotenv()

SCAN_RANGE = os.getenv("SCAN_RANGE", "192.168.68.0/24")
SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL_SECONDS", "900"))
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")

app = FastAPI(title="Network Dashboard API")
scanner = NetworkScanner()
registry = DeviceRegistry()
scan_task = None
scan_lock = asyncio.Lock()
scan_state = {
    "network_range": SCAN_RANGE,
    "running": False,
    "last_started_at": None,
    "last_finished_at": None,
    "last_success_at": None,
    "last_success": 0,
    "last_error": "",
    "last_duration_seconds": 0.0,
    "last_device_count": 0,
}


class DiscoveredDevice(BaseModel):
    ip: str
    hostname: str = ""
    mac: str = ""
    vendor: str = "Unknown"


class DiscoveryImport(BaseModel):
    network_range: str = SCAN_RANGE
    source: str = "host-scan"
    devices: list[DiscoveredDevice]
device_total_gauge = Gauge("network_dashboard_devices_total", "Registered devices by status", ["status"])
device_up_gauge = Gauge(
    "network_dashboard_device_up",
    "Merged device inventory up status",
    ["ip", "hostname", "mac", "vendor", "role", "location", "criticality", "source"],
)
device_info = Info(
    "network_dashboard_device",
    "Merged device inventory metadata",
    ["ip", "hostname", "mac", "vendor", "role", "location", "criticality", "source"],
)
scan_last_success_timestamp = Gauge(
    "network_dashboard_lan_scan_last_success_timestamp",
    "Unix timestamp of the last successful LAN scan",
)
scan_last_success_age = Gauge(
    "network_dashboard_lan_scan_last_success_age_seconds",
    "Age in seconds since the last successful LAN scan",
)
scan_success_gauge = Gauge("network_dashboard_lan_scan_success", "Last LAN scan success status")
scan_duration_gauge = Gauge("network_dashboard_lan_scan_duration_seconds", "Last LAN scan duration in seconds")
scan_discovered_gauge = Gauge("network_dashboard_lan_scan_discovered_devices", "Last LAN scan discovered device count")
scan_unknown_gauge = Gauge("network_dashboard_unknown_devices_needing_review", "Scan-only devices needing review")
known_offline_gauge = Gauge("network_dashboard_known_devices_offline", "Known devices currently offline after scan")


@app.on_event("startup")
async def start_scheduled_discovery():
    global scan_task
    scan_task = asyncio.create_task(scheduled_discovery_loop())


@app.on_event("shutdown")
async def stop_scheduled_discovery():
    if scan_task:
        scan_task.cancel()
        try:
            await scan_task
        except asyncio.CancelledError:
            pass


async def scheduled_discovery_loop():
    while True:
        await run_discovery_scan(SCAN_RANGE)
        await asyncio.sleep(SCAN_INTERVAL_SECONDS)


async def run_discovery_scan(network_range):
    if scan_lock.locked():
        return {"network_range": network_range, "devices": [], "skipped": True, "reason": "scan already running"}

    async with scan_lock:
        started = time.time()
        scan_state.update({
            "network_range": network_range,
            "running": True,
            "last_started_at": started,
            "last_error": "",
        })
        try:
            devices = await scanner.scan_network(network_range)
            registry.update_devices(devices)
            finished = time.time()
            scan_state.update({
                "running": False,
                "last_finished_at": finished,
                "last_success_at": finished,
                "last_success": 1,
                "last_duration_seconds": finished - started,
                "last_device_count": len(devices),
                "last_error": "",
            })
            return {"network_range": network_range, "devices": devices, "skipped": False}
        except Exception as exc:
            finished = time.time()
            scan_state.update({
                "running": False,
                "last_finished_at": finished,
                "last_success": 0,
                "last_duration_seconds": finished - started,
                "last_error": str(exc),
            })
            raise


@app.get("/")
@app.get("/root")
async def root():
    return {"message": "Network Dashboard API is running"}


@app.get("/health")
async def healthcheck():
    return {"status": "healthy"}


@app.get("/scan")
async def scan(network_range: str = SCAN_RANGE):
    try:
        return await run_discovery_scan(network_range)
    except UnreliableScanResult as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/discovery/import")
async def import_discovery(payload: DiscoveryImport):
    started = time.time()
    devices = [device.model_dump() for device in payload.devices]
    source = payload.source or "host-scan"
    try:
        registry.update_devices(devices, source=source)
        finished = time.time()
        scan_state.update({
            "network_range": payload.network_range,
            "running": False,
            "last_started_at": started,
            "last_finished_at": finished,
            "last_success_at": finished,
            "last_success": 1,
            "last_duration_seconds": finished - started,
            "last_device_count": len(devices),
            "last_error": "",
            "last_source": source,
        })
        return {"network_range": payload.network_range, "source": source, "devices": devices}
    except Exception as exc:
        finished = time.time()
        scan_state.update({
            "network_range": payload.network_range,
            "running": False,
            "last_started_at": started,
            "last_finished_at": finished,
            "last_success": 0,
            "last_duration_seconds": finished - started,
            "last_error": str(exc),
            "last_source": source,
        })
        raise HTTPException(status_code=500, detail=f"Failed to import discovery results: {exc}") from exc


@app.get("/devices")
async def get_devices(source: str | None = None, review: str | None = Query(default=None)):
    try:
        return {"devices": registry.get_merged_devices(source=source, review=review)}
    except sqlite3.OperationalError as exc:
        raise HTTPException(status_code=503, detail=f"Device registry unavailable: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve devices: {exc}") from exc


@app.get("/discovery/status")
async def get_discovery_status():
    status = get_discovery_status_payload()
    return {**status, "summary": [status]}


def get_discovery_status_payload():
    last_success_at = scan_state.get("last_success_at")
    age = time.time() - last_success_at if last_success_at else None
    return {
        **scan_state,
        "scan_interval_seconds": SCAN_INTERVAL_SECONDS,
        "last_success_age_seconds": age,
        "unknown_devices_needing_review": len(registry.get_review_needed_devices()),
        "known_devices_offline": len(registry.get_offline_known_devices()),
    }


@app.get("/topology/nodes")
async def get_topology_nodes():
    try:
        return {"nodes": registry.get_topology_nodes()}
    except sqlite3.OperationalError as exc:
        raise HTTPException(status_code=503, detail=f"Device registry unavailable: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve topology nodes: {exc}") from exc


@app.get("/topology/edges")
async def get_topology_edges():
    try:
        return {"edges": registry.get_topology_edges()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve topology edges: {exc}") from exc


@app.get("/network/utilization")
async def get_network_utilization(network_range: str = SCAN_RANGE):
    try:
        utilization = registry.get_network_utilization(network_range)
        return {**utilization, "summary": [utilization]}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid network range: {exc}") from exc
    except sqlite3.OperationalError as exc:
        raise HTTPException(status_code=503, detail=f"Device registry unavailable: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to calculate network utilization: {exc}") from exc


@app.get("/alerts")
async def get_alerts(limit: int = 20):
    try:
        return {"alerts": registry.get_alerts(limit=limit)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/scan/ports")
async def scan_ports(host: str, port_range: str = "1-1024"):
    try:
        open_ports = await scanner.scan_ports(host, port_range)
        return {"host": host, "port_range": port_range, "open_ports": open_ports}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/metrics")
async def get_latest_influx_metrics():
    if not all([INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET]):
        return {"metrics": []}

    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    try:
        query_api = client.query_api()
        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -5m)
          |> filter(fn: (r) => r["_measurement"] == "system_metrics")
          |> last()
        '''
        results = []
        for table in query_api.query(query):
            for record in table.records:
                results.append({
                    "time": record.get_time().isoformat(),
                    "host": record.values.get("host"),
                    "field": record.get_field(),
                    "value": record.get_value(),
                })
        return {"metrics": results}
    except Exception as exc:
        return {"metrics": [], "error": str(exc)}
    finally:
        client.close()


@app.get("/prometheus")
async def prometheus_metrics():
    devices = registry.get_all_devices()
    online = sum(1 for device in devices if device.get("status") in {"online", "known"})
    offline = sum(1 for device in devices if device.get("status") == "offline")
    device_total_gauge.labels(status="online").set(online)
    device_total_gauge.labels(status="offline").set(offline)

    for device in devices:
        labels = {
            "ip": str(device.get("ip") or ""),
            "hostname": str(device.get("hostname") or ""),
            "mac": str(device.get("mac") or ""),
            "vendor": str(device.get("vendor") or "Unknown"),
            "role": str(device.get("role") or "unknown"),
            "location": str(device.get("location") or "unknown"),
            "criticality": str(device.get("criticality") or "standard"),
            "source": str(device.get("source") or "unknown"),
        }
        status = str(device.get("status") or "").lower()
        device_up_gauge.labels(**labels).set(1 if status in {"online", "known"} else 0)
        device_info.labels(**labels).info({"status": status or "unknown"})

    status_payload = get_discovery_status_payload()
    last_success_at = status_payload.get("last_success_at") or 0
    scan_last_success_timestamp.set(last_success_at)
    scan_last_success_age.set(status_payload.get("last_success_age_seconds") or 0)
    scan_success_gauge.set(status_payload.get("last_success") or 0)
    scan_duration_gauge.set(status_payload.get("last_duration_seconds") or 0)
    scan_discovered_gauge.set(status_payload.get("last_device_count") or 0)
    scan_unknown_gauge.set(status_payload.get("unknown_devices_needing_review") or 0)
    known_offline_gauge.set(status_payload.get("known_devices_offline") or 0)

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
