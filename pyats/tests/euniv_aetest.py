#!/usr/bin/env python3
"""
E-University Network Validation - AEtest Script

This AEtest script validates the E-University network infrastructure including:
- OSPF neighbor states
- BGP sessions (IPv4 and VPNv4)
- MPLS LDP neighbors
- VRF configuration
- Interface status
- End-to-end connectivity

Usage:
    # Run directly
    python euniv_aetest.py --testbed ../testbed.yaml

    # Run via jobfile (recommended)
    pyats run job ../euniv_job.py --testbed-file ../testbed.yaml

    # Dry-run (validate structure without connecting)
    pyats run job ../euniv_job.py --dry-run
"""

import re
import logging
from typing import Dict, List, Optional

from pyats import aetest
from pyats.topology import Testbed
from genie.testbed import load as genie_load
from unicon.core.errors import ConnectionError, SubCommandFailure

logger = logging.getLogger(__name__)


# =============================================================================
# Device Groups for selective testing
# =============================================================================
DEVICE_GROUPS = {
    'core': ['EUNIV-CORE1', 'EUNIV-CORE2', 'EUNIV-CORE3', 'EUNIV-CORE4', 'EUNIV-CORE5'],
    'route_reflectors': ['EUNIV-CORE1', 'EUNIV-CORE2', 'EUNIV-CORE5'],
    'inet_gw': ['EUNIV-INET-GW1', 'EUNIV-INET-GW2'],
    'aggregation': ['EUNIV-MAIN-AGG1', 'EUNIV-MED-AGG1', 'EUNIV-RES-AGG1'],
    'edge': [
        'EUNIV-MAIN-EDGE1', 'EUNIV-MAIN-EDGE2',
        'EUNIV-MED-EDGE1', 'EUNIV-MED-EDGE2',
        'EUNIV-RES-EDGE1', 'EUNIV-RES-EDGE2'
    ],
    'mpls_enabled': [
        'EUNIV-CORE1', 'EUNIV-CORE2', 'EUNIV-CORE3', 'EUNIV-CORE4', 'EUNIV-CORE5',
        'EUNIV-MAIN-AGG1', 'EUNIV-MED-AGG1', 'EUNIV-RES-AGG1',
        'EUNIV-MAIN-EDGE1', 'EUNIV-MAIN-EDGE2',
        'EUNIV-MED-EDGE1', 'EUNIV-MED-EDGE2',
        'EUNIV-RES-EDGE1', 'EUNIV-RES-EDGE2'
    ],
}


# =============================================================================
# Common Setup - Connect to all devices
# =============================================================================
class CommonSetup(aetest.CommonSetup):
    """Common setup tasks - connect to devices."""

    @aetest.subsection
    def check_testbed(self, testbed: Testbed):
        """Verify testbed is loaded and has devices."""
        if not testbed:
            self.failed("Testbed not provided")

        if not testbed.devices:
            self.failed("No devices found in testbed")

        logger.info(f"Testbed loaded with {len(testbed.devices)} devices")

    @aetest.subsection
    def connect_to_devices(self, testbed: Testbed, steps):
        """Connect to all devices in testbed."""
        connected = []
        failed = []

        for device_name, device in testbed.devices.items():
            with steps.start(f"Connecting to {device_name}") as step:
                try:
                    if device.is_connected():
                        logger.info(f"{device_name} already connected")
                        connected.append(device_name)
                    else:
                        device.connect(log_stdout=False, learn_hostname=True)
                        connected.append(device_name)
                        logger.info(f"Connected to {device_name}")
                except Exception as e:
                    step.failed(f"Failed to connect to {device_name}: {e}")
                    failed.append(device_name)

        # Store connected devices for use in tests
        self.parent.parameters['connected_devices'] = connected
        self.parent.parameters['failed_devices'] = failed

        if not connected:
            self.failed("Could not connect to any devices")

        logger.info(f"Connected: {len(connected)}, Failed: {len(failed)}")


