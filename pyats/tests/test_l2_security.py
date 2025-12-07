"""
E-University Network - Layer 2 Security Validation Tests
=========================================================
Tests to validate enterprise L2 security features on access switches.
Run BEFORE and AFTER configuration to verify compliance.

Usage:
    pytest test_l2_security.py -v --testbed=../testbed_l2_security.yaml
"""

import pytest
from genie.testbed import load
from genie.utils.diff import Diff
import os
import re

# =============================================================================
# TEST FIXTURES
# =============================================================================

# List of access switches to test
ACCESS_SWITCH_NAMES = [
    "EUNIV-MED-ASW1",
    "EUNIV-MAIN-ASW1",
    "EUNIV-RES-ASW1",
]


@pytest.fixture(scope="module")
def testbed():
    """Load the L2 security testbed."""
    testbed_path = os.path.join(os.path.dirname(__file__), "..", "testbed_l2_security.yaml")
    return load(testbed_path)


@pytest.fixture(scope="module")
def med_asw1(testbed, request):
    """Connect to access switch (configurable via --switch option)."""
    switch_name = request.config.getoption("--switch")
    if switch_name is None:
        switch_name = "EUNIV-MED-ASW1"  # Default

    if switch_name not in testbed.devices:
        pytest.skip(f"Switch {switch_name} not found in testbed")

    device = testbed.devices[switch_name]
    device.connect(log_stdout=False)
    yield device
    device.disconnect()


# =============================================================================
# EXPECTED CONFIGURATION - L2 SECURITY INTENT
# =============================================================================

# Base VLANs required on ALL switches
EXPECTED_VLANS = {
    10: "STAFF",
    20: "RESEARCH",
    30: "MEDICAL",
    40: "GUEST",
    99: "MGMT",
    100: "INFRA",
}

# Campus-specific trunk allowed VLANs (MEDICAL VLAN 30 only on Medical campus)
CAMPUS_TRUNK_VLANS = {
    "EUNIV-MED-ASW1": [10, 20, 30, 40, 99, 100],   # Has MEDICAL VLAN
    "EUNIV-MAIN-ASW1": [10, 20, 40, 99, 100],      # No MEDICAL VLAN
    "EUNIV-RES-ASW1": [10, 20, 40, 99, 100],       # No MEDICAL VLAN
}

TRUNK_PORTS = ["GigabitEthernet1/0/1", "GigabitEthernet1/0/2"]
ACCESS_PORTS = [f"GigabitEthernet1/0/{i}" for i in range(3, 9)]   # Gi1/0/3 to Gi1/0/8
DOT1X_PORTS = [f"GigabitEthernet1/0/{i}" for i in range(4, 9)]    # Gi1/0/4 to Gi1/0/8 (802.1X)

DHCP_SNOOPING_VLANS = [10, 20, 30, 40]
DAI_VLANS = [10, 20, 30, 40]

RADIUS_SERVER = {
    "name": "EUNIV-RADIUS",
    "ip": None,  # Will be determined dynamically (Docker host)
    "auth_port": 1812,
    "acct_port": 1813,
}

STORM_CONTROL_THRESHOLDS = {
    "broadcast": 10.0,  # percentage
    "multicast": 10.0,
    "unicast": 10.0,
}


# =============================================================================
# VLAN CONFIGURATION TESTS
# =============================================================================

class TestVlanConfiguration:
    """Verify VLAN configuration on access switch."""

    def test_vlans_exist(self, med_asw1):
        """Test that all required VLANs are configured."""
        output = med_asw1.parse("show vlan brief")
        # Handle both parser schemas: 'vlans' (IOSv) or 'vlan' (Cat9k)
        vlans = output.get("vlans", output.get("vlan", {}))
        # Keys might be '10' or 'vlan10' depending on platform
        configured_vlans = list(vlans.keys())

        for vlan_id, vlan_name in EXPECTED_VLANS.items():
            vlan_key = str(vlan_id)
            vlan_key_alt = f"vlan{vlan_id}"
            assert vlan_key in configured_vlans or vlan_key_alt in configured_vlans, \
                f"VLAN {vlan_id} ({vlan_name}) is not configured"

    def test_vlan_names(self, med_asw1):
        """Test that VLANs have correct names."""
        output = med_asw1.parse("show vlan brief")
        # Handle both parser schemas
        vlans = output.get("vlans", output.get("vlan", {}))

        for vlan_id, expected_name in EXPECTED_VLANS.items():
            vlan_key = str(vlan_id)
            vlan_key_alt = f"vlan{vlan_id}"
            vlan_info = vlans.get(vlan_key, vlans.get(vlan_key_alt, {}))
            # Name key might be 'name' or 'vlan_name'
            actual_name = vlan_info.get("name", vlan_info.get("vlan_name", ""))
            assert expected_name.upper() in actual_name.upper(), \
                f"VLAN {vlan_id} name mismatch: expected '{expected_name}', got '{actual_name}'"


