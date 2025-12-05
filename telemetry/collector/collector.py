#!/usr/bin/env python3
"""
E-University Network Telemetry Collector

Collects metrics from network devices and pushes to InfluxDB.
Metrics collected:
- Device health (CPU, memory)
- Interface statistics (bytes, packets, errors)
- Protocol health (BGP, OSPF, BFD, HSRP)
"""

import os
import re
import time
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional

from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from devices import DEVICES

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment configuration
INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', 'euniv-super-secret-token')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', 'euniv')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', 'network_telemetry')
DEVICE_USERNAME = os.getenv('DEVICE_USERNAME', 'admin')
DEVICE_PASSWORD = os.getenv('DEVICE_PASSWORD', 'admin')
DEVICE_ENABLE_PASSWORD = os.getenv('DEVICE_ENABLE_PASSWORD', 'admin')
COLLECTION_INTERVAL = int(os.getenv('COLLECTION_INTERVAL', '30'))


class TelemetryCollector:
    """Collects telemetry from Cisco IOS-XE devices."""

    def __init__(self):
        self.influx_client = InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        )
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)

    def connect_device(self, hostname: str, device_info: Dict) -> Optional[Any]:
        """Establish SSH connection to a device."""
        try:
            device = {
                'device_type': 'cisco_xe',
                'host': device_info['host'],
                'username': DEVICE_USERNAME,
                'password': DEVICE_PASSWORD,
                'secret': DEVICE_ENABLE_PASSWORD,
                'timeout': 30,
                'session_timeout': 60,
            }
            conn = ConnectHandler(**device)
            conn.enable()
            return conn
        except NetmikoTimeoutException:
            logger.warning(f"Timeout connecting to {hostname}")
            return None
        except NetmikoAuthenticationException:
            logger.warning(f"Authentication failed for {hostname}")
            return None
        except Exception as e:
            logger.warning(f"Failed to connect to {hostname}: {e}")
            return None

    def collect_cpu_memory(self, conn: Any, hostname: str, device_info: Dict) -> List[Point]:
        """Collect CPU and memory utilization."""
        points = []
        try:
            # CPU utilization
            cpu_output = conn.send_command('show processes cpu | include CPU')
            # Parse: CPU utilization for five seconds: 5%/0%; one minute: 6%; five minutes: 6%
            cpu_match = re.search(r'five seconds: (\d+)%.*one minute: (\d+)%.*five minutes: (\d+)%', cpu_output)
            if cpu_match:
                points.append(
                    Point("cpu_utilization")
                    .tag("device", hostname)
                    .tag("role", device_info['role'])
                    .tag("campus", device_info['campus'])
                    .field("five_sec", int(cpu_match.group(1)))
                    .field("one_min", int(cpu_match.group(2)))
                    .field("five_min", int(cpu_match.group(3)))
                )

            # Memory utilization
            mem_output = conn.send_command('show memory statistics | include Processor')
            # Parse: Processor  7FDB89324048   2342404364   255217360   2087187004
            # Format: Processor <hex_addr> <total> <used> <free>
            mem_match = re.search(r'Processor\s+\S+\s+(\d+)\s+(\d+)\s+(\d+)', mem_output)
            if mem_match:
                total = int(mem_match.group(1))
                used = int(mem_match.group(2))
                free = int(mem_match.group(3))
                utilization = (used / total * 100) if total > 0 else 0
                points.append(
                    Point("memory_utilization")
                    .tag("device", hostname)
                    .tag("role", device_info['role'])
                    .tag("campus", device_info['campus'])
                    .field("total_bytes", total)
                    .field("used_bytes", used)
                    .field("free_bytes", free)
                    .field("utilization_pct", round(utilization, 2))
                )
        except Exception as e:
            logger.warning(f"Error collecting CPU/memory from {hostname}: {e}")

        return points

    def collect_interfaces(self, conn: Any, hostname: str, device_info: Dict) -> List[Point]:
        """Collect interface statistics."""
        points = []
        try:
            output = conn.send_command('show interfaces | include ^Gi|packets input|packets output|input errors|output errors|input rate|output rate')

            current_interface = None
            interface_data = {}

            for line in output.split('\n'):
                # Match interface name
                if_match = re.match(r'^(Gi\S+)', line)
                if if_match:
                    # Save previous interface data
                    if current_interface and interface_data:
                        points.append(
                            Point("interface_stats")
                            .tag("device", hostname)
                            .tag("interface", current_interface)
                            .tag("role", device_info['role'])
                            .tag("campus", device_info['campus'])
                            .field("input_packets", interface_data.get('input_packets', 0))
                            .field("output_packets", interface_data.get('output_packets', 0))
                            .field("input_errors", interface_data.get('input_errors', 0))
                            .field("output_errors", interface_data.get('output_errors', 0))
                            .field("input_rate_bps", interface_data.get('input_rate', 0))
                            .field("output_rate_bps", interface_data.get('output_rate', 0))
                        )
                    current_interface = if_match.group(1)
                    interface_data = {}
                    continue

                # Parse packet counts
                if 'packets input' in line:
                    pkt_match = re.search(r'(\d+) packets input', line)
                    if pkt_match:
                        interface_data['input_packets'] = int(pkt_match.group(1))
                elif 'packets output' in line:
                    pkt_match = re.search(r'(\d+) packets output', line)
                    if pkt_match:
                        interface_data['output_packets'] = int(pkt_match.group(1))
                elif 'input errors' in line:
                    err_match = re.search(r'(\d+) input errors', line)
                    if err_match:
                        interface_data['input_errors'] = int(err_match.group(1))
                elif 'output errors' in line:
                    err_match = re.search(r'(\d+) output errors', line)
                    if err_match:
                        interface_data['output_errors'] = int(err_match.group(1))
                elif 'input rate' in line:
                    rate_match = re.search(r'(\d+) bits/sec', line)
                    if rate_match:
                        interface_data['input_rate'] = int(rate_match.group(1))
                elif 'output rate' in line:
                    rate_match = re.search(r'(\d+) bits/sec', line)
                    if rate_match:
                        interface_data['output_rate'] = int(rate_match.group(1))

            # Don't forget the last interface
            if current_interface and interface_data:
                points.append(
                    Point("interface_stats")
                    .tag("device", hostname)
                    .tag("interface", current_interface)
                    .tag("role", device_info['role'])
                    .tag("campus", device_info['campus'])
                    .field("input_packets", interface_data.get('input_packets', 0))
                    .field("output_packets", interface_data.get('output_packets', 0))
                    .field("input_errors", interface_data.get('input_errors', 0))
                    .field("output_errors", interface_data.get('output_errors', 0))
                    .field("input_rate_bps", interface_data.get('input_rate', 0))
                    .field("output_rate_bps", interface_data.get('output_rate', 0))
                )

        except Exception as e:
            logger.warning(f"Error collecting interfaces from {hostname}: {e}")

        return points

    def collect_bgp(self, conn: Any, hostname: str, device_info: Dict) -> List[Point]:
        """Collect BGP session statistics."""
        points = []
        try:
            output = conn.send_command('show bgp vpnv4 unicast all summary')

            # Skip header lines, find neighbor entries
            in_neighbors = False
            for line in output.split('\n'):
                if 'Neighbor' in line and 'AS' in line:
                    in_neighbors = True
                    continue
                if not in_neighbors:
                    continue

                # Parse neighbor line: 10.255.0.1  4   65000  123  456  789  0  0  01:23:45  100
                parts = line.split()
                if len(parts) >= 10 and re.match(r'\d+\.\d+\.\d+\.\d+', parts[0]):
                    neighbor = parts[0]
                    state = parts[-1]
                    # State is either a number (prefixes) or a state string
                    is_established = state.isdigit()
                    prefix_count = int(state) if is_established else 0

                    points.append(
                        Point("bgp_neighbor")
                        .tag("device", hostname)
                        .tag("neighbor", neighbor)
                        .tag("role", device_info['role'])
                        .tag("campus", device_info['campus'])
                        .field("established", 1 if is_established else 0)
                        .field("prefix_count", prefix_count)
                    )

        except Exception as e:
            logger.warning(f"Error collecting BGP from {hostname}: {e}")

        return points

    def collect_ospf(self, conn: Any, hostname: str, device_info: Dict) -> List[Point]:
        """Collect OSPF neighbor statistics."""
        points = []
        try:
            output = conn.send_command('show ip ospf neighbor')

            neighbor_count = 0
            full_count = 0

            for line in output.split('\n'):
                # Parse: 10.255.0.1  1  FULL/  -  00:00:32  10.0.0.1  GigabitEthernet2
                if re.match(r'\d+\.\d+\.\d+\.\d+', line.strip()):
                    neighbor_count += 1
                    if 'FULL' in line:
                        full_count += 1

            points.append(
                Point("ospf_summary")
                .tag("device", hostname)
                .tag("role", device_info['role'])
                .tag("campus", device_info['campus'])
                .field("neighbor_count", neighbor_count)
                .field("full_adjacencies", full_count)
            )

        except Exception as e:
            logger.warning(f"Error collecting OSPF from {hostname}: {e}")

        return points

    def collect_bfd(self, conn: Any, hostname: str, device_info: Dict) -> List[Point]:
        """Collect BFD session statistics."""
        points = []
        try:
            output = conn.send_command('show bfd neighbors')

            up_count = 0
            down_count = 0

            for line in output.split('\n'):
                if re.match(r'\d+\.\d+\.\d+\.\d+', line.strip()):
                    if 'Up' in line:
                        up_count += 1
                    elif 'Down' in line:
                        down_count += 1

            points.append(
                Point("bfd_summary")
                .tag("device", hostname)
                .tag("role", device_info['role'])
                .tag("campus", device_info['campus'])
                .field("sessions_up", up_count)
                .field("sessions_down", down_count)
            )

        except Exception as e:
            logger.warning(f"Error collecting BFD from {hostname}: {e}")

        return points

    def collect_hsrp(self, conn: Any, hostname: str, device_info: Dict) -> List[Point]:
        """Collect HSRP status for edge devices."""
        points = []
        if device_info['role'] != 'edge':
            return points

        try:
            output = conn.send_command('show standby brief')

            for line in output.split('\n'):
                # Parse: Gi3.100  100  P  Active  local  10.100.1.1  10.100.1.254
                match = re.match(r'(\S+)\s+(\d+)\s+\S+\s+(Active|Standby|Init)', line)
                if match:
                    interface = match.group(1)
                    group = match.group(2)
                    state = match.group(3)

                    points.append(
                        Point("hsrp_status")
                        .tag("device", hostname)
                        .tag("interface", interface)
                        .tag("group", group)
                        .tag("role", device_info['role'])
                        .tag("campus", device_info['campus'])
                        .field("state", state)
                        .field("is_active", 1 if state == 'Active' else 0)
                    )

        except Exception as e:
            logger.warning(f"Error collecting HSRP from {hostname}: {e}")

        return points

    def collect_device(self, hostname: str, device_info: Dict) -> List[Point]:
        """Collect all metrics from a single device."""
        all_points = []

        conn = self.connect_device(hostname, device_info)
        if not conn:
            # Device unreachable - record that
            all_points.append(
                Point("device_reachability")
                .tag("device", hostname)
                .tag("role", device_info['role'])
                .tag("campus", device_info['campus'])
                .field("reachable", 0)
            )
            return all_points

        try:
            # Device is reachable
            all_points.append(
                Point("device_reachability")
                .tag("device", hostname)
                .tag("role", device_info['role'])
                .tag("campus", device_info['campus'])
                .field("reachable", 1)
            )

            # Collect all metrics
            all_points.extend(self.collect_cpu_memory(conn, hostname, device_info))
            all_points.extend(self.collect_interfaces(conn, hostname, device_info))
            all_points.extend(self.collect_bgp(conn, hostname, device_info))
            all_points.extend(self.collect_ospf(conn, hostname, device_info))
            all_points.extend(self.collect_bfd(conn, hostname, device_info))
            all_points.extend(self.collect_hsrp(conn, hostname, device_info))

            logger.info(f"Collected {len(all_points)} metrics from {hostname}")

        finally:
            conn.disconnect()

        return all_points

    def collect_all(self) -> int:
        """Collect metrics from all devices in parallel."""
        all_points = []

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(self.collect_device, hostname, device_info): hostname
                for hostname, device_info in DEVICES.items()
            }

            for future in as_completed(futures):
                hostname = futures[future]
                try:
                    points = future.result()
                    all_points.extend(points)
                except Exception as e:
                    logger.error(f"Error collecting from {hostname}: {e}")

        # Write all points to InfluxDB
        if all_points:
            try:
                self.write_api.write(bucket=INFLUXDB_BUCKET, record=all_points)
                logger.info(f"Wrote {len(all_points)} points to InfluxDB")
            except Exception as e:
                logger.error(f"Error writing to InfluxDB: {e}")

        return len(all_points)

    def run(self):
        """Main collection loop."""
        logger.info(f"Starting telemetry collector (interval: {COLLECTION_INTERVAL}s)")
        logger.info(f"InfluxDB: {INFLUXDB_URL}, Bucket: {INFLUXDB_BUCKET}")
        logger.info(f"Monitoring {len(DEVICES)} devices")

        while True:
            start_time = time.time()

            try:
                points_collected = self.collect_all()
                elapsed = time.time() - start_time
                logger.info(f"Collection cycle completed in {elapsed:.2f}s")
            except Exception as e:
                logger.error(f"Collection cycle failed: {e}")

            # Sleep for remaining interval time
            sleep_time = max(0, COLLECTION_INTERVAL - (time.time() - start_time))
            if sleep_time > 0:
                time.sleep(sleep_time)


if __name__ == '__main__':
    collector = TelemetryCollector()
    collector.run()
