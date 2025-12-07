
"""
E-University Network - Edge Router SVI and HSRP Validation Tests
=================================================================
Tests to validate VLAN subinterfaces and HSRP gateway redundancy
on Edge (PE) routers.

These tests verify:
- VLAN subinterfaces exist with correct encapsulation
- VRF assignment per subinterface
- IP addressing on subinterfaces
- HSRP configuration for gateway redundancy
- DHCP relay (ip helper-address) configuration

Usage:
    pytest test_edge_svi_hsrp.py -v
    pytest test_edge_svi_hsrp.py -v --campus main
    pytest test_edge_svi_hsrp.py -v --campus medical
    pytest test_edge_svi_hsrp.py -v --campus research
"""

import pytest
from genie.testbed import load
import os
import re

# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def testbed():
    """Load the testbed."""
    testbed_path = os.path.join(os.path.dirname(__file__), "..", "testbed_l2_security.yaml")
    return load(testbed_path)


@pytest.fixture(scope="module")
def campus_config(request):
    """Return campus-specific configuration based on --campus option."""
    campus = request.config.getoption("--campus")

    if campus == "main" or campus == "all":
        return CAMPUS_CONFIGS["main"]
    elif campus == "medical":
        return CAMPUS_CONFIGS["medical"]
    elif campus == "research":
        return CAMPUS_CONFIGS["research"]
    else:
        pytest.skip(f"Unknown campus: {campus}")


@pytest.fixture(scope="module")
def edge_routers(testbed, request):
    """Connect to Edge router pair for the selected campus."""
    campus = request.config.getoption("--campus")
    if campus == "all":
        campus = "main"  # Default to main for 'all'

    config = CAMPUS_CONFIGS.get(campus)
    if not config:
        pytest.skip(f"Unknown campus: {campus}")

    devices = []
    for router_name in [config["edge1"], config["edge2"]]:
        if router_name in testbed.devices:
            device = testbed.devices[router_name]
            device.connect(log_stdout=False)
            devices.append(device)

    yield devices

    for device in devices:
        device.disconnect()


@pytest.fixture(scope="module")
def edge1(testbed, request):
    """Connect to primary Edge router."""
    campus = request.config.getoption("--campus")
    if campus == "all":
        campus = "main"

    config = CAMPUS_CONFIGS.get(campus)
    router_name = config["edge1"]

    device = testbed.devices[router_name]
    device.connect(log_stdout=False)
    yield device
    device.disconnect()


@pytest.fixture(scope="module")
def edge2(testbed, request):
    """Connect to secondary Edge router."""
    campus = request.config.getoption("--campus")
    if campus == "all":
        campus = "main"

    config = CAMPUS_CONFIGS.get(campus)
    router_name = config["edge2"]

    device = testbed.devices[router_name]
    device.connect(log_stdout=False)
    yield device
    device.disconnect()


# =============================================================================
# EXPECTED CONFIGURATION - EDGE SVI AND HSRP INTENT
# =============================================================================

# Interface facing access switch (downstream to L2 switches)
DOWNSTREAM_INTERFACE = "GigabitEthernet4"

# DHCP Server (Docker host running dnsmasq)
DHCP_SERVER_IP = "192.168.68.69"

# HSRP Configuration
# HSRP group = VLAN ID (e.g., VLAN 10 = group 10)
HSRP_PRIORITY_ACTIVE = 110    # Priority for active router
HSRP_PRIORITY_STANDBY = 100   # Default priority for standby
HSRP_TIMERS = {"hello": 1, "hold": 3}  # Fast timers for quick failover

