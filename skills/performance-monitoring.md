# Performance & Monitoring Skills

## Real-Time Monitoring

- **CPU monitoring** — Per-core usage, frequency, temperature
- **Memory monitoring** — RAM and swap usage with trends
- **Disk I/O** — Read/write throughput per device
- **Network I/O** — Interface traffic rates and totals

**Modules:** `utils/monitor.py`, `services/hardware/temperature.py`
**UI:** Monitor Tab
**CLI:** `health`, `temperature`

## Health Timeline

- **Health metrics database** — SQLite-backed historical health data
- **Anomaly detection** — Automatic detection of unusual system behavior
- **Trend analysis** — Track performance over time with visualizations
- **Health scoring** — Composite system health score (0-100)

**Modules:** `utils/health_timeline.py`, `utils/health_score.py`
**UI:** Health Timeline Tab
**CLI:** `health-history`

## Auto-Tuning

- **Workload detection** — Identify current workload type (gaming, development, server)
- **Kernel tuning** — Automatically adjust kernel parameters for workload
- **Swappiness control** — Dynamic swap behavior adjustment
- **I/O scheduler** — Select optimal I/O scheduler for storage type

**Modules:** `utils/auto_tuner.py`, `utils/performance.py`
**UI:** Performance Tab
**CLI:** `tuner`, `advanced`

## Power Management

- **Power profiles** — Switch between power-saver, balanced, performance
- **Battery limits** — Set charging thresholds to extend battery life
- **Battery monitoring** — Charge level, health, cycle count tracking

**Modules:** `core/executor/operations.py` (TweakOps), `services/hardware/battery.py`
**UI:** Hardware Tab, Profiles Tab
**CLI:** `tweak`

## ZRAM Management

- **ZRAM swap** — Configure compressed RAM swap devices
- **Size tuning** — Adjust ZRAM size based on available RAM
- **Compression algorithm** — Select compression (zstd, lz4, lzo)

**Modules:** `utils/zram.py`
**UI:** Performance Tab

## Network Monitoring

- **Interface monitoring** — Track network interface state and throughput
- **Connection status** — Verify internet connectivity
- **DNS resolution** — Test DNS resolver performance

**Modules:** `utils/network_monitor.py`
**UI:** Network Tab
**CLI:** `netmon`

## Smart Logs

- **Intelligent filtering** — AI-assisted log analysis and categorization
- **Pattern detection** — Identify recurring errors and warnings
- **Log export** — Export filtered logs to file

**Modules:** `utils/smart_logs.py`, `utils/journal.py`
**UI:** Logs Tab
**CLI:** `logs`
