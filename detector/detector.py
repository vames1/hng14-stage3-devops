import time

class AnomalyDetector:
    """
    Compares current traffic rates against the baseline.
    Uses z-score and rate multiplier to detect anomalies.
    Tightens thresholds automatically on error surges.
    """

    def __init__(self, config):
        self.zscore_threshold = config['zscore_threshold']
        self.rate_multiplier = config['rate_multiplier_threshold']
        self.error_rate_multiplier = config['error_rate_multiplier']

    def compute_zscore(self, current_rate, mean, stddev):
        """
        Z-score tells us how many standard deviations the current
        rate is away from the mean. Formula: (value - mean) / stddev
        A z-score above 3.0 means the rate is extremely abnormal.
        """
        if stddev == 0:
            return 0.0
        return (current_rate - mean) / stddev

    def check_ip(self, ip, ip_rate, ip_error_rate, baseline):
        """
        Check if a single IP is behaving anomalously.
        Returns a dict with is_anomalous, reason, zscore, rate.
        """
        mean = baseline['mean']
        stddev = baseline['stddev']
        error_mean = baseline['error_mean']

        # Check if this IP has an error surge
        # If so, tighten detection thresholds automatically
        error_surge = ip_error_rate > (error_mean * self.error_rate_multiplier)
        if error_surge:
            # Tighten thresholds by 40% during error surge
            zscore_threshold = self.zscore_threshold * 0.6
            rate_threshold = self.rate_multiplier * 0.6
        else:
            zscore_threshold = self.zscore_threshold
            rate_threshold = self.rate_multiplier

        # Calculate z-score for this IP
        zscore = self.compute_zscore(ip_rate, mean, stddev)

        # Fire on z-score OR rate multiplier — whichever comes first
        if zscore > zscore_threshold:
            return {
                'is_anomalous': True,
                'reason': f'z-score {zscore:.2f} exceeds threshold {zscore_threshold:.2f}',
                'zscore': zscore,
                'rate': ip_rate,
                'error_surge': error_surge
            }

        if mean > 0 and ip_rate > (mean * rate_threshold):
            return {
                'is_anomalous': True,
                'reason': f'rate {ip_rate:.2f} is {ip_rate/mean:.1f}x baseline mean',
                'zscore': zscore,
                'rate': ip_rate,
                'error_surge': error_surge
            }

        return {
            'is_anomalous': False,
            'reason': 'normal',
            'zscore': zscore,
            'rate': ip_rate,
            'error_surge': error_surge
        }

    def check_global(self, global_rate, baseline):
        """
        Check if global traffic is anomalous.
        Global anomaly triggers Slack alert only — no IP block.
        """
        mean = baseline['mean']
        stddev = baseline['stddev']

        zscore = self.compute_zscore(global_rate, mean, stddev)

        if zscore > self.zscore_threshold:
            return {
                'is_anomalous': True,
                'reason': f'global z-score {zscore:.2f} exceeds {self.zscore_threshold}',
                'zscore': zscore,
                'rate': global_rate
            }

        if mean > 0 and global_rate > (mean * self.rate_multiplier):
            return {
                'is_anomalous': True,
                'reason': f'global rate {global_rate:.2f} is {global_rate/mean:.1f}x baseline',
                'zscore': zscore,
                'rate': global_rate
            }

        return {
            'is_anomalous': False,
            'reason': 'normal',
            'zscore': zscore,
            'rate': global_rate
        }
