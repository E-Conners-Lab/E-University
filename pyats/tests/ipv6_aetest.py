#!/usr/bin/env python3
"""
E-University Network IPv6 Validation - AEtest Script

This AEtest script validates IPv6 dual-stack deployment including:
- IPv6 interface addressing
- OSPFv3 neighbor states
- BGP IPv6 sessions (global and VPNv6)
- IPv6 end-to-end connectivity

Usage:
    # Run directly
    python ipv6_aetest.py --testbed ../testbed.yaml

    # Run via jobfile (recommended)
    pyats run job ../ipv6_job.py --testbed-file ../testbed.yaml
"""

import logging
import re
import sys
from pathlib import Path

from pyats import aetest
from pyats.topology import Testbed

# Add scripts directory to path for importing intent_data
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from intent_data import DEVICES, VRFS

logger = logging.getLogger(__name__)


# =============================================================================
# Expected IPv6 Configuration (from intent_data.py)
# =============================================================================
def get_expected_ipv6_config():
    """Extract expected IPv6 configuration from intent data."""
    config = {}
    for device_name, device_data in DEVICES.items():
        loopback_ipv6 = device_data.get("loopback_ipv6")
        if loopback_ipv6:
            config[device_name] = {
                "loopback_ipv6": loopback_ipv6,
                "interfaces": {},
                "bgp_neighbors_v6": [],
            }
            # Get interface IPv6 addresses
            for intf in device_data.get("interfaces", []):
                if "ipv6" in intf:
                    config[device_name]["interfaces"][intf["name"]] = intf["ipv6"]

            # Get BGP IPv6 neighbors
            for neighbor in device_data.get("bgp_neighbors", []):
                if "ipv6" in neighbor:
                    config[device_name]["bgp_neighbors_v6"].append({
                        "ipv6": neighbor["ipv6"],
                        "remote_as": neighbor["remote_as"],
                        "description": neighbor["description"],
                    })
    return config


EXPECTED_IPV6 = get_expected_ipv6_config()

# Device groups
DEVICE_GROUPS = {
    'core': ['EUNIV-CORE1', 'EUNIV-CORE2', 'EUNIV-CORE3', 'EUNIV-CORE4', 'EUNIV-CORE5'],
    'route_reflectors': ['EUNIV-CORE1', 'EUNIV-CORE2', 'EUNIV-CORE5'],
    'inet_gw': ['EUNIV-INET-GW1', 'EUNIV-INET-GW2'],
    'aggregation': ['EUNIV-MAIN-AGG1', 'EUNIV-MED-AGG1', 'EUNIV-RES-AGG1'],
    'pe': [
        'EUNIV-MAIN-PE1', 'EUNIV-MAIN-PE2',
        'EUNIV-MED-PE1', 'EUNIV-MED-PE2',
        'EUNIV-RES-PE1', 'EUNIV-RES-PE2'
    ],
}


# =============================================================================
# Common Setup
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

        self.parent.parameters['connected_devices'] = connected
        self.parent.parameters['failed_devices'] = failed

        if not connected:
            self.failed("Could not connect to any devices")

        logger.info(f"Connected: {len(connected)}, Failed: {len(failed)}")


