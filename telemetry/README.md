# E-University Network Streaming Telemetry

Real-time network observability stack for the E-University lab environment.

## Architecture

```
┌─────────────────┐    SSH/CLI     ┌─────────────────┐
│  Network        │◄──────────────►│   Collector     │
│  Devices (16)   │                │   (Python)      │
└─────────────────┘                └────────┬────────┘
                                            │
                                            ▼
                                   ┌─────────────────┐
                                   │   InfluxDB 2.x  │
                                   │   (Time-Series) │
                                   └────────┬────────┘
                                            │
                                            ▼
                                   ┌─────────────────┐
                                   │   Grafana       │
                                   │   (Dashboards)  │
                                   └─────────────────┘
```

## Quick Start

```bash
# First time - build and start
./start.sh --build

# Subsequent runs
./start.sh

# View collector logs
./start.sh --logs collector

# Stop everything
./start.sh --stop
```

## Access

| Service  | URL                    | Credentials            |
|----------|------------------------|------------------------|
| Grafana  | http://localhost:3001  | See `.env` file        |
| InfluxDB | http://localhost:8086  | See `.env` file        |

**Note:** Copy `.env.example` to `.env` and configure your credentials before starting.

## Metrics Collected

### Device Health
- **CPU Utilization** - 5 sec, 1 min, 5 min averages
- **Memory Utilization** - Total, used, free, percentage
- **Device Reachability** - Up/down status

### Interface Statistics
- Input/output packet counts
- Input/output bit rates
- Error counters

### Protocol Health
- **OSPF** - Neighbor count, full adjacencies
- **BGP** - Session state, prefix counts per neighbor
- **BFD** - Sessions up/down
- **HSRP** - Active/standby state per group

## Collection Interval

Default: 30 seconds. Modify via `COLLECTION_INTERVAL` environment variable.

## Dashboard Panels

The pre-configured Grafana dashboard includes:
- Device reachability status grid
- CPU/Memory utilization time series
- Protocol health summary stats
- BGP prefix counts over time
- Interface traffic graphs
- Error counters by device

## Customization

### Adding Devices

Edit `collector/devices.py` to add or remove devices from collection.

### Modifying Collection

Edit `collector/collector.py` to:
- Add new metrics
- Change parsing logic
- Adjust collection methods

### Dashboard Changes

Dashboards auto-reload from `grafana/dashboards/`. Edit JSON files or create new ones.

## Troubleshooting

### Collector not connecting to devices
```bash
# Check credentials are loaded
./start.sh --logs collector

# Verify .env file exists in parent directory
cat ../.env
```

### InfluxDB connection errors
```bash
# Check InfluxDB is healthy
docker compose ps
docker compose logs influxdb
```

### No data in Grafana
1. Wait 60 seconds for first collection cycle
2. Check collector logs for errors
3. Verify InfluxDB datasource in Grafana
