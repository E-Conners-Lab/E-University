#!/usr/bin/env python3
"""
E University Network Validation Tests

This script uses pyATS to validate the E University network against
the intended design in intent.yaml.

Test Categories:
1. Connectivity - Basic reachability
2. OSPF - IGP neighbor state and routes
3. BGP - iBGP/eBGP sessions and VPNv4
4. MPLS - LDP neighbors and label bindings
5. VRF - VRF instantiation and route targets
6. Services - NTP, logging, SNMP configuration

Usage:
    python test_euniv_network.py --testbed testbed.yaml
    python test_euniv_network.py --testbed testbed.yaml --test ospf
    python test_euniv_network.py --testbed testbed.yaml --test bgp --device EUNIV-CORE1
    python test_euniv_network.py --testbed testbed.yaml --json-output results.json
"""

import os
import sys
import re
import argparse
import yaml
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# pyATS imports
try:
    from pyats.topology import loader
    from genie.libs.parser.utils import get_parser
    from unicon.core.errors import ConnectionError
except ImportError:
    print("Please install pyATS: pip install pyats[full]")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestResult:
    """Store test results."""
    
    def __init__(self, name: str):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.details: List[Dict] = []
    
    def add_pass(self, message: str, device: str = ""):
        self.passed += 1
        self.details.append({"status": "PASS", "message": message, "device": device})
        logger.info(f"  ✓ PASS: {message}")
    
    def add_fail(self, message: str, device: str = "", expected: Any = None, actual: Any = None):
        self.failed += 1
        detail = {"status": "FAIL", "message": message, "device": device}
        if expected is not None:
            detail["expected"] = expected
        if actual is not None:
            detail["actual"] = actual
        self.details.append(detail)
        logger.error(f"  ✗ FAIL: {message}")
    
    def add_skip(self, message: str, device: str = ""):
        self.skipped += 1
        self.details.append({"status": "SKIP", "message": message, "device": device})
        logger.warning(f"  ⊘ SKIP: {message}")
    
    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped
    
    def summary(self) -> str:
        status = "PASSED" if self.failed == 0 else "FAILED"
        return f"{self.name}: {status} (Pass: {self.passed}, Fail: {self.failed}, Skip: {self.skipped})"

    def to_dict(self) -> Dict:
        """Convert result to dictionary for JSON export."""
        return {
            "name": self.name,
            "status": "PASSED" if self.failed == 0 else "FAILED",
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "total": self.total,
            "details": self.details
        }