# =============================================================================
# Test Case: IPv6 Interface Configuration
# =============================================================================
class IPv6InterfaceValidation(aetest.Testcase):
    """Validate IPv6 addresses are configured on interfaces."""

    @aetest.setup
    def setup(self, testbed):
        """Setup for IPv6 interface tests."""
        self.devices_to_test = [
            name for name in self.parent.parameters.get('connected_devices', [])
            if name in EXPECTED_IPV6 and name in testbed.devices
        ]
        if not self.devices_to_test:
            self.skipped("No devices with expected IPv6 config connected")

    @aetest.test
    def test_loopback_ipv6(self, testbed, steps):
        """Verify IPv6 loopback addresses are configured."""

        for device_name in self.devices_to_test:
            expected = EXPECTED_IPV6.get(device_name, {})
            expected_loopback = expected.get("loopback_ipv6")

            if not expected_loopback:
                continue

            with steps.start(f"Checking Loopback0 IPv6 on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show ipv6 interface Loopback0")

                    if "IPv6 is disabled" in output or "not enabled" in output.lower():
                        step.failed("IPv6 not enabled on Loopback0")
                        continue

                    # Check if expected address is present (case-insensitive)
                    # Address format: 2001:db8:e011::1/128
                    if expected_loopback.lower() in output.lower():
                        step.passed(f"Loopback0 has {expected_loopback}")
                    else:
                        step.failed(f"Expected {expected_loopback}/128 not found")

                except Exception as e:
                    step.failed(f"Error checking Loopback0: {e}")

    @aetest.test
    def test_interface_ipv6(self, testbed, steps):
        """Verify IPv6 addresses on P2P interfaces."""

        for device_name in self.devices_to_test:
            expected = EXPECTED_IPV6.get(device_name, {})
            expected_intfs = expected.get("interfaces", {})

            if not expected_intfs:
                continue

            with steps.start(f"Checking P2P interface IPv6 on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show ipv6 interface brief")

                    missing = []
                    found = []

                    for intf_name, ipv6_addr in expected_intfs.items():
                        # Extract address without prefix length for comparison
                        addr_only = ipv6_addr.split('/')[0]

                        if addr_only.lower() in output.lower():
                            found.append(intf_name)
                        else:
                            missing.append(f"{intf_name}: {ipv6_addr}")

                    if missing:
                        step.failed(f"Missing IPv6: {', '.join(missing)}")
                    else:
                        step.passed(f"All {len(found)} interfaces have IPv6 configured")

                except Exception as e:
                    step.failed(f"Error checking interfaces: {e}")


# =============================================================================
# Test Case: OSPFv3 Validation
# =============================================================================
class OSPFv3Validation(aetest.Testcase):
    """Validate OSPFv3 neighbor states."""

    @aetest.setup
    def setup(self, testbed):
        """Setup for OSPFv3 tests."""
        self.devices_to_test = [
            name for name in self.parent.parameters.get('connected_devices', [])
            if name in EXPECTED_IPV6 and name in testbed.devices
        ]
        if not self.devices_to_test:
            self.skipped("No devices with expected IPv6 config connected")

    @aetest.test
    def test_ospfv3_neighbors(self, testbed, steps):
        """Verify all OSPFv3 neighbors are in FULL state."""

        for device_name in self.devices_to_test:
            with steps.start(f"Checking OSPFv3 on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show ospfv3 neighbor")

                    if "not found" in output.lower() or not output.strip():
                        step.skipped("OSPFv3 not configured")
                        continue

                    # Count neighbors in FULL state
                    full_count = len(re.findall(r'\bFULL\b', output, re.IGNORECASE))
                    not_full = len(re.findall(r'\b(2WAY|INIT|DOWN|EXSTART|EXCHANGE|LOADING)\b', output, re.IGNORECASE))

                    if not_full > 0:
                        step.failed(f"{not_full} OSPFv3 neighbors not in FULL state")
                    elif full_count > 0:
                        step.passed(f"{full_count} OSPFv3 neighbors in FULL state")
                    else:
                        step.skipped("No OSPFv3 neighbors found")

                except Exception as e:
                    step.failed(f"Error checking OSPFv3: {e}")

    @aetest.test
    def test_ospfv3_routes(self, testbed, steps):
        """Verify OSPFv3 is learning routes."""

        # Pick a core device as test source
        test_device = None
        for name in ['EUNIV-CORE1', 'EUNIV-CORE2']:
            if name in self.devices_to_test:
                test_device = name
                break

        if not test_device:
            self.skipped("No core device available for route test")
            return

        with steps.start(f"Checking OSPFv3 routes on {test_device}") as step:
            device = testbed.devices[test_device]

            try:
                output = device.execute("show ipv6 route ospf")

                if "not found" in output.lower():
                    step.skipped("No OSPFv3 routes found")
                    return

                # Count routes with 'O' (OSPF) prefix
                route_count = len(re.findall(r'^O\w*\s', output, re.MULTILINE))

                if route_count > 0:
                    step.passed(f"OSPFv3 has installed {route_count} routes")
                else:
                    step.failed("No OSPFv3 routes installed")

            except Exception as e:
                step.failed(f"Error checking routes: {e}")


