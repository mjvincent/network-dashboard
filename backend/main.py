from fastapi import FastAPI, HTTPException
from scanner import NetworkScanner, UbuntuMonitor

app = FastAPI(title="Network Dashboard API")
scanner = NetworkScanner()
ubuntu_monitor = UbuntuMonitor()

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
        return {"network_range": network_range, "devices": devices}
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
    # Implement logic to fetch network metrics here
    return {"metrics": "Not implemented yet"}
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