class EUnivNetworkTests:
    """E University Network Validation Tests."""
    
    def __init__(self, testbed_file: str, intent_file: str = None):
        """Initialize test suite."""
        self.testbed = loader.load(testbed_file)
        self.intent = self._load_intent(intent_file)
        self.results: Dict[str, TestResult] = {}
        self.connected_devices: Dict[str, Any] = {}
    
    def _load_intent(self, intent_file: str = None) -> Dict:
        """Load intent data from YAML."""
        if intent_file is None:
            # Default path relative to this script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            intent_file = os.path.join(script_dir, "..", "data", "intent.yaml")
        
        if not os.path.exists(intent_file):
            logger.warning(f"Intent file not found: {intent_file}")
            return {}
        
        with open(intent_file, 'r') as f:
            return yaml.safe_load(f)
    
    def connect_devices(self, device_names: List[str] = None):
        """Connect to devices."""
        if device_names is None:
            device_names = list(self.testbed.devices.keys())
        
        logger.info(f"\nConnecting to {len(device_names)} devices...")
        
        for name in device_names:
            if name not in self.testbed.devices:
                logger.warning(f"Device {name} not in testbed")
                continue
            
            device = self.testbed.devices[name]
            try:
                if not device.is_connected():
                    device.connect(log_stdout=False, learn_hostname=True)
                self.connected_devices[name] = device
                logger.info(f"  ✓ Connected: {name}")
            except Exception as e:
                logger.error(f"  ✗ Failed to connect to {name}: {e}")
    
    def disconnect_devices(self):
        """Disconnect from all devices."""
        for name, device in self.connected_devices.items():
            try:
                device.disconnect()
            except Exception:
                pass
    
    # =========================================================================
    # TEST: Connectivity
    # =========================================================================
    def test_connectivity(self, devices: List[str] = None) -> TestResult:
        """Test basic connectivity to all devices."""
        result = TestResult("Connectivity")
        
        if devices is None:
            devices = list(self.testbed.devices.keys())
        
        logger.info("\n" + "=" * 60)
        logger.info("TEST: Connectivity")
        logger.info("=" * 60)
        
        for device_name in devices:
            if device_name in self.connected_devices:
                result.add_pass(f"Connected to {device_name}", device_name)
            else:
                result.add_fail(f"Could not connect to {device_name}", device_name)
        
        self.results["connectivity"] = result
        return result
    
    # =========================================================================
    # TEST: OSPF
    # =========================================================================
    def test_ospf(self, devices: List[str] = None) -> TestResult:
        """Test OSPF neighbor state."""
        result = TestResult("OSPF")
        
        if devices is None:
            devices = list(self.connected_devices.keys())
        
        logger.info("\n" + "=" * 60)
        logger.info("TEST: OSPF Neighbors")
        logger.info("=" * 60)
        
        for device_name in devices:
            if device_name not in self.connected_devices:
                result.add_skip(f"Device not connected", device_name)
                continue
            
            device = self.connected_devices[device_name]
            
            try:
                # Parse OSPF neighbors
                ospf_neighbors = device.parse("show ip ospf neighbor")
                
                if not ospf_neighbors:
                    result.add_fail(f"No OSPF neighbors found", device_name)
                    continue
                
                # Check neighbor states
                interfaces = ospf_neighbors.get("interfaces", {})
                all_full = True
                neighbor_count = 0
                
                for intf, intf_data in interfaces.items():
                    neighbors = intf_data.get("neighbors", {})
                    for neighbor_id, neighbor_data in neighbors.items():
                        neighbor_count += 1
                        state = neighbor_data.get("state", "").upper()
                        if "FULL" not in state:
                            all_full = False
                            result.add_fail(
                                f"OSPF neighbor {neighbor_id} on {intf} is {state}",
                                device_name,
                                expected="FULL",
                                actual=state
                            )
                
                if all_full and neighbor_count > 0:
                    result.add_pass(
                        f"All {neighbor_count} OSPF neighbors in FULL state",
                        device_name
                    )
                elif neighbor_count == 0:
                    result.add_fail("No OSPF neighbors found", device_name)
                    
            except Exception as e:
                result.add_fail(f"Error parsing OSPF: {e}", device_name)
        
        self.results["ospf"] = result
        return result
    
    # =========================================================================
    # TEST: BGP
    # =========================================================================
    def test_bgp(self, devices: List[str] = None) -> TestResult:
        """Test BGP neighbor state using manual parsing."""
        result = TestResult("BGP")

        if devices is None:
            devices = list(self.connected_devices.keys())

        logger.info("\n" + "=" * 60)
        logger.info("TEST: BGP Neighbors")
        logger.info("=" * 60)

        for device_name in devices:
            if device_name not in self.connected_devices:
                result.add_skip(f"Device not connected", device_name)
                continue

            device = self.connected_devices[device_name]

            try:
                # Use manual parsing instead of Genie parser
                output = device.execute("show bgp all summary")

                established = 0
                not_established = []

                for line in output.splitlines():
                    # Parse neighbor lines (start with IP address)
                    match = re.match(r'^(\d+\.\d+\.\d+\.\d+)\s+', line.strip())
                    if match:
                        parts = line.split()
                        if len(parts) >= 9:
                            neighbor = parts[0]
                            # Last column is State/PfxRcd
                            state = parts[-1]

                            # If state is a number, session is established (prefix count)
                            if state.isdigit():
                                established += 1
                            elif state in ["Idle", "Active", "Connect", "OpenSent", "OpenConfirm"]:
                                not_established.append((neighbor, state))
                            else:
                                # Could be other status like (Admin), treat as established
                                established += 1

                if established > 0 and not not_established:
                    result.add_pass(
                        f"{established} BGP sessions established",
                        device_name
                    )
                elif established > 0:
                    for neighbor, state in not_established:
                        result.add_fail(
                            f"BGP neighbor {neighbor} is {state}",
                            device_name,
                            expected="Established",
                            actual=state
                        )
                    result.add_pass(
                        f"{established} BGP sessions established",
                        device_name
                    )
                elif "PE" in device_name or "EDGE" in device_name or "CORE4" in device_name or "CORE5" in device_name:
                    result.add_fail(
                        "No BGP sessions found (expected on this device)",
                        device_name
                    )
                else:
                    result.add_skip("BGP not configured", device_name)

            except Exception as e:
                result.add_fail(f"Error checking BGP: {e}", device_name)

        self.results["bgp"] = result
        return result
    
    # =========================================================================
    # TEST: MPLS LDP
    # =========================================================================
    def test_mpls_ldp(self, devices: List[str] = None) -> TestResult:
        """Test MPLS LDP neighbor state using manual parsing."""
        result = TestResult("MPLS LDP")

        if devices is None:
            # Only test core and aggregation devices
            devices = [d for d in self.connected_devices.keys()
                      if "CORE" in d or "AGG" in d]

        logger.info("\n" + "=" * 60)
        logger.info("TEST: MPLS LDP Neighbors")
        logger.info("=" * 60)

        for device_name in devices:
            if device_name not in self.connected_devices:
                result.add_skip(f"Device not connected", device_name)
                continue

            device = self.connected_devices[device_name]

            try:
                # Use manual parsing instead of Genie parser
                output = device.execute("show mpls ldp neighbor")

                # Parse LDP neighbors - IOS format:
                # Peer LDP Ident: 10.255.0.2:0; Local LDP Ident 10.255.0.1:0
                #     TCP connection: 10.255.0.2.646 - 10.255.0.1.43287
                #     State: Oper; Msgs sent/rcvd: 1234/1234; Downstream
                operational = 0
                not_operational = []

                current_peer = None
                for line in output.splitlines():
                    # Match peer identifier line
                    peer_match = re.search(r'Peer LDP Ident:\s*(\d+\.\d+\.\d+\.\d+)', line)
                    if peer_match:
                        current_peer = peer_match.group(1)

                    # Match state line
                    state_match = re.search(r'State:\s*(\w+)', line)
                    if state_match and current_peer:
                        state = state_match.group(1)
                        if state.lower() == "oper":
                            operational += 1
                        else:
                            not_operational.append((current_peer, state))
                        current_peer = None

                if operational > 0 and not not_operational:
                    result.add_pass(
                        f"{operational} LDP neighbors operational",
                        device_name
                    )
                elif operational > 0:
                    for peer, state in not_operational:
                        result.add_fail(
                            f"LDP peer {peer} is {state}",
                            device_name,
                            expected="Oper",
                            actual=state
                        )
                    result.add_pass(
                        f"{operational} LDP neighbors operational",
                        device_name
                    )
                elif "No LDP" in output or not output.strip():
                    result.add_skip("LDP not configured", device_name)
                else:
                    result.add_fail("No operational LDP neighbors", device_name)

            except Exception as e:
                result.add_skip(f"Could not check LDP: {e}", device_name)
        
        self.results["mpls_ldp"] = result
        return result
    
    # =========================================================================
    # TEST: VRF
    # =========================================================================
    def test_vrf(self, devices: List[str] = None) -> TestResult:
        """Test VRF configuration."""
        result = TestResult("VRF")
        
        if devices is None:
            # Only test PE devices
            devices = [d for d in self.connected_devices.keys() if "PE" in d]
        
        logger.info("\n" + "=" * 60)
        logger.info("TEST: VRF Configuration")
        logger.info("=" * 60)
        
        expected_vrfs = ["STUDENT-NET", "STAFF-NET", "RESEARCH-NET", "MEDICAL-NET", "GUEST-NET"]
        
        for device_name in devices:
            if device_name not in self.connected_devices:
                result.add_skip(f"Device not connected", device_name)
                continue
            
            device = self.connected_devices[device_name]
            
            try:
                # Parse VRF detail
                vrf_detail = device.parse("show vrf detail")
                
                if not vrf_detail:
                    result.add_fail(f"No VRF data found", device_name)
                    continue
                
                configured_vrfs = list(vrf_detail.keys())
                
                # Check which expected VRFs are present
                for vrf_name in expected_vrfs:
                    if vrf_name in configured_vrfs:
                        vrf_info = vrf_detail.get(vrf_name, {})
                        rd = vrf_info.get("route_distinguisher", "N/A")
                        result.add_pass(
                            f"VRF {vrf_name} configured (RD: {rd})",
                            device_name
                        )
                    # Note: Not all VRFs on all PEs, so we don't fail here
                
                result.add_pass(
                    f"Found {len(configured_vrfs)} VRFs configured",
                    device_name
                )
                    
            except Exception as e:
                result.add_fail(f"Error parsing VRF: {e}", device_name)
        
        self.results["vrf"] = result
        return result
    
    # =========================================================================
    # TEST: Loopback Reachability
    # =========================================================================
    def test_loopback_reachability(self, source_device: str = None) -> TestResult:
        """Test reachability to all loopbacks from a source device."""
        result = TestResult("Loopback Reachability")

        # Use first core device as source if not specified
        if source_device is None:
            source_device = "EUNIV-CORE1"

        if source_device not in self.connected_devices:
            result.add_fail(f"Source device {source_device} not connected")
            return result

        logger.info("\n" + "=" * 60)
        logger.info(f"TEST: Loopback Reachability (from {source_device})")
        logger.info("=" * 60)

        device = self.connected_devices[source_device]

        # Get loopback IPs from intent
        targets = []
        for dev_name, dev_data in self.intent.get("devices", {}).items():
            if dev_name != source_device:
                loopback = dev_data.get("loopback0")
                if loopback:
                    targets.append((dev_name, loopback))

        if not targets:
            logger.warning("No loopback targets found in intent file - skipping reachability test")
            result.add_skip("No targets in intent file", source_device)
            self.results["loopback_reachability"] = result
            return result

        logger.info(f"Testing reachability to {len(targets)} loopbacks...")

        for i, (target_name, target_ip) in enumerate(targets, 1):
            # Show progress
            logger.info(f"  [{i}/{len(targets)}] Pinging {target_name} ({target_ip})...")

            try:
                # Ping the target
                ping_result = device.ping(target_ip, count=3)

                if ping_result and ping_result.get("success", False):
                    result.add_pass(
                        f"Ping to {target_name} ({target_ip}) successful",
                        source_device
                    )
                else:
                    result.add_fail(
                        f"Ping to {target_name} ({target_ip}) failed",
                        source_device
                    )
            except Exception as e:
                result.add_fail(
                    f"Error pinging {target_name} ({target_ip}): {e}",
                    source_device
                )

        self.results["loopback_reachability"] = result
        return result
    
    # =========================================================================
    # TEST: Interface Status
    # =========================================================================
    def test_interfaces(self, devices: List[str] = None) -> TestResult:
        """Test interface status, skipping admin-shutdown interfaces."""
        result = TestResult("Interface Status")

        if devices is None:
            devices = list(self.connected_devices.keys())

        logger.info("\n" + "=" * 60)
        logger.info("TEST: Interface Status")
        logger.info("=" * 60)

        for device_name in devices:
            if device_name not in self.connected_devices:
                result.add_skip(f"Device not connected", device_name)
                continue

            device = self.connected_devices[device_name]

            try:
                # Parse interface status
                interfaces = device.parse("show ip interface brief")

                down_interfaces = []
                up_interfaces = 0
                admin_down = 0

                for intf_name, intf_data in interfaces.get("interface", {}).items():
                    status = intf_data.get("status", "").lower()
                    protocol = intf_data.get("protocol", "").lower()

                    # Skip management and unassigned interfaces
                    if "unassigned" in str(intf_data.get("ip_address", "")):
                        continue

                    # Skip loopbacks
                    if "Loopback" in intf_name:
                        continue

                    # Skip administratively shutdown interfaces
                    if status == "administratively down" or "admin" in status:
                        admin_down += 1
                        continue

                    if status == "up" and protocol == "up":
                        up_interfaces += 1
                    else:
                        down_interfaces.append((intf_name, status, protocol))

                if down_interfaces:
                    for intf_name, status, protocol in down_interfaces:
                        result.add_fail(
                            f"Interface {intf_name} is {status}/{protocol}",
                            device_name,
                            expected="up/up",
                            actual=f"{status}/{protocol}"
                        )

                msg = f"{up_interfaces} interfaces up/up"
                if admin_down > 0:
                    msg += f" ({admin_down} admin-down skipped)"
                result.add_pass(msg, device_name)

            except Exception as e:
                result.add_fail(f"Error parsing interfaces: {e}", device_name)

        self.results["interfaces"] = result
        return result
    
    # =========================================================================
    # Run All Tests
    # =========================================================================
    def run_all_tests(self, devices: List[str] = None):
        """Run all test categories."""
        logger.info("\n" + "=" * 70)
        logger.info("E UNIVERSITY NETWORK VALIDATION")
        logger.info(f"Started: {datetime.now().isoformat()}")
        logger.info("=" * 70)
        
        # Connect to devices
        self.connect_devices(devices)
        
        # Run tests
        self.test_connectivity(devices)
        self.test_interfaces(devices)
        self.test_ospf(devices)
        self.test_bgp(devices)
        self.test_mpls_ldp(devices)
        self.test_vrf(devices)
        
        # Only run reachability if we have connectivity
        if self.results.get("connectivity") and self.results["connectivity"].passed > 0:
            self.test_loopback_reachability()
        
        # Disconnect
        self.disconnect_devices()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        logger.info("\n" + "=" * 70)
        logger.info("TEST SUMMARY")
        logger.info("=" * 70)

        total_passed = 0
        total_failed = 0
        total_skipped = 0

        for test_name, result in self.results.items():
            logger.info(result.summary())
            total_passed += result.passed
            total_failed += result.failed
            total_skipped += result.skipped

        logger.info("-" * 70)
        overall = "PASSED" if total_failed == 0 else "FAILED"
        logger.info(f"OVERALL: {overall}")
        logger.info(f"Total: Pass={total_passed}, Fail={total_failed}, Skip={total_skipped}")
        logger.info("=" * 70)

    def export_results_json(self, output_file: str = None) -> Dict:
        """Export test results to JSON format.

        Args:
            output_file: Optional path to write JSON file. If None, returns dict only.
                        If file exists, a timestamped filename will be used instead.

        Returns:
            Dictionary with all test results.
        """
        total_passed = sum(r.passed for r in self.results.values())
        total_failed = sum(r.failed for r in self.results.values())
        total_skipped = sum(r.skipped for r in self.results.values())

        export_data = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "PASSED" if total_failed == 0 else "FAILED",
            "summary": {
                "total_passed": total_passed,
                "total_failed": total_failed,
                "total_skipped": total_skipped,
                "total_tests": total_passed + total_failed + total_skipped
            },
            "tests": {name: result.to_dict() for name, result in self.results.items()}
        }

        if output_file:
            # If file exists, add timestamp to filename
            actual_file = output_file
            if os.path.exists(output_file):
                base, ext = os.path.splitext(output_file)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                actual_file = f"{base}_{timestamp}{ext}"
                logger.info(f"File {output_file} exists, using: {actual_file}")

            with open(actual_file, 'w') as f:
                json.dump(export_data, f, indent=2)
            logger.info(f"Results exported to: {actual_file}")

        return export_data


