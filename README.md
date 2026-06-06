# Network Dashboard

A containerized home network monitoring stack centered on Grafana, Prometheus,
Node Exporter, Telegraf ping checks, and an optional InfluxDB packet/protocol
agent.

## Services

* Grafana: `http://localhost:3001`
* Prometheus: `http://localhost:9090`
* InfluxDB: `http://localhost:8086`
* Backend API: `http://localhost:8000`
* React app: `http://localhost:3000`

## Known Device Monitoring

Known devices are the source of truth for ping monitoring. Create your local
inventory from the tracked example:

```bash
cp config/known_devices.example.yml config/known_devices.yml
```

Edit `config/known_devices.yml` with your real home devices, then regenerate
Telegraf's ping config:

```bash
python3 scripts/generate_telegraf_config.py
docker compose up -d --force-recreate telegraf
```

The generated `telegraf/telegraf.conf` exposes ping metrics with labels such as
`device_name`, `role`, `criticality`, and `location`. Grafana uses those labels
in the Home Network Overview dashboard.

Backend Nmap scanning remains available for exploration, but the primary
Grafana inventory is the known-device YAML plus Telegraf ping metrics.

## Discovery Review Workflow

The backend runs scheduled LAN discovery every 15 minutes against
`SCAN_RANGE`, which defaults to `192.168.68.0/24`. You can still trigger a scan
manually:

```bash
curl "http://localhost:8000/scan?network_range=192.168.68.0/24"
```

Scan-only devices appear in Grafana as devices needing review. To promote one:

1. Identify it from IP, hostname, MAC, vendor, and `last_seen`.
2. Add it to `config/known_devices.yml` with name, role, location,
   criticality, and optional `uplink`.
3. Regenerate ping monitoring and restart Telegraf:

```bash
python3 scripts/generate_telegraf_config.py
docker compose up -d --force-recreate telegraf
```

Unknown scan-only devices are visible in inventory and utilization panels, but
they do not receive topology map edges until they are added to known devices.

On Docker Desktop, container-based nmap discovery may report every LAN address
as up. The backend refuses that likely false-positive result, and Grafana shows
the scan result as failed rather than polluting inventory with fake devices.
For authoritative discovery, the next step is a host-side scanner on the Mac,
a scanner running directly on the Ubuntu server, or a router integration.

## Ubuntu Server Metrics

The Ubuntu Server panels expect node_exporter to run directly on the Ubuntu
host at `192.168.68.85:9100`. On the Ubuntu server, run node_exporter with your
preferred package/service manager or with Docker:

```bash
docker run -d --name node-exporter --restart unless-stopped \
  --net host --pid host \
  -v /:/host:ro,rslave \
  prom/node-exporter:latest \
  --path.rootfs=/host
```

Prometheus scrapes this as the `ubuntu-node-exporter` job. The local
`node-exporter` container remains useful for Docker-host/internal visibility,
but it is no longer used for Ubuntu Server disk panels.

## MacBook Metrics

MacBook Pro host panels use Homebrew's `node_exporter` service on the Mac:

```bash
brew install node_exporter
brew services start node_exporter
```

Prometheus scrapes it from the Docker network as `macbook-node-exporter` at
`host.docker.internal:9100`.

## Alerts

Grafana alert rules are provisioned from
`grafana/provisioning/alerting/home-network.yml`. Current rules cover:

* known devices down
* critical known devices down
* packet loss above 5%
* LAN or Docker latency above 75 ms
* core monitoring targets down

The rules are intentionally committed without notification contact points.
Add local notification routes later for email, Slack, Discord, Pushover, or
another private destination.

## Getting Started

1. Copy `.env.example` to `.env` and set real local values.
2. Copy `config/known_devices.example.yml` to `config/known_devices.yml`.
3. Generate Telegraf config with `python3 scripts/generate_telegraf_config.py`.
4. Start the stack with `docker compose up -d --build`.

## Security

Keep `.env` and `config/known_devices.yml` local. They are ignored so secrets
and private home-network details do not get committed.
