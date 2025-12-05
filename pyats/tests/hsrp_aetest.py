#!/usr/bin/env python3
"""
E-University HSRP Validation - AEtest Script

Validates HSRP configuration on edge/PE routers including:
- HSRP version 2 configuration
- Active/Standby states per group
- Load balancing verification (PE1 vs PE2 ownership)
- Virtual IP configuration
- Preemption settings
- Failover testing (optional)

HSRP Design:
- Interface: Gi3 subinterfaces (Gi3.100, Gi3.200, etc.)
- IP Scheme: 10.{vlan}.{campus}.0/24
  - Campus: Main=1, Med=2, Res=3
  - PE1 IP: .1, PE2 IP: .2, Virtual IP: .254
- Load Balancing:
  - PE1 Active: VLAN 100 (STUDENT), 300 (RESEARCH)
  - PE2 Active: VLAN 200 (STAFF), 400 (MEDICAL), 500 (GUEST)

Usage:
    pyats run job ../hsrp_job.py --testbed-file ../testbed.yaml
"""

import logging
import re
from typing import Dict, List, Tuple

from pyats import aetest
from pyats.topology import Testbed

logger = logging.getLogger(__name__)


# =============================================================================
# HSRP Expected State Configuration
# =============================================================================

# Campus identifier mapping (used in IP addressing: 10.VLAN.CAMPUS.x)
CAMPUS_ID = {
    'MAIN': 1,
    'MED': 2,
    'RES': 3,
}

# VLANs per campus with VRF mapping
CAMPUS_VLANS = {
    'MAIN': {
        100: 'STUDENT-NET',
        200: 'STAFF-NET',
        300: 'RESEARCH-NET',
        500: 'GUEST-NET',
    },
    'MED': {
        200: 'STAFF-NET',
        300: 'RESEARCH-NET',
        400: 'MEDICAL-NET',
        500: 'GUEST-NET',
    },
    'RES': {
        200: 'STAFF-NET',
        300: 'RESEARCH-NET',
        500: 'GUEST-NET',
    },
}

# Load balancing: PE1 is Active for these VLANs (priority 150)
PE1_ACTIVE_VLANS = [100, 300]  # STUDENT-NET, RESEARCH-NET
# PE2 is Active for: 200, 400, 500 (STAFF-NET, MEDICAL-NET, GUEST-NET)

# Edge device pairs per campus
EDGE_PAIRS = {
    'MAIN': ('EUNIV-MAIN-EDGE1', 'EUNIV-MAIN-EDGE2'),
    'MED': ('EUNIV-MED-EDGE1', 'EUNIV-MED-EDGE2'),
    'RES': ('EUNIV-RES-EDGE1', 'EUNIV-RES-EDGE2'),
}

# All edge devices
EDGE_DEVICES = [
    'EUNIV-MAIN-EDGE1', 'EUNIV-MAIN-EDGE2',
    'EUNIV-MED-EDGE1', 'EUNIV-MED-EDGE2',
    'EUNIV-RES-EDGE1', 'EUNIV-RES-EDGE2',
]


def get_campus_from_device(device_name: str) -> str:
    """Extract campus identifier from device name."""
    if 'MAIN' in device_name:
        return 'MAIN'
    elif 'MED' in device_name:
        return 'MED'
    elif 'RES' in device_name:
        return 'RES'
    return None


def is_pe1(device_name: str) -> bool:
    """Check if device is PE1 (EDGE1) in the campus pair."""
    return device_name.endswith('EDGE1') or device_name.endswith('PE1')


def get_expected_hsrp_state(device_name: str, vlan: int) -> str:
    """
    Determine expected HSRP state for a device/VLAN combo.

    Load Balancing Strategy:
    - PE1/EDGE1 is Active for VLANs 100, 300 (priority 150)
    - PE2/EDGE2 is Active for VLANs 200, 400, 500 (priority 150)
    """
    device_is_pe1 = is_pe1(device_name)
    vlan_should_be_on_pe1 = vlan in PE1_ACTIVE_VLANS

    if device_is_pe1 == vlan_should_be_on_pe1:
        return 'Active'
    else:
        return 'Standby'


def vlan_to_subnet(vlan: int) -> int:
    """Convert VLAN to valid subnet octet (divide by 10 for VLANs > 255)."""
    # VLAN 100 -> 10, VLAN 200 -> 20, VLAN 300 -> 30, etc.
    return vlan // 10


