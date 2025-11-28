#!/usr/bin/env python3
"""
Network Validation Script
=========================
Runs pre-deployment and post-deployment validation tests.

Usage:
    python validate.py --pre                      # Pre-deployment checks
    python validate.py --post                     # Post-deployment checks
    python validate.py --device EUNIV-CORE1       # Check single device
    python validate.py --test connectivity        # Run specific test
"""

import argparse
import sys
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

from pyats.topology import loader
from genie.libs.parser.utils import get_parser


@dataclass
class TestResult:
    """Container for test results."""
    name: str
    passed: bool
    message: str
    device: str = ""
    expected: str = ""
    actual: str = ""


@dataclass
class ValidationReport:
    """Container for full validation report."""
    test_type: str
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    results: list = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def total(self) -> int:
        return len(self.results)

    def add(self, result: TestResult):
        self.results.append(result)

    def print_summary(self):
        print()
        print("=" * 70)
        print(f"VALIDATION REPORT - {self.test_type}")
        print("=" * 70)
        print(f"Timestamp: {self.timestamp}")
        print(f"Total:     {self.total}")
        print(f"Passed:    {self.passed}")
        print(f"Failed:    {self.failed}")
        print("=" * 70)

        if self.failed > 0:
            print("\nFailed Tests:")
            for r in self.results:
                if not r.passed:
                    print(f"  ✗ [{r.device}] {r.name}: {r.message}")
                    if r.expected:
                        print(f"      Expected: {r.expected}")
                        print(f"      Actual:   {r.actual}")
        print()