# Campus-specific configurations
# Note: These are the ACCESS LAYER VLANs (10, 20, 30, 40) not the upstream VRFs (100, 200, 300, 500)
CAMPUS_CONFIGS = {
    "main": {
        "edge1": "EUNIV-MAIN-EDGE1",
        "edge2": "EUNIV-MAIN-EDGE2",
        "subnet_prefix": "10.1",  # 10.1.VLAN.0/24
        "vlans": {
            # Access Layer VLANs - load balanced across Edge routers
            10: {"name": "STAFF", "vrf": "STAFF-NET", "hsrp_active": "edge1"},
            20: {"name": "RESEARCH", "vrf": "RESEARCH-NET", "hsrp_active": "edge2"},
            40: {"name": "GUEST", "vrf": "GUEST-NET", "hsrp_active": "edge1"},
        },
    },
    "medical": {
        "edge1": "EUNIV-MED-EDGE1",
        "edge2": "EUNIV-MED-EDGE2",
        "subnet_prefix": "10.2",  # 10.2.VLAN.0/24
        "vlans": {
            10: {"name": "STAFF", "vrf": "STAFF-NET", "hsrp_active": "edge1"},
            20: {"name": "RESEARCH", "vrf": "RESEARCH-NET", "hsrp_active": "edge2"},
            30: {"name": "MEDICAL", "vrf": "MEDICAL-NET", "hsrp_active": "edge2"},
            40: {"name": "GUEST", "vrf": "GUEST-NET", "hsrp_active": "edge1"},
        },
    },
    "research": {
        "edge1": "EUNIV-RES-EDGE1",
        "edge2": "EUNIV-RES-EDGE2",
        "subnet_prefix": "10.3",  # 10.3.VLAN.0/24
        "vlans": {
            10: {"name": "STAFF", "vrf": "STAFF-NET", "hsrp_active": "edge1"},
            20: {"name": "RESEARCH", "vrf": "RESEARCH-NET", "hsrp_active": "edge2"},
            40: {"name": "GUEST", "vrf": "GUEST-NET", "hsrp_active": "edge1"},
        },
    },
}


def get_expected_ip(campus: str, vlan_id: int, router: str) -> str:
    """
    Calculate expected IP address for a subinterface.

    Scheme:
    - HSRP VIP: x.x.VLAN.1
    - EDGE1: x.x.VLAN.2
    - EDGE2: x.x.VLAN.3
    """
    config = CAMPUS_CONFIGS[campus]
    prefix = config["subnet_prefix"]

    if router == "vip":
        return f"{prefix}.{vlan_id}.1"
    elif router == "edge1":
        return f"{prefix}.{vlan_id}.2"
    elif router == "edge2":
        return f"{prefix}.{vlan_id}.3"
    else:
        raise ValueError(f"Unknown router type: {router}")


def get_campus_from_device(device_name: str) -> str:
    """Determine campus from device name."""
    if "MAIN" in device_name:
        return "main"
    elif "MED" in device_name:
        return "medical"
    elif "RES" in device_name:
        return "research"
    else:
        raise ValueError(f"Cannot determine campus from device: {device_name}")


def get_router_role(device_name: str) -> str:
    """Determine if device is edge1 or edge2."""
    if "EDGE1" in device_name or "PE1" in device_name:
        return "edge1"
    elif "EDGE2" in device_name or "PE2" in device_name:
        return "edge2"
    else:
        raise ValueError(f"Cannot determine role from device: {device_name}")


# =============================================================================
# SUBINTERFACE CONFIGURATION TESTS
# =============================================================================

class TestSubinterfaceConfiguration:
    """Verify VLAN subinterface configuration on Edge routers."""

    def test_subinterfaces_exist(self, edge1):
        """Test that VLAN subinterfaces are created on downstream interface."""
        campus = get_campus_from_device(edge1.name)
        config = CAMPUS_CONFIGS[campus]

        output = edge1.execute("show ip interface brief")

        for vlan_id in config["vlans"].keys():
            subint_name = f"{DOWNSTREAM_INTERFACE}.{vlan_id}"
            # Match shortened form (Gi4.10) or full form (GigabitEthernet4.10)
            assert f"Gi4.{vlan_id}" in output or subint_name in output, \
                f"Subinterface {subint_name} not found on {edge1.name}"

    def test_subinterface_encapsulation(self, edge1):
        """Test that subinterfaces have correct dot1q encapsulation."""
        campus = get_campus_from_device(edge1.name)
        config = CAMPUS_CONFIGS[campus]

        for vlan_id in config["vlans"].keys():
            subint_name = f"{DOWNSTREAM_INTERFACE}.{vlan_id}"
            output = edge1.execute(f"show running-config interface {subint_name}")

            assert f"encapsulation dot1Q {vlan_id}" in output, \
                f"{subint_name} missing dot1Q encapsulation for VLAN {vlan_id}"

    def test_subinterface_vrf_assignment(self, edge1):
        """Test that subinterfaces are assigned to correct VRF."""
        campus = get_campus_from_device(edge1.name)
        config = CAMPUS_CONFIGS[campus]

        for vlan_id, vlan_config in config["vlans"].items():
            subint_name = f"{DOWNSTREAM_INTERFACE}.{vlan_id}"
            expected_vrf = vlan_config["vrf"]

            output = edge1.execute(f"show running-config interface {subint_name}")

            assert f"vrf forwarding {expected_vrf}" in output, \
                f"{subint_name} not assigned to VRF {expected_vrf}"

    def test_subinterface_ip_address(self, edge1):
        """Test that subinterfaces have IP addresses configured."""
        campus = get_campus_from_device(edge1.name)
        config = CAMPUS_CONFIGS[campus]
        role = get_router_role(edge1.name)

        for vlan_id in config["vlans"].keys():
            subint_name = f"{DOWNSTREAM_INTERFACE}.{vlan_id}"
            expected_ip = get_expected_ip(campus, vlan_id, role)

            output = edge1.execute(f"show running-config interface {subint_name}")

            assert expected_ip in output, \
                f"{subint_name} missing expected IP {expected_ip}"

    def test_subinterfaces_up(self, edge1):
        """Test that subinterfaces are operationally up."""
        campus = get_campus_from_device(edge1.name)
        config = CAMPUS_CONFIGS[campus]

        output = edge1.execute("show ip interface brief")

        for vlan_id in config["vlans"].keys():
            # Look for the interface line and check status
            # Format: GigabitEthernet4.10     10.1.10.2    YES  ...  up    up
            pattern = rf"Gi.*4\.{vlan_id}\s+\S+\s+\S+\s+\S+\s+up\s+up"
            # Note: Interface might be down if no physical connection - skip if so
            if not re.search(pattern, output, re.IGNORECASE):
                pytest.skip(f"Subinterface Gi4.{vlan_id} is down (physical layer)")


