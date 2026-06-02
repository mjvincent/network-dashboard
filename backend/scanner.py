import nmap
import asyncio
import paramiko
import os
from dotenv import load_dotenv

load_dotenv()

class NetworkScanner:
    def __init__(self):
        self.nm = nmap.PortScanner()

    async def scan_network(self, network_range: str):
        """
        Performs an nmap scan on the specified network range.
        Returns a list of discovered devices with their details.
        """
        # Running nmap in a thread to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run_scan, network_range)

    def _run_scan(self, network_range: str):
        devices = []
        try:
            # -sn is for ping scan (discovery only)
            self.nm.scan(hosts=network_range, arguments='-sn')
            
            for host in self.nm.all_hosts():
                device_info = {
                    "ip": host,
                    "hostname": self.nm[host].hostname(),
                    "status": self.arm_host_status(host),
                }
                
                # Try to get MAC address and vendor
                if 'mac' in self.nm[host]['addresses']:
                    device_int_mac = self.nm[host]['addresses']['mac']
                    device_info["mac"] = device_int_mac
                    device_info["vendor"] = self.nm[host]['vendor'].get(device_int_mac, "Unknown")
                
                devices.append(device_info)
                
        except Exception as e:
            print(f"Error during scan: {e}")
            
        return devices

    def arm_host_status(self, host):
        return self.nm[host].state()

    async def scan_ports(self, host: str, port_range: str):
        """
        Performs a port scan on a specific host for a given port range.
        Returns a list of open ports.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run_port_scan, host, port_range)

    def _run_port_scan(self, host: str, port_range: str):
        open_ports = []
        try:
            # -sS is a TCP SYN scan, which is relatively fast and stealthy
            self.nm.scan(hosts=host, ports=port_range, arguments='-sS')
            
            for proto in self.nm[host].all_protocols():
                lport = self.nm[host][proto].keys()
                for port in lport:
                    if self.nm[host][proto][port]['state'] == 'open':
                        open_ports.append({
                            "port": port,
                            "protocol": proto,
                            "service": self.nm[host][proto][port]['name']
                        })
        except Exception as e:
            print(f"Error during port scan: {e}")
            
        return open_ports

class UbuntuMonitor:
    def __init__(self):
        self.ip = os.getenv("UBUNTU_SERVER_IP")
        self.user = os.getenv("UBUNTU_SERVER_USER")
        self.password = os.getenv("UBUNTU_SERVER_PASSWORD")
        self.ssh_key_path = os.getenv("UBUNTU_SERVER_SSH_KEY_PATH")

    async def get_metrics(self):
        if not self.ip or not self.user:
            return {"error": "Ubuntu server configuration missing in .env"}

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._fetch_metrics)

    def _fetch_metrics(self):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.ssh_key_path:
                client.connect(self.ip, username=self.user, key_filename=self.ssh_key_path)
            else:
                client.connect(self.ip, username=self.user, password=self.password)

            metrics = {}
            
            # CPU Usage
            stdin, stdout, stderr = client.exec_command("top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/' | awk '{print 100 - $1}'")
            metrics["cpu_usage_percent"] = float(stdout.read().decode().strip())

            # Memory Usage
            stdin, stdout, stderr = client.exec_command("free -m | grep Mem | awk '{print $3/$2 * 100.0}'")
            metrics["memory_usage_percent"] = float(stdout.read().decode().strip())

            # Disk Usage (Root partition)
            stdin, stdout, stderr = client.exec_command("df -h / | awk 'NR==2 {print $5}' | sed 's/%//'")
            metrics["disk_usage_percent"] = float(stdout.read().decode().strip())

            # Uptime
            stdin, stdout, stderr = client.exec_command("uptime -p")
            metrics["uptime"] = stdout.read().decode().strip()

            client.close()
            return metrics

        except Exception as e:
            return {"error": f"Failed to fetch metrics: {str(e)}"}