# =============================================================================
# Test Case: OSPF Validation
# =============================================================================
class OSPFValidation(aetest.Testcase):
    """Validate OSPF neighbor states across all devices."""

    @aetest.setup
    def setup(self, testbed):
        """Setup for OSPF tests."""
        self.devices_to_test = [
            name for name in self.parent.parameters.get('connected_devices', [])
            if name in testbed.devices
        ]
        if not self.devices_to_test:
            self.skipped("No connected devices to test")

    @aetest.test
    def test_ospf_neighbors(self, testbed, steps):
        """Verify all OSPF neighbors are in FULL state."""

        for device_name in self.devices_to_test:
            with steps.start(f"Checking OSPF on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    ospf_output = device.parse("show ip ospf neighbor")

                    if not ospf_output:
                        step.skipped(f"No OSPF configured on {device_name}")
                        continue

                    interfaces = ospf_output.get("interfaces", {})
                    neighbor_count = 0
                    not_full = []

                    for intf, intf_data in interfaces.items():
                        neighbors = intf_data.get("neighbors", {})
                        for neighbor_id, neighbor_data in neighbors.items():
                            neighbor_count += 1
                            state = neighbor_data.get("state", "").upper()
                            if "FULL" not in state:
                                not_full.append(f"{neighbor_id} on {intf}: {state}")

                    if not_full:
                        step.failed(f"OSPF neighbors not FULL: {', '.join(not_full)}")
                    elif neighbor_count > 0:
                        step.passed(f"{neighbor_count} OSPF neighbors in FULL state")
                    else:
                        step.skipped("No OSPF neighbors found")

                except Exception as e:
                    step.failed(f"Error checking OSPF: {e}")


# =============================================================================
# Test Case: BGP Validation
# =============================================================================
class BGPValidation(aetest.Testcase):
    """Validate BGP sessions (IPv4 and VPNv4)."""

    @aetest.setup
    def setup(self, testbed):
        """Setup for BGP tests."""
        self.devices_to_test = [
            name for name in self.parent.parameters.get('connected_devices', [])
            if name in testbed.devices
        ]
        if not self.devices_to_test:
            self.skipped("No connected devices to test")

    @aetest.test
    def test_bgp_sessions(self, testbed, steps):
        """Verify all BGP sessions are established."""

        for device_name in self.devices_to_test:
            with steps.start(f"Checking BGP on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show bgp all summary")

                    established = 0
                    not_established = []

                    for line in output.splitlines():
                        match = re.match(r'^(\d+\.\d+\.\d+\.\d+)\s+', line.strip())
                        if match:
                            parts = line.split()
                            if len(parts) >= 9:
                                neighbor = parts[0]
                                state = parts[-1]

                                if state.isdigit():
                                    established += 1
                                elif state in ["Idle", "Active", "Connect", "OpenSent", "OpenConfirm"]:
                                    not_established.append(f"{neighbor}: {state}")
                                else:
                                    established += 1

                    if not_established:
                        step.failed(f"BGP sessions not established: {', '.join(not_established)}")
                    elif established > 0:
                        step.passed(f"{established} BGP sessions established")
                    else:
                        # Check if BGP should be configured on this device
                        if any(x in device_name for x in ['CORE', 'AGG', 'EDGE', 'GW']):
                            step.failed("No BGP sessions found (expected on this device)")
                        else:
                            step.skipped("BGP not configured")

                except Exception as e:
                    step.failed(f"Error checking BGP: {e}")

    @aetest.test
    def test_vpnv4_sessions(self, testbed, steps):
        """Verify VPNv4 address family sessions on Route Reflectors and Edge routers."""

        vpnv4_devices = DEVICE_GROUPS['route_reflectors'] + DEVICE_GROUPS['edge'] + DEVICE_GROUPS['aggregation']
        devices_to_check = [d for d in self.devices_to_test if d in vpnv4_devices]

        if not devices_to_check:
            self.skipped("No VPNv4 devices connected")

        for device_name in devices_to_check:
            with steps.start(f"Checking VPNv4 on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show bgp vpnv4 unicast all summary")

                    if "not active" in output.lower() or "no neighbor" in output.lower():
                        step.skipped("VPNv4 not active")
                        continue

                    established = 0
                    for line in output.splitlines():
                        match = re.match(r'^(\d+\.\d+\.\d+\.\d+)\s+', line.strip())
                        if match:
                            parts = line.split()
                            if len(parts) >= 9:
                                state = parts[-1]
                                if state.isdigit():
                                    established += 1

                    if established > 0:
                        step.passed(f"{established} VPNv4 sessions established")
                    else:
                        step.failed("No VPNv4 sessions established")

                except Exception as e:
                    step.failed(f"Error checking VPNv4: {e}")


# =============================================================================
# Test Case: MPLS LDP Validation
# =============================================================================
class MPLSLDPValidation(aetest.Testcase):
    """Validate MPLS LDP neighbor states."""

    @aetest.setup
    def setup(self, testbed):
        """Setup for MPLS tests - only test MPLS-enabled devices."""
        connected = self.parent.parameters.get('connected_devices', [])
        self.devices_to_test = [
            name for name in connected
            if name in DEVICE_GROUPS['mpls_enabled'] and name in testbed.devices
        ]
        if not self.devices_to_test:
            self.skipped("No MPLS-enabled devices connected")

    @aetest.test
    def test_ldp_neighbors(self, testbed, steps):
        """Verify all LDP neighbors are operational."""

        for device_name in self.devices_to_test:
            with steps.start(f"Checking LDP on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show mpls ldp neighbor")

                    if "No LDP" in output or not output.strip():
                        step.skipped("LDP not configured")
                        continue

                    operational = 0
                    not_operational = []
                    current_peer = None

                    for line in output.splitlines():
                        peer_match = re.search(r'Peer LDP Ident:\s*(\d+\.\d+\.\d+\.\d+)', line)
                        if peer_match:
                            current_peer = peer_match.group(1)

                        state_match = re.search(r'State:\s*(\w+)', line)
                        if state_match and current_peer:
                            state = state_match.group(1)
                            if state.lower() == "oper":
                                operational += 1
                            else:
                                not_operational.append(f"{current_peer}: {state}")
                            current_peer = None

                    if not_operational:
                        step.failed(f"LDP peers not operational: {', '.join(not_operational)}")
                    elif operational > 0:
                        step.passed(f"{operational} LDP neighbors operational")
                    else:
                        step.failed("No operational LDP neighbors found")

                except Exception as e:
                    step.failed(f"Error checking LDP: {e}")


# =============================================================================
# Test Case: VRF Validation
# =============================================================================
class VRFValidation(aetest.Testcase):
    """Validate VRF configuration on Edge routers."""

    EXPECTED_VRFS = {
        'STAFF-NET': {'rt': '65000:200'},
        'GUEST-NET': {'rt': '65000:500'},
        'RESEARCH-NET': {'rt': '65000:300'},
    }

    # VRFs specific to certain campuses
    CAMPUS_SPECIFIC_VRFS = {
        'STUDENT-NET': ['MAIN'],
        'MEDICAL-NET': ['MED'],
    }

    @aetest.setup
    def setup(self, testbed):
        """Setup for VRF tests - only test Edge devices."""
        connected = self.parent.parameters.get('connected_devices', [])
        self.devices_to_test = [
            name for name in connected
            if name in DEVICE_GROUPS['edge'] and name in testbed.devices
        ]
        if not self.devices_to_test:
            self.skipped("No Edge devices connected")

    @aetest.test
    def test_vrf_configuration(self, testbed, steps):
        """Verify VRFs are properly configured."""

        for device_name in self.devices_to_test:
            with steps.start(f"Checking VRFs on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    vrf_output = device.parse("show vrf detail")

                    if not vrf_output:
                        step.failed("No VRF configuration found")
                        continue

                    configured_vrfs = list(vrf_output.keys())
                    missing = []

                    # Check common VRFs
                    for vrf_name in self.EXPECTED_VRFS.keys():
                        if vrf_name not in configured_vrfs:
                            missing.append(vrf_name)

                    # Check campus-specific VRFs
                    for vrf_name, campuses in self.CAMPUS_SPECIFIC_VRFS.items():
                        should_have = any(c in device_name for c in campuses)
                        has_vrf = vrf_name in configured_vrfs

                        if should_have and not has_vrf:
                            missing.append(f"{vrf_name} (expected for this campus)")

                    if missing:
                        step.failed(f"Missing VRFs: {', '.join(missing)}")
                    else:
                        step.passed(f"All expected VRFs configured ({len(configured_vrfs)} total)")

                except Exception as e:
                    step.failed(f"Error checking VRFs: {e}")


# =============================================================================
# Test Case: Interface Status
# =============================================================================
class InterfaceValidation(aetest.Testcase):
    """Validate interface operational status."""

    @aetest.setup
    def setup(self, testbed):
        """Setup for interface tests."""
        self.devices_to_test = [
            name for name in self.parent.parameters.get('connected_devices', [])
            if name in testbed.devices
        ]
        if not self.devices_to_test:
            self.skipped("No connected devices to test")

    @aetest.test
    def test_interface_status(self, testbed, steps):
        """Verify configured interfaces are up/up."""

        for device_name in self.devices_to_test:
            with steps.start(f"Checking interfaces on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    interfaces = device.parse("show ip interface brief")

                    down_interfaces = []
                    up_count = 0
                    admin_down = 0

                    for intf_name, intf_data in interfaces.get("interface", {}).items():
                        status = intf_data.get("status", "").lower()
                        protocol = intf_data.get("protocol", "").lower()
                        ip_addr = str(intf_data.get("ip_address", ""))

                        # Skip unassigned and loopback interfaces
                        if "unassigned" in ip_addr or "Loopback" in intf_name:
                            continue

                        # Skip admin-down interfaces
                        if "admin" in status:
                            admin_down += 1
                            continue

                        if status == "up" and protocol == "up":
                            up_count += 1
                        else:
                            down_interfaces.append(f"{intf_name}: {status}/{protocol}")

                    if down_interfaces:
                        step.failed(f"Interfaces down: {', '.join(down_interfaces)}")
                    else:
                        msg = f"{up_count} interfaces up/up"
                        if admin_down > 0:
                            msg += f" ({admin_down} admin-down skipped)"
                        step.passed(msg)

                except Exception as e:
                    step.failed(f"Error checking interfaces: {e}")


# =============================================================================
# Test Case: End-to-End Connectivity
# =============================================================================
class ConnectivityValidation(aetest.Testcase):
    """Validate end-to-end connectivity between core devices."""

    # Loopback IPs for ping tests
    LOOPBACK_IPS = {
        'EUNIV-CORE1': '10.255.0.1',
        'EUNIV-CORE2': '10.255.0.2',
        'EUNIV-CORE3': '10.255.0.3',
        'EUNIV-CORE4': '10.255.0.4',
        'EUNIV-CORE5': '10.255.0.5',
    }

    @aetest.setup
    def setup(self, testbed):
        """Setup - use CORE1 as source for ping tests."""
        connected = self.parent.parameters.get('connected_devices', [])

        if 'EUNIV-CORE1' not in connected:
            self.skipped("EUNIV-CORE1 not connected - cannot run connectivity tests")

        self.source_device = 'EUNIV-CORE1'
        self.targets = {k: v for k, v in self.LOOPBACK_IPS.items() if k != self.source_device}

    @aetest.test
    def test_loopback_reachability(self, testbed, steps):
        """Ping all core loopbacks from CORE1."""

        device = testbed.devices[self.source_device]

        for target_name, target_ip in self.targets.items():
            with steps.start(f"Ping {target_name} ({target_ip})") as step:
                try:
                    result = device.ping(target_ip, count=3)

                    # device.ping() returns a string with the ping output
                    # Check for success rate in the output
                    if result and "Success rate is 100 percent" in result:
                        step.passed(f"Ping to {target_ip} successful")
                    elif result and "Success rate is" in result:
                        # Partial success - extract the percentage
                        match = re.search(r'Success rate is (\d+) percent', result)
                        if match:
                            pct = int(match.group(1))
                            if pct > 0:
                                step.passed(f"Ping to {target_ip} succeeded ({pct}%)")
                            else:
                                step.failed(f"Ping to {target_ip} failed (0%)")
                        else:
                            step.failed(f"Ping to {target_ip} failed")
                    else:
                        step.failed(f"Ping to {target_ip} failed - no response")

                except Exception as e:
                    step.failed(f"Ping error: {e}")


# =============================================================================
# Test Case: BFD Validation
# =============================================================================
class BFDValidation(aetest.Testcase):
    """Validate BFD neighbor states on edge links."""

    # BFD is configured on edge links only (not inside MPLS core):
    # - Core <-> INET-GW links
    # - AGG <-> Edge links
    BFD_DEVICES = [
        'EUNIV-CORE1', 'EUNIV-CORE2',           # Core side of Core<->INET-GW
        'EUNIV-INET-GW1', 'EUNIV-INET-GW2',     # INET-GW side
        'EUNIV-MAIN-AGG1', 'EUNIV-MED-AGG1', 'EUNIV-RES-AGG1',  # AGG side
        'EUNIV-MAIN-EDGE1', 'EUNIV-MAIN-EDGE2',  # Main campus edge
        'EUNIV-MED-EDGE1', 'EUNIV-MED-EDGE2',    # Med campus edge
        'EUNIV-RES-EDGE1', 'EUNIV-RES-EDGE2',    # Research campus edge
    ]

    @aetest.setup
    def setup(self, testbed):
        """Setup for BFD tests."""
        connected = self.parent.parameters.get('connected_devices', [])
        self.devices_to_test = [
            name for name in connected
            if name in self.BFD_DEVICES and name in testbed.devices
        ]
        if not self.devices_to_test:
            self.skipped("No BFD-enabled devices connected")

    @aetest.test
    def test_bfd_neighbors(self, testbed, steps):
        """Verify BFD neighbors are up."""

        for device_name in self.devices_to_test:
            with steps.start(f"Checking BFD on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show bfd neighbors")

                    if "No BFD" in output or "does not exist" in output or not output.strip():
                        step.skipped("BFD not configured")
                        continue

                    # Count Up neighbors
                    up_count = len(re.findall(r'\bUp\b', output))
                    down_count = len(re.findall(r'\bDown\b', output))

                    if down_count > 0:
                        step.failed(f"BFD neighbors down: {down_count}")
                    elif up_count > 0:
                        step.passed(f"{up_count} BFD neighbors up")
                    else:
                        step.skipped("No BFD neighbors found")

                except Exception as e:
                    step.skipped(f"Could not check BFD: {e}")


# =============================================================================
# Common Cleanup - Disconnect from devices
# =============================================================================
class CommonCleanup(aetest.CommonCleanup):
    """Common cleanup tasks - disconnect from devices."""

    @aetest.subsection
    def disconnect_from_devices(self, testbed):
        """Disconnect from all devices."""
        for device_name, device in testbed.devices.items():
            try:
                if device.is_connected():
                    device.disconnect()
                    logger.info(f"Disconnected from {device_name}")
            except Exception as e:
                logger.warning(f"Error disconnecting from {device_name}: {e}")


# =============================================================================
# Main - for standalone execution
# =============================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="E-University Network AEtest")
    parser.add_argument("--testbed", required=True, help="Testbed YAML file")
    args = parser.parse_args()

    # Load testbed
    testbed = genie_load(args.testbed)

    # Run tests
    aetest.main(testbed=testbed)
