import sqlite3
import os

class DeviceRegistry:
    def __init__(self, db_path=None):
        self.db_path = db_path or os.getenv("DEVICE_DB_PATH", "/data/devices.db")
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
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
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'online'
                )
            ''')
            # Add status column if it doesn't exist (for migration)
            try:
                cursor.execute("ALTER TABLE devices ADD COLUMN status TEXT DEFAULT 'online'")
            except sqlite3.OperationalError:
                pass

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT,
                    ip TEXT,
                    hostname TEXT,
                    mac TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def update_device(self, device_info, cursor=None):
        """
        Updates or inserts a device in the registry.
        """
        ip = device_info.get("ip")
        hostname = device_info.get("hostname")
        mac = device_info.get("mac")
        vendor = device_info.get("vendor", "Unknown")

        if not ip:
            return

        query = '''
            INSERT INTO devices (ip, hostname, mac, vendor, last_seen, status)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 'online')
            ON CONFLICT(ip) DO UPDATE SET
                hostname=excluded.hostname,
                mac=excluded.mac,
                vendor=excluded.vendor,
                last_seen=CURRENT_TIMESTAMP,
                status='online'
        '''

        if cursor:
            cursor.execute(query, (ip, hostname, mac, vendor))
            return

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(query, (ip, hostname, mac, vendor))
            conn.commit()

    def update_devices(self, devices):
        """
        Updates devices from scan results and detects new or disappeared devices.
        """
        new_device_ips = set()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get all currently registered IPs and their status
            cursor.execute("SELECT ip, status FROM devices")
            existing_devices = {row['ip']: row['status'] for row in cursor.fetchall()}
            
            for device in devices:
                ip = device.get("ip")
                if not ip:
                    continue
                new_device_ips.add(ip)
                
                is_new = ip not in existing_devices
                self.update_device(device, cursor=cursor)
                
                if is_new:
                    # Create discovery alert
                    hostname = device.get("hostname", "Unknown")
                    mac = device.get("mac", "Unknown")
                    cursor.execute('''
                        INSERT INTO alerts (type, ip, hostname, mac)
                        VALUES (?, ?, ?, ?)
                    ''', ('discovery', ip, hostname, mac))

            # Check for disappeared devices
            for ip, status in existing_devices.items():
                if ip not in new_device_ips and status == 'online':
                    # Device disappeared
                    cursor.execute("UPDATE devices SET status = 'offline' WHERE ip = ?", (ip,))
                    
                    # Get info for the alert
                    cursor.execute("SELECT hostname, mac FROM devices WHERE ip = ?", (ip,))
                    row = cursor.fetchone()
                    hostname = row['hostname'] if row else "Unknown"
                    mac = row['mac'] if row else "Unknown"
                    
                    cursor.execute('''
                        INSERT INTO alerts (type, ip, hostname, mac)
                        VALUES (?, ?, ?, ?)
                    ''', ('disconnection', ip, hostname, mac))
            
            conn.commit()

    def get_alerts(self, limit=20):
        """
        Returns the recent alerts.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

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
