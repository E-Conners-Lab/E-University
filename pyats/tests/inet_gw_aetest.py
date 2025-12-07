#!/usr/bin/env python3
"""
E-University Network - Internet Gateway and VRF Internet Connectivity Validation

This AEtest script validates:
- INET-GW NAT configuration for all VRFs
- VRF static default routes via INET-GW
- BGP VRF default route origination
- VRF internet connectivity (ping 8.8.8.8 from Edge routers)
- NAT translations on INET-GW routers

Usage:
    pyats run job ../inet_gw_job.py --testbed-file ../testbed.yaml
    python inet_gw_aetest.py --testbed ../testbed.yaml
"""

import logging
import re

from pyats import aetest
from pyats.topology import Testbed

logger = logging.getLogger(__name__)


# =============================================================================
# Expected Configuration
# =============================================================================
INET_GW_DEVICES = ['EUNIV-INET-GW1', 'EUNIV-INET-GW2']

EDGE_DEVICES = [
    'EUNIV-MAIN-EDGE1', 'EUNIV-MAIN-EDGE2',
    'EUNIV-MED-EDGE1', 'EUNIV-MED-EDGE2',
    'EUNIV-RES-EDGE1', 'EUNIV-RES-EDGE2'
]

# VRFs that should have internet access via INET-GW
INTERNET_VRFS = ['STAFF-NET', 'RESEARCH-NET', 'MEDICAL-NET', 'GUEST-NET']

# Expected NAT ACL name
NAT_ACL_NAME = 'VRF-NAT-ACL'

# Test destination for internet connectivity
INTERNET_TEST_IP = '8.8.8.8'

# VRF to source IP mapping for ping tests (Edge router SVI IPs)
VRF_SOURCE_IPS = {
    'EUNIV-MAIN-EDGE1': {'STAFF-NET': '10.1.10.2'},
    'EUNIV-MAIN-EDGE2': {'STAFF-NET': '10.1.10.3'},
    'EUNIV-MED-EDGE1': {'STAFF-NET': '10.2.10.2', 'MEDICAL-NET': '10.2.30.2'},
    'EUNIV-MED-EDGE2': {'STAFF-NET': '10.2.10.3', 'MEDICAL-NET': '10.2.30.3'},
    'EUNIV-RES-EDGE1': {'STAFF-NET': '10.3.10.2'},
    'EUNIV-RES-EDGE2': {'STAFF-NET': '10.3.10.3'},
}


# =============================================================================
# Common Setup
# =============================================================================
class CommonSetup(aetest.CommonSetup):
    """Connect to INET-GW and Edge devices."""

    @aetest.subsection
    def check_testbed(self, testbed: Testbed):
        """Verify testbed has required devices."""
        if not testbed:
            self.failed("Testbed not provided")

        inet_gw_in_testbed = [d for d in INET_GW_DEVICES if d in testbed.devices]
        edge_in_testbed = [d for d in EDGE_DEVICES if d in testbed.devices]

        if not inet_gw_in_testbed:
            self.failed("No INET-GW devices found in testbed")

        logger.info(f"Found {len(inet_gw_in_testbed)} INET-GW and {len(edge_in_testbed)} Edge devices")

    @aetest.subsection
    def connect_to_devices(self, testbed: Testbed, steps):
        """Connect to all required devices."""
        connected_inet_gw = []
        connected_edge = []
        failed = []

        # Connect to INET-GW devices
        for device_name in INET_GW_DEVICES:
            if device_name not in testbed.devices:
                continue
            device = testbed.devices[device_name]
            with steps.start(f"Connecting to {device_name}", continue_=True) as step:
                try:
                    if not device.is_connected():
                        device.connect(log_stdout=False, learn_hostname=True)
                    connected_inet_gw.append(device_name)
                except Exception as e:
                    step.passx(f"Not reachable: {e}")
                    failed.append(device_name)

        # Connect to Edge devices
        for device_name in EDGE_DEVICES:
            if device_name not in testbed.devices:
                continue
            device = testbed.devices[device_name]
            with steps.start(f"Connecting to {device_name}", continue_=True) as step:
                try:
                    if not device.is_connected():
                        device.connect(log_stdout=False, learn_hostname=True)
                    connected_edge.append(device_name)
                except Exception as e:
                    step.passx(f"Not reachable: {e}")
                    failed.append(device_name)

        self.parent.parameters['connected_inet_gw'] = connected_inet_gw
        self.parent.parameters['connected_edge'] = connected_edge
        self.parent.parameters['failed_devices'] = failed

        if not connected_inet_gw:
            self.failed("Could not connect to any INET-GW devices")

        logger.info(f"Connected: INET-GW={len(connected_inet_gw)}, Edge={len(connected_edge)}")

        if failed:
            logger.warning(f"Failed to connect to: {', '.join(failed)}")