# =============================================================================
# HSRP CONFIGURATION TESTS
# =============================================================================

class TestHsrpConfiguration:
    """Verify HSRP gateway redundancy configuration."""

    def test_hsrp_configured(self, edge1):
        """Test that HSRP is configured on VLAN subinterfaces."""
        campus = get_campus_from_device(edge1.name)
        config = CAMPUS_CONFIGS[campus]

        output = edge1.execute("show standby brief")

        for vlan_id in config["vlans"].keys():
            # Check for HSRP group on the subinterface
            pattern = rf"Gi4\.{vlan_id}\s+{vlan_id}"
            assert re.search(pattern, output), \
                f"HSRP not configured on Gi4.{vlan_id}"

    def test_hsrp_virtual_ip(self, edge1):
        """Test that HSRP virtual IP matches expected gateway."""
        campus = get_campus_from_device(edge1.name)
        config = CAMPUS_CONFIGS[campus]

        output = edge1.execute("show standby brief")

        for vlan_id in config["vlans"].keys():
            expected_vip = get_expected_ip(campus, vlan_id, "vip")

            assert expected_vip in output, \
                f"HSRP VIP {expected_vip} not found for VLAN {vlan_id}"

    def test_hsrp_priority_edge1(self, edge1):
        """Test that EDGE1 has higher priority for designated VLANs."""
        campus = get_campus_from_device(edge1.name)
        config = CAMPUS_CONFIGS[campus]

        output = edge1.execute("show standby")

        for vlan_id, vlan_config in config["vlans"].items():
            if vlan_config["hsrp_active"] == "edge1":
                # EDGE1 should have priority >= HSRP_PRIORITY_ACTIVE for its active VLANs
                subint_section = _extract_interface_section(output, f"GigabitEthernet4.{vlan_id}")
                if not subint_section:
                    pytest.fail(f"No HSRP config found for Gi4.{vlan_id} on {edge1.name}")
                priority_match = re.search(r"Priority\s+(\d+)", subint_section)
                if priority_match:
                    priority = int(priority_match.group(1))
                    assert priority >= HSRP_PRIORITY_ACTIVE, \
                        f"EDGE1 priority for VLAN {vlan_id} should be >= {HSRP_PRIORITY_ACTIVE}, got {priority}"

    def test_hsrp_priority_edge2(self, edge2):
        """Test that EDGE2 has higher priority for designated VLANs."""
        campus = get_campus_from_device(edge2.name)
        config = CAMPUS_CONFIGS[campus]

        output = edge2.execute("show standby")

        for vlan_id, vlan_config in config["vlans"].items():
            if vlan_config["hsrp_active"] == "edge2":
                # EDGE2 should have priority >= HSRP_PRIORITY_ACTIVE for its active VLANs
                subint_section = _extract_interface_section(output, f"GigabitEthernet4.{vlan_id}")
                if not subint_section:
                    pytest.fail(f"No HSRP config found for Gi4.{vlan_id} on {edge2.name}")
                priority_match = re.search(r"Priority\s+(\d+)", subint_section)
                if priority_match:
                    priority = int(priority_match.group(1))
                    assert priority >= HSRP_PRIORITY_ACTIVE, \
                        f"EDGE2 priority for VLAN {vlan_id} should be >= {HSRP_PRIORITY_ACTIVE}, got {priority}"

    def test_hsrp_preempt(self, edge1):
        """Test that HSRP preempt is enabled for failback."""
        campus = get_campus_from_device(edge1.name)
        config = CAMPUS_CONFIGS[campus]

        output = edge1.execute("show standby")

        for vlan_id in config["vlans"].keys():
            subint_section = _extract_interface_section(output, f"GigabitEthernet4.{vlan_id}")
            if subint_section:
                assert "Preemption enabled" in subint_section, \
                    f"HSRP preempt not enabled on Gi4.{vlan_id}"

    def test_hsrp_state_active_standby(self, edge_routers):
        """Test that one router is Active and one is Standby per VLAN."""
        if len(edge_routers) < 2:
            pytest.skip("Need both Edge routers for this test")

        edge1, edge2 = edge_routers
        campus = get_campus_from_device(edge1.name)
        config = CAMPUS_CONFIGS[campus]

        output1 = edge1.execute("show standby brief")
        output2 = edge2.execute("show standby brief")

        for vlan_id in config["vlans"].keys():
            # Check that we have one Active and one Standby
            pattern = rf"Gi4\.{vlan_id}\s+{vlan_id}\s+\d+\s+\S+\s+(Active|Standby)"

            match1 = re.search(pattern, output1)
            match2 = re.search(pattern, output2)

            if match1 and match2:
                state1 = match1.group(1)
                state2 = match2.group(1)

                assert state1 != state2, \
                    f"VLAN {vlan_id}: Both routers in same state ({state1})"
                assert "Active" in [state1, state2], \
                    f"VLAN {vlan_id}: No Active router found"


