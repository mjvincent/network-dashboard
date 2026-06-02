import psutil
import time
import os
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

if not all([INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET]):
    raise ValueError("Missing required InfluxDB configuration in .env file")

def get_system_metrics(sniffer=None):
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
    
    metrics = {
        "cpu_usage_percent": cpu_usage,
        "memory_usage_percent": memory_usage,
        "disk_usage_percent": disk_usage,
        "network_bytes_sent": bytes_sent,
        "network_bytes_recv": bytes_recv
    }

    if sniffer:
        proto_metrics = sniffer.get_metrics()
        metrics.update(proto_metrics)
    
    return metrics

def push_to_influxdb(write_api, metrics):
    """
    Pushes collected metrics to InfluxDB.
    """
    point = Point("system_metrics") \
        .tag("host", os.uname().nodename) \
        .field("cpu_usage_percent", metrics["cpu_usage_percent"]) \
        .field("memory_usage_percent", metrics["memory_usage_percent"]) \
        .field("disk_usage_percent", metrics["disk_usage_percent"]) \
        .field("network_bytes_sent", metrics["network_bytes_sent"]) \
        .field("network_bytes_recv", metrics["network_bytes_recv"]) \
        .time(datetime.now(timezone.utc), WritePrecision.NS)

    # Add protocol counts as fields if they exist in metrics
    for key, value in metrics.items():
        if key not in ["cpu_usage_percent", "memory_usage_percent", "disk_usage_percent", "network_bytes_sent", "network_bytes_recv"]:
            point.field(f"proto_{key}", value)

    write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)

def main():
    print(f"Starting Agent on {os.uname().nodename}...")
    print(f"Pushing to InfluxDB at {INFLUXDB_URL}")
    
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    sniffer = NetworkSniffer()
    sniffer.start()
    
    try:
        while True:
            metrics = get_system_metrics(sniffer=sniffer)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Collected metrics: {metrics}")
            
            try:
                push_to_influxdb(write_api, metrics)
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
        client.close()

if __name__ == "__main__":
    main()