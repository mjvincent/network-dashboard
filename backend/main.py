import os
import sqlite3

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response
from influxdb_client import InfluxDBClient
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, Info, generate_latest

from registry import DeviceRegistry
from scanner import NetworkScanner, UnreliableScanResult

load_dotenv()

SCAN_RANGE = os.getenv("SCAN_RANGE", "192.168.68.0/24")
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")

app = FastAPI(title="Network Dashboard API")
scanner = NetworkScanner()
registry = DeviceRegistry()
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
        devices = await scanner.scan_network(network_range)
        registry.update_devices(devices)
        return {"network_range": network_range, "devices": devices}
    except UnreliableScanResult as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/devices")
async def get_devices():
    try:
        return {"devices": registry.get_all_devices()}
    except sqlite3.OperationalError as exc:
        raise HTTPException(status_code=503, detail=f"Device registry unavailable: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve devices: {exc}") from exc


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

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
