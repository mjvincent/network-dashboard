# Network Dashboard: Metrics & Integration Proposal

This document outlines the proposed metrics and integration capabilities for the Home Network Dashboard.

## 1. Core Network Metrics (All Devices)
The primary goal is to provide visibility into what is currently active on the network.
*   **Device Presence:** Online/Offline status (based on periodic scans).
*   **Identity:** IP Address, MAC Address, Hostname, and Manufacturer (via OUI lookup).
*   **Network Profile:** Discovery of open ports (e.g., 80, 443, 22) to identify device types (Web Server, Printer, IoT, etc.).
*   **Discovery Alerts:** Notifications when a new device joins the network or an existing one disappears.

## 2. Ubuntu Server Specific Metrics
Since the Ubuntu server is a key part of the infrastructure, we can implement deeper monitoring via SSH or a lightweight agent.
*   **Resource Utilization:**
    *   **CPU Usage:** Real-time load percentage and per-core breakdown.
    *   **Memory Usage:** Total, Used, and Available RAM.
    *   **Disk I/O & Capacity:** Usage per partition and disk latency.
*   **Network Performance:**
    *   **Bandwidth Usage:** Inbound and Outbound traffic throughput.
*   **System Health:**
    *   **Uptime:** How long the server has been running.
    *   **Service Status:** Monitoring critical services (e.g., Docker, Nginx, Plex).
    *   **Temperature/Thermal:** (If hardware sensors are available).

## 3. Integration & Connectivity Capabilities
To allow "connecting capabilities" from the dashboard, we propose:
*   **SSH Terminal Integration:** A web-based terminal (using `xterm.js` and `ssh2` on the backend) to execute commands directly on the Ubuntu server from the dashboard.
*   **Quick Actions:**
    *   **Reboot/Shutdown:** One-click buttons to trigger controlled restarts.
    *   **Service Restart:** Ability to restart specific Docker containers or systemd services.
*   **Web UI Access:** One-click links to the web interfaces of discovered devices (e.g., Router admin page, Printer web interface).

## 4. Implementation Roadmap
1.  **Phase 1 (Current):** Infrastructure setup (Docker, Backend/Frontend scaffolding).
2.  **Phase 2:** Implement `nmap`-based discovery engine in Python.
3.  **Phase 3:** Implement SSH-based metric collection for the Ubuntu server.
4.  **Phase 4:** Develop the React-based dashboard UI with real-time updates (WebSockets).
5.  **Phase 5:** Add advanced features (Terminal, Alerting).