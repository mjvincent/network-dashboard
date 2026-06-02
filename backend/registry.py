import sqlite3
import os

class DeviceRegistry:
    def __init__(self, db_path="devices.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    ip TEXT PRIMARY KEY,
                    hostname TEXT,
                    mac TEXT,
                    vendor TEXT,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def update_device(self, device_info):
        """
        Updates or inserts a device in the registry.
        """
        ip = device_info.get("ip")
        hostname = device_info.get("hostname")
        mac = device_info.get("mac")
        vendor = device_info.get("vendor", "Unknown")

        if not ip:
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO devices (ip, hostname, mac, vendor, last_seen)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(ip) DO UPDATE SET
                    hostname=excluded.hostname,
                    mac=excluded.mac,
                    vendor=excluded.vendor,
                    last_seen=CURRENT_TIMESTAMP
            ''', (ip, hostname, mac, vendor))
            conn.commit()

    def update_devices(self, devices):
        for device in devices:
            self.update_device(device)

    def get_all_devices(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM devices ORDER BY last_seen DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_device(self, ip):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM devices WHERE ip = ?", (ip,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def remove_device(self, ip):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM devices WHERE ip = ?", (ip,))
            conn.commit()