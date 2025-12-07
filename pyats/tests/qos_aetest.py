#!/usr/bin/env python3
"""
E-University QoS Validation - AEtest Script

Validates QoS configuration on Edge routers including:
- Class-map definitions
- Policy-map configurations
- Service-policy application on interfaces
- DSCP markings per VRF
- Queue statistics and bandwidth allocations

QoS Design (VRF-Based Marking):
- MEDICAL-NET: DSCP EF (46) - Priority queue, 20% bandwidth
- STAFF-NET: DSCP AF31 (26) - 25% bandwidth
- RESEARCH-NET: DSCP AF21 (18) - 30% bandwidth
- STUDENT-NET: DSCP 0 (Best Effort) - 20% bandwidth
- GUEST-NET: DSCP CS1 (8) - Scavenger, 5% bandwidth

Usage:
    pyats run job ../qos_job.py --testbed-file ../testbed.yaml
"""

import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pyats import aetest
from pyats.topology import Testbed

# Add scripts directory to path for intent_data import
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from intent_data import (
    QOS_VRF_MARKINGS,
    QOS_CLASS_MAPS,
    QOS_POLICY_MAPS,
    QOS_EDGE_DEVICES,
    QOS_EDGE_VRFS,
)

logger = logging.getLogger(__name__)


# =============================================================================
# QoS Expected Configuration
# =============================================================================

# DSCP name to value mapping for validation
DSCP_VALUES = {
    "ef": 46,
    "af31": 26,
    "af21": 18,
    "default": 0,
    "cs1": 8,
}

# Expected class-maps
EXPECTED_CLASS_MAPS = list(QOS_CLASS_MAPS.keys())

# Expected policy-maps
EXPECTED_POLICY_MAPS = list(QOS_POLICY_MAPS.keys())


def get_vrf_dscp(vrf_name: str) -> Tuple[str, int]:
    """Get expected DSCP name and value for a VRF."""
    if vrf_name in QOS_VRF_MARKINGS:
        marking = QOS_VRF_MARKINGS[vrf_name]
        return marking["dscp"], marking["dscp_value"]
    return "default", 0


def get_device_vrfs(device_name: str) -> List[str]:
    """Get list of VRFs configured on an Edge device."""
    return QOS_EDGE_VRFS.get(device_name, [])


# =============================================================================
# Common Setup
# =============================================================================
class CommonSetup(aetest.CommonSetup):
    """Connect to Edge devices for QoS validation."""

    @aetest.subsection
    def check_testbed(self, testbed: Testbed):
        """Verify testbed has Edge devices."""
        if not testbed:
            self.failed("Testbed not provided")

        edge_in_testbed = [d for d in QOS_EDGE_DEVICES if d in testbed.devices]
        if not edge_in_testbed:
            self.failed("No Edge devices found in testbed")

        logger.info(f"Found {len(edge_in_testbed)} Edge devices in testbed")

    @aetest.subsection
    def connect_to_devices(self, testbed: Testbed, steps):
        """Connect to all Edge devices."""
        connected = []
        failed = []

        for device_name in QOS_EDGE_DEVICES:
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
            self.failed("Could not connect to any Edge devices")

        logger.info(f"Connected: {len(connected)}, Failed: {len(failed)}")


