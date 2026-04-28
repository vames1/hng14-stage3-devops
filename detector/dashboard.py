import time
import psutil
import threading
from flask import Flask, jsonify, render_template_string

# HTML template for the dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>HNG Anomaly Detector Dashboard</title>
    <meta http-equiv="refresh" content="3">
    <style>
        body { font-family: monospace; background: #0d1117; color: #c9d1d9; padding: 20px; }
        h1 { color: #58a6ff; }
        h2 { color: #79c0ff; border-bottom: 1px solid #30363d; padding-bottom: 5px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; }
        .stat { font-size: 2em; color: #58a6ff; font-weight: bold; }
        .label { color: #8b949e; font-size: 0.85em; }
        table { width: 100%; border-collapse: collapse; }
        th { text-align: left; color: #8b949e; padding: 5px; border-bottom: 1px solid #30363d; }
        td { padding: 5px; border-bottom: 1px solid #21262d; }
        .banned { color: #f85149; }
        .normal { color: #3fb950; }
        .warn { color: #d29922; }
        .uptime { color: #3fb950; }
    </style>
</head>
<body>
    <h1>🛡️ HNG Anomaly Detection Engine</h1>
    <p class="uptime">Uptime: {{ uptime }} | Last updated: {{ timestamp }}</p>

    <div class="grid">
        <div class="card">
            <div class="label">Global Request Rate</div>
            <div class="stat">{{ global_rate }} req/s</div>
        </div>
        <div class="card">
            <div class="label">Baseline Mean / StdDev</div>
            <div class="stat">{{ mean }} / {{ stddev }}</div>
        </div>
        <div class="card">
            <div class="label">CPU Usage</div>
            <div class="stat">{{ cpu }}%</div>
        </div>
        <div class="card">
            <div class="label">Memory Usage</div>
            <div class="stat">{{ memory }}%</div>
        </div>
    </div>

    <br>
    <h2>🚫 Banned IPs ({{ banned_count }})</h2>
    <table>
        <tr><th>IP</th><th>Reason</th><th>Duration</th><th>Banned At</th></tr>
        {% for ip, info in banned_ips.items() %}
        <tr>
            <td class="banned">{{ ip }}</td>
            <td>{{ info.reason }}</td>
            <td>{{ 'permanent' if info.duration == -1 else (info.duration // 60)|string + ' min' }}</td>
            <td>{{ info.banned_at|int }}</td>
        </tr>
        {% endfor %}
    </table>

    <br>
    <h2>📊 Top 10 Source IPs</h2>
    <table>
        <tr><th>IP</th><th>Requests (last 60s)</th></tr>
        {% for ip, count in top_ips %}
        <tr>
            <td>{{ ip }}</td>
            <td>{{ count }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

class Dashboard:
    """
    Serves a live web dashboard using Flask.
    Refreshes every 3 seconds showing all key metrics.
    """

    def __init__(self, config, monitor, baseline_mgr, blocker):
        self.port = config['dashboard']['port']
        self.monitor = monitor
        self.baseline_mgr = baseline_mgr
        self.blocker = blocker
        self.start_time = time.time()
        self.app = Flask(__name__)
        self._register_routes()

    def _register_routes(self):
        """Register Flask routes."""

        @self.app.route('/')
        def index():
            baseline = self.baseline_mgr.get_baseline()
            uptime_seconds = int(time.time() - self.start_time)
            hours = uptime_seconds // 3600
            minutes = (uptime_seconds % 3600) // 60
            seconds = uptime_seconds % 60

            return render_template_string(DASHBOARD_HTML,
                global_rate=f"{self.monitor.get_global_rate():.2f}",
                mean=f"{baseline['mean']:.2f}",
                stddev=f"{baseline['stddev']:.2f}",
                cpu=f"{psutil.cpu_percent():.1f}",
                memory=f"{psutil.virtual_memory().percent:.1f}",
                banned_ips=self.blocker.get_banned_ips(),
                banned_count=len(self.blocker.get_banned_ips()),
                top_ips=self.monitor.get_top_ips(10),
                timestamp=time.strftime('%Y-%m-%dT%H:%M:%S'),
                uptime=f"{hours}h {minutes}m {seconds}s"
            )

        @self.app.route('/api/metrics')
        def metrics():
            baseline = self.baseline_mgr.get_baseline()
            return jsonify({
                'global_rate': self.monitor.get_global_rate(),
                'baseline': baseline,
                'banned_ips': list(self.blocker.get_banned_ips().keys()),
                'top_ips': self.monitor.get_top_ips(10),
                'cpu': psutil.cpu_percent(),
                'memory': psutil.virtual_memory().percent,
                'uptime': int(time.time() - self.start_time)
            })

    def start(self):
        """Start Flask dashboard in a background thread."""
        thread = threading.Thread(
            target=lambda: self.app.run(
                host='0.0.0.0',
                port=self.port,
                debug=False
            ),
            daemon=True
        )
        thread.start()
        print(f"[Dashboard] Started on port {self.port}")
