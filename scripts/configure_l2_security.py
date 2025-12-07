#!/usr/bin/env python3
"""
E-University Network - Layer 2 Security Configuration Script
=============================================================
Deploys enterprise L2 security configuration to access switches.

Features configured:
- VLANs
- Trunk ports (with non-default native VLAN)
- AAA / RADIUS
- 802.1X port-based authentication
- DHCP Snooping
- Dynamic ARP Inspection (DAI)
- Port Security
- BPDU Guard / PortFast
- Storm Control

Usage:
    python configure_l2_security.py [--switch SWITCH_NAME] [--dry-run]

Examples:
    python configure_l2_security.py --switch EUNIV-MED-ASW1
    python configure_l2_security.py --switch EUNIV-MED-ASW1 --dry-run
"""

import argparse
import os
import sys

from dotenv import load_dotenv
from genie.testbed import load as load_testbed

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intent_data import (
    ACCESS_SWITCHES,
    L2_VLANS,
    L2_SECURITY,
    RADIUS_CONFIG,
    ENTERPRISE,
)

# Load environment variables
load_dotenv()


def generate_vlan_config() -> str:
    """Generate VLAN configuration."""
    config_lines = ["! === VLAN Configuration ==="]

    for vlan_id, vlan_info in L2_VLANS.items():
        config_lines.append(f"vlan {vlan_id}")
        config_lines.append(f"  name {vlan_info['name']}")

    return "\n".join(config_lines)


def generate_aaa_radius_config() -> str:
    """Generate AAA and RADIUS configuration for 802.1X."""
    config_lines = [
        "! === AAA and RADIUS Configuration ===",
        "aaa new-model",
        "",
        "! RADIUS Server",
        f"radius server {RADIUS_CONFIG['server_name']}",
        f"  address ipv4 {RADIUS_CONFIG['server_ip']} auth-port {RADIUS_CONFIG['auth_port']} acct-port {RADIUS_CONFIG['acct_port']}",
        f"  key {RADIUS_CONFIG['secret']}",
        f"  timeout {RADIUS_CONFIG['timeout']}",
        f"  retransmit {RADIUS_CONFIG['retransmit']}",
        "",
        "! AAA Server Group",
        "aaa group server radius RADIUS-SERVERS",
        f"  server name {RADIUS_CONFIG['server_name']}",
        "",
        "! AAA Authentication",
        "aaa authentication dot1x default group RADIUS-SERVERS",
        "aaa authentication login default local",
        "",
        "! AAA Authorization",
        "aaa authorization network default group RADIUS-SERVERS",
        "aaa authorization exec default local",
        "",
        "! AAA Accounting",
        "aaa accounting dot1x default start-stop group RADIUS-SERVERS",
        "",
        "! Enable 802.1X globally",
        "dot1x system-auth-control",
    ]

    return "\n".join(config_lines)


def generate_dhcp_snooping_config() -> str:
    """Generate DHCP Snooping configuration."""
    vlans = ",".join(str(v) for v in L2_SECURITY["dhcp_snooping_vlans"])

    config_lines = [
        "! === DHCP Snooping Configuration ===",
        "ip dhcp snooping",
        f"ip dhcp snooping vlan {vlans}",
        "ip dhcp snooping database flash:dhcp_snooping.db",
        "no ip dhcp snooping information option",
    ]

    return "\n".join(config_lines)


def generate_dai_config() -> str:
    """Generate Dynamic ARP Inspection configuration."""
    vlans = ",".join(str(v) for v in L2_SECURITY["dai_vlans"])

    config_lines = [
        "! === Dynamic ARP Inspection Configuration ===",
        f"ip arp inspection vlan {vlans}",
        "ip arp inspection validate src-mac dst-mac ip",
    ]

    return "\n".join(config_lines)


def generate_trunk_port_config(switch_name: str) -> str:
    """Generate trunk port configuration."""
    switch = ACCESS_SWITCHES[switch_name]
    config_lines = ["! === Trunk Port Configuration ==="]

    for uplink in switch["uplinks"]:
        config_lines.extend([
            f"interface {uplink['interface']}",
            f"  description {uplink['description']}",
            "  switchport mode trunk",
            f"  switchport trunk allowed vlan {uplink['allowed_vlans']}",
            f"  switchport trunk native vlan {uplink['native_vlan']}",
            "  switchport nonegotiate",
            "  ! DHCP Snooping - trust uplinks",
            "  ip dhcp snooping trust",
            "  ! DAI - trust uplinks",
            "  ip arp inspection trust",
            "  ! STP Protection",
            "  spanning-tree guard root",
            "  no shutdown",
        ])

    return "\n".join(config_lines)


