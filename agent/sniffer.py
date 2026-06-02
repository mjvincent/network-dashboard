import scapy.all as scapy
import threading
import os
from collections import Counter

class NetworkSniffer:
    def __init__(self):
        self.packet_counts = Counter()
        self.running = False
        self.thread = None

    def _packet_callback(self, packet):
        if packet.haslayer(scapy.IP):
            proto = packet[scapy.IP].proto
            # Simplified: just counting protocol numbers
            self.packet_counts[proto] += 1

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
        # Return a copy of the current counts
        return dict(self.packet_counts)

if __name__ == "__main__":
    # For testing purposes
    sniffer = NetworkSniffer()
    print("Starting sniffer test...")
    sniffer.start()
    import time
    time.sleep(10)
    print("Metrics captured:", sniffer.get_metrics())
    sniffer.stop()