def get_hsrp_ips(campus: str, vlan: int) -> Tuple[str, str, str]:
    """
    Calculate HSRP IPs for a campus/VLAN.

    Returns: (pe1_ip, pe2_ip, virtual_ip)
    IP Scheme: 10.{subnet}.{campus_id}.{host}
    Where subnet = VLAN/10 (100->10, 200->20, 300->30, etc.)
    """
    campus_id = CAMPUS_ID[campus]
    subnet = vlan_to_subnet(vlan)
    network = f"10.{subnet}.{campus_id}"
    return (
        f"{network}.1",    # PE1/EDGE1 IP
        f"{network}.2",    # PE2/EDGE2 IP
        f"{network}.254",  # Virtual IP
    )


# =============================================================================
# Common Setup
# =============================================================================
class CommonSetup(aetest.CommonSetup):
    """Connect to edge devices for HSRP validation."""

    @aetest.subsection
    def check_testbed(self, testbed: Testbed):
        """Verify testbed has edge devices."""
        if not testbed:
            self.failed("Testbed not provided")

        edge_in_testbed = [d for d in EDGE_DEVICES if d in testbed.devices]
        if not edge_in_testbed:
            self.failed("No edge devices found in testbed")

        logger.info(f"Found {len(edge_in_testbed)} edge devices in testbed")

    @aetest.subsection
    def connect_to_devices(self, testbed: Testbed, steps):
        """Connect to all edge devices."""
        connected = []
        failed = []

        for device_name in EDGE_DEVICES:
            if device_name not in testbed.devices:
                continue

            device = testbed.devices[device_name]
            with steps.start(f"Connecting to {device_name}") as step:
                try:
                    if not device.is_connected():
                        device.connect(log_stdout=False, learn_hostname=True)
                    connected.append(device_name)
                    logger.info(f"Connected to {device_name}")
                except Exception as e:
                    step.failed(f"Failed to connect: {e}")
                    failed.append(device_name)

        self.parent.parameters['connected_devices'] = connected
        self.parent.parameters['failed_devices'] = failed

        if not connected:
            self.failed("Could not connect to any edge devices")

        logger.info(f"Connected: {len(connected)}, Failed: {len(failed)}")


# =============================================================================
# Test Case: HSRP Configuration Validation
# =============================================================================
class HSRPConfigValidation(aetest.Testcase):
    """Validate HSRP is configured correctly on edge devices."""

    @aetest.setup
    def setup(self, testbed):
        """Setup test - get connected edge devices."""
        self.devices_to_test = [
            name for name in self.parent.parameters.get('connected_devices', [])
            if name in EDGE_DEVICES and name in testbed.devices
        ]
        if not self.devices_to_test:
            self.skipped("No edge devices connected")

    @aetest.test
    def test_hsrp_version(self, testbed, steps):
        """Verify HSRP version 2 is configured on all subinterfaces."""

        for device_name in self.devices_to_test:
            with steps.start(f"Checking HSRP version on {device_name}") as step:
                device = testbed.devices[device_name]
                campus = get_campus_from_device(device_name)

                if not campus:
                    step.skipped("Could not determine campus")
                    continue

                try:
                    output = device.execute("show standby brief")

                    if "HSRP not" in output or not output.strip():
                        step.failed("HSRP not configured")
                        continue

                    # Check for version 2 - "V2" should appear in output
                    # or check running config
                    config_output = device.execute("show run | section interface Gi.*3\\.")

                    if "standby version 2" not in config_output.lower():
                        # Check if any subinterface has version 2
                        v2_count = config_output.lower().count("standby version 2")
                        expected_vlans = len(CAMPUS_VLANS.get(campus, {}))

                        if v2_count < expected_vlans:
                            step.failed(f"HSRP version 2 not configured on all interfaces (found {v2_count}, expected {expected_vlans})")
                        else:
                            step.passed(f"HSRP version 2 configured on {v2_count} interfaces")
                    else:
                        step.passed("HSRP version 2 configured")

                except Exception as e:
                    step.failed(f"Error checking HSRP version: {e}")

    @aetest.test
    def test_hsrp_timers(self, testbed, steps):
        """Verify HSRP timers are set to 1/3 seconds."""

        for device_name in self.devices_to_test:
            with steps.start(f"Checking HSRP timers on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show standby | include timers")

                    # Expected: "timers 1 sec, hold 3 sec" or similar
                    # Check for hello=1, hold=3
                    hello_match = re.search(r'hello\s+(\d+)\s*(?:sec|msec)', output, re.IGNORECASE)
                    hold_match = re.search(r'hold\s+(\d+)\s*(?:sec|msec)', output, re.IGNORECASE)

                    if not hello_match or not hold_match:
                        # Try alternative format: "timers 1 3"
                        timer_match = re.findall(r'timers\s+(\d+)\s+(?:sec\s+)?(\d+)', output.lower())
                        if timer_match:
                            for hello, hold in timer_match:
                                if int(hello) != 1 or int(hold) != 3:
                                    step.failed(f"Incorrect timers: hello={hello}, hold={hold} (expected 1/3)")
                                    break
                            else:
                                step.passed("HSRP timers correctly set to 1/3 seconds")
                        else:
                            step.skipped("Could not parse timer values")
                    else:
                        hello = int(hello_match.group(1))
                        hold = int(hold_match.group(1))

                        if hello == 1 and hold == 3:
                            step.passed("HSRP timers correctly set to 1/3 seconds")
                        else:
                            step.failed(f"Incorrect timers: hello={hello}, hold={hold} (expected 1/3)")

                except Exception as e:
                    step.failed(f"Error checking timers: {e}")

    @aetest.test
    def test_hsrp_preempt(self, testbed, steps):
        """Verify preemption is enabled with delay."""

        for device_name in self.devices_to_test:
            with steps.start(f"Checking preemption on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show standby | include Preemption")

                    if "enabled" not in output.lower():
                        step.failed("Preemption not enabled")
                        continue

                    # Check for preempt delay
                    delay_match = re.search(r'delay\s+(\d+)\s*sec', output, re.IGNORECASE)
                    if delay_match:
                        delay = int(delay_match.group(1))
                        if delay >= 30:
                            step.passed(f"Preemption enabled with {delay}s delay")
                        else:
                            step.failed(f"Preempt delay too short: {delay}s (expected >= 30s)")
                    else:
                        step.passed("Preemption enabled")

                except Exception as e:
                    step.failed(f"Error checking preemption: {e}")