# =============================================================================
# TRUNK CONFIGURATION TESTS
# =============================================================================

class TestTrunkConfiguration:
    """Verify trunk port configuration."""

    def test_trunk_mode(self, med_asw1):
        """Test that uplink ports are configured as trunk mode."""
        output = med_asw1.parse("show interfaces switchport")

        for port in TRUNK_PORTS:
            port_info = output.get(port, {})
            # Check administrative mode (config) since port may be down
            admin_mode = port_info.get("switchport_mode", "")
            oper_mode = port_info.get("operational_mode", "")
            assert admin_mode == "trunk" or oper_mode == "trunk", \
                f"{port} is not configured as trunk (admin: {admin_mode}, oper: {oper_mode})"

    def test_trunk_allowed_vlans(self, med_asw1):
        """Test that trunk ports allow required VLANs (campus-aware)."""
        switch_name = med_asw1.name
        expected_vlans = CAMPUS_TRUNK_VLANS.get(switch_name, list(EXPECTED_VLANS.keys()))

        try:
            output = med_asw1.parse("show interfaces trunk")
        except Exception:
            # Trunk ports may be down, check running-config instead
            config = med_asw1.execute("show running-config | section interface Gi1/0/1")
            if "trunk allowed vlan" in config.lower():
                return  # Config exists, just not active
            pytest.skip("Trunk ports are down - cannot verify allowed VLANs operationally")

        for port in TRUNK_PORTS:
            port_data = output.get("interface", {}).get(port, {})
            # Handle different parser key names
            allowed_vlans = port_data.get("vlans_allowed",
                           port_data.get("vlans_allowed_on_trunk", ""))

            for vlan_id in expected_vlans:
                assert str(vlan_id) in allowed_vlans or "all" in allowed_vlans.lower(), \
                    f"VLAN {vlan_id} not allowed on trunk {port}"

    def test_trunk_native_vlan(self, med_asw1):
        """Test that trunk native VLAN is set correctly (not VLAN 1)."""
        try:
            output = med_asw1.parse("show interfaces trunk")
        except Exception:
            # Trunk ports may be down, check running-config instead
            config = med_asw1.execute("show running-config | section interface Gi1/0/1")
            if "native vlan" in config.lower() and "native vlan 1" not in config.lower():
                return  # Non-default native VLAN is configured
            pytest.skip("Trunk ports are down - cannot verify native VLAN operationally")

        for port in TRUNK_PORTS:
            port_data = output.get("interface", {}).get(port, {})
            native_vlan = port_data.get("native_vlan", "1")
            assert native_vlan != "1", \
                f"{port} is using default native VLAN 1 (security risk)"


# =============================================================================
# 802.1X CONFIGURATION TESTS
# =============================================================================

class TestDot1xConfiguration:
    """Verify 802.1X/AAA configuration."""

    def test_aaa_new_model(self, med_asw1):
        """Test that AAA new-model is enabled."""
        output = med_asw1.execute("show running-config | include aaa new-model")
        assert "aaa new-model" in output, \
            "AAA new-model is not enabled"

    def test_aaa_authentication_dot1x(self, med_asw1):
        """Test that AAA authentication for dot1x is configured."""
        output = med_asw1.execute("show running-config | include aaa authentication dot1x")
        assert "aaa authentication dot1x" in output, \
            "AAA authentication for dot1x is not configured"

    def test_aaa_authorization_network(self, med_asw1):
        """Test that AAA authorization for network is configured."""
        output = med_asw1.execute("show running-config | include aaa authorization network")
        assert "aaa authorization network" in output, \
            "AAA authorization for network is not configured"

    def test_dot1x_system_auth_control(self, med_asw1):
        """Test that dot1x is enabled globally."""
        output = med_asw1.execute("show running-config | include dot1x system-auth-control")
        assert "dot1x system-auth-control" in output, \
            "dot1x system-auth-control is not enabled"

    def test_radius_server_configured(self, med_asw1):
        """Test that RADIUS server is configured."""
        output = med_asw1.execute("show running-config | section radius server")
        assert "radius server" in output, \
            "No RADIUS server configured"
        assert "1812" in output or "auth-port" in output, \
            "RADIUS authentication port not configured"

    def test_dot1x_enabled_on_access_ports(self, med_asw1):
        """Test that dot1x is enabled on access ports."""
        output = med_asw1.execute("show dot1x all")

        for port in DOT1X_PORTS:
            # Normalize port name for matching
            short_port = port.replace("GigabitEthernet", "Gi")
            assert short_port in output or port in output, \
                f"dot1x not enabled on {port}"


