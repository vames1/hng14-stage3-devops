import time
import yaml
import os
import threading
from monitor import LogMonitor
from baseline import BaselineManager
from detector import AnomalyDetector
from blocker import Blocker
from unbanner import Unbanner
from notifier import Notifier
from dashboard import Dashboard

class AuditLogger:
    def __init__(self, log_path):
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

    def _write(self, entry):
        with open(self.log_path, "a") as f:
            f.write(entry + "\n")
        print(f"[Audit] {entry}")

    def log_ban(self, ip, condition, rate, baseline, duration):
        duration_str = "permanent" if duration == -1 else f"{duration}s"
        entry = (f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] BAN {ip} | "
                 f"condition={condition} | rate={rate:.2f} | "
                 f"baseline={baseline['mean']:.2f} | duration={duration_str}")
        self._write(entry)

    def log_unban(self, ip, duration, reason):
        duration_str = "permanent" if duration == -1 else f"{duration}s"
        entry = (f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] UNBAN {ip} | "
                 f"reason={reason} | duration={duration_str}")
        self._write(entry)

    def log_baseline(self, mean, stddev, samples):
        entry = (f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] BASELINE_RECALC | "
                 f"mean={mean:.4f} | stddev={stddev:.4f} | samples={samples}")
        self._write(entry)


def main():
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    print("[Main] Starting HNG Anomaly Detection Engine...")

    monitor      = LogMonitor(config)
    baseline_mgr = BaselineManager(config)
    detector     = AnomalyDetector(config)
    blocker      = Blocker(config)
    notifier     = Notifier(config)
    audit_logger = AuditLogger(config["audit_log_path"])

    unbanner = Unbanner(config, blocker, notifier, audit_logger)
    unbanner.start()

    dashboard = Dashboard(config, monitor, baseline_mgr, blocker)
    dashboard.start()

    print("[Main] All modules started. Entering detection loop...")

    line_count = 0
    for line in monitor.tail():
        entry = monitor.parse_line(line)
        if not entry:
            continue

        ip     = entry.get("source_ip", "")
        status = int(entry.get("status", 200))

        if not ip:
            continue

        line_count += 1
        if line_count % 5 == 0:
            print(f"[Main] Lines={line_count} global={monitor.get_global_rate():.2f} req/s")

        if blocker.is_banned(ip):
            continue

        is_error = status >= 400
        monitor.record_request(ip, entry.get("timestamp"), status)
        baseline_mgr.record_request(is_error=is_error)

        ip_rate       = monitor.get_ip_rate(ip)
        global_rate   = monitor.get_global_rate()
        ip_error_rate = monitor.get_ip_error_rate(ip)
        baseline      = baseline_mgr.get_baseline()

        print(f"[Debug] ip={ip} rate={ip_rate:.2f} mean={baseline['mean']:.2f} stddev={baseline['stddev']:.2f}")

        ip_result = detector.check_ip(ip, ip_rate, ip_error_rate, baseline)
        if ip_result["is_anomalous"]:
            print(f"[ALERT] ANOMALY: {ip} | {ip_result['reason']}")
            duration = blocker.ban(ip, ip_result["reason"])
            notifier.send_ban_alert(ip=ip, reason=ip_result["reason"],
                rate=ip_rate, baseline=baseline, duration=duration)
            audit_logger.log_ban(ip=ip, condition=ip_result["reason"],
                rate=ip_rate, baseline=baseline, duration=duration)
            continue

        global_result = detector.check_global(global_rate, baseline)
        if global_result["is_anomalous"]:
            print(f"[ALERT] GLOBAL: {global_result['reason']}")
            notifier.send_global_alert(reason=global_result["reason"],
                rate=global_rate, baseline=baseline)

if __name__ == "__main__":
    main()