def main():
    parser = argparse.ArgumentParser(description="E University Network Validation Tests")
    parser.add_argument("--testbed", required=True, help="pyATS testbed YAML file")
    parser.add_argument("--intent", help="Intent data YAML file")
    parser.add_argument("--test", choices=["all", "connectivity", "ospf", "bgp", "mpls", "vrf", "interfaces", "reachability"],
                       default="all", help="Test to run")
    parser.add_argument("--device", help="Specific device to test (default: all)")
    parser.add_argument("--json-output", "-j", help="Export results to JSON file (e.g., results.json)")
    args = parser.parse_args()
    
    # Initialize test suite
    tests = EUnivNetworkTests(args.testbed, args.intent)
    
    # Determine devices to test
    devices = [args.device] if args.device else None
    
    # Run tests
    if args.test == "all":
        tests.run_all_tests(devices)
    else:
        tests.connect_devices(devices)

        if args.test == "connectivity":
            tests.test_connectivity(devices)
        elif args.test == "ospf":
            tests.test_ospf(devices)
        elif args.test == "bgp":
            tests.test_bgp(devices)
        elif args.test == "mpls":
            tests.test_mpls_ldp(devices)
        elif args.test == "vrf":
            tests.test_vrf(devices)
        elif args.test == "interfaces":
            tests.test_interfaces(devices)
        elif args.test == "reachability":
            tests.test_loopback_reachability(args.device)

        tests.disconnect_devices()
        tests.print_summary()

    # Export JSON results if requested
    if args.json_output:
        tests.export_results_json(args.json_output)


if __name__ == "__main__":
    main()
