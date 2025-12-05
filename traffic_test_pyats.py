#!/usr/bin/env python3
"""
E-University Network Lab - End-to-End Traffic Test (pyATS Version)

Uses pyATS/Genie framework to perform structured traffic testing between
all host routers. Leverages Genie parsers for reliable output parsing.

Tests performed:
1. Full mesh connectivity between all 6 hosts
2. Throughput measurement via extended pings with large packets
3. Path analysis via traceroute with MPLS label detection
4. Interface counter collection

Usage:
    python traffic_test_pyats.py                           # Full mesh test
    python traffic_test_pyats.py --quick                   # Quick connectivity only
    python traffic_test_pyats.py --testbed custom.yaml     # Custom testbed
    python traffic_test_pyats.py --output results.json     # Custom output file

Output: Structured JSON suitable for visualization dashboards
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

# pyATS imports
try:
    from genie.libs.parser.utils import get_parser
    from pyats.topology import loader
    from unicon.core.errors import ConnectionError, SubCommandFailure
except ImportError:
    print("Please install pyATS: pip install pyats[full] genie")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default testbed path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TESTBED = os.path.join(SCRIPT_DIR, "pyats", "host_testbed.yaml")

# Test parameters
PING_COUNT_QUICK = 5
PING_COUNT_FULL = 100
PING_SIZE = 1400
PING_TIMEOUT = 2


@dataclass
class PingResult:
    """Results from a ping test"""
    source: str
    destination: str
    dest_ip: str
    packets_sent: int = 0
    packets_received: int = 0
    packet_loss_pct: float = 100.0
    min_ms: float = 0.0
    avg_ms: float = 0.0
    max_ms: float = 0.0
    success: bool = False
    error: Optional[str] = None


@dataclass
class TracerouteResult:
    """Results from a traceroute"""
    source: str
    destination: str
    dest_ip: str
    hops: list = field(default_factory=list)
    total_hops: int = 0
    success: bool = False
    error: Optional[str] = None


@dataclass
class ThroughputResult:
    """Throughput calculation for a path"""
    source: str
    destination: str
    bytes_sent: int = 0
    duration_sec: float = 0.0
    throughput_bps: float = 0.0
    throughput_kbps: float = 0.0
    throughput_mbps: float = 0.0
    packets_sent: int = 0
    packets_received: int = 0
    success: bool = False


class TrafficTest:
    """pyATS-based traffic test suite."""

    def __init__(self, testbed_file: str):
        """Initialize with testbed."""
        self.testbed = loader.load(testbed_file)
        self.connected_devices: Dict[str, Any] = {}
        self.host_ips: Dict[str, str] = {}

        # Extract host IPs from testbed custom fields
        for name, device in self.testbed.devices.items():
            if hasattr(device, 'custom') and 'host_ip' in device.custom:
                self.host_ips[name] = device.custom['host_ip']

    def connect_hosts(self) -> Dict[str, bool]:
        """Connect to all host devices."""
        results = {}
        logger.info(f"\nConnecting to {len(self.testbed.devices)} host devices...")

        for name, device in self.testbed.devices.items():
            try:
                if not device.is_connected():
                    device.connect(log_stdout=False, learn_hostname=True)
                self.connected_devices[name] = device
                results[name] = True
                logger.info(f"  + Connected: {name}")
            except Exception as e:
                results[name] = False
                logger.error(f"  ! Failed to connect to {name}: {e}")

        return results

    def disconnect_hosts(self):
        """Disconnect from all devices."""
        for name, device in self.connected_devices.items():
            try:
                device.disconnect()
            except Exception:
                pass

    def run_ping(self, source_name: str, dest_name: str,
                 count: int = 5, size: int = 100) -> PingResult:
        """Execute ping using device.execute() for reliable parsing."""
        dest_ip = self.host_ips.get(dest_name, "")
        result = PingResult(
            source=source_name,
            destination=dest_name,
            dest_ip=dest_ip
        )

        if source_name not in self.connected_devices:
            result.error = "Source device not connected"
            return result

        device = self.connected_devices[source_name]

        try:
            # Use execute for more reliable output parsing
            cmd = f"ping {dest_ip} repeat {count} size {size} timeout {PING_TIMEOUT}"
            output = device.execute(cmd, timeout=count * PING_TIMEOUT + 30)

            # Parse success rate: "Success rate is X percent (Y/Z)"
            rate_match = re.search(r'Success rate is (\d+) percent \((\d+)/(\d+)\)', output)
            if rate_match:
                success_pct = int(rate_match.group(1))
                result.packets_received = int(rate_match.group(2))
                result.packets_sent = int(rate_match.group(3))
                result.packet_loss_pct = 100.0 - success_pct
                result.success = result.packets_received > 0

            # Parse RTT: "round-trip min/avg/max = X/Y/Z ms"
            rtt_match = re.search(r'round-trip min/avg/max = ([\d.]+)/([\d.]+)/([\d.]+)', output)
            if rtt_match:
                result.min_ms = float(rtt_match.group(1))
                result.avg_ms = float(rtt_match.group(2))
                result.max_ms = float(rtt_match.group(3))

        except SubCommandFailure:
            result.packets_sent = count
            result.packets_received = 0
            result.packet_loss_pct = 100.0
            result.success = False
        except Exception as e:
            result.error = str(e)

        return result

    def run_traceroute(self, source_name: str, dest_name: str) -> TracerouteResult:
        """Execute traceroute and parse path."""
        dest_ip = self.host_ips.get(dest_name, "")
        result = TracerouteResult(
            source=source_name,
            destination=dest_name,
            dest_ip=dest_ip
        )

        if source_name not in self.connected_devices:
            result.error = "Source device not connected"
            return result

        device = self.connected_devices[source_name]

        try:
            # Execute traceroute command
            output = device.execute(
                f"traceroute {dest_ip} timeout 2 probe 1",
                timeout=120
            )

            # Parse each hop using regex
            # Format: "  1 10.0.0.1 4 msec" or with MPLS labels
            hop_pattern = re.compile(
                r'^\s*(\d+)\s+(\d+\.\d+\.\d+\.\d+|\*)'
                r'(?:\s+(\d+)\s*msec)?'
                r'(?:.*\[MPLS:\s*Label\s+(\d+))?',
                re.MULTILINE
            )

            hops = []
            for match in hop_pattern.finditer(output):
                hop_num = int(match.group(1))
                hop_ip = match.group(2)
                latency = float(match.group(3)) if match.group(3) else None
                mpls_label = int(match.group(4)) if match.group(4) else None

                hop_data = {
                    "hop": hop_num,
                    "ip": hop_ip,
                    "latency_ms": latency,
                }
                if mpls_label:
                    hop_data["mpls_label"] = mpls_label
                hops.append(hop_data)

            result.hops = hops
            result.total_hops = len(hops)
            result.success = len(hops) > 0 and hops[-1]["ip"] == dest_ip

        except Exception as e:
            result.error = str(e)

        return result

    def get_interface_counters(self, device_name: str) -> Dict[str, int]:
        """Get interface byte counters using Genie parser."""
        if device_name not in self.connected_devices:
            return {"bytes_in": 0, "bytes_out": 0, "packets_in": 0, "packets_out": 0}

        device = self.connected_devices[device_name]

        try:
            # Use Genie parser for structured output
            parsed = device.parse("show interfaces GigabitEthernet0/0")

            intf_data = parsed.get("GigabitEthernet0/0", {})
            counters = intf_data.get("counters", {})

            return {
                "bytes_in": counters.get("in_octets", 0),
                "bytes_out": counters.get("out_octets", 0),
                "packets_in": counters.get("in_pkts", 0),
                "packets_out": counters.get("out_pkts", 0),
            }
        except Exception:
            # Fallback to manual parsing
            try:
                output = device.execute(
                    "show interface GigabitEthernet0/0 | include packets input|packets output"
                )
                in_match = re.search(r'(\d+) packets input, (\d+) bytes', output)
                out_match = re.search(r'(\d+) packets output, (\d+) bytes', output)
                return {
                    "bytes_in": int(in_match.group(2)) if in_match else 0,
                    "bytes_out": int(out_match.group(2)) if out_match else 0,
                    "packets_in": int(in_match.group(1)) if in_match else 0,
                    "packets_out": int(out_match.group(1)) if out_match else 0,
                }
            except Exception:
                return {"bytes_in": 0, "bytes_out": 0, "packets_in": 0, "packets_out": 0}

    def measure_throughput(self, source_name: str, dest_name: str) -> ThroughputResult:
        """Measure throughput by sending traffic and measuring counters."""
        dest_ip = self.host_ips.get(dest_name, "")
        result = ThroughputResult(source=source_name, destination=dest_name)

        if source_name not in self.connected_devices:
            return result

        device = self.connected_devices[source_name]

        try:
            # Get counters before
            before = self.get_interface_counters(source_name)
            start_time = time.time()

            # Send high-volume ping traffic
            ping_result = self.run_ping(
                source_name, dest_name,
                count=PING_COUNT_FULL,
                size=PING_SIZE
            )

            end_time = time.time()
            # Get counters after
            after = self.get_interface_counters(source_name)

            # Calculate throughput
            bytes_sent = after["bytes_out"] - before["bytes_out"]
            duration = end_time - start_time

            result.packets_sent = ping_result.packets_sent
            result.packets_received = ping_result.packets_received

            if duration > 0 and bytes_sent > 0:
                result.bytes_sent = bytes_sent
                result.duration_sec = round(duration, 2)
                result.throughput_bps = round(bytes_sent * 8 / duration, 2)
                result.throughput_kbps = round(result.throughput_bps / 1000, 2)
                result.throughput_mbps = round(result.throughput_bps / 1_000_000, 4)
                result.success = True

        except Exception:
            result.success = False

        return result

    def test_host_to_all(self, source_name: str, quick: bool = False) -> Dict:
        """Test from one source host to all other hosts."""
        results = {
            "source": source_name,
            "source_ip": self.host_ips.get(source_name, ""),
            "campus": "",
            "ping_results": [],
            "throughput_results": [],
            "traceroute_results": [],
        }

        # Get campus from testbed custom fields
        if source_name in self.testbed.devices:
            device = self.testbed.devices[source_name]
            if hasattr(device, 'custom'):
                results["campus"] = device.custom.get('campus', '')

        if source_name not in self.connected_devices:
            return results

        for dest_name in self.host_ips.keys():
            if dest_name == source_name:
                continue

            # Quick connectivity ping
            ping = self.run_ping(
                source_name, dest_name,
                count=PING_COUNT_QUICK,
                size=100
            )
            results["ping_results"].append(asdict(ping))

            if quick:
                continue

            # Full throughput test
            throughput = self.measure_throughput(source_name, dest_name)
            results["throughput_results"].append(asdict(throughput))

            # Traceroute for path analysis
            trace = self.run_traceroute(source_name, dest_name)
            results["traceroute_results"].append(asdict(trace))

        return results


def generate_connectivity_matrix(all_results: List[Dict]) -> Dict:
    """Generate a connectivity matrix from test results."""
    matrix = {}
    for result in all_results:
        source = result["source"]
        matrix[source] = {}
        for ping in result["ping_results"]:
            dest = ping["destination"]
            matrix[source][dest] = {
                "reachable": ping["success"],
                "packet_loss_pct": ping["packet_loss_pct"],
                "avg_latency_ms": ping["avg_ms"],
            }
    return matrix


def calculate_summary(all_results: List[Dict]) -> Dict:
    """Calculate aggregate statistics."""
    total_paths = 0
    reachable_paths = 0
    total_throughput = []
    latencies = []

    for result in all_results:
        for ping in result["ping_results"]:
            total_paths += 1
            if ping["success"]:
                reachable_paths += 1
                latencies.append(ping["avg_ms"])

        for tp in result.get("throughput_results", []):
            if tp["success"]:
                total_throughput.append(tp["throughput_mbps"])

    summary = {
        "total_paths_tested": total_paths,
        "reachable_paths": reachable_paths,
        "unreachable_paths": total_paths - reachable_paths,
        "connectivity_pct": round(reachable_paths / total_paths * 100, 1) if total_paths else 0,
    }

    if latencies:
        summary["latency_ms"] = {
            "min": round(min(latencies), 2),
            "max": round(max(latencies), 2),
            "avg": round(sum(latencies) / len(latencies), 2),
        }

    if total_throughput:
        summary["throughput_mbps"] = {
            "min": round(min(total_throughput), 4),
            "max": round(max(total_throughput), 4),
            "avg": round(sum(total_throughput) / len(total_throughput), 4),
            "total_measured": len(total_throughput),
        }

    return summary


def run_traffic_test(testbed_file: str, quick: bool = False, output_file: str = None):
    """Execute full traffic test suite using pyATS."""
    start_time = datetime.now()

    print("=" * 70)
    print("E-University Network - End-to-End Traffic Test (pyATS)")
    print("=" * 70)
    print(f"Start time: {start_time.isoformat()}")
    print(f"Testbed: {testbed_file}")
    print(f"Mode: {'Quick connectivity check' if quick else 'Full throughput test'}")
    print()

    # Initialize test suite
    test = TrafficTest(testbed_file)
    print(f"Hosts found: {len(test.host_ips)}")

    # Connect to hosts
    connection_results = test.connect_hosts()
    connected_count = sum(1 for v in connection_results.values() if v)
    print(f"Connected: {connected_count}/{len(connection_results)}")
    print()

    # Run tests from each host
    print("Running traffic tests...")
    print("-" * 70)

    all_results = []

    # Run tests sequentially (pyATS connections aren't thread-safe)
    for host_name in test.host_ips.keys():
        if host_name not in test.connected_devices:
            logger.warning(f"  [{host_name}] Skipped - not connected")
            continue

        result = test.test_host_to_all(host_name, quick=quick)
        all_results.append(result)

        # Print progress
        success_count = sum(1 for p in result["ping_results"] if p["success"])
        total_count = len(result["ping_results"])
        campus = result["campus"].upper() if result["campus"] else "?"
        print(f"  [{campus:8}] {host_name}: {success_count}/{total_count} destinations reachable")

    # Disconnect
    test.disconnect_hosts()

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Build output structure
    output = {
        "test_metadata": {
            "timestamp": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": round(duration, 2),
            "test_mode": "quick" if quick else "full",
            "framework": "pyATS",
            "hosts_tested": len(test.host_ips),
            "hosts_connected": connected_count,
            "paths_tested": len(test.host_ips) * (len(test.host_ips) - 1),
        },
        "hosts": {
            name: {
                "ip": test.host_ips.get(name, ""),
                "mgmt_ip": str(test.testbed.devices[name].connections.cli.ip)
                           if name in test.testbed.devices else "",
                "campus": test.testbed.devices[name].custom.get('campus', '')
                          if name in test.testbed.devices and
                             hasattr(test.testbed.devices[name], 'custom') else "",
                "edge_router": test.testbed.devices[name].custom.get('edge_router', '')
                               if name in test.testbed.devices and
                                  hasattr(test.testbed.devices[name], 'custom') else "",
            }
            for name in test.host_ips.keys()
        },
        "connectivity_matrix": generate_connectivity_matrix(all_results),
        "detailed_results": all_results,
        "summary": calculate_summary(all_results),
    }

    # Print summary
    print()
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    summary = output["summary"]
    print(f"  Total paths tested: {summary['total_paths_tested']}")
    print(f"  Reachable: {summary['reachable_paths']} ({summary['connectivity_pct']}%)")
    print(f"  Unreachable: {summary['unreachable_paths']}")

    if "latency_ms" in summary:
        lat = summary["latency_ms"]
        print(f"  Latency: min={lat['min']}ms, avg={lat['avg']}ms, max={lat['max']}ms")

    if "throughput_mbps" in summary:
        tp = summary["throughput_mbps"]
        print(f"  Throughput: min={tp['min']}Mbps, avg={tp['avg']}Mbps, max={tp['max']}Mbps")

    print(f"  Duration: {duration:.1f} seconds")

    # Print connectivity matrix
    print()
    print("Connectivity Matrix (latency in ms):")
    print("-" * 70)
    hosts_list = list(test.host_ips.keys())
    header = "         " + "".join(f"{h:>8}" for h in hosts_list)
    print(header)

    matrix = output["connectivity_matrix"]
    for src in hosts_list:
        row = f"{src:<8} "
        for dst in hosts_list:
            if src == dst:
                row += "      - "
            elif src in matrix and dst in matrix[src]:
                entry = matrix[src][dst]
                if entry["reachable"]:
                    row += f"{entry['avg_latency_ms']:>7.1f} "
                else:
                    row += "      X "
            else:
                row += "      ? "
        print(row)

    # Save to file
    if output_file is None:
        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(SCRIPT_DIR, f"traffic_test_pyats_{timestamp}.json")

    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print()
    print(f"Results saved to: {output_file}")
    print("=" * 70)

    return output


def main():
    parser = argparse.ArgumentParser(
        description="E-University Network End-to-End Traffic Test (pyATS)"
    )
    parser.add_argument(
        "--testbed", "-t",
        type=str,
        default=DEFAULT_TESTBED,
        help=f"pyATS testbed YAML file (default: {DEFAULT_TESTBED})"
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Quick connectivity check only (skip throughput/traceroute)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output JSON file path"
    )

    args = parser.parse_args()

    if not os.path.exists(args.testbed):
        print(f"Error: Testbed file not found: {args.testbed}")
        sys.exit(1)

    run_traffic_test(
        testbed_file=args.testbed,
        quick=args.quick,
        output_file=args.output
    )


if __name__ == "__main__":
    main()
