# HNG Stage 3 — Anomaly Detection Engine

## Server Details
- **Server IP:** 54.209.135.163
- **Metrics Dashboard:** http://54.209.135.163.nip.io:8080
- **GitHub Repo:** https://github.com/vames1/hng14-stage3-devops

## Language Choice
Built in **Python** because:
- Fast development under deadline pressure
- Rich standard library (collections.deque, statistics)
- Flask makes dashboard serving simple
- subprocess module handles iptables calls cleanly

## How the Sliding Window Works
Two deque-based windows track request rates:
- **Per-IP window:** `{ip: deque([t1, t2, t3...])}` — timestamps of requests from each IP
- **Global window:** `deque([t1, t2, t3...])` — timestamps of all requests

**Eviction logic:** On every new request, we compare the leftmost timestamp against `now - 60`. While it's older than 60 seconds, we call `popleft()` to remove it. This keeps the deque always representing exactly the last 60 seconds. Rate = `len(deque) / 60`.

## How the Baseline Works
- **Window size:** 30 minutes of per-second request counts
- **Recalculation interval:** Every 60 seconds
- **Per-hour slots:** Separate baselines per hour — current hour preferred when it has 10+ samples
- **Floor values:** minimum mean=1.0, stddev=0.5 to prevent false positives on quiet traffic
- Mean and stddev calculated from scratch on each recalculation

## How Detection Works
Two conditions — whichever fires first:
1. **Z-score > 3.0** — `(current_rate - mean) / stddev > 3.0`
2. **Rate > 5x mean** — current rate exceeds 5 times the baseline mean
3. **Error surge** — if 4xx/5xx rate is 3x baseline error rate, thresholds tighten by 40%

## How iptables Blocking Works
When an IP is flagged:
This inserts a DROP rule at position 1 (top of the chain) so it takes effect immediately. All packets from that IP are silently dropped. Auto-unban follows a backoff schedule: 10min → 30min → 2hr → permanent.

## Setup Instructions

### 1. Provision a Linux VPS (minimum t2.small)
### 2. Install Docker and Docker Compose
```bash
sudo dnf install -y docker
sudo systemctl start docker && sudo systemctl enable docker
sudo curl -SL https://github.com/docker/buildx/releases/download/v0.19.3/buildx-v0.19.3.linux-amd64 \
  -o /usr/local/lib/docker/cli-plugins/docker-buildx
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx
```
### 3. Clone the repository
```bash
git clone https://github.com/vames1/hng14-stage3-devops.git
cd hng14-stage3-devops
```
### 4. Add your Slack webhook URL
```bash
nano detector/config.yaml
# Replace YOUR_SLACK_WEBHOOK_URL_HERE with your real webhook URL
```
### 5. Launch all containers
```bash
docker-compose up --build -d
```
### 6. Verify everything is running
```bash
docker ps
docker logs hng-detector
```

## Blog Post
[Coming soon - will be added before submission]

## Blog Post
https://medium.com/@victoroluwaseyi2018/how-i-built-a-real-time-ddos-detection-engine-from-scratch-b071bd746514
