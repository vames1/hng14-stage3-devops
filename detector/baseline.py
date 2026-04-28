import time
import math
from collections import deque

class BaselineManager:
    """
    Maintains a rolling 30-minute baseline of traffic.
    Recalculates mean and stddev every 60 seconds.
    Maintains per-hour slots and prefers current hour's
    baseline when it has enough data.
    """

    def __init__(self, config):
        self.window_minutes = config['baseline_window_minutes']
        self.recalc_interval = config['baseline_recalculation_interval']
        self.min_samples = config['min_baseline_samples']
        self.floor_mean = 1.0      # Minimum mean to avoid division by zero
        self.floor_stddev = 0.5    # Minimum stddev to avoid false positives

        # Rolling window of (timestamp, per_second_count) tuples
        self.window = deque()

        # Per-hour slots: {hour: [per_second_counts]}
        self.hourly_slots = {}

        # Current baseline values
        self.effective_mean = self.floor_mean
        self.effective_stddev = self.floor_stddev
        self.error_mean = 0.1
        self.error_stddev = 0.1

        # Tracking
        self.last_recalc = time.time()
        self.last_second_count = 0
        self.last_second_error_count = 0
        self.current_second = int(time.time())

        # Audit log entries for baseline recalculations
        self.recalc_history = []

    def record_request(self, is_error=False):
        """Record a single request into the current second's bucket."""
        current = int(time.time())
        if current != self.current_second:
            # New second — store the completed second's count
            self._commit_second(
                self.current_second,
                self.last_second_count,
                self.last_second_error_count
            )
            self.current_second = current
            self.last_second_count = 0
            self.last_second_error_count = 0

        self.last_second_count += 1
        if is_error:
            self.last_second_error_count += 1

    def _commit_second(self, second, count, error_count):
        """Add a completed second's count to the rolling window."""
        now = time.time()
        self.window.append((second, count, error_count))

        # Evict entries older than the window
        cutoff = now - (self.window_minutes * 60)
        while self.window and self.window[0][0] < cutoff:
            self.window.popleft()

        # Add to hourly slot
        hour = time.strftime('%H', time.localtime(second))
        if hour not in self.hourly_slots:
            self.hourly_slots[hour] = []
        self.hourly_slots[hour].append((count, error_count))

        # Recalculate if interval has passed
        if now - self.last_recalc >= self.recalc_interval:
            self._recalculate()
            self.last_recalc = now

    def _recalculate(self):
        """
        Recalculate mean and stddev from the rolling window.
        Prefer current hour's data if it has enough samples.
        Apply floor values to prevent false positives on quiet traffic.
        """
        current_hour = time.strftime('%H')

        # Try current hour's data first
        if current_hour in self.hourly_slots and \
           len(self.hourly_slots[current_hour]) >= self.min_samples:
            counts = [c for c, _ in self.hourly_slots[current_hour]]
            error_counts = [e for _, e in self.hourly_slots[current_hour]]
        else:
            # Fall back to full rolling window
            counts = [c for _, c, _ in self.window]
            error_counts = [e for _, _, e in self.window]

        if len(counts) < self.min_samples:
            return  # Not enough data yet

        # Calculate mean
        mean = sum(counts) / len(counts)
        error_mean = sum(error_counts) / len(error_counts)

        # Calculate standard deviation
        variance = sum((x - mean) ** 2 for x in counts) / len(counts)
        stddev = math.sqrt(variance)

        error_variance = sum(
            (x - error_mean) ** 2 for x in error_counts
        ) / len(error_counts)
        error_stddev = math.sqrt(error_variance)

        # Apply floor values
        self.effective_mean = max(mean, self.floor_mean)
        self.effective_stddev = max(stddev, self.floor_stddev)
        self.error_mean = max(error_mean, 0.1)
        self.error_stddev = max(error_stddev, 0.1)

        # Record recalculation for audit log
        entry = {
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'effective_mean': round(self.effective_mean, 4),
            'effective_stddev': round(self.effective_stddev, 4),
            'samples': len(counts),
            'hour': current_hour
        }
        self.recalc_history.append(entry)

        print(f"[Baseline] Recalculated: mean={self.effective_mean:.4f} "
              f"stddev={self.effective_stddev:.4f} samples={len(counts)}")

    def get_baseline(self):
        """Return current baseline values."""
        return {
            'mean': self.effective_mean,
            'stddev': self.effective_stddev,
            'error_mean': self.error_mean,
            'error_stddev': self.error_stddev
        }
