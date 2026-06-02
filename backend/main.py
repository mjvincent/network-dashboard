from fastapi import FastAPI, HTTPException
from scanner import NetworkScanner, UbuntuMonitor
from registry import DeviceRegistry
from influxdb_client import InfluxDBClient
from dotenv import load_dotenv
import os

load_dotenv()

INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")

app = FastAPI(title="Network Dashboard API")
scanner = NetworkScanner()
ubuntu_monitor = UbuntuMonitor()
registry = DeviceRegistry()

@app.get("/")
@app.get("/root")
async def root():
    return {"message": "Network Dashboard API is running"}
@app.get("/health")
async def healthcheck():
    return {"status": "healthy"}
@app.get("/scan")
async def scan(network_range: str = "192.168.1.0/24"):
    """
    Performs a network scan on the specified range.
    """
    try:
        devices = await scanner.scan_network(network_range)
        registry.update_devices(devices)
        return {"network_range": network_range, "devices": devices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/devices")
async def get_devices():
    """
    Returns all registered devices.
    """
    try:
        devices = registry.get_all_devices()
        return {"devices": devices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scan/ports")
async def scan_ports(host: str, port_range: str = "1-1024"):
    """
    Performs a port scan on a specific host.
    """
    try:
        open_ports = await scanner.scan_ports(host, port_range)
        return {"host": host, "port_range": port_range, "open_ports": open_ports}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def get_metrics():
    """
    Retrieves the latest metrics from InfluxDB.
    """
    if not all([INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET]):
        raise HTTPException(status_code=500, detail="InfluxDB configuration missing in backend")

    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()
        
        # Query the last 10 points from system_metrics
        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
            |> range(start: -5m)
            |> filter(fn: (r) => r["_measurement"] == "system_metrics")
            |> last()
        '''
        
        tables = query_api.query(query)
        
        results = []
        for table in tables:
            for record in table.records:
                results.append({
                    "time": record.get_time(),
                    "host": record.values.get("host"),
                    "field": record.get_field(),
                    "value": record.get_value()
                })
        
        client.close()
        return {"metrics": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/metrics/ubuntu")
async def get_ubuntu_metrics():
    """
    Retrieves system metrics from the configured Ubuntu server via SSH.
    """
    try:
        metrics = await ubuntu_monitor.get_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