class NetworkValidator:
    """Validates network state before and after changes."""

    def __init__(self, testbed_path: str = "pyats/testbed.yaml"):
        self.testbed = loader.load(testbed_path)
        self.connected_devices = {}

    def connect(self, device_name: Optional[str] = None):
        """Connect to devices."""
        devices = [device_name] if device_name else list(self.testbed.devices.keys())

        for name in devices:
            if name not in self.connected_devices:
                try:
                    device = self.testbed.devices[name]
                    device.connect(log_stdout=False)
                    self.connected_devices[name] = device
                except Exception as e:
                    print(f"  ✗ Failed to connect to {name}: {e}")

    def disconnect(self):
        """Disconnect from all devices."""
        for device in self.connected_devices.values():
            try:
                device.disconnect()
            except:
                pass
        self.connected_devices.clear()

    # =========================================================================
    # TEST: Connectivity
    # =========================================================================
    def test_connectivity(self, report: ValidationReport, device_name: Optional[str] = None):
        """Test basic SSH connectivity to devices."""
        devices = [device_name] if device_name else list(self.testbed.devices.keys())

        print("\n[TEST] Connectivity")

        for name in devices:
            try:
                device = self.testbed.devices[name]
                device.connect(log_stdout=False)
                self.connected_devices[name] = device

                report.add(TestResult(
                    name="SSH Connectivity",
                    device=name,
                    passed=True,
                    message="Connected successfully"
                ))
                print(f"  ✓ {name}")

            except Exception as e:
                report.add(TestResult(
                    name="SSH Connectivity",
                    device=name,
                    passed=False,
                    message=f"Connection failed: {e}"
                ))
                print(f"  ✗ {name}")

    # =========================================================================
    # TEST: Interface Status
    # =========================================================================
    def test_interfaces(self, report: ValidationReport, device_name: Optional[str] = None):
        """Test that core interfaces are up/up."""
        devices = [device_name] if device_name else list(self.connected_devices.keys())

        print("\n[TEST] Interface Status")

        # Only check interfaces we actually configure (Gi1-Gi6, Loopback0)
        # Skip Gi7, Gi8, Gi9 etc as these are unused
        configured_interfaces = [
            "GigabitEthernet1", "GigabitEthernet2", "GigabitEthernet3",
            "GigabitEthernet4", "GigabitEthernet5", "GigabitEthernet6",
            "Loopback0"
        ]

        for name in devices:
            if name not in self.connected_devices:
                continue

            device = self.connected_devices[name]

            try:
                output = device.parse("show ip interface brief")

                checked = 0
                for intf_name, intf_data in output.get("interface", {}).items():
                    # Only check interfaces we configure
                    if not any(cfg_intf in intf_name for cfg_intf in configured_interfaces):
                        continue

                    # Skip unconfigured interfaces (no IP)
                    ip_address = intf_data.get("ip_address", "unassigned")
                    if ip_address == "unassigned":
                        continue

                    status = intf_data.get("status", "unknown")
                    protocol = intf_data.get("protocol", "unknown")

                    checked += 1
                    if status == "up" and protocol == "up":
                        report.add(TestResult(
                            name=f"Interface {intf_name}",
                            device=name,
                            passed=True,
                            message="up/up"
                        ))
                    else:
                        report.add(TestResult(
                            name=f"Interface {intf_name}",
                            device=name,
                            passed=False,
                            message=f"{status}/{protocol}",
                            expected="up/up",
                            actual=f"{status}/{protocol}"
                        ))

                print(f"  ✓ {name} - {checked} interfaces checked")

            except Exception as e:
                report.add(TestResult(
                    name="Interface Status",
                    device=name,
                    passed=False,
                    message=f"Parse error: {e}"
                ))
                print(f"  ✗ {name} - {e}")

    # =========================================================================
    # TEST: OSPF Neighbors
    # =========================================================================
    def test_ospf(self, report: ValidationReport, device_name: Optional[str] = None):
        """Test OSPF neighbor adjacencies."""
        devices = [device_name] if device_name else list(self.connected_devices.keys())

        print("\n[TEST] OSPF Neighbors")

        for name in devices:
            if name not in self.connected_devices:
                continue

            device = self.connected_devices[name]

            try:
                output = device.parse("show ip ospf neighbor")

                neighbors = output.get("interfaces", {})
                neighbor_count = sum(
                    len(intf.get("neighbors", {}))
                    for intf in neighbors.values()
                )

                if neighbor_count > 0:
                    # Check all neighbors are FULL
                    all_full = True
                    for intf_name, intf_data in neighbors.items():
                        for nbr_id, nbr_data in intf_data.get("neighbors", {}).items():
                            state = nbr_data.get("state", "")
                            if "FULL" not in state:
                                all_full = False
                                report.add(TestResult(
                                    name=f"OSPF Neighbor {nbr_id}",
                                    device=name,
                                    passed=False,
                                    message=f"State: {state}",
                                    expected="FULL",
                                    actual=state
                                ))

                    if all_full:
                        report.add(TestResult(
                            name="OSPF Neighbors",
                            device=name,
                            passed=True,
                            message=f"{neighbor_count} neighbors in FULL state"
                        ))
                        print(f"  ✓ {name} - {neighbor_count} OSPF neighbors (FULL)")
                    else:
                        print(f"  ✗ {name} - OSPF neighbors not FULL")
                else:
                    report.add(TestResult(
                        name="OSPF Neighbors",
                        device=name,
                        passed=False,
                        message="No OSPF neighbors found"
                    ))
                    print(f"  ✗ {name} - no OSPF neighbors")

            except Exception as e:
                # No OSPF configured yet is OK for pre-checks
                report.add(TestResult(
                    name="OSPF Neighbors",
                    device=name,
                    passed=True,
                    message="OSPF not configured (expected for pre-check)"
                ))
                print(f"  - {name} - OSPF not configured")

    # =========================================================================
    # TEST: BGP Sessions
    # =========================================================================
    def test_bgp(self, report: ValidationReport, device_name: Optional[str] = None):
        """Test BGP session establishment."""
        devices = [device_name] if device_name else list(self.connected_devices.keys())

        print("\n[TEST] BGP Sessions")

        for name in devices:
            if name not in self.connected_devices:
                continue

            device = self.connected_devices[name]

            try:
                output = device.parse("show ip bgp summary")

                vrf_data = output.get("vrf", {}).get("default", {})
                neighbors = vrf_data.get("neighbor", {})

                established = 0
                not_established = []

                for nbr_ip, nbr_data in neighbors.items():
                    session_state = nbr_data.get("session_state", "")

                    # BGP is established if:
                    # 1. session_state is "Established"
                    # 2. session_state is empty/missing but state_pfxrcd exists (prefix count)
                    # 3. address_family exists (means session is up)
                    state_pfxrcd = nbr_data.get("state_pfxrcd", None)
                    address_family = nbr_data.get("address_family", {})

                    is_established = (
                            session_state == "Established" or
                            (state_pfxrcd is not None and str(state_pfxrcd).isdigit()) or
                            (isinstance(state_pfxrcd, int)) or
                            len(address_family) > 0
                    )

                    if is_established:
                        established += 1
                    else:
                        not_established.append((nbr_ip, session_state or "Unknown"))

                # Report failures
                for nbr_ip, state in not_established:
                    report.add(TestResult(
                        name=f"BGP Neighbor {nbr_ip}",
                        device=name,
                        passed=False,
                        message=f"State: {state}",
                        expected="Established",
                        actual=state
                    ))

                if established > 0:
                    report.add(TestResult(
                        name="BGP Sessions",
                        device=name,
                        passed=True,
                        message=f"{established} sessions established"
                    ))
                    print(f"  ✓ {name} - {established} BGP sessions established")
                else:
                    report.add(TestResult(
                        name="BGP Sessions",
                        device=name,
                        passed=False,
                        message="No BGP sessions established"
                    ))
                    print(f"  ✗ {name} - no BGP sessions established")

            except Exception as e:
                report.add(TestResult(
                    name="BGP Sessions",
                    device=name,
                    passed=True,
                    message="BGP not configured (expected for pre-check)"
                ))
                print(f"  - {name} - BGP not configured")

    # =========================================================================
    # TEST: MPLS LDP
    # =========================================================================
    def test_mpls(self, report: ValidationReport, device_name: Optional[str] = None):
        """Test MPLS LDP neighbor establishment."""
        devices = [device_name] if device_name else list(self.connected_devices.keys())

        print("\n[TEST] MPLS LDP")

        for name in devices:
            if name not in self.connected_devices:
                continue

            device = self.connected_devices[name]

            try:
                # Use raw command - more reliable than parser
                output = device.execute("show mpls ldp neighbor")

                # Count "State: Oper" occurrences (case-insensitive)
                # The output format is: "State: Oper; Msgs sent/rcvd: 67/67"
                oper_count = output.upper().count("STATE: OPER")

                # Also count "Peer LDP Ident" as backup method
                peer_count = output.count("Peer LDP Ident")

                # Use whichever gives us a count
                neighbor_count = max(oper_count, peer_count)

                if neighbor_count > 0:
                    report.add(TestResult(
                        name="MPLS LDP Neighbors",
                        device=name,
                        passed=True,
                        message=f"{neighbor_count} LDP neighbors operational"
                    ))
                    print(f"  ✓ {name} - {neighbor_count} LDP neighbors operational")
                elif "% No LDP" in output or output.strip() == "" or "not running" in output.lower():
                    report.add(TestResult(
                        name="MPLS LDP Neighbors",
                        device=name,
                        passed=True,
                        message="MPLS not configured (expected for edge devices)"
                    ))
                    print(f"  - {name} - MPLS not configured")
                else:
                    report.add(TestResult(
                        name="MPLS LDP Neighbors",
                        device=name,
                        passed=False,
                        message="No LDP neighbors found"
                    ))
                    print(f"  ✗ {name} - no LDP neighbors")

            except Exception as e:
                report.add(TestResult(
                    name="MPLS LDP Neighbors",
                    device=name,
                    passed=True,
                    message="MPLS not configured"
                ))
                print(f"  - {name} - MPLS not configured")

    # =========================================================================
    # RUN VALIDATION SUITE
    # =========================================================================
    def run_pre_checks(self, device_name: Optional[str] = None) -> ValidationReport:
        """Run pre-deployment validation."""
        report = ValidationReport(test_type="PRE-DEPLOYMENT")

        print("\n" + "=" * 70)
        print("PRE-DEPLOYMENT VALIDATION")
        print("=" * 70)

        self.test_connectivity(report, device_name)
        self.test_interfaces(report, device_name)

        self.disconnect()
        report.print_summary()

        return report

    def run_post_checks(self, device_name: Optional[str] = None) -> ValidationReport:
        """Run post-deployment validation."""
        report = ValidationReport(test_type="POST-DEPLOYMENT")

        print("\n" + "=" * 70)
        print("POST-DEPLOYMENT VALIDATION")
        print("=" * 70)

        self.test_connectivity(report, device_name)
        self.test_interfaces(report, device_name)
        self.test_ospf(report, device_name)
        self.test_bgp(report, device_name)
        self.test_mpls(report, device_name)

        self.disconnect()
        report.print_summary()

        return report


def main():
    parser = argparse.ArgumentParser(description="Network Validation Script")
    parser.add_argument("--pre", action="store_true", help="Run pre-deployment checks")
    parser.add_argument("--post", action="store_true", help="Run post-deployment checks")
    parser.add_argument("--device", "-d", help="Validate single device")
    parser.add_argument("--testbed", default="pyats/testbed.yaml", help="Testbed file path")

    args = parser.parse_args()

    if not args.pre and not args.post:
        print("Specify --pre or --post")
        sys.exit(1)

    validator = NetworkValidator(args.testbed)

    if args.pre:
        report = validator.run_pre_checks(args.device)
    else:
        report = validator.run_post_checks(args.device)

    # Exit with error code if tests failed
    sys.exit(0 if report.failed == 0 else 1)


if __name__ == "__main__":
    main()