# =============================================================================
# Test Case: HSRP State Validation
# =============================================================================
class HSRPStateValidation(aetest.Testcase):
    """Validate HSRP Active/Standby states match expected load balancing."""

    @aetest.setup
    def setup(self, testbed):
        """Setup test."""
        self.devices_to_test = [
            name for name in self.parent.parameters.get('connected_devices', [])
            if name in EDGE_DEVICES and name in testbed.devices
        ]
        if not self.devices_to_test:
            self.skipped("No edge devices connected")

    @aetest.test
    def test_hsrp_states(self, testbed, steps):
        """Verify HSRP Active/Standby states match expected load balancing."""

        for device_name in self.devices_to_test:
            with steps.start(f"Checking HSRP states on {device_name}") as step:
                device = testbed.devices[device_name]
                campus = get_campus_from_device(device_name)

                if not campus:
                    step.skipped("Could not determine campus")
                    continue

                expected_vlans = CAMPUS_VLANS.get(campus, {})
                if not expected_vlans:
                    step.skipped(f"No VLANs defined for campus {campus}")
                    continue

                try:
                    output = device.execute("show standby brief")

                    incorrect_states = []
                    correct_states = []
                    missing_groups = []

                    for vlan, vrf in expected_vlans.items():
                        expected_state = get_expected_hsrp_state(device_name, vlan)
                        interface = f"Gi3.{vlan}"

                        # Parse HSRP state for this interface
                        # Format: Interface   Grp  Pri P State    Active          Standby         Virtual IP
                        # Gi3.100     100  150 P Active  local           10.100.1.2      10.100.1.254
                        pattern = rf'{interface}\s+{vlan}\s+\d+\s+\S*\s+(Active|Standby|Init|Listen)'
                        match = re.search(pattern, output, re.IGNORECASE)

                        if not match:
                            # Try alternative parsing
                            alt_pattern = rf'Gi.*3\.{vlan}.*\s+(Active|Standby|Init|Listen)'
                            match = re.search(alt_pattern, output, re.IGNORECASE)

                        if match:
                            actual_state = match.group(1)
                            if actual_state.lower() == expected_state.lower():
                                correct_states.append(f"{interface}: {actual_state}")
                            else:
                                incorrect_states.append(
                                    f"{interface}: {actual_state} (expected {expected_state})"
                                )
                        else:
                            missing_groups.append(f"{interface} (VLAN {vlan})")

                    # Report results
                    if missing_groups:
                        step.failed(f"Missing HSRP groups: {', '.join(missing_groups)}")
                    elif incorrect_states:
                        step.failed(f"Incorrect states: {', '.join(incorrect_states)}")
                    else:
                        step.passed(f"{len(correct_states)} HSRP groups in expected state")

                except Exception as e:
                    step.failed(f"Error checking states: {e}")

    @aetest.test
    def test_virtual_ip_configuration(self, testbed, steps):
        """Verify virtual IPs are correctly configured."""

        for device_name in self.devices_to_test:
            with steps.start(f"Checking virtual IPs on {device_name}") as step:
                device = testbed.devices[device_name]
                campus = get_campus_from_device(device_name)

                if not campus:
                    step.skipped("Could not determine campus")
                    continue

                expected_vlans = CAMPUS_VLANS.get(campus, {})

                try:
                    output = device.execute("show standby brief")

                    incorrect_vips = []
                    correct_vips = []

                    for vlan in expected_vlans.keys():
                        _, _, expected_vip = get_hsrp_ips(campus, vlan)
                        interface = f"Gi3.{vlan}"

                        # Find virtual IP in output
                        # Last column in "show standby brief" is Virtual IP
                        pattern = rf'{interface}\s+{vlan}\s+.*?(\d+\.\d+\.\d+\.\d+)\s*$'
                        match = re.search(pattern, output, re.MULTILINE)

                        if match:
                            actual_vip = match.group(1)
                            if actual_vip == expected_vip:
                                correct_vips.append(f"{interface}: {actual_vip}")
                            else:
                                incorrect_vips.append(
                                    f"{interface}: {actual_vip} (expected {expected_vip})"
                                )
                        else:
                            incorrect_vips.append(f"{interface}: VIP not found")

                    if incorrect_vips:
                        step.failed(f"Incorrect VIPs: {', '.join(incorrect_vips)}")
                    else:
                        step.passed(f"{len(correct_vips)} virtual IPs correct")

                except Exception as e:
                    step.failed(f"Error checking VIPs: {e}")


