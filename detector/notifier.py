import requests
import time
import yaml

class Notifier:
    """
    Sends Slack webhook notifications for ban, unban,
    and global anomaly events.
    """

    def __init__(self, config):
        self.webhook_url = config['slack']['webhook_url']

    def _send(self, message):
        """Send a message to Slack via webhook."""
        if self.webhook_url == "YOUR_SLACK_WEBHOOK_URL_HERE":
            print(f"[Notifier] Slack not configured. Message: {message}")
            return

        try:
            response = requests.post(
                self.webhook_url,
                json={"text": message},
                timeout=5
            )
            if response.status_code != 200:
                print(f"[Notifier] Slack error: {response.status_code}")
        except requests.RequestException as e:
            print(f"[Notifier] Failed to send Slack alert: {e}")

    def send_ban_alert(self, ip, reason, rate, baseline, duration):
        """Send a Slack alert when an IP is banned."""
        duration_str = 'permanent' if duration == -1 \
                       else f'{duration // 60} minutes'
        message = (
            f"🚨 *IP BANNED*\n"
            f"*IP:* `{ip}`\n"
            f"*Condition:* {reason}\n"
            f"*Current Rate:* {rate:.2f} req/s\n"
            f"*Baseline Mean:* {baseline['mean']:.2f} req/s\n"
            f"*Ban Duration:* {duration_str}\n"
            f"*Timestamp:* {time.strftime('%Y-%m-%dT%H:%M:%S')}"
        )
        print(f"[Notifier] Sending ban alert for {ip}")
        self._send(message)

    def send_unban_alert(self, ip, duration, reason):
        """Send a Slack alert when an IP is unbanned."""
        duration_str = f'{duration // 60} minutes'
        message = (
            f"✅ *IP UNBANNED*\n"
            f"*IP:* `{ip}`\n"
            f"*Was banned for:* {duration_str}\n"
            f"*Original reason:* {reason}\n"
            f"*Timestamp:* {time.strftime('%Y-%m-%dT%H:%M:%S')}"
        )
        print(f"[Notifier] Sending unban alert for {ip}")
        self._send(message)

    def send_global_alert(self, reason, rate, baseline):
        """Send a Slack alert for global traffic anomaly."""
        message = (
            f"⚠️ *GLOBAL TRAFFIC ANOMALY*\n"
            f"*Condition:* {reason}\n"
            f"*Global Rate:* {rate:.2f} req/s\n"
            f"*Baseline Mean:* {baseline['mean']:.2f} req/s\n"
            f"*Action:* Alert only — no IP block\n"
            f"*Timestamp:* {time.strftime('%Y-%m-%dT%H:%M:%S')}"
        )
        print(f"[Notifier] Sending global anomaly alert")
        self._send(message)