def generate_access_port_config(switch_name: str) -> str:
    """Generate access port configuration with security features."""
    switch = ACCESS_SWITCHES[switch_name]
    security = L2_SECURITY
    dot1x_settings = security["dot1x"]
    port_sec = security["port_security"]
    storm = security["storm_control"]

    config_lines = ["! === Access Port Configuration ==="]

    for port in switch["access_ports"]:
        config_lines.extend([
            f"interface {port['interface']}",
            f"  description {port['description']}",
            "  switchport mode access",
            f"  switchport access vlan {port['vlan']}",
            "",
            "  ! Spanning Tree Protection",
            "  spanning-tree portfast",
            "  spanning-tree bpduguard enable",
            "",
            "  ! Storm Control",
            f"  storm-control broadcast level {storm['broadcast']}",
            f"  storm-control multicast level {storm['multicast']}",
            f"  storm-control unicast level {storm['unicast']}",
            "  storm-control action trap",
        ])

        # 802.1X configuration (only for dot1x-enabled ports)
        if port.get("dot1x", False):
            config_lines.extend([
                "",
                "  ! 802.1X Authentication",
                "  authentication port-control auto",
                f"  authentication host-mode {dot1x_settings['host_mode']}",
                "  authentication periodic",
                f"  authentication timer reauthenticate {dot1x_settings['reauth_period']}",
                "  authentication violation restrict",
                "  dot1x pae authenticator",
                f"  dot1x timeout tx-period {dot1x_settings['tx_period']}",
                f"  dot1x timeout quiet-period {dot1x_settings['quiet_period']}",
                "",
                "  ! Port Security (with 802.1X)",
                "  switchport port-security",
                f"  switchport port-security maximum {port_sec['max_mac_addresses']}",
                f"  switchport port-security violation {port_sec['violation_action']}",
                "",
                "  ! IP Source Guard (requires DHCP snooping)",
                "  ip verify source",
            ])
        else:
            # Static ports (like RADIUS server) - no 802.1X but still secure
            config_lines.extend([
                "",
                "  ! Port Security (static port)",
                "  switchport port-security",
                f"  switchport port-security maximum {port_sec['max_mac_addresses']}",
                f"  switchport port-security violation {port_sec['violation_action']}",
            ])

        config_lines.append("  no shutdown")
        config_lines.append("")

    return "\n".join(config_lines)


def generate_global_security_config() -> str:
    """Generate global security hardening configuration."""
    config_lines = [
        "! === Global Security Hardening ===",
        "",
        "! Disable unused services",
        "no ip http server",
        "no ip http secure-server",
        "no ip finger",
        "no ip bootp server",
        "no service pad",
        "no service tcp-small-servers",
        "no service udp-small-servers",
        "",
        "! Enable STP features globally",
        "spanning-tree mode rapid-pvst",
        "spanning-tree portfast default",
        "spanning-tree portfast bpduguard default",
        "spanning-tree extend system-id",
        "",
        "! Logging",
        "logging buffered 16384 informational",
        "logging console informational",
        "",
        "! LLDP for network visibility",
        "lldp run",
    ]

    return "\n".join(config_lines)


def generate_full_config(switch_name: str) -> str:
    """Generate complete L2 security configuration for a switch."""
    config_sections = [
        "! " + "=" * 70,
        f"! E-University L2 Security Configuration for {switch_name}",
        "! " + "=" * 70,
        "",
        generate_vlan_config(),
        "",
        generate_aaa_radius_config(),
        "",
        generate_dhcp_snooping_config(),
        "",
        generate_dai_config(),
        "",
        generate_global_security_config(),
        "",
        generate_trunk_port_config(switch_name),
        "",
        generate_access_port_config(switch_name),
        "",
        "! === End of Configuration ===",
    ]

    return "\n".join(config_sections)


def deploy_config(switch_name: str, dry_run: bool = False):
    """Deploy configuration to the switch."""
    if switch_name not in ACCESS_SWITCHES:
        print(f"Error: Switch '{switch_name}' not found in ACCESS_SWITCHES")
        print(f"Available switches: {', '.join(ACCESS_SWITCHES.keys())}")
        sys.exit(1)

    # Generate configuration
    config = generate_full_config(switch_name)

    if dry_run:
        print("=" * 70)
        print("DRY RUN - Configuration that would be applied:")
        print("=" * 70)
        print(config)
        print("=" * 70)
        print("DRY RUN - No changes made to device")
        return

    # Load testbed
    testbed_path = os.path.join(
        os.path.dirname(__file__), "..", "pyats", "testbed_l2_security.yaml"
    )
    testbed = load_testbed(testbed_path)

    # Connect to switch
    print(f"Connecting to {switch_name}...")
    device = testbed.devices[switch_name]
    device.connect(log_stdout=False)

    try:
        print(f"Deploying L2 security configuration to {switch_name}...")

        # Apply configuration
        device.configure(config)

        print("Configuration applied successfully!")

        # Save configuration
        print("Saving configuration...")
        device.execute("write memory")

        print(f"L2 security configuration deployed to {switch_name}")

    except Exception as e:
        print(f"Error deploying configuration: {e}")
        sys.exit(1)

    finally:
        device.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description="Deploy L2 security configuration to access switches"
    )
    parser.add_argument(
        "--switch",
        required=True,
        help="Switch name (e.g., EUNIV-MED-ASW1)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show configuration without applying",
    )

    args = parser.parse_args()

    deploy_config(args.switch, args.dry_run)


if __name__ == "__main__":
    main()