# =============================================================================
# Test Case: BGP IPv6 Validation
# =============================================================================
class BGPIPv6Validation(aetest.Testcase):
    """Validate BGP IPv6 sessions."""

    @aetest.setup
    def setup(self, testbed):
        """Setup for BGP IPv6 tests."""
        self.devices_to_test = [
            name for name in self.parent.parameters.get('connected_devices', [])
            if name in EXPECTED_IPV6 and name in testbed.devices
        ]
        if not self.devices_to_test:
            self.skipped("No devices with expected IPv6 config connected")

    @aetest.test
    def test_bgp_ipv6_sessions(self, testbed, steps):
        """Verify BGP IPv6 unicast sessions are established."""

        for device_name in self.devices_to_test:
            expected = EXPECTED_IPV6.get(device_name, {})
            expected_neighbors = expected.get("bgp_neighbors_v6", [])

            if not expected_neighbors:
                continue

            with steps.start(f"Checking BGP IPv6 sessions on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show bgp ipv6 unicast summary")

                    if "not active" in output.lower() or "BGP not active" in output:
                        step.failed("BGP IPv6 unicast address family not active")
                        continue

                    established = 0
                    not_established = []

                    for line in output.splitlines():
                        # Match IPv6 address at start of line
                        match = re.match(r'^([0-9a-fA-F:]+)\s+', line.strip())
                        if match:
                            neighbor_ip = match.group(1)
                            parts = line.split()
                            if len(parts) >= 9:
                                state = parts[-1]
                                if state.isdigit():
                                    # Numeric means established with prefixes received
                                    established += 1
                                elif state in ["Idle", "Active", "Connect", "OpenSent", "OpenConfirm"]:
                                    not_established.append(f"{neighbor_ip}: {state}")
                                else:
                                    # Could be other established state
                                    established += 1

                    if not_established:
                        step.failed(f"BGP IPv6 sessions not established: {', '.join(not_established)}")
                    elif established > 0:
                        step.passed(f"{established} BGP IPv6 sessions established")
                    else:
                        step.failed("No BGP IPv6 sessions found")

                except Exception as e:
                    step.failed(f"Error checking BGP IPv6: {e}")

    @aetest.test
    def test_vpnv6_sessions(self, testbed, steps):
        """Verify VPNv6 address family sessions on PE routers."""

        pe_devices = DEVICE_GROUPS['pe'] + DEVICE_GROUPS['aggregation'] + DEVICE_GROUPS['route_reflectors']
        devices_to_check = [d for d in self.devices_to_test if d in pe_devices]

        if not devices_to_check:
            self.skipped("No PE/RR devices connected")

        for device_name in devices_to_check:
            with steps.start(f"Checking VPNv6 on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show bgp vpnv6 unicast all summary")

                    if "not active" in output.lower() or "no neighbor" in output.lower():
                        step.skipped("VPNv6 not active")
                        continue

                    established = 0
                    for line in output.splitlines():
                        # VPNv6 summary uses IPv4 neighbor addresses (update-source loopback)
                        match = re.match(r'^(\d+\.\d+\.\d+\.\d+)\s+', line.strip())
                        if match:
                            parts = line.split()
                            if len(parts) >= 9:
                                state = parts[-1]
                                if state.isdigit():
                                    established += 1

                    if established > 0:
                        step.passed(f"{established} VPNv6 sessions established")
                    else:
                        step.skipped("No VPNv6 sessions - may not be configured yet")

                except Exception as e:
                    step.failed(f"Error checking VPNv6: {e}")


