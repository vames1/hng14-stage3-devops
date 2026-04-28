import subprocess
import time

class Blocker:
    """
    Manages iptables rules to block and unblock IPs.
    Tracks ban counts per IP for backoff schedule.
    Must run as root or with CAP_NET_ADMIN capability.
    """

    def __init__(self, config):
        self.ban_schedule = config['ban_schedule']
        # {ip: {'banned_at': timestamp, 'ban_count': int, 'reason': str}}
        self.banned_ips = {}

    def ban(self, ip, reason):
        """
        Add an iptables DROP rule for the given IP.
        Returns ban duration in seconds (-1 = permanent).
        """
        if ip in self.banned_ips:
            # IP was banned before — increment ban count
            self.banned_ips[ip]['ban_count'] += 1
        else:
            self.banned_ips[ip] = {'ban_count': 0}

        ban_count = self.banned_ips[ip]['ban_count']

        # Get duration from backoff schedule
        if ban_count >= len(self.ban_schedule):
            duration = -1  # Permanent
        else:
            duration = self.ban_schedule[ban_count]

        # Add iptables DROP rule
        try:
            subprocess.run([
                'iptables', '-I', 'INPUT', '1',
                '-s', ip,
                '-j', 'DROP',
                '-m', 'comment',
                '--comment', f'hng-detector-ban'
            ], check=True, capture_output=True)

            self.banned_ips[ip].update({
                'banned_at': time.time(),
                'reason': reason,
                'duration': duration
            })

            print(f"[Blocker] Banned {ip} for "
                  f"{'permanent' if duration == -1 else f'{duration}s'} "
                  f"| reason: {reason}")

        except subprocess.CalledProcessError as e:
            print(f"[Blocker] Failed to ban {ip}: {e.stderr.decode()}")

        return duration

    def unban(self, ip):
        """Remove iptables DROP rule for the given IP."""
        try:
            subprocess.run([
                'iptables', '-D', 'INPUT',
                '-s', ip,
                '-j', 'DROP',
                '-m', 'comment',
                '--comment', f'hng-detector-ban'
            ], check=True, capture_output=True)

            print(f"[Blocker] Unbanned {ip}")
            return True

        except subprocess.CalledProcessError as e:
            print(f"[Blocker] Failed to unban {ip}: {e.stderr.decode()}")
            return False

    def is_banned(self, ip):
        """Check if an IP is currently banned."""
        return ip in self.banned_ips and \
               self.banned_ips[ip].get('banned_at') is not None

    def get_banned_ips(self):
        """Return all currently banned IPs with their details."""
        return self.banned_ips