# =============================================================================
# Test Case: HSRP Redundancy Validation
# =============================================================================
class HSRPRedundancyValidation(aetest.Testcase):
    """Validate HSRP redundancy by checking both peers have complementary states."""

    @aetest.setup
    def setup(self, testbed):
        """Setup test - verify both peers are connected per campus."""
        connected = self.parent.parameters.get('connected_devices', [])

        self.campus_pairs = {}
        for campus, (pe1, pe2) in EDGE_PAIRS.items():
            if pe1 in connected and pe2 in connected:
                self.campus_pairs[campus] = (pe1, pe2)

        if not self.campus_pairs:
            self.skipped("No complete edge pairs connected")

    @aetest.test
    def test_complementary_states(self, testbed, steps):
        """Verify each HSRP group has exactly one Active and one Standby."""

        for campus, (pe1_name, pe2_name) in self.campus_pairs.items():
            with steps.start(f"Checking redundancy for {campus} campus") as step:
                pe1 = testbed.devices[pe1_name]
                pe2 = testbed.devices[pe2_name]

                vlans = CAMPUS_VLANS.get(campus, {})

                try:
                    pe1_output = pe1.execute("show standby brief")
                    pe2_output = pe2.execute("show standby brief")

                    issues = []
                    valid_groups = []

                    for vlan in vlans.keys():
                        interface = f"Gi3.{vlan}"

                        # Get PE1 state
                        pe1_pattern = rf'{interface}\s+{vlan}\s+\d+\s+\S*\s+(Active|Standby)'
                        pe1_match = re.search(pe1_pattern, pe1_output, re.IGNORECASE)

                        # Get PE2 state
                        pe2_pattern = rf'{interface}\s+{vlan}\s+\d+\s+\S*\s+(Active|Standby)'
                        pe2_match = re.search(pe2_pattern, pe2_output, re.IGNORECASE)

                        if not pe1_match or not pe2_match:
                            issues.append(f"VLAN {vlan}: HSRP not configured on both peers")
                            continue

                        pe1_state = pe1_match.group(1).lower()
                        pe2_state = pe2_match.group(1).lower()

                        # Check complementary states
                        states = {pe1_state, pe2_state}
                        if states != {'active', 'standby'}:
                            issues.append(
                                f"VLAN {vlan}: {pe1_name}={pe1_state}, {pe2_name}={pe2_state} "
                                "(expected one Active, one Standby)"
                            )
                        else:
                            valid_groups.append(f"VLAN {vlan}")

                    if issues:
                        step.failed(f"Redundancy issues: {'; '.join(issues)}")
                    else:
                        step.passed(f"{len(valid_groups)} groups properly redundant")

                except Exception as e:
                    step.failed(f"Error checking redundancy: {e}")

    @aetest.test
    def test_load_balancing(self, testbed, steps):
        """Verify load is balanced according to design (PE1 owns 100/300, PE2 owns 200/400/500)."""

        for campus, (pe1_name, pe2_name) in self.campus_pairs.items():
            with steps.start(f"Checking load balance for {campus} campus") as step:
                pe1 = testbed.devices[pe1_name]

                vlans = CAMPUS_VLANS.get(campus, {})

                try:
                    pe1_output = pe1.execute("show standby brief")

                    pe1_active_count = 0
                    pe2_active_count = 0
                    incorrect_ownership = []

                    for vlan in vlans.keys():
                        interface = f"Gi3.{vlan}"
                        expected_owner = "PE1" if vlan in PE1_ACTIVE_VLANS else "PE2"

                        # Check PE1 state
                        pattern = rf'{interface}\s+{vlan}\s+\d+\s+\S*\s+(Active|Standby)'
                        match = re.search(pattern, pe1_output, re.IGNORECASE)

                        if match:
                            pe1_state = match.group(1).lower()
                            actual_owner = "PE1" if pe1_state == 'active' else "PE2"

                            if actual_owner == "PE1":
                                pe1_active_count += 1
                            else:
                                pe2_active_count += 1

                            if actual_owner != expected_owner:
                                incorrect_ownership.append(
                                    f"VLAN {vlan}: {actual_owner} active (expected {expected_owner})"
                                )

                    if incorrect_ownership:
                        step.failed(f"Load balance mismatch: {', '.join(incorrect_ownership)}")
                    else:
                        step.passed(f"Load balanced: PE1 active={pe1_active_count}, PE2 active={pe2_active_count}")

                except Exception as e:
                    step.failed(f"Error checking load balance: {e}")