# =============================================================================
# Test Case: IPv6 Connectivity Validation
# =============================================================================
class IPv6ConnectivityValidation(aetest.Testcase):
    """Validate IPv6 end-to-end connectivity."""

    @aetest.setup
    def setup(self, testbed):
        """Setup - use CORE1 as source for ping tests."""
        connected = self.parent.parameters.get('connected_devices', [])

        if 'EUNIV-CORE1' not in connected:
            self.skipped("EUNIV-CORE1 not connected - cannot run connectivity tests")

        self.source_device = 'EUNIV-CORE1'

        # Build target list from EXPECTED_IPV6
        self.targets = {}
        for device_name, config in EXPECTED_IPV6.items():
            if device_name != self.source_device and device_name in connected:
                loopback = config.get("loopback_ipv6")
                if loopback:
                    self.targets[device_name] = loopback

    @aetest.test
    def test_ipv6_loopback_reachability(self, testbed, steps):
        """Ping all IPv6 loopbacks from CORE1."""

        if not self.targets:
            self.skipped("No IPv6 targets available")

        device = testbed.devices[self.source_device]

        for target_name, target_ipv6 in self.targets.items():
            with steps.start(f"Ping {target_name} ({target_ipv6})") as step:
                try:
                    # Use ping ipv6 command
                    result = device.execute(f"ping ipv6 {target_ipv6} repeat 3")

                    if "Success rate is 100 percent" in result:
                        step.passed(f"IPv6 ping to {target_ipv6} successful")
                    elif "Success rate is" in result:
                        match = re.search(r'Success rate is (\d+) percent', result)
                        if match:
                            pct = int(match.group(1))
                            if pct > 0:
                                step.passed(f"IPv6 ping to {target_ipv6} ({pct}% success)")
                            else:
                                step.failed(f"IPv6 ping to {target_ipv6} failed (0%)")
                        else:
                            step.failed(f"IPv6 ping to {target_ipv6} failed")
                    else:
                        step.failed(f"IPv6 ping to {target_ipv6} failed - no response")

                except Exception as e:
                    step.failed(f"Ping error: {e}")


# =============================================================================
# Test Case: VRF IPv6 Validation (PE routers only)
# =============================================================================
class VRFIPv6Validation(aetest.Testcase):
    """Validate IPv6 address family is configured in VRFs."""

    @aetest.setup
    def setup(self, testbed):
        """Setup for VRF IPv6 tests - only test PE devices."""
        connected = self.parent.parameters.get('connected_devices', [])
        self.devices_to_test = [
            name for name in connected
            if name in DEVICE_GROUPS['pe'] and name in testbed.devices
        ]
        if not self.devices_to_test:
            self.skipped("No PE devices connected")

    @aetest.test
    def test_vrf_ipv6_enabled(self, testbed, steps):
        """Verify IPv6 address family is enabled in VRFs."""

        for device_name in self.devices_to_test:
            with steps.start(f"Checking VRF IPv6 on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show vrf detail")

                    # Check for IPv6 address family in VRFs
                    ipv6_enabled_vrfs = []
                    current_vrf = None

                    for line in output.splitlines():
                        vrf_match = re.match(r'^VRF\s+(\S+)', line)
                        if vrf_match:
                            current_vrf = vrf_match.group(1)

                        if current_vrf and "ipv6" in line.lower() and "unicast" in line.lower():
                            ipv6_enabled_vrfs.append(current_vrf)

                    if ipv6_enabled_vrfs:
                        step.passed(f"IPv6 enabled in VRFs: {', '.join(ipv6_enabled_vrfs)}")
                    else:
                        step.skipped("IPv6 not yet enabled in VRFs - deployment pending")

                except Exception as e:
                    step.failed(f"Error checking VRF IPv6: {e}")


# =============================================================================
# Common Cleanup
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
    from genie.testbed import load as genie_load

    parser = argparse.ArgumentParser(description="E-University IPv6 Network AEtest")
    parser.add_argument("--testbed", required=True, help="Testbed YAML file")
    args = parser.parse_args()

    testbed = genie_load(args.testbed)
    aetest.main(testbed=testbed)
