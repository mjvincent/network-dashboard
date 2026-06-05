import asyncio

import nmap


class NetworkScanner:
    def __init__(self):
        self.nm = nmap.PortScanner()

    async def scan_network(self, network_range: str):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run_scan, network_range)

    def _run_scan(self, network_range: str):
        devices = []
        self.nm.scan(hosts=network_range, arguments="-sn")

        for host in self.nm.all_hosts():
            hostname = self.nm[host].hostname() or ""
            addresses = self.nm[host].get("addresses", {})
            vendors = self.nm[host].get("vendor", {})
            mac = addresses.get("mac", "")

            devices.append({
                "ip": host,
                "hostname": hostname,
                "mac": mac,
                "vendor": vendors.get(mac, "Unknown") if mac else "Unknown",
                "status": self.nm[host].state() or "unknown",
            })

        return devices

    async def scan_ports(self, host: str, port_range: str):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run_port_scan, host, port_range)

    def _run_port_scan(self, host: str, port_range: str):
        open_ports = []
        self.nm.scan(hosts=host, ports=port_range, arguments="-sS")

        if host not in self.nm.all_hosts():
            return open_ports

        for protocol in self.nm[host].all_protocols():
            for port, details in self.nm[host][protocol].items():
                if details.get("state") == "open":
                    open_ports.append({
                        "port": port,
                        "protocol": protocol,
                        "service": details.get("name", "unknown"),
                    })

        return open_ports
