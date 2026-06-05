import os
import socket
import time
from datetime import datetime, timezone

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
START_TIME = time.time()


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


def get_custom_metrics(sniffer=None):
    metrics = {
        "agent_uptime_seconds": int(time.time() - START_TIME),
    }

    if sniffer:
        sniffer_metrics = sniffer.get_metrics()
        for protocol, count in sniffer_metrics.get("protocols", {}).items():
            metrics[f"proto_{protocol}"] = int(count)
        metrics["seen_ip_count"] = int(len(sniffer_metrics.get("seen_ips", [])))

    return metrics


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

    try:
        while True:
            time.sleep(COLLECTION_INTERVAL)
            metrics = get_custom_metrics(sniffer=sniffer)

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