# =============================================================================
# Test Case: HSRP Interface Validation (Pre-deployment check)
# =============================================================================
class HSRPInterfaceValidation(aetest.Testcase):
    """Validate Gi3 interface is available for HSRP configuration."""

    @aetest.setup
    def setup(self, testbed):
        """Setup test."""
        self.devices_to_test = [
            name for name in self.parent.parameters.get('connected_devices', [])
            if name in EDGE_DEVICES and name in testbed.devices
        ]
        if not self.devices_to_test:
            self.skipped("No edge devices connected")

    @aetest.test
    def test_gi3_exists(self, testbed, steps):
        """Verify GigabitEthernet3 exists on edge devices."""

        for device_name in self.devices_to_test:
            with steps.start(f"Checking Gi3 on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show ip interface brief | include Gi.*3")

                    if "GigabitEthernet3" in output or "Gi3" in output:
                        step.passed("GigabitEthernet3 found")
                    else:
                        step.failed("GigabitEthernet3 not found")

                except Exception as e:
                    step.failed(f"Error checking interface: {e}")

    @aetest.test
    def test_gi3_connectivity(self, testbed, steps):
        """Verify Gi3 P2P link between PE1 and PE2 is operational."""

        for campus, (pe1_name, pe2_name) in EDGE_PAIRS.items():
            if pe1_name not in self.devices_to_test:
                continue

            with steps.start(f"Checking Gi3 link on {campus} campus") as step:
                pe1 = testbed.devices[pe1_name]

                try:
                    output = pe1.execute("show interfaces GigabitEthernet3 | include protocol")

                    if "up" in output.lower() and "line protocol is up" in output.lower():
                        step.passed("Gi3 link is up/up")
                    elif "administratively down" in output.lower():
                        step.failed("Gi3 is administratively down")
                    else:
                        step.failed("Gi3 link is not operational")

                except Exception as e:
                    step.failed(f"Error checking Gi3 status: {e}")


# =============================================================================
# Common Cleanup
# =============================================================================
class CommonCleanup(aetest.CommonCleanup):
    """Disconnect from all devices."""

    @aetest.subsection
    def disconnect_from_devices(self, testbed):
        """Disconnect from all devices."""
        for device_name in EDGE_DEVICES:
            if device_name not in testbed.devices:
                continue
            device = testbed.devices[device_name]
            try:
                if device.is_connected():
                    device.disconnect()
                    logger.info(f"Disconnected from {device_name}")
            except Exception as e:
                logger.warning(f"Error disconnecting from {device_name}: {e}")


# =============================================================================
# Main
# =============================================================================
if __name__ == "__main__":
    import argparse
    from genie.testbed import load as genie_load

    parser = argparse.ArgumentParser(description="E-University HSRP AEtest")
    parser.add_argument("--testbed", required=True, help="Testbed YAML file")
    args = parser.parse_args()

    testbed = genie_load(args.testbed)
    aetest.main(testbed=testbed)