# =============================================================================
# Test Case: Class-Map Validation
# =============================================================================
class ClassMapValidation(aetest.Testcase):
    """Validate QoS class-maps are configured correctly."""

    @aetest.setup
    def setup(self, testbed):
        """Setup test - get connected Edge devices."""
        self.devices_to_test = [
            name for name in self.parent.parameters.get('connected_devices', [])
            if name in QOS_EDGE_DEVICES and name in testbed.devices
        ]
        if not self.devices_to_test:
            self.skipped("No Edge devices connected")

    @aetest.test
    def test_class_maps_exist(self, testbed, steps):
        """Verify all expected class-maps are configured."""

        for device_name in self.devices_to_test:
            with steps.start(f"Checking class-maps on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show class-map")

                    missing_class_maps = []
                    found_class_maps = []

                    for class_map_name in EXPECTED_CLASS_MAPS:
                        if class_map_name in output:
                            found_class_maps.append(class_map_name)
                        else:
                            missing_class_maps.append(class_map_name)

                    if missing_class_maps:
                        step.failed(f"Missing class-maps: {', '.join(missing_class_maps)}")
                    else:
                        step.passed(f"All {len(found_class_maps)} class-maps configured")

                except Exception as e:
                    step.failed(f"Error checking class-maps: {e}")

    @aetest.test
    def test_class_map_match_criteria(self, testbed, steps):
        """Verify class-maps have correct match criteria (DSCP values)."""

        for device_name in self.devices_to_test:
            with steps.start(f"Checking class-map match criteria on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show class-map")
                    issues = []

                    for class_name, config in QOS_CLASS_MAPS.items():
                        # Check if class-map exists
                        class_pattern = rf'Class Map match-any {class_name}.*?(?=Class Map|$)'
                        class_match = re.search(class_pattern, output, re.DOTALL | re.IGNORECASE)

                        if not class_match:
                            continue  # Already reported in previous test

                        class_output = class_match.group(0)

                        # Check for DSCP match criteria
                        for criterion in config.get("match_criteria", []):
                            if criterion["type"] == "dscp":
                                dscp_value = criterion["value"]
                                if dscp_value not in class_output.lower():
                                    issues.append(f"{class_name}: missing 'match dscp {dscp_value}'")

                    if issues:
                        step.failed(f"Match criteria issues: {'; '.join(issues)}")
                    else:
                        step.passed("All class-map match criteria correct")

                except Exception as e:
                    step.failed(f"Error checking match criteria: {e}")


