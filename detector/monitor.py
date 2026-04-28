import time
import os
from collections import deque

class LogMonitor:
    def __init__(self, config):
        self.log_path = config["log_path"]
        self.window_seconds = config["sliding_window_seconds"]
        self.ip_windows = {}
        self.global_window = deque()
        self.ip_errors = {}

    def tail(self):
        import json
        while not os.path.exists(self.log_path):
            print(f"[Monitor] Waiting for log file: {self.log_path}")
            time.sleep(2)

        print(f"[Monitor] Tailing log file: {self.log_path}")
        last_size = os.path.getsize(self.log_path)

        with open(self.log_path, "r") as f:
            f.seek(0, 2)  # seek to end
            while True:
                current_size = os.path.getsize(self.log_path)
                if current_size > last_size:
                    # New data available
                    new_data = f.read()
                    if new_data:
                        lines = new_data.splitlines()
                        for line in lines:
                            line = line.strip()
                            if line:
                                print(f"[Monitor] New line: {line[:80]}")
                                yield line
                    last_size = current_size
                else:
                    time.sleep(0.1)

    def parse_line(self, line):
        import json
        try:
            return json.loads(line)
        except:
            return None

    def record_request(self, ip, timestamp, status):
        now = time.time()
        if ip not in self.ip_windows:
            self.ip_windows[ip] = deque()
        self.ip_windows[ip].append(now)
        while self.ip_windows[ip] and self.ip_windows[ip][0] < now - self.window_seconds:
            self.ip_windows[ip].popleft()
        self.global_window.append(now)
        while self.global_window and self.global_window[0] < now - self.window_seconds:
            self.global_window.popleft()
        if status >= 400:
            if ip not in self.ip_errors:
                self.ip_errors[ip] = deque()
            self.ip_errors[ip].append(now)
            while self.ip_errors[ip] and self.ip_errors[ip][0] < now - self.window_seconds:
                self.ip_errors[ip].popleft()

    def get_ip_rate(self, ip):
        if ip not in self.ip_windows:
            return 0.0
        return len(self.ip_windows[ip]) / self.window_seconds

    def get_global_rate(self):
        return len(self.global_window) / self.window_seconds

    def get_ip_error_rate(self, ip):
        if ip not in self.ip_errors:
            return 0.0
        return len(self.ip_errors[ip]) / self.window_seconds

    def get_top_ips(self, n=10):
        ip_counts = {ip: len(w) for ip, w in self.ip_windows.items() if w}
        return sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:n]
