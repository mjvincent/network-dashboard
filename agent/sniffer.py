import scapy.all as scapy
import threading
import os
from collections import Counter

class NetworkSniffer:
    # Map common IP protocol numbers to readable names
    PROTOCOL_MAP = {
        1: "ICMP",
        2: "IGMP",
        6: "TCP",
        17: "UDP",
        58: "ESP",
        89: "OSPF"
    }

    def __init__(self):
        self.packet_counts = Counter()
        self.seen_ips = set()
        self.running = False
        self.thread = None

    def _packet_callback(self, packet):
        if packet.haslayer(scapy.IP):
            proto_num = packet[scapy.IP].proto
            proto_name = self.PROTOCOL_MAP.get(proto_num, f"proto_{proto_num}")
            
            # Count protocol usage
            self.packet_counts[proto_name] += 1
            
            # Track seen IP addresses for device discovery
            src_ip = packet[scapy.IP].src
            dst_ip = packet[scapy.IP].dst
            self.seen_ips.add(src_ip)
            self.seen_ips.add(dst_ip)

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._sniff_loop, daemon=True)
        self.thread.start()

    def _sniff_loop(self):
        # Note: sniffing often requires root privileges
        scapy.sniff(prn=self._packet_callback, store=False, stop_filter=self._stop_filter)

    def _stop_filter(self, packet):
        return not self.running

    def stop(self):
        self.running = False

    def get_metrics(self):
        # Return a copy of the current counts and seen IPs
        return {
            "protocols": dict(self.packet_counts),
            "seen_ips": list(self.seen_ips)
        }

if __name__ == "__main__":
    # For testing purposes
    sniffer = NetworkSniffer()
    print("Starting sniffer test...")
    sniffer.start()
    import time
    time.sleep(10)
    print("Metrics captured:", sniffer.get_metrics())
    sniffer.stop()