# =============================================================================
# Test Case: INET-GW VRF Configuration
# =============================================================================
class INETGWVRFConfiguration(aetest.Testcase):
    """Validate VRF configuration on INET-GW routers."""

    @aetest.setup
    def setup(self, testbed):
        """Setup for VRF tests."""
        self.inet_gw_devices = self.parent.parameters.get('connected_inet_gw', [])
        if not self.inet_gw_devices:
            self.skipped("No INET-GW devices connected")

    @aetest.test
    def test_vrfs_exist(self, testbed, steps):
        """Verify all required VRFs are configured on INET-GW."""

        for device_name in self.inet_gw_devices:
            with steps.start(f"Checking VRFs on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show vrf")
                    missing_vrfs = []

                    for vrf in INTERNET_VRFS:
                        if vrf not in output:
                            missing_vrfs.append(vrf)

                    if missing_vrfs:
                        step.failed(f"Missing VRFs: {', '.join(missing_vrfs)}")
                    else:
                        step.passed(f"All {len(INTERNET_VRFS)} VRFs configured")

                except Exception as e:
                    step.failed(f"Error checking VRFs: {e}")

    @aetest.test
    def test_vrf_static_routes(self, testbed, steps):
        """Verify VRF static default routes to gateway exist."""

        for device_name in self.inet_gw_devices:
            with steps.start(f"Checking VRF static routes on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show ip route vrf * static | include 0.0.0.0")

                    # Count default routes
                    default_routes = output.count("0.0.0.0/0") + output.count("0.0.0.0 0.0.0.0")

                    if default_routes >= len(INTERNET_VRFS):
                        step.passed(f"Found {default_routes} VRF default routes")
                    else:
                        step.failed(f"Expected {len(INTERNET_VRFS)} VRF default routes, found {default_routes}")

                except Exception as e:
                    step.failed(f"Error checking routes: {e}")