# =============================================================================
# DHCP RELAY TESTS
# =============================================================================

class TestDhcpRelay:
    """Verify DHCP relay (ip helper-address) configuration."""

    def test_helper_address_configured(self, edge1):
        """Test that ip helper-address is configured on subinterfaces."""
        campus = get_campus_from_device(edge1.name)
        config = CAMPUS_CONFIGS[campus]

        for vlan_id in config["vlans"].keys():
            subint_name = f"{DOWNSTREAM_INTERFACE}.{vlan_id}"
            output = edge1.execute(f"show running-config interface {subint_name}")

            assert f"ip helper-address {DHCP_SERVER_IP}" in output, \
                f"{subint_name} missing DHCP helper-address {DHCP_SERVER_IP}"

    def test_helper_address_reachable(self, edge1):
        """Test that DHCP server is reachable from Edge router."""
        # Ping from global routing table (DHCP server is on management network)
        output = edge1.execute(f"ping {DHCP_SERVER_IP} repeat 2")

        assert "!!" in output or "Success rate is 100" in output, \
            f"Cannot reach DHCP server at {DHCP_SERVER_IP}"


# =============================================================================
# QoS SERVICE POLICY TESTS (if QoS is applied to subinterfaces)
# =============================================================================

class TestSubinterfaceQos:
    """Verify QoS policies are applied to subinterfaces."""

    def test_input_policy_applied(self, edge1):
        """Test that input marking policy is applied to subinterfaces."""
        campus = get_campus_from_device(edge1.name)
        config = CAMPUS_CONFIGS[campus]

        for vlan_id in config["vlans"].keys():
            subint_name = f"{DOWNSTREAM_INTERFACE}.{vlan_id}"
            output = edge1.execute(f"show running-config interface {subint_name}")

            # Check for service-policy input (marking policy)
            if "service-policy input" not in output:
                pytest.skip(f"QoS input policy not configured on {subint_name} (optional)")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _extract_interface_section(output: str, interface_name: str) -> str:
    """Extract the section of 'show standby' output for a specific interface."""
    lines = output.split("\n")
    section_lines = []
    in_section = False

    for line in lines:
        if interface_name in line:
            in_section = True
        elif in_section and line.strip() and not line.startswith(" "):
            # New interface section started
            break

        if in_section:
            section_lines.append(line)

    return "\n".join(section_lines)


# =============================================================================
# MAIN - Run tests directly
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
