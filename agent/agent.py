import os
import socket
import time
from datetime import datetime, timezone

import psutil
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from sniffer import NetworkSniffer

load_dotenv()

INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")
COLLECTION_INTERVAL = int(os.getenv("COLLECTION_INTERVAL", "10"))
ENABLE_PACKET_SNIFFER = os.getenv("ENABLE_PACKET_SNIFFER", "true").lower() == "true"


def require_influx_config():
    missing = [
        name for name, value in {
            "INFLUXDB_TOKEN": INFLUXDB_TOKEN,
            "INFLUXDB_ORG": INFLUXDB_ORG,
            "INFLUXDB_BUCKET": INFLUXDB_BUCKET,
        }.items()
        if not value
    ]
    if missing:
        raise ValueError(f"Missing required InfluxDB configuration: {', '.join(missing)}")


def calculate_rate(current, previous, attr, elapsed):
    if previous is None or elapsed <= 0:
        return 0.0
    return max(0.0, (getattr(current, attr, 0) - getattr(previous, attr, 0)) / elapsed)


def get_system_metrics(sniffer=None, previous_net=None, previous_disk=None, elapsed=0):
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()
    disk_io = psutil.disk_io_counters()

    metrics = {
        "cpu_usage_percent": psutil.cpu_percent(interval=None),
        "memory_usage_percent": memory.percent,
        "disk_usage_percent": disk.percent,
        "uptime_seconds": int(time.time() - psutil.boot_time()),
        "process_count": len(psutil.pids()),
        "network_bytes_sent_rate": calculate_rate(net, previous_net, "bytes_sent", elapsed),
        "network_bytes_recv_rate": calculate_rate(net, previous_net, "bytes_recv", elapsed),
        "network_packets_sent_rate": calculate_rate(net, previous_net, "packets_sent", elapsed),
        "network_packets_recv_rate": calculate_rate(net, previous_net, "packets_recv", elapsed),
        "network_dropin_rate": calculate_rate(net, previous_net, "dropin", elapsed),
        "network_dropout_rate": calculate_rate(net, previous_net, "dropout", elapsed),
        "disk_io_read_bytes_rate": calculate_rate(disk_io, previous_disk, "read_bytes", elapsed),
        "disk_io_write_bytes_rate": calculate_rate(disk_io, previous_disk, "write_bytes", elapsed),
    }

    if sniffer:
        sniffer_metrics = sniffer.get_metrics()
        for protocol, count in sniffer_metrics.get("protocols", {}).items():
            metrics[f"proto_{protocol}"] = float(count)
        metrics["discovered_devices"] = float(len(sniffer_metrics.get("seen_ips", [])))

    return metrics, net, disk_io


def push_to_influxdb(write_api, metrics):
    point = (
        Point("system_metrics")
        .tag("host", socket.gethostname())
        .time(datetime.now(timezone.utc), WritePrecision.NS)
    )

    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            point.field(key, value)

    write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)


def main():
    require_influx_config()
    print(f"Starting optional Influx agent on {socket.gethostname()}")
    print(f"Pushing custom metrics to {INFLUXDB_URL}")

    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    sniffer = NetworkSniffer() if ENABLE_PACKET_SNIFFER else None

    if sniffer:
        try:
            sniffer.start()
        except Exception as exc:
            print(f"Packet sniffer disabled after startup failure: {exc}")
            sniffer = None

    previous_net = psutil.net_io_counters()
    previous_disk = psutil.disk_io_counters()
    previous_time = time.monotonic()

    try:
        while True:
            time.sleep(COLLECTION_INTERVAL)
            now = time.monotonic()
            elapsed = now - previous_time
            metrics, previous_net, previous_disk = get_system_metrics(
                sniffer=sniffer,
                previous_net=previous_net,
                previous_disk=previous_disk,
                elapsed=elapsed,
            )
            previous_time = now

            try:
                push_to_influxdb(write_api, metrics)
                print(f"[{datetime.now(timezone.utc).isoformat()}] pushed {len(metrics)} metrics")
            except Exception as exc:
                print(f"Error pushing to InfluxDB: {exc}")
    except KeyboardInterrupt:
        print("Agent stopping...")
    finally:
        if sniffer:
            sniffer.stop()
        client.close()


if __name__ == "__main__":
    main()
