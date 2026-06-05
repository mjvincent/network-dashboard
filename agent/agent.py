import psutil
import time
import os
import subprocess
import threading
import re
import socket
from datetime import datetime, timezone
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from dotenv import load_dotenv
from sniffer import NetworkSniffer

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")
COLLECTION_INTERVAL = int(os.getenv("COLLECTION_INTERVAL", "10"))
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "60"))

if not all([INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET]):
    raise ValueError("Missing required InfluxDB configuration in .env file")

class NetworkScanner:
    def __init__(self):
        self.discovered_ips = []
        self.running = False
        self.thread = None

    def _scan_loop(self):
        while self.running:
            try:
                # Dynamically detect the local subnet
                subnet = "192.168.1.0/24"  # Default fallback
                try:
                    # Create a dummy socket to find the local IP
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    local_ip = s.getsockname()[0]
                    s.close()
                    
                    # Derive subnet from local IP (assuming /24 for simplicity)
                    ip_parts = local_ip.split('.')
                    subnet = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
                except Exception:
                    pass

                result = subprocess.check_output(["nmap", "-sn", subnet], stderr=subprocess.STDOUT, text=True)
                
                # Extract IPs from nmap output
                ips = re.findall(r"Nmap scan report for ([\d\.]+)", result)
                self.discovered_ips = ips
                print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] Network scan completed on {subnet}. Found {len(ips)} devices.")
            except Exception as e:
                print(f"Nmap scan error: {e}")
            
            # Sleep for SCAN_INTERVAL, but check running status frequently
            for _ in range(SCAN_INTERVAL):
                if not self.running:
                    break
                time.sleep(1)

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

    def get_discovered_ips(self):
        return self.discovered_ips

def get_system_metrics(sniffer=None, scanner=None, prev_net=None, prev_disk=None, interval=None):
    # Calculate system uptime in seconds
    boot_time_seconds = psutil.boot_time()
    current_time = time.time()
    uptime_seconds = int(current_time - boot_time_seconds)
    
    return uptime_seconds
    """
    Collects system metrics using psutil.
    """
    # CPU Usage
    cpu_usage = psutil.cpu_percent(interval=1)
    
    # Memory Usage
    memory = psutil.virtual_memory()
    memory_usage = memory.percent
    
    # Disk Usage (Root partition)
    disk = psutil.disk_usage('/')
    disk_usage = disk.percent
    
    # Network I/O
    net_io = psutil.net_io_counters()
    bytes_sent = net_io.bytes_sent
    bytes_recv = net_io.bytes_recv
    packets_sent = net_io.packets_sent
    packets_recv = net_io.packets_recv
    dropin = net_io.dropin
    dropout = net_io.dropout
    
    # Disk I/O
    try:
        disk_io = psutil.disk_io_counters()
        disk_read = disk_io.read_bytes
        disk_write = disk_io.write_bytes
    except Exception:
        disk_read = 0
        disk_write = 0

    # Process metrics (Top 5 by CPU usage)
    top_processes = []
    try:
        process_list = []
        for proc in process_iter:
            try:
                pinfo = proc.as_dict()
                # Only collect process name, PID, CPU, and Memory
                process_list.append({
                    "pid": pinfo.get("pid"),
                    "name": pinfo.get("name"),
                    "cpu_percent": pinfo.get("cpu_percent"),
                    "memory_percent": pinfo.get("memory_percent")
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by CPU usage and take top 5
        process_list.sort(key=lambda x: x["cpu_percent"], reverse=True)
        top_processes = process_list[:5]
        
    except Exception as e:
        print(f"Error collecting process metrics: {e}")
        top_processes = []

    metrics = {
        "cpu_usage_percent": cpu_usage,
        "memory_usage_percent": memory_usage,
        "disk_usage_percent": disk_usage,
        "network_bytes_sent_rate": bytes_sent_rate,
        "network_bytes_recv_rate": bytes_recv_rate,
        "network_packets_sent_rate": packets_sent_rate,
        "network_packets_recv_rate": packets_recv_rate,
        "network_dropin_rate": dropin_rate,
        "network_dropout_rate": dropout_rate,
        "disk_io_read_bytes_rate": disk_read_rate,
        "disk_io_write_bytes_rate": disk_write_rate,
        "process_count": process_list.get("count", 0), # Using count from process_list if available
        "top_processes": top_processes
    }

    if sniffer:
        sniffer_metrics = sniffer.get_metrics()
        for proto, count in sniffer_metrics.get("protocols", {}).items():
            metrics[f"proto_{proto}"] = count
        metrics["discovered_devices"] = len(sniffer_metrics.get("seen_ips", []))
    
    if scanner:
        metrics["discovered_devices_count"] = len(scanner.get_discovered_ips())
    
    return metrics
    # Process metrics (Top 5 by CPU usage)
    top_processes = []
    try:
        process_list = []
        # Use psutil.process_iter for robust process iteration
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                # Ensure process is still alive and data is accessible
                if proc.is_running():
                    pinfo = proc.as_dict()
                    process_list.append({
                        "pid": pinfo["pid"],
                        "name": pinfo["name"],
                        "cpu_percent": pinfo["cpu_percent"],
                        "memory_percent": pinfo["memory_percent"]
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by CPU usage and take top 5
        process_list.sort(key=lambda x: x["cpu_percent"], reverse=True)
        top_processes = process_list[:5]
        
    except Exception as e:
        print(f"Error collecting process metrics: {e}")
        top_processes = []

    metrics = {
        "cpu_usage_percent": cpu_usage,
        "memory_usage_percent": memory_usage,
        "disk_usage_percent": disk_usage,
        "network_bytes_sent_rate": bytes_sent_rate,
        "network_bytes_recv_rate": bytes_recv_rate,
        "network_packets_sent_rate": packets_sent_rate,
        "network_packets_recv_rate": packets_recv_rate,
        "network_dropin_rate": dropin_rate,
        "network_dropout_rate": dropout_rate,
        "disk_io_read_bytes_rate": disk_read_rate,
        "disk_io_write_bytes_rate": disk_write_rate,
        "process_count": len(process_list),
        "uptime_seconds": uptime_seconds,
        "top_processes": top_processes
    }

    if sniffer:
        sniffer_metrics = sniffer.get_metrics()
        for proto, count in sniffer_metrics.get("protocols", {}).items():
            metrics[f"proto_{proto}"] = count
        metrics["discovered_devices"] = len(sniffer_metrics.get("seen_ips", []))
    
    if scanner:
        metrics["discovered_devices_count"] = len(scanner.get_discovered_ips())
    
    return metrics
    # Process metrics (Top 5 by CPU usage)
    top_processes = []
    try:
        process_list = []
        # Use psutil.process_iter for robust process iteration
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                # Ensure process is still alive and data is accessible
                if proc.is_running():
                    pinfo = proc.as_dict()
                    process_list.append({
                        "pid": pinfo["pid"],
                        "name": pinfo["name"],
                        "cpu_percent": pinfo["cpu_percent"],
                        "memory_percent": pinfo["memory_percent"]
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by CPU usage and take top 5
        process_list.sort(key=lambda x: x["cpu_percent"], reverse=True)
        top_processes = process_list[:5]
        
    except Exception as e:
        print(f"Error collecting process metrics: {e}")
        top_processes = []

    metrics = {
        "cpu_usage_percent": cpu_usage,
        "memory_usage_percent": memory_usage,
        "disk_usage_percent": disk_usage,
        "network_bytes_sent_rate": bytes_sent_rate,
        "network_bytes_recv_rate": bytes_recv_rate,
        "network_packets_sent_rate": packets_sent_rate,
        "network_packets_recv_rate": packets_recv_rate,
        "network_dropin_rate": dropin_rate,
        "network_dropout_rate": dropout_rate,
        "disk_io_read_bytes_rate": disk_read_rate,
        "disk_io_write_bytes_rate": disk_write_rate,
        "process_count": len(process_list),
        "top_processes": top_processes
    }

    if sniffer:
        sniffer_metrics = sniffer.get_metrics()
        for proto, count in sniffer_metrics.get("protocols", {}).items():
            metrics[f"proto_{proto}"] = count
        metrics["discovered_devices"] = len(sniffer_metrics.get("seen_ips", []))
    
    if scanner:
        metrics["discovered_devices_count"] = len(scanner.get_discovered_ips())
    
    return metrics
def get_system_metrics(sniffer=None, scanner=None, prev_net=None, prev_disk=None, interval=None):
    """
    Collects system metrics using psutil and calculates rates.
    """
    # CPU Usage (Measure over a short interval)
    cpu_usage = psutil.cpu_percent(interval=1)
    
    # Memory Usage
    memory = psutil.virtual_memory()
    memory_usage = memory.percent
    
    # Disk Usage (Root partition)
    disk = psutil.disk_usage('/')
    disk_usage = disk.percent
    
    # Network I/O (Calculate Rate)
    net_io = psutil.net_io_counters()
    
    bytes_sent = net_io.bytes_sent
    bytes_recv = net_io.bytes_recv
    packets_sent = net_io.packets_sent
    packets_recv = net_io.packets_recv
    dropin = net_io.dropin
    dropout = net_io.dropout
    
    # Rate calculation (assuming interval is the time elapsed in seconds)
    if prev_net:
        bytes_sent_rate = (bytes_sent - prev_net.bytes_sent) / interval
        bytes_recv_rate = (bytes_recv - prev_net.bytes_recv) / interval
        packets_sent_rate = (packets_sent - prev_net.packets_sent) / interval
        packets_recv_rate = (packets_recv - prev_net.packets_recv) / interval
        dropin_rate = (dropin - prev_net.dropin) / interval
        dropout_rate = (dropout - prev_net.dropout) / interval
    else:
        # Fallback for first run
        bytes_sent_rate, bytes_recv_rate, packets_sent_rate, packets_recv_rate = 0, 0, 0, 0
        dropin_rate, dropout_rate = 0, 0

    # Disk I/O (Calculate Rate)
    try:
        disk_io = psutil.disk_io_counters()
        disk_read = disk_io.read_bytes
        disk_write = disk_io.write_bytes
    except Exception:
        disk_read = 0
        disk_write = 0

    if prev_disk:
        disk_read_rate = (disk_read - prev_disk.read_bytes) / interval
        disk_write_rate = (disk_write - prev_disk.write_bytes) / interval
    else:
        disk_read_rate, disk_write_rate = 0, 0

    # Process metrics (Top 5 by CPU usage)
    top_processes = []
    try:
        process_list = []
        # Use psutil.process_iter for robust process iteration
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                # Ensure process is still alive and data is accessible
                if proc.is_running():
                    pinfo = proc.as_dict()
                    process_list.append({
                        "pid": pinfo["pid"],
                        "name": pinfo["name"],
                        "cpu_percent": pinfo["cpu_percent"],
                        "memory_percent": pinfo["memory_percent"]
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by CPU usage and take top 5
        process_list.sort(key=lambda x: x["cpu_percent"], reverse=True)
        top_processes = process_list[:5]
        
    except Exception as e:
        print(f"Error collecting process metrics: {e}")
        top_processes = []

    metrics = {
        "cpu_usage_percent": cpu_usage,
        "memory_usage_percent": memory_usage,
        "disk_usage_percent": disk_usage,
        "network_bytes_sent_rate": bytes_sent_rate,
        "network_bytes_recv_rate": bytes_recv_rate,
        "network_packets_sent_rate": packets_sent_rate,
        "network_packets_recv_rate": packets_recv_rate,
        "network_dropin_rate": dropin_rate,
        "network_dropout_rate": dropout_rate,
        "disk_io_read_bytes_rate": disk_read_rate,
        "disk_io_write_bytes_rate": disk_write_rate,
        "process_count": len(process_list),
        "top_processes": top_processes
    }

    if sniffer:
        sniffer_metrics = sniffer.get_metrics()
        for proto, count in sniffer_metrics.get("protocols", {}).items():
            metrics[f"proto_{proto}"] = count
        metrics["discovered_devices"] = len(sniffer_metrics.get("seen_ips", []))
    
    if scanner:
        metrics["discovered_devices_count"] = len(scanner.get_discovered_ips())
    
    return metrics

def push_to_influxdb(client, write_api, metrics, bucket, org):
    """
    Pushes collected metrics to InfluxDB.
    """
    point = Point("system_metrics") \
        .tag("host", os.uname().nodename) \
        .time(datetime.now(timezone.utc), WritePrecision.NS)

    # Add all metrics as fields
    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            point.field(key, value)
        elif isinstance(value, str):
            point.field(key, value)
    
    write_api.write(bucket=bucket, org=org, record=point)

def main():
    print(f"Starting Agent on {os.uname().nodename}...")
    print(f"Pushing to InfluxDB at {INFLUXDB_URL}")
    
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    sniffer = NetworkSniffer()
    sniffer.start()

    scanner = NetworkScanner()
    scanner.start()
    
    try:
        while True:
            metrics = get_system_metrics(sniffer=sniffer, scanner=scanner)
            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp}] Collected metrics: {metrics}")
            
            try:
                push_to_influxdb(client, write_api, metrics, INFLUXDB_BUCKET, INFLUXDB_ORG)
                print("Successfully pushed to InfluxDB.")
            except Exception as e:
                print(f"Error pushing to InfluxDB: {e}")

            time.sleep(COLLECTION_INTERVAL)
            
    except KeyboardInterrupt:
        print("Agent stopping...")
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        sniffer.stop()
        scanner.stop()
        client.close()

if __name__ == "__main__":
    main()