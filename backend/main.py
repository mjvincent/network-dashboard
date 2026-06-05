from fastapi import FastAPI, HTTPException
from scanner import NetworkScanner, UbuntuMonitor, MacbookMonitor
from registry import DeviceRegistry
from influxdb_client import InfluxDBClient
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")

app = FastAPI(title="Network Dashboard API")
scanner = NetworkScanner()
ubuntu_monitor = UbuntuMonitor()
macbook_monitor = MacbookMonitor()
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

@app.get("/metrics")
async def get_metrics_prometheus():
    """
    Exposes system and device metrics in Prometheus format.
    """
    metrics = []
    
    # 1. Device Registry Metrics
    try:
        devices = await asyncio.to_thread(registry.get_all_devices)
        total_devices = len(devices)
        online_devices = sum(1 for d in devices if d.get("status") == "online")
        offline_devices = total_devices - online_devices
        
        metrics.append(f'network_dashboard_total_devices{{"status=\"online\""}} {online_devices}')
        metrics.append(f'network_dashboard_total_devices{{"status=\"offline\""}} {offline_devices}')
        metrics.append(f'network_dashboard_total_devices_count {total_devices}')
        
        # Append individual device last seen timestamp metrics (simplified)
        for device in devices:
            metrics.append(f'network_dashboard_device_last_seen{{{{"ip=\"" + device["ip"] + "\"" + "," + "host=\"" + device["hostname"] + "\"" + "," + "mac=\"" + device["mac"] + "\"" + "}}} " + device["last_seen"])
            
    except Exception as e:
        metrics.append(f'network_dashboard_device_status_error{{"error_message=\"{str(e)\""}}} 1')

    # 2. Remote Server Metrics (Ubuntu & Macbook)
    try:
        ubuntu_metrics = await asyncio.to_thread(ubuntu_monitor.get_metrics)
        metrics.append(f'system_cpu_usage_percent{{"server=\"ubuntu\""}} {ubuntu_metrics.get("cpu_usage_percent", 0.0)}')
        metrics.append(f'system_memory_usage_percent{{"server=\"ubuntu\""}} {ubuntu_metrics.get("memory_usage_percent", 0.0)}')
        metrics.append(f'system_disk_usage_percent{{"server=\"ubuntu\""}} {ubuntu_metrics.get("disk_usage_percent", 0.0")}')
        metrics.append(f'system_uptime{{"server=\"ubuntu\""}} {ubuntu_metrics.get("uptime", "unknown")}')
    except Exception as e:
        metrics.append(f'system_metrics_error{{"server=\"ubuntu\"","error_message=\"{str(e)}\""}} 1')

    try:
        macbook_metrics = await asyncio.to_thread(macbook_monitor.get_metrics)
        metrics.append(f'system_cpu_usage_percent{{"server=\"macbook\""}} {macbook_metrics.get("cpu_usage_percent", 0.0)}')
        metrics.append(f'system_memory_usage_percent{{"server=\"macbook\""}} {macbook_metrics.get("memory_usage_percent", 0.0)}')
        metrics.append(f'system_disk_usage_percent{{"server=\"macbook\""}} {macbook_metrics.get("disk_usage_percent", 0.0")}')
        metrics.append(f'system_uptime{{"server=\"macbook\""}} {macbook_metrics.get("uptime", "unknown")}')
    except Exception as e:
        metrics.append(f'system_metrics_error{{"server=\"macbook\"","error_message=\"{str(e)}\""}} 1')
        
    return "\n".join(metrics)

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

@app.get("/metrics")
async def get_metrics_prometheus():
    """
    Exposes system and device metrics in Prometheus format.
    """
    metrics = []
    
    # 1. Device Registry Metrics
    try:
        devices = await asyncio.to_thread(registry.get_all_devices)
        total_devices = len(devices)
        online_devices = sum(1 for d in devices if d.get("status") == "online")
        offline_devices = total_devices - online_devices
        
        metrics.append(f'network_dashboard_total_devices{{"status=\"online\""}} {online_devices}')
        metrics.append(f'network_dashboard_total_devices{{"status=\"offline\""}} {offline_devices}')
        metrics.append(f'network_dashboard_total_devices_count {total_devices}')
        
        # Append individual device last seen timestamp metrics (simplified)
        for device in devices:
            metrics.append(f'network_dashboard_device_last_seen{{{{"ip=\"" + device["ip"] + "\"" + "," + "host=\"" + device["hostname"] + "\"" + "," + "mac=\"" + device["mac"] + "\"" + "}}} " + device["last_seen"])
            
    except Exception as e:
        metrics.append(f'network_dashboard_device_status_error{{"error_message=\"{str(e)\""}}} 1')

    # 2. Remote Server Metrics (Ubuntu & Macbook)
    # Note: The monitor classes handle the blocking IO and network calls internally.
    
    # Ubuntu Metrics
    try:
        ubuntu_metrics = await asyncio.to_thread(ubuntu_monitor.get_metrics)
        metrics.append(f'system_cpu_usage_percent{{"server=\"ubuntu\""}} {ubuntu_metrics.get("cpu_usage_percent", 0.0)}')
        metrics.append(f'system_memory_usage_percent{{"server=\"ubuntu\""}} {ubuntu_metrics.get("memory_usage_percent", 0.0)}')
        metrics.append(f'system_disk_usage_percent{{"server=\"ubuntu\""}} {ubuntu_metrics.get("disk_usage_percent", 0.0")}')
        metrics.append(f'system_uptime{{"server=\"ubuntu\""}} {ubuntu_metrics.get("uptime", "unknown")}')
    except Exception as e:
        metrics.append(f'system_metrics_error{{"server=\"ubuntu\"","error_message=\"{str(e)}\""}} 1')

    # MacBook Metrics
    try:
        macbook_metrics = await asyncio.to_thread(macbook_monitor.get_metrics)
        metrics.append(f'system_cpu_usage_percent{{"server=\"macbook\""}} {macbook_metrics.get("cpu_usage_percent", 0.0)}')
        metrics.append(f'system_memory_usage_percent{{"server=\"macbook\""}} {macbook_metrics.get("memory_usage_percent", 0.0)}')
        metrics.append(f'system_disk_usage_percent{{"server=\"macbook\""}} {macbook_metrics.get("disk_usage_percent", 0.0")}')
        metrics.append(f'system_uptime{{"server=\"macbook\""}} {macbook_metrics.get("uptime", "unknown")}')
    except Exception as e:
        metrics.append(f'system_metrics_error{{"server=\"macbook\"","error_message=\"{str(e)}\""}} 1')
        
    return "\n".join(metrics)
>>>>
<task_progress>
- [ ] Confirm the correct Grafana dashboard and its port
- [ ] Provide detailed instructions to access the dashboard
- [x] Diagnose the root cause of the "Failed to load dashboard data" error by inspecting the backend and Prometheus configurations (Completed)
- [ ] Ensure the backend API is correctly exposing metrics consumable by Prometheus (Implementing now)
- [ ] Update the Grafana dashboard configuration with the correct data sources and structure
</task_progress>

@app.get("/alerts")
async def get_alerts():
    """
    Returns recent alerts.
    """
    try:
        alerts = registry.get_alerts()
        return {"alerts": alerts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/devices")
async def get_devices():
    """
    Returns all registered devices.
    """
    try:
        # Run synchronous DB operation in a separate thread to prevent blocking the event loop
        devices = await asyncio.to_thread(registry.get_all_devices)
        return {"devices": devices}
    except sqlite3.OperationalError as e:
        # Catch specific DB connection/operational errors and raise 503 Service Unavailable
        raise HTTPException(status_code=503, detail=f"Database Operational Error: {e}. The device registry might be unavailable.")
    except Exception as e:
        # Handle all other exceptions
        raise HTTPException(status_code=500, detail=f"Failed to retrieve devices: {str(e)}")

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

@app.get("/metrics/macbook")
async def get_macbook_metrics():
    """
    Retrieves system metrics from the configured MacBook Pro via SSH.
    """
    try:
        metrics = await macbook_monitor.get_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
