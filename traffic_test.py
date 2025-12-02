#!/usr/bin/env python3
"""
E-University Network Lab - End-to-End Traffic Test

Generates real traffic between all hosts, measures throughput using interface
counters, and collects path information via traceroute. Outputs structured
JSON data suitable for visualization.

Tests performed:
1. Full mesh connectivity between all 6 hosts
2. Throughput measurement via high-volume extended pings (1500-byte packets)
3. Path analysis via traceroute
4. Interface counter collection (bytes in/out)

Usage:
    python traffic_test.py                  # Run full mesh test
    python traffic_test.py --quick          # Quick connectivity check only
    python traffic_test.py --output FILE    # Save JSON to specific file

Output JSON structure:
{
    "test_metadata": { timestamp, duration, hosts_tested },
    "connectivity_matrix": { host-to-host reachability },
    "throughput_results": { per-path throughput measurements },
    "path_analysis": { traceroute hops for each path },
    "summary": { aggregate statistics }
}
"""

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

from netmiko import ConnectHandler


# Host configuration (matches deploy_host_switches.py)
HOSTS = {
    "HOST1": {
        "mgmt_ip": "192.168.68.55",
        "host_ip": "172.18.1.10",
        "campus": "research",
        "edge_router": "EUNIV-RES-EDGE1",
    },
    "HOST2": {
        "mgmt_ip": "192.168.68.74",
        "host_ip": "172.18.2.10",
        "campus": "research",
        "edge_router": "EUNIV-RES-EDGE2",
    },
    "HOST3": {
        "mgmt_ip": "192.168.68.77",
        "host_ip": "172.16.1.10",
        "campus": "main",
        "edge_router": "EUNIV-MAIN-EDGE1",
    },
    "HOST4": {
        "mgmt_ip": "192.168.68.78",
        "host_ip": "172.16.2.10",
        "campus": "main",
        "edge_router": "EUNIV-MAIN-EDGE2",
    },
    "HOST5": {
        "mgmt_ip": "192.168.68.79",
        "host_ip": "172.17.2.10",
        "campus": "medical",
        "edge_router": "EUNIV-MED-EDGE2",
    },
    "HOST6": {
        "mgmt_ip": "192.168.68.80",
        "host_ip": "172.17.1.10",
        "campus": "medical",
        "edge_router": "EUNIV-MED-EDGE1",
    },
}

CREDENTIALS = {
    "username": "admin",
    "password": "REDACTED",
}

# Test parameters
PING_COUNT = 100         # Number of pings for throughput test
PING_SIZE = 1400         # Packet size (bytes) - MTU minus headers
PING_TIMEOUT = 2         # Ping timeout in seconds


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
    success: bool = False


def get_connection(host_name: str) -> Optional[ConnectHandler]:
    """Establish SSH connection to a host"""
    cfg = HOSTS[host_name]
    device = {
        "device_type": "cisco_ios",
        "host": cfg["mgmt_ip"],
        "username": CREDENTIALS["username"],
        "password": CREDENTIALS["password"],
        "secret": CREDENTIALS["password"],
        "timeout": 30,
        "session_timeout": 60,
    }
    try:
        conn = ConnectHandler(**device)
        conn.enable()
        return conn
    except Exception as e:
        print(f"  ! Connection to {host_name} failed: {e}")
        return None


def run_ping(conn: ConnectHandler, source_name: str, dest_name: str,
             count: int = 5, size: int = 100) -> PingResult:
    """Execute ping and parse results"""
    dest_ip = HOSTS[dest_name]["host_ip"]
    result = PingResult(
        source=source_name,
        destination=dest_name,
        dest_ip=dest_ip
    )

    try:
        # Extended ping with specific count and size
        cmd = f"ping {dest_ip} repeat {count} size {size} timeout {PING_TIMEOUT}"
        output = conn.send_command(cmd, read_timeout=count * PING_TIMEOUT + 30)

        # Parse success rate
        # Format: "Success rate is X percent (Y/Z)"
        rate_match = re.search(r'Success rate is (\d+) percent \((\d+)/(\d+)\)', output)
        if rate_match:
            result.packets_received = int(rate_match.group(2))
            result.packets_sent = int(rate_match.group(3))
            result.packet_loss_pct = 100.0 - float(rate_match.group(1))
            result.success = result.packets_received > 0

        # Parse round-trip times
        # Format: "round-trip min/avg/max = X/Y/Z ms"
        rtt_match = re.search(r'round-trip min/avg/max = ([\d.]+)/([\d.]+)/([\d.]+)', output)
        if rtt_match:
            result.min_ms = float(rtt_match.group(1))
            result.avg_ms = float(rtt_match.group(2))
            result.max_ms = float(rtt_match.group(3))

    except Exception as e:
        result.error = str(e)

    return result