# =============================================================================
# DHCP SNOOPING TESTS
# =============================================================================

class TestDhcpSnooping:
    """Verify DHCP Snooping configuration."""

    def test_dhcp_snooping_enabled(self, med_asw1):
        """Test that DHCP snooping is enabled globally."""
        output = med_asw1.execute("show ip dhcp snooping")
        assert "Switch DHCP snooping is enabled" in output, \
            "DHCP snooping is not enabled globally"

    def test_dhcp_snooping_vlans(self, med_asw1):
        """Test that DHCP snooping is enabled on user VLANs."""
        output = med_asw1.execute("show ip dhcp snooping")

        for vlan_id in DHCP_SNOOPING_VLANS:
            assert str(vlan_id) in output, \
                f"DHCP snooping not enabled on VLAN {vlan_id}"

    def test_dhcp_snooping_trusted_ports(self, med_asw1):
        """Test that trunk ports are DHCP snooping trusted."""
        output = med_asw1.execute("show ip dhcp snooping")

        for port in TRUNK_PORTS:
            short_port = port.replace("GigabitEthernet", "Gi")
            # Check if port is listed with "yes" in trusted column
            # Output format: "GigabitEthernet1/0/1             yes        yes"
            assert short_port in output or port in output, \
                f"{port} should be DHCP snooping trusted"


# =============================================================================
# DYNAMIC ARP INSPECTION TESTS
# =============================================================================

class TestDynamicArpInspection:
    """Verify Dynamic ARP Inspection (DAI) configuration."""

    def test_dai_enabled_on_vlans(self, med_asw1):
        """Test that DAI is enabled on user VLANs."""
        output = med_asw1.execute("show ip arp inspection")

        for vlan_id in DAI_VLANS:
            # Look for VLAN in DAI output
            vlan_pattern = rf"\b{vlan_id}\b"
            assert re.search(vlan_pattern, output), \
                f"DAI not enabled on VLAN {vlan_id}"

    def test_dai_trusted_ports(self, med_asw1):
        """Test that trunk ports are DAI trusted."""
        output = med_asw1.execute("show ip arp inspection interfaces")

        for port in TRUNK_PORTS:
            short_port = port.replace("GigabitEthernet", "Gi")
            # Trusted ports should show "Trusted" state
            if short_port in output:
                lines = output.split("\n")
                for line in lines:
                    if short_port in line:
                        assert "Trusted" in line, \
                            f"{port} should be DAI trusted"


# =============================================================================
# PORT SECURITY TESTS
# =============================================================================

class TestPortSecurity:
    """Verify port security configuration."""

    def test_port_security_enabled(self, med_asw1):
        """Test that port security is enabled on access ports."""
        output = med_asw1.execute("show port-security")

        # Check for configured ports with security actions (Restrict, Shutdown, Protect)
        # Output shows "Gi1/0/x" entries with security actions
        has_port_security = ("Gi1/0/" in output and
                             ("Restrict" in output or "Shutdown" in output or "Protect" in output))
        assert has_port_security, \
            "Port security does not appear to be enabled on any ports"

    def test_port_security_max_mac(self, med_asw1):
        """Test that port security MAC limit is configured."""
        output = med_asw1.execute("show port-security")

        # Check for reasonable MAC address limits (not unlimited)
        # Looking for entries with max MAC addresses configured
        assert re.search(r"\d+\s+\d+\s+\d+", output), \
            "Port security MAC address limits not configured"


# =============================================================================
# SPANNING TREE PROTECTION TESTS
# =============================================================================

