import json
import time
import os
from collections import deque

class LogMonitor:
    """
    Continuously tails the Nginx access log and parses each line.
    Uses a deque-based sliding window to track per-IP and global
    request rates over the last 60 seconds.
    """

    def __init__(self, config):
        self.log_path = config['log_path']
        self.window_seconds = config['sliding_window_seconds']
        # per-IP sliding window: {ip: deque of timestamps}
        self.ip_windows = {}
        # global sliding window: deque of timestamps
        self.global_window = deque()
        # per-IP error tracking: {ip: deque of (timestamp, status)}
        self.ip_errors = {}

    def tail(self):
        """
        Generator that yields new log lines as they appear.
        Waits for the log file to exist, then reads from the end.
        """
        # Wait until log file exists
        while not os.path.exists(self.log_path):
            print(f"[Monitor] Waiting for log file: {self.log_path}")
            time.sleep(2)

        with open(self.log_path, 'r') as f:
            # Move to end of file - we only want new lines
            f.seek(0, 2)
            print(f"[Monitor] Tailing log file: {self.log_path}")
            while True:
                line = f.readline()
                if line:
                    yield line.strip()
                else:
                    time.sleep(0.1)  # Small sleep to avoid busy waiting

    def parse_line(self, line):
        """
        Parse a JSON log line into a dictionary.
        Returns None if the line is not valid JSON.
        """
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return None

    def record_request(self, ip, timestamp, status):
        """
        Add a request to the sliding windows for this IP and globally.
        Evicts entries older than window_seconds automatically.
        """
        now = time.time()

        # --- Per-IP sliding window ---
        if ip not in self.ip_windows:
            self.ip_windows[ip] = deque()
        self.ip_windows[ip].append(now)

        # Evict old entries outside the window
        while self.ip_windows[ip] and \
              self.ip_windows[ip][0] < now - self.window_seconds:
            self.ip_windows[ip].popleft()

        # --- Global sliding window ---
        self.global_window.append(now)
        while self.global_window and \
              self.global_window[0] < now - self.window_seconds:
            self.global_window.popleft()

        # --- Per-IP error tracking ---
        if status >= 400:
            if ip not in self.ip_errors:
                self.ip_errors[ip] = deque()
            self.ip_errors[ip].append(now)
            while self.ip_errors[ip] and \
                  self.ip_errors[ip][0] < now - self.window_seconds:
                self.ip_errors[ip].popleft()

    def get_ip_rate(self, ip):
        """Return requests per second for a given IP over the window."""
        if ip not in self.ip_windows:
            return 0.0
        return len(self.ip_windows[ip]) / self.window_seconds

    def get_global_rate(self):
        """Return global requests per second over the window."""
        return len(self.global_window) / self.window_seconds

    def get_ip_error_rate(self, ip):
        """Return error requests per second for a given IP."""
        if ip not in self.ip_errors:
            return 0.0
        return len(self.ip_errors[ip]) / self.window_seconds

    def get_top_ips(self, n=10):
        """Return top N IPs by request count in current window."""
        ip_counts = {
            ip: len(window)
            for ip, window in self.ip_windows.items()
            if window
        }
        return sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:n]