def run_traceroute(conn: ConnectHandler, source_name: str, dest_name: str) -> TracerouteResult:
    """Execute traceroute and parse path"""
    dest_ip = HOSTS[dest_name]["host_ip"]
    result = TracerouteResult(
        source=source_name,
        destination=dest_name,
        dest_ip=dest_ip
    )

    try:
        cmd = f"traceroute {dest_ip} timeout 2 probe 1"
        output = conn.send_command(cmd, read_timeout=120)

        # Parse each hop
        # Format: "  1 10.0.0.1 4 msec" or "  1 10.0.0.1 [MPLS: Label X]"
        hop_pattern = re.compile(
            r'^\s*(\d+)\s+(\d+\.\d+\.\d+\.\d+|\*)\s+(?:(\d+)\s*msec)?(?:.*\[MPLS: Label (\d+))?',
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


def get_interface_counters(conn: ConnectHandler) -> dict:
    """Get interface byte counters for Gi0/0"""
    try:
        output = conn.send_command("show interface GigabitEthernet0/0 | include packets input|packets output")

        # Parse input/output packet counts and bytes
        # Format: "X packets input, Y bytes, Z no buffer"
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


def measure_throughput(conn: ConnectHandler, source_name: str, dest_name: str) -> ThroughputResult:
    """Measure throughput by sending high-volume traffic and measuring counters"""
    dest_ip = HOSTS[dest_name]["host_ip"]
    result = ThroughputResult(source=source_name, destination=dest_name)

    try:
        # Get counters before
        before = get_interface_counters(conn)
        start_time = time.time()

        # Send high-volume ping traffic (large packets, many repetitions)
        cmd = f"ping {dest_ip} repeat {PING_COUNT} size {PING_SIZE} timeout {PING_TIMEOUT}"
        output = conn.send_command(cmd, read_timeout=PING_COUNT * PING_TIMEOUT + 60)

        end_time = time.time()
        # Get counters after
        after = get_interface_counters(conn)

        # Calculate throughput
        bytes_sent = after["bytes_out"] - before["bytes_out"]
        duration = end_time - start_time

        if duration > 0 and bytes_sent > 0:
            result.bytes_sent = bytes_sent
            result.duration_sec = round(duration, 2)
            result.throughput_bps = round(bytes_sent * 8 / duration, 2)
            result.throughput_kbps = round(result.throughput_bps / 1000, 2)
            result.throughput_mbps = round(result.throughput_bps / 1_000_000, 4)
            result.success = True

    except Exception as e:
        result.success = False

    return result


def test_host_to_all(source_name: str, all_hosts: list, quick: bool = False) -> dict:
    """Test from one source host to all destinations"""
    results = {
        "source": source_name,
        "source_ip": HOSTS[source_name]["host_ip"],
        "campus": HOSTS[source_name]["campus"],
        "ping_results": [],
        "throughput_results": [],
        "traceroute_results": [],
    }

    conn = get_connection(source_name)
    if not conn:
        return results

    try:
        for dest_name in all_hosts:
            if dest_name == source_name:
                continue

            # Quick ping for connectivity
            ping = run_ping(conn, source_name, dest_name, count=5, size=100)
            results["ping_results"].append(asdict(ping))

            if quick:
                continue

            # Full throughput test
            throughput = measure_throughput(conn, source_name, dest_name)
            results["throughput_results"].append(asdict(throughput))

            # Traceroute for path
            trace = run_traceroute(conn, source_name, dest_name)
            results["traceroute_results"].append(asdict(trace))

    finally:
        conn.disconnect()

    return results


def generate_connectivity_matrix(all_results: list) -> dict:
    """Generate a connectivity matrix from test results"""
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


def calculate_summary(all_results: list) -> dict:
    """Calculate aggregate statistics"""
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


def run_traffic_test(quick: bool = False, output_file: str = None):
    """Execute full traffic test suite"""
    start_time = datetime.now()
    print("=" * 70)
    print("E-University Network - End-to-End Traffic Test")
    print("=" * 70)
    print(f"Start time: {start_time.isoformat()}")
    print(f"Mode: {'Quick connectivity check' if quick else 'Full throughput test'}")
    print(f"Hosts: {len(HOSTS)}")
    print()

    all_hosts = list(HOSTS.keys())
    all_results = []

    # Run tests from each host in parallel
    print("Testing connectivity and throughput...")
    print("-" * 70)

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(test_host_to_all, host, all_hosts, quick): host
            for host in all_hosts
        }

        for future in as_completed(futures):
            host = futures[future]
            try:
                result = future.result()
                all_results.append(result)

                # Print progress
                success_count = sum(1 for p in result["ping_results"] if p["success"])
                total_count = len(result["ping_results"])
                campus = result["campus"].upper()
                print(f"  [{campus:8}] {host}: {success_count}/{total_count} destinations reachable")

            except Exception as e:
                print(f"  [ERROR] {host}: {e}")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Build output structure
    output = {
        "test_metadata": {
            "timestamp": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": round(duration, 2),
            "test_mode": "quick" if quick else "full",
            "hosts_tested": len(HOSTS),
            "paths_tested": len(HOSTS) * (len(HOSTS) - 1),
        },
        "hosts": {
            name: {
                "ip": cfg["host_ip"],
                "mgmt_ip": cfg["mgmt_ip"],
                "campus": cfg["campus"],
                "edge_router": cfg["edge_router"],
            }
            for name, cfg in HOSTS.items()
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
    hosts_list = list(HOSTS.keys())
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
        output_file = f"/Users/elliotconner/PycharmProjects/euniv-lab/traffic_test_{timestamp}.json"

    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print()
    print(f"Results saved to: {output_file}")
    print("=" * 70)

    return output


def main():
    parser = argparse.ArgumentParser(
        description="E-University Network End-to-End Traffic Test"
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
    run_traffic_test(quick=args.quick, output_file=args.output)


if __name__ == "__main__":
    main()
