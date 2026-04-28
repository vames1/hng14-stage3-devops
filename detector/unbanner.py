import time
import threading

class Unbanner:
    """
    Runs in a background thread checking banned IPs.
    Releases bans according to the backoff schedule.
    Sends Slack notification on every unban.
    """

    def __init__(self, config, blocker, notifier, audit_logger):
        self.blocker = blocker
        self.notifier = notifier
        self.audit_logger = audit_logger
        self.running = False

    def start(self):
        """Start the unbanner in a background thread."""
        self.running = True
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()
        print("[Unbanner] Started background unban thread")

    def _run(self):
        """
        Main loop — checks every 60 seconds for IPs
        whose ban duration has expired.
        """
        while self.running:
            self._check_bans()
            time.sleep(60)

    def _check_bans(self):
        """Check all banned IPs and release expired bans."""
        now = time.time()
        # Copy to avoid modifying dict while iterating
        banned = dict(self.blocker.get_banned_ips())

        for ip, info in banned.items():
            duration = info.get('duration', -1)

            # Skip permanent bans
            if duration == -1:
                continue

            banned_at = info.get('banned_at', now)
            elapsed = now - banned_at

            if elapsed >= duration:
                # Ban has expired — release it
                success = self.blocker.unban(ip)

                if success:
                    # Remove from banned_ips tracking
                    del self.blocker.banned_ips[ip]

                    # Send Slack notification
                    self.notifier.send_unban_alert(
                        ip=ip,
                        duration=duration,
                        reason=info.get('reason', 'unknown')
                    )

                    # Write audit log entry
                    self.audit_logger.log_unban(
                        ip=ip,
                        duration=duration,
                        reason=info.get('reason', 'unknown')
                    )

    def stop(self):
        """Stop the unbanner thread."""
        self.running = False
