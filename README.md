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