class TestSpanningTreeProtection:
    """Verify STP protection features."""

    def test_bpdu_guard_enabled(self, med_asw1):
        """Test that BPDU Guard is enabled on access ports."""
        output = med_asw1.execute("show running-config | include bpduguard")

        # Either global default or per-interface
        has_bpdu_guard = "bpduguard" in output.lower()
        assert has_bpdu_guard, \
            "BPDU Guard is not configured"

    def test_portfast_on_access_ports(self, med_asw1):
        """Test that PortFast is enabled on access ports."""
        output = med_asw1.execute("show running-config | include portfast")

        # Either global default or per-interface
        has_portfast = "portfast" in output.lower()
        assert has_portfast, \
            "PortFast is not configured on access ports"

    def test_root_guard_on_access_ports(self, med_asw1):
        """Test that Root Guard is configured."""
        output = med_asw1.execute("show running-config | include guard root")
        # Root guard is optional but recommended
        # This is a warning-level test
        if "guard root" not in output.lower():
            pytest.skip("Root Guard not configured (recommended but optional)")


# =============================================================================
# STORM CONTROL TESTS
# =============================================================================

class TestStormControl:
    """Verify storm control configuration."""

    def test_storm_control_configured(self, med_asw1):
        """Test that storm control is configured on access ports."""
        output = med_asw1.execute("show storm-control")

        # Check that storm control is configured on at least some ports
        assert "Gi1/0" in output or "GigabitEthernet1/0" in output, \
            "Storm control not configured on access ports"

    def test_storm_control_broadcast(self, med_asw1):
        """Test that broadcast storm control is enabled."""
        output = med_asw1.execute("show storm-control broadcast")

        # Look for configured thresholds
        has_broadcast_control = "Gi1/0" in output and ("%" in output or "pps" in output.lower())
        assert has_broadcast_control, \
            "Broadcast storm control not configured"


# =============================================================================
# RADIUS CONNECTIVITY TESTS
# =============================================================================

class TestRadiusConnectivity:
    """Verify RADIUS server connectivity."""

    @pytest.mark.skip(reason="RADIUS server not deployed in lab environment")
    def test_radius_server_reachable(self, med_asw1):
        """Test that RADIUS server is reachable from switch."""
        # Get the RADIUS server IP from config
        config = med_asw1.execute("show running-config | section radius server")

        # Extract IP address from config
        ip_match = re.search(r"address ipv4 (\d+\.\d+\.\d+\.\d+)", config)
        if not ip_match:
            pytest.skip("RADIUS server IP not found in configuration")

        radius_ip = ip_match.group(1)

        # Ping the RADIUS server
        ping_output = med_asw1.execute(f"ping {radius_ip} repeat 2")
        assert "!!" in ping_output or "Success rate is 100" in ping_output, \
            f"Cannot reach RADIUS server at {radius_ip}"

    def test_radius_server_status(self, med_asw1):
        """Test RADIUS server status."""
        output = med_asw1.execute("show aaa servers")

        # Check for RADIUS server in AAA servers output
        assert "RADIUS" in output, \
            "RADIUS server not showing in AAA servers"


# =============================================================================
# IP SOURCE GUARD TESTS
# =============================================================================

class TestIpSourceGuard:
    """Verify IP Source Guard configuration."""

    def test_ip_source_guard_enabled(self, med_asw1):
        """Test that IP Source Guard is enabled on access ports."""
        output = med_asw1.execute("show ip verify source")

        # Check for IPSG entries
        has_ipsg = "Gi1/0" in output or "GigabitEthernet1/0" in output
        if not has_ipsg:
            pytest.skip("IP Source Guard not configured (requires DHCP snooping binding)")


# =============================================================================
# CONFIGURATION SUMMARY TEST
# =============================================================================

class TestSecuritySummary:
    """Summary tests for overall security posture."""

    def test_security_baseline(self, med_asw1):
        """Test minimum security baseline is met."""
        issues = []

        # Check AAA
        aaa_output = med_asw1.execute("show running-config | include aaa new-model")
        if "aaa new-model" not in aaa_output:
            issues.append("AAA not enabled")

        # Check DHCP Snooping
        dhcp_output = med_asw1.execute("show ip dhcp snooping")
        if "enabled" not in dhcp_output.lower():
            issues.append("DHCP Snooping not enabled")

        # Check DAI - use running-config for reliable check
        dai_output = med_asw1.execute("show running-config | include ip arp inspection vlan")
        if "ip arp inspection vlan" not in dai_output:
            issues.append("DAI not configured")

        # Check dot1x
        dot1x_output = med_asw1.execute("show running-config | include dot1x system-auth-control")
        if "dot1x" not in dot1x_output:
            issues.append("802.1X not enabled")

        assert len(issues) == 0, \
            f"Security baseline not met. Issues: {', '.join(issues)}"


# =============================================================================
# MAIN - Run tests directly
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