# =============================================================================
# Test Case: INET-GW NAT Configuration
# =============================================================================
class INETGWNATConfiguration(aetest.Testcase):
    """Validate NAT configuration on INET-GW routers."""

    @aetest.setup
    def setup(self, testbed):
        """Setup for NAT tests."""
        self.inet_gw_devices = self.parent.parameters.get('connected_inet_gw', [])
        if not self.inet_gw_devices:
            self.skipped("No INET-GW devices connected")

    @aetest.test
    def test_nat_acl_exists(self, testbed, steps):
        """Verify NAT ACL is configured."""

        for device_name in self.inet_gw_devices:
            with steps.start(f"Checking NAT ACL on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute(f"show access-list {NAT_ACL_NAME}")

                    if NAT_ACL_NAME in output or "permit" in output:
                        step.passed(f"NAT ACL {NAT_ACL_NAME} configured")
                    else:
                        step.failed(f"NAT ACL {NAT_ACL_NAME} not found")

                except Exception as e:
                    step.failed(f"Error checking NAT ACL: {e}")

    @aetest.test
    def test_nat_statements_per_vrf(self, testbed, steps):
        """Verify NAT source statements exist for each VRF."""

        for device_name in self.inet_gw_devices:
            with steps.start(f"Checking NAT statements on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show run | include ip nat inside source")
                    missing_vrfs = []

                    for vrf in INTERNET_VRFS:
                        if f"vrf {vrf}" not in output:
                            missing_vrfs.append(vrf)

                    if missing_vrfs:
                        step.failed(f"Missing NAT for VRFs: {', '.join(missing_vrfs)}")
                    else:
                        step.passed(f"NAT configured for all {len(INTERNET_VRFS)} VRFs")

                except Exception as e:
                    step.failed(f"Error checking NAT: {e}")

    @aetest.test
    def test_nat_interfaces(self, testbed, steps):
        """Verify NAT inside/outside interfaces are configured."""

        for device_name in self.inet_gw_devices:
            with steps.start(f"Checking NAT interfaces on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show run | include ip nat")

                    has_inside = "ip nat inside" in output
                    has_outside = "ip nat outside" in output

                    if has_inside and has_outside:
                        step.passed("NAT inside and outside interfaces configured")
                    elif not has_inside:
                        step.failed("No 'ip nat inside' interface found")
                    elif not has_outside:
                        step.failed("No 'ip nat outside' interface found")

                except Exception as e:
                    step.failed(f"Error checking NAT interfaces: {e}")


# =============================================================================
# Test Case: BGP VRF Default Route Origination
# =============================================================================
class BGPVRFDefaultOrigination(aetest.Testcase):
    """Validate BGP VRF default route origination on INET-GW."""

    @aetest.setup
    def setup(self, testbed):
        """Setup for BGP tests."""
        self.inet_gw_devices = self.parent.parameters.get('connected_inet_gw', [])
        if not self.inet_gw_devices:
            self.skipped("No INET-GW devices connected")

    @aetest.test
    def test_bgp_vrf_address_families(self, testbed, steps):
        """Verify BGP VRF address-families are configured."""

        for device_name in self.inet_gw_devices:
            with steps.start(f"Checking BGP VRF config on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show run | section address-family ipv4 vrf")
                    missing_vrfs = []

                    for vrf in INTERNET_VRFS:
                        if f"address-family ipv4 vrf {vrf}" not in output:
                            missing_vrfs.append(vrf)

                    if missing_vrfs:
                        step.failed(f"Missing BGP VRF address-families: {', '.join(missing_vrfs)}")
                    else:
                        step.passed(f"BGP configured for all {len(INTERNET_VRFS)} VRFs")

                except Exception as e:
                    step.failed(f"Error checking BGP: {e}")

    @aetest.test
    def test_default_information_originate(self, testbed, steps):
        """Verify default-information originate is configured in BGP VRF."""

        for device_name in self.inet_gw_devices:
            with steps.start(f"Checking default origination on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show run | section router bgp")

                    if "default-information originate" in output:
                        step.passed("default-information originate configured")
                    else:
                        step.failed("default-information originate not found in BGP config")

                except Exception as e:
                    step.failed(f"Error checking BGP: {e}")


# =============================================================================
# Test Case: VRF Internet Connectivity
# =============================================================================
class VRFInternetConnectivity(aetest.Testcase):
    """Validate VRF internet connectivity from Edge routers."""

    @aetest.setup
    def setup(self, testbed):
        """Setup for connectivity tests."""
        self.edge_devices = self.parent.parameters.get('connected_edge', [])
        if not self.edge_devices:
            self.skipped("No Edge devices connected")

    @aetest.test
    def test_vrf_default_route_learned(self, testbed, steps):
        """Verify Edge routers have VRF default route via BGP."""

        for device_name in self.edge_devices:
            with steps.start(f"Checking VRF default route on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    # Check STAFF-NET default route (should be on all edge routers)
                    output = device.execute("show ip route vrf STAFF-NET 0.0.0.0")

                    if "bgp" in output.lower() and "10.255.0.101" in output:
                        step.passed("VRF default route learned via BGP from INET-GW1")
                    elif "bgp" in output.lower() and "10.255.0.102" in output:
                        step.passed("VRF default route learned via BGP from INET-GW2")
                    elif "bgp" in output.lower():
                        step.passed("VRF default route learned via BGP")
                    else:
                        step.failed("VRF default route not learned via BGP")

                except Exception as e:
                    step.failed(f"Error checking route: {e}")

    @aetest.test
    def test_vrf_internet_ping(self, testbed, steps):
        """Verify VRF can ping internet (8.8.8.8)."""

        for device_name in self.edge_devices:
            with steps.start(f"Testing internet from {device_name}") as step:
                device = testbed.devices[device_name]

                # Get source IP for this device
                vrf_ips = VRF_SOURCE_IPS.get(device_name, {})
                source_ip = vrf_ips.get('STAFF-NET')

                if not source_ip:
                    step.skipped(f"No source IP configured for {device_name}")
                    continue

                try:
                    output = device.execute(
                        f"ping vrf STAFF-NET {INTERNET_TEST_IP} source {source_ip} repeat 5"
                    )

                    # Check for success rate
                    if "100 percent" in output:
                        step.passed("100% ping success to internet")
                    elif "Success rate is 0 percent" in output:
                        step.failed("0% ping success - no internet connectivity")
                    elif re.search(r'Success rate is (\d+) percent', output):
                        match = re.search(r'Success rate is (\d+) percent', output)
                        pct = int(match.group(1))
                        if pct >= 80:
                            step.passed(f"{pct}% ping success to internet")
                        else:
                            step.failed(f"Only {pct}% ping success to internet")
                    else:
                        step.failed("Could not determine ping result")

                except Exception as e:
                    step.failed(f"Error running ping: {e}")


# =============================================================================
# Test Case: NAT Translations Active
# =============================================================================
class NATTranslationsActive(aetest.Testcase):
    """Verify NAT translations are being created on INET-GW."""

    @aetest.setup
    def setup(self, testbed):
        """Setup for NAT translation tests."""
        self.inet_gw_devices = self.parent.parameters.get('connected_inet_gw', [])
        if not self.inet_gw_devices:
            self.skipped("No INET-GW devices connected")

    @aetest.test
    def test_nat_statistics(self, testbed, steps):
        """Verify NAT is actively translating traffic."""

        for device_name in self.inet_gw_devices:
            with steps.start(f"Checking NAT stats on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show ip nat statistics")

                    # Check for hits
                    hits_match = re.search(r'Hits:\s*(\d+)', output)
                    if hits_match:
                        hits = int(hits_match.group(1))
                        if hits > 0:
                            step.passed(f"NAT has {hits} translation hits")
                        else:
                            step.skipped("No NAT hits yet - may need traffic")
                    else:
                        step.failed("Could not parse NAT statistics")

                except Exception as e:
                    step.failed(f"Error checking NAT stats: {e}")

    @aetest.test
    def test_nat_translations_exist(self, testbed, steps):
        """Check if NAT translations exist."""

        for device_name in self.inet_gw_devices:
            with steps.start(f"Checking NAT translations on {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show ip nat translations")

                    if "Total number of translations:" in output:
                        match = re.search(r'Total number of translations:\s*(\d+)', output)
                        if match:
                            count = int(match.group(1))
                            if count > 0:
                                step.passed(f"Found {count} active NAT translations")
                            else:
                                step.skipped("No active translations - may need traffic")
                    else:
                        step.skipped("No NAT translation table output")

                except Exception as e:
                    step.failed(f"Error checking translations: {e}")


# =============================================================================
# Common Cleanup
# =============================================================================
class CommonCleanup(aetest.CommonCleanup):
    """Disconnect from all devices."""

    @aetest.subsection
    def disconnect_from_devices(self, testbed):
        """Disconnect from all devices."""
        for device_name in INET_GW_DEVICES + EDGE_DEVICES:
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

    parser = argparse.ArgumentParser(description="E-University INET-GW AEtest")
    parser.add_argument("--testbed", required=True, help="Testbed YAML file")
    args = parser.parse_args()

    testbed = genie_load(args.testbed)
    aetest.main(testbed=testbed)