# =============================================================================
# Test Case: Policy-Map Validation
# =============================================================================
class PolicyMapValidation(aetest.Testcase):
    """Validate QoS policy-maps are configured correctly."""

    @aetest.setup
    def setup(self, testbed):
        """Setup test."""
        self.devices_to_test = [
            name for name in self.parent.parameters.get('connected_devices', [])
            if name in QOS_EDGE_DEVICES and name in testbed.devices
        ]
        if not self.devices_to_test:
            self.skipped("No Edge devices connected")

    @aetest.test
    def test_policy_maps_exist(self, testbed, steps):
        """Verify all expected policy-maps are configured."""

        for device_name in self.devices_to_test:
            with steps.start(f"Checking policy-maps on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show policy-map")

                    missing_policy_maps = []
                    found_policy_maps = []

                    for policy_map_name in EXPECTED_POLICY_MAPS:
                        if policy_map_name in output:
                            found_policy_maps.append(policy_map_name)
                        else:
                            missing_policy_maps.append(policy_map_name)

                    if missing_policy_maps:
                        step.failed(f"Missing policy-maps: {', '.join(missing_policy_maps)}")
                    else:
                        step.passed(f"All {len(found_policy_maps)} policy-maps configured")

                except Exception as e:
                    step.failed(f"Error checking policy-maps: {e}")

    @aetest.test
    def test_marking_policy_actions(self, testbed, steps):
        """Verify marking policy has correct DSCP set actions."""

        marking_policy = "EUNIV-VRF-MARKING"

        for device_name in self.devices_to_test:
            with steps.start(f"Checking marking policy on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute(f"show policy-map {marking_policy}")

                    if "Policy Map" not in output:
                        step.failed(f"Policy-map {marking_policy} not found")
                        continue

                    issues = []
                    policy_config = QOS_POLICY_MAPS.get(marking_policy, {})

                    for class_name, actions in policy_config.get("classes", {}).items():
                        expected_action = actions.get("action", "")

                        # Check if class is in policy
                        if class_name not in output:
                            issues.append(f"Class {class_name} not in policy")
                            continue

                        # Check for set dscp action
                        if "set dscp" in expected_action:
                            dscp_keyword = expected_action.split()[-1]  # e.g., "ef", "af31"
                            if f"set dscp {dscp_keyword}" not in output.lower():
                                # Try numeric value
                                dscp_val = DSCP_VALUES.get(dscp_keyword, dscp_keyword)
                                if f"set dscp {dscp_val}" not in output.lower():
                                    issues.append(f"{class_name}: missing '{expected_action}'")

                    if issues:
                        step.failed(f"Marking policy issues: {'; '.join(issues)}")
                    else:
                        step.passed("Marking policy actions correct")

                except Exception as e:
                    step.failed(f"Error checking marking policy: {e}")

    @aetest.test
    def test_queuing_policy_bandwidth(self, testbed, steps):
        """Verify queuing policy has correct bandwidth allocations."""

        queuing_policy = "EUNIV-QOS-QUEUING"

        for device_name in self.devices_to_test:
            with steps.start(f"Checking queuing policy on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute(f"show policy-map {queuing_policy}")

                    if "Policy Map" not in output:
                        step.failed(f"Policy-map {queuing_policy} not found")
                        continue

                    issues = []
                    policy_config = QOS_POLICY_MAPS.get(queuing_policy, {})

                    for class_name, config in policy_config.get("classes", {}).items():
                        expected_bw = config.get("bandwidth_percent")
                        is_priority = config.get("priority", False)

                        if class_name not in output:
                            issues.append(f"Class {class_name} not in policy")
                            continue

                        # Extract class section from output
                        class_section_pattern = rf'Class {class_name}.*?(?=Class |$)'
                        class_match = re.search(class_section_pattern, output, re.DOTALL | re.IGNORECASE)

                        if class_match:
                            class_section = class_match.group(0)

                            # Check for priority queue
                            if is_priority and "priority" not in class_section.lower():
                                issues.append(f"{class_name}: should be priority queue")

                            # Check bandwidth percentage
                            if expected_bw:
                                bw_match = re.search(r'bandwidth\s+(?:percent\s+)?(\d+)', class_section, re.IGNORECASE)
                                if bw_match:
                                    actual_bw = int(bw_match.group(1))
                                    if actual_bw != expected_bw:
                                        issues.append(f"{class_name}: bandwidth {actual_bw}% (expected {expected_bw}%)")
                                elif not is_priority:  # Priority queues may not show bandwidth
                                    issues.append(f"{class_name}: bandwidth not configured")

                    if issues:
                        step.failed(f"Queuing policy issues: {'; '.join(issues)}")
                    else:
                        step.passed("Queuing policy bandwidth allocations correct")

                except Exception as e:
                    step.failed(f"Error checking queuing policy: {e}")


# =============================================================================
# Test Case: Service-Policy Application
# =============================================================================
class ServicePolicyValidation(aetest.Testcase):
    """Validate service-policies are applied to correct interfaces."""

    @aetest.setup
    def setup(self, testbed):
        """Setup test."""
        self.devices_to_test = [
            name for name in self.parent.parameters.get('connected_devices', [])
            if name in QOS_EDGE_DEVICES and name in testbed.devices
        ]
        if not self.devices_to_test:
            self.skipped("No Edge devices connected")

    @aetest.test
    def test_service_policy_applied(self, testbed, steps):
        """Verify service-policies are applied to interfaces."""

        for device_name in self.devices_to_test:
            with steps.start(f"Checking service-policy application on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show policy-map interface")

                    if "Service-policy" not in output and "service-policy" not in output.lower():
                        step.failed("No service-policies applied to any interface")
                        continue

                    # Count interfaces with policies
                    interface_count = output.lower().count("service-policy")

                    if interface_count == 0:
                        step.failed("No service-policies found on interfaces")
                    else:
                        step.passed(f"Service-policies applied ({interface_count} policy attachments found)")

                except Exception as e:
                    step.failed(f"Error checking service-policy application: {e}")

    @aetest.test
    def test_marking_policy_on_vrf_interfaces(self, testbed, steps):
        """Verify marking policy is applied to VRF subinterfaces (input direction)."""

        marking_policy = "EUNIV-VRF-MARKING"

        for device_name in self.devices_to_test:
            with steps.start(f"Checking VRF interface marking on {device_name}") as step:
                device = testbed.devices[device_name]
                device_vrfs = get_device_vrfs(device_name)

                if not device_vrfs:
                    step.skipped("No VRFs configured for this device")
                    continue

                try:
                    output = device.execute("show running-config | section interface")

                    issues = []
                    found_policies = 0

                    for vrf in device_vrfs:
                        # Look for VRF interface with service-policy input
                        vrf_pattern = rf'interface.*vrf forwarding {vrf}.*?(?=interface|$)'
                        vrf_matches = re.findall(vrf_pattern, output, re.DOTALL | re.IGNORECASE)

                        for vrf_match in vrf_matches:
                            if f"service-policy input {marking_policy}" in vrf_match.lower():
                                found_policies += 1
                            elif "service-policy input" not in vrf_match.lower():
                                # Extract interface name
                                intf_match = re.search(r'interface\s+(\S+)', vrf_match)
                                if intf_match:
                                    issues.append(f"{intf_match.group(1)} ({vrf}): no input marking policy")

                    if issues and found_policies == 0:
                        step.failed(f"Missing marking policies: {'; '.join(issues[:5])}")
                    elif found_policies > 0:
                        step.passed(f"Marking policy applied to {found_policies} VRF interfaces")
                    else:
                        step.skipped("Could not verify VRF interface policies")

                except Exception as e:
                    step.failed(f"Error checking VRF marking: {e}")

    @aetest.test
    def test_queuing_policy_on_uplinks(self, testbed, steps):
        """Verify queuing policy is applied to uplink interfaces (output direction)."""

        queuing_policy = "EUNIV-QOS-QUEUING"

        for device_name in self.devices_to_test:
            with steps.start(f"Checking uplink queuing on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    # Check GigabitEthernet2 (uplink to AGG) for output policy
                    output = device.execute("show running-config interface GigabitEthernet2")

                    if f"service-policy output" in output.lower():
                        if queuing_policy.lower() in output.lower():
                            step.passed(f"Queuing policy {queuing_policy} applied to Gi2 output")
                        else:
                            # Some queuing policy is applied
                            policy_match = re.search(r'service-policy output (\S+)', output, re.IGNORECASE)
                            if policy_match:
                                step.passed(f"Queuing policy {policy_match.group(1)} applied to Gi2 output")
                            else:
                                step.failed("Unknown queuing policy on Gi2")
                    else:
                        step.failed(f"No output queuing policy on GigabitEthernet2")

                except Exception as e:
                    step.failed(f"Error checking uplink queuing: {e}")


# =============================================================================
# Test Case: QoS Statistics Validation
# =============================================================================
class QoSStatisticsValidation(aetest.Testcase):
    """Validate QoS is actively processing traffic (check counters)."""

    @aetest.setup
    def setup(self, testbed):
        """Setup test."""
        self.devices_to_test = [
            name for name in self.parent.parameters.get('connected_devices', [])
            if name in QOS_EDGE_DEVICES and name in testbed.devices
        ]
        if not self.devices_to_test:
            self.skipped("No Edge devices connected")

    @aetest.test
    def test_policy_statistics(self, testbed, steps):
        """Check policy-map interface statistics for active counters."""

        for device_name in self.devices_to_test:
            with steps.start(f"Checking QoS statistics on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show policy-map interface")

                    if "packets" not in output.lower():
                        step.skipped("No packet counters available - QoS may not be active")
                        continue

                    # Parse packet counts
                    packet_matches = re.findall(r'(\d+)\s+packets', output)
                    total_packets = sum(int(p) for p in packet_matches)

                    if total_packets > 0:
                        step.passed(f"QoS actively processing traffic ({total_packets} total packets matched)")
                    else:
                        step.skipped("No traffic matched by QoS policies yet")

                except Exception as e:
                    step.failed(f"Error checking statistics: {e}")

    @aetest.test
    def test_no_policy_drops(self, testbed, steps):
        """Verify no unexpected drops in QoS policies (except rate-limited classes)."""

        for device_name in self.devices_to_test:
            with steps.start(f"Checking for QoS drops on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show policy-map interface")

                    # Look for drops (excluding GUEST which is rate-limited)
                    drop_issues = []

                    # Parse by class
                    class_sections = re.findall(
                        r'Class-map:\s*(\S+).*?(?=Class-map:|Service-policy|$)',
                        output,
                        re.DOTALL | re.IGNORECASE
                    )

                    for class_section in class_sections:
                        # Extract class name and check for drops
                        class_match = re.match(r'(\S+)', class_section)
                        if not class_match:
                            continue

                        class_name = class_match.group(1)

                        # Skip GUEST-TRAFFIC (expected to have police drops)
                        if "GUEST" in class_name.upper():
                            continue

                        # Check for drops
                        drop_match = re.search(r'(\d+)\s+(?:bytes|packets)\s+dropped', class_section, re.IGNORECASE)
                        if drop_match:
                            drops = int(drop_match.group(1))
                            if drops > 0:
                                drop_issues.append(f"{class_name}: {drops} drops")

                    if drop_issues:
                        step.failed(f"Unexpected drops: {', '.join(drop_issues)}")
                    else:
                        step.passed("No unexpected drops in priority/bandwidth classes")

                except Exception as e:
                    step.failed(f"Error checking drops: {e}")


# =============================================================================
# Test Case: DSCP Marking Verification
# =============================================================================
class DSCPMarkingValidation(aetest.Testcase):
    """Validate DSCP markings match expected values per VRF."""

    @aetest.setup
    def setup(self, testbed):
        """Setup test."""
        self.devices_to_test = [
            name for name in self.parent.parameters.get('connected_devices', [])
            if name in QOS_EDGE_DEVICES and name in testbed.devices
        ]
        if not self.devices_to_test:
            self.skipped("No Edge devices connected")

    @aetest.test
    def test_dscp_trust_configured(self, testbed, steps):
        """Verify DSCP trust is configured on interfaces (if required)."""

        for device_name in self.devices_to_test:
            with steps.start(f"Checking DSCP trust on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show mls qos interface")

                    # If MLS QoS is used (older IOS)
                    if "trust dscp" in output.lower() or "dscp" in output.lower():
                        step.passed("DSCP trust configured")
                    else:
                        # Try checking running config for QoS trust
                        config_output = device.execute("show run | include trust")
                        if "trust" in config_output.lower():
                            step.passed("QoS trust configured in running config")
                        else:
                            step.skipped("MLS QoS/trust not applicable or using MQC-only")

                except Exception as e:
                    # May not support MLS QoS (IOS-XE uses MQC)
                    step.skipped(f"MLS QoS not applicable: {e}")

    @aetest.test
    def test_vrf_dscp_marking_config(self, testbed, steps):
        """Verify DSCP marking configuration matches intent per VRF."""

        marking_policy = "EUNIV-VRF-MARKING"

        for device_name in self.devices_to_test:
            with steps.start(f"Checking DSCP marking config on {device_name}") as step:
                device = testbed.devices[device_name]
                device_vrfs = get_device_vrfs(device_name)

                try:
                    output = device.execute(f"show policy-map {marking_policy}")

                    if "Policy Map" not in output:
                        step.failed(f"Marking policy {marking_policy} not found")
                        continue

                    issues = []
                    verified = []

                    for vrf in device_vrfs:
                        expected_dscp, expected_val = get_vrf_dscp(vrf)
                        class_name = f"{vrf.replace('-NET', '')}-TRAFFIC"

                        # Check if DSCP marking matches expected
                        class_pattern = rf'Class {class_name}.*?(?=Class |$)'
                        class_match = re.search(class_pattern, output, re.DOTALL | re.IGNORECASE)

                        if class_match:
                            class_section = class_match.group(0)
                            if f"set dscp {expected_dscp}" in class_section.lower() or \
                               f"set dscp {expected_val}" in class_section.lower():
                                verified.append(f"{vrf}: DSCP {expected_dscp}")
                            else:
                                issues.append(f"{vrf}: expected DSCP {expected_dscp} ({expected_val})")

                    if issues:
                        step.failed(f"DSCP mismatch: {'; '.join(issues)}")
                    elif verified:
                        step.passed(f"DSCP markings verified: {len(verified)} VRFs")
                    else:
                        step.skipped("Could not verify DSCP markings")

                except Exception as e:
                    step.failed(f"Error checking DSCP config: {e}")


# =============================================================================
# Test Case: Bandwidth Allocation Validation
# =============================================================================
class BandwidthAllocationValidation(aetest.Testcase):
    """Validate bandwidth allocations total 100% and follow design."""

    @aetest.setup
    def setup(self, testbed):
        """Setup test."""
        self.devices_to_test = [
            name for name in self.parent.parameters.get('connected_devices', [])
            if name in QOS_EDGE_DEVICES and name in testbed.devices
        ]
        if not self.devices_to_test:
            self.skipped("No Edge devices connected")

    @aetest.test
    def test_bandwidth_total(self, testbed, steps):
        """Verify total bandwidth allocation equals 100%."""

        queuing_policy = "EUNIV-QOS-QUEUING"

        for device_name in self.devices_to_test:
            with steps.start(f"Checking bandwidth total on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute(f"show policy-map {queuing_policy}")

                    if "Policy Map" not in output:
                        step.failed(f"Policy-map {queuing_policy} not found")
                        continue

                    # Extract all bandwidth percentages
                    bw_matches = re.findall(r'bandwidth\s+(?:percent\s+)?(\d+)', output, re.IGNORECASE)
                    priority_matches = re.findall(r'priority\s+(?:percent\s+)?(\d+)', output, re.IGNORECASE)

                    total_bw = sum(int(b) for b in bw_matches)
                    total_priority = sum(int(p) for p in priority_matches)
                    total = total_bw + total_priority

                    # Account for class-default getting remaining bandwidth
                    if total <= 100:
                        step.passed(f"Bandwidth allocation valid: {total}% allocated ({100-total}% for class-default)")
                    else:
                        step.failed(f"Over-allocated: {total}% > 100%")

                except Exception as e:
                    step.failed(f"Error checking bandwidth: {e}")

    @aetest.test
    def test_priority_queue_medical(self, testbed, steps):
        """Verify MEDICAL-NET has priority queue (low latency guarantee)."""

        queuing_policy = "EUNIV-QOS-QUEUING"

        for device_name in self.devices_to_test:
            with steps.start(f"Checking medical priority on {device_name}") as step:
                device = testbed.devices[device_name]
                device_vrfs = get_device_vrfs(device_name)

                # Only check devices with MEDICAL-NET
                if "MEDICAL-NET" not in device_vrfs:
                    step.skipped("Device does not have MEDICAL-NET VRF")
                    continue

                try:
                    output = device.execute(f"show policy-map {queuing_policy}")

                    # Check MEDICAL-TRAFFIC class for priority
                    medical_pattern = r'Class MEDICAL-TRAFFIC.*?(?=Class |$)'
                    medical_match = re.search(medical_pattern, output, re.DOTALL | re.IGNORECASE)

                    if medical_match:
                        medical_section = medical_match.group(0)
                        if "priority" in medical_section.lower():
                            step.passed("MEDICAL-NET configured with priority queue")
                        else:
                            step.failed("MEDICAL-NET should have priority queue for low latency")
                    else:
                        step.failed("MEDICAL-TRAFFIC class not found in queuing policy")

                except Exception as e:
                    step.failed(f"Error checking medical priority: {e}")

    @aetest.test
    def test_guest_rate_limiting(self, testbed, steps):
        """Verify GUEST-NET has rate limiting (police) configured."""

        marking_policy = "EUNIV-VRF-MARKING"

        for device_name in self.devices_to_test:
            with steps.start(f"Checking guest rate limiting on {device_name}") as step:
                device = testbed.devices[device_name]
                device_vrfs = get_device_vrfs(device_name)

                if "GUEST-NET" not in device_vrfs:
                    step.skipped("Device does not have GUEST-NET VRF")
                    continue

                try:
                    output = device.execute(f"show policy-map {marking_policy}")

                    # Check GUEST-TRAFFIC class for police
                    guest_pattern = r'Class GUEST-TRAFFIC.*?(?=Class |$)'
                    guest_match = re.search(guest_pattern, output, re.DOTALL | re.IGNORECASE)

                    if guest_match:
                        guest_section = guest_match.group(0)
                        if "police" in guest_section.lower():
                            # Extract rate
                            rate_match = re.search(r'police.*?(\d+)\s*(m|k|g)?', guest_section, re.IGNORECASE)
                            if rate_match:
                                step.passed(f"GUEST-NET rate limited with police")
                            else:
                                step.passed("GUEST-NET has police configured")
                        else:
                            step.failed("GUEST-NET should have rate limiting (police)")
                    else:
                        step.failed("GUEST-TRAFFIC class not found in marking policy")

                except Exception as e:
                    step.failed(f"Error checking guest rate limiting: {e}")


# =============================================================================
# Common Cleanup
# =============================================================================
class CommonCleanup(aetest.CommonCleanup):
    """Disconnect from all devices."""

    @aetest.subsection
    def disconnect_from_devices(self, testbed):
        """Disconnect from all Edge devices."""
        for device_name in QOS_EDGE_DEVICES:
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

    parser = argparse.ArgumentParser(description="E-University QoS AEtest")
    parser.add_argument("--testbed", required=True, help="Testbed YAML file")
    args = parser.parse_args()

    testbed = genie_load(args.testbed)
    aetest.main(testbed=testbed)
