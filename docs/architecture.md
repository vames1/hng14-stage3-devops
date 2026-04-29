# Architecture

Internet → Nginx (port 80) → Nextcloud (port 80)
                ↓
        HNG-nginx-logs volume
                ↓
        Detector Daemon
        ├── monitor.py (tail logs)
        ├── baseline.py (learn normal)
        ├── detector.py (detect anomaly)
        ├── blocker.py (iptables ban)
        ├── unbanner.py (auto release)
        ├── notifier.py (Slack alerts)
        └── dashboard.py (web UI :8080)
