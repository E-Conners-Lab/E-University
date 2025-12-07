#!/usr/bin/env python3
"""
E-University Network - Edge Router Access Layer SVI Configuration
==================================================================
Deploys VLAN subinterfaces and HSRP gateway redundancy on Edge routers
for the access layer (downstream to L2 access switches).

Features configured:
- Gi4 subinterfaces for each access VLAN (10, 20, 30, 40)
- VRF assignment per subinterface
- HSRP for gateway redundancy with load balancing
- DHCP relay (ip helper-address)

Usage:
    python configure_edge_svi.py --campus main [--dry-run]
    python configure_edge_svi.py --campus medical [--dry-run]
    python configure_edge_svi.py --campus research [--dry-run]
    python configure_edge_svi.py --campus all [--dry-run]

Examples:
    python configure_edge_svi.py --campus main --dry-run
    python configure_edge_svi.py --campus all
"""

import argparse
import os
import sys

from dotenv import load_dotenv
from genie.testbed import load as load_testbed

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intent_data import (
    ACCESS_LAYER_SVIS,
    ACCESS_DOWNSTREAM_INTERFACE,
    DHCP_SERVER_IP,
    HSRP_CONFIG,
    get_svi_ip,
)

# Load environment variables
load_dotenv()


def get_router_role(device_name: str) -> str:
    """Determine if device is edge1 or edge2 from its name."""
    if "EDGE1" in device_name or "PE1" in device_name:
        return "edge1"
    elif "EDGE2" in device_name or "PE2" in device_name:
        return "edge2"
    else:
        raise ValueError(f"Cannot determine role from device: {device_name}")


def generate_remove_gi4_ip_config() -> str:
    """Generate config to remove existing IP from Gi4 base interface."""
    return f"""! Remove existing IP from {ACCESS_DOWNSTREAM_INTERFACE}
interface {ACCESS_DOWNSTREAM_INTERFACE}
  no ip address
  no shutdown
"""


def generate_subinterface_config(
    campus: str,
    vlan_id: int,
    vlan_config: dict,
    router_role: str,
) -> str:
    """
    Generate configuration for a single VLAN subinterface.

    Args:
        campus: Campus name (main, medical, research)
        vlan_id: VLAN ID (10, 20, 30, 40)
        vlan_config: VLAN configuration dict from intent_data
        router_role: "edge1" or "edge2"
    """
    interface = f"{ACCESS_DOWNSTREAM_INTERFACE}.{vlan_id}"
    vrf = vlan_config["vrf"]
    ip_addr = get_svi_ip(campus, vlan_id, router_role)
    vip = get_svi_ip(campus, vlan_id, "vip")
    hsrp_group = vlan_config["hsrp_group"]
    hsrp_active = vlan_config["hsrp_active"]

    # Determine HSRP priority based on whether this router is active for this VLAN
    if hsrp_active == router_role:
        hsrp_priority = HSRP_CONFIG["priority_active"]
    else:
        hsrp_priority = HSRP_CONFIG["priority_standby"]

    config_lines = [
        f"! === VLAN {vlan_id} ({vlan_config['name']}) ===",
        f"interface {interface}",
        f"  description Access Layer - VLAN {vlan_id} {vlan_config['name']}",
        f"  encapsulation dot1Q {vlan_id}",
        f"  vrf forwarding {vrf}",
        f"  ip address {ip_addr} 255.255.255.0",
        f"  ip helper-address {DHCP_SERVER_IP}",
        f"  no shutdown",
        "",
        f"  ! HSRP Configuration",
        f"  standby version {HSRP_CONFIG['version']}",
        f"  standby {hsrp_group} ip {vip}",
        f"  standby {hsrp_group} priority {hsrp_priority}",
        f"  standby {hsrp_group} timers {HSRP_CONFIG['hello_interval']} {HSRP_CONFIG['hold_time']}",
    ]

    if HSRP_CONFIG["preempt"]:
        config_lines.append(f"  standby {hsrp_group} preempt")

    config_lines.append("")

    return "\n".join(config_lines)


def generate_full_config(campus: str, device_name: str) -> str:
    """Generate complete SVI + HSRP configuration for an Edge router."""
    config = ACCESS_LAYER_SVIS[campus]
    router_role = get_router_role(device_name)

    sections = [
        "!" + "=" * 70,
        f"! Access Layer SVI Configuration for {device_name}",
        f"! Campus: {campus.upper()}, Role: {router_role.upper()}",
        "!" + "=" * 70,
        "",
        generate_remove_gi4_ip_config(),
    ]

    for vlan_id, vlan_config in config["vlans"].items():
        sections.append(
            generate_subinterface_config(campus, vlan_id, vlan_config, router_role)
        )

    sections.append("! === End of Configuration ===")

    return "\n".join(sections)


def deploy_to_campus(campus: str, dry_run: bool = False):
    """Deploy SVI configuration to both Edge routers in a campus."""
    if campus not in ACCESS_LAYER_SVIS:
        print(f"Error: Unknown campus '{campus}'")
        print(f"Available: {', '.join(ACCESS_LAYER_SVIS.keys())}")
        sys.exit(1)

    config = ACCESS_LAYER_SVIS[campus]
    edge_routers = [config["edge1"], config["edge2"]]

    # Load testbed
    testbed_path = os.path.join(
        os.path.dirname(__file__), "..", "pyats", "testbed_l2_security.yaml"
    )
    testbed = load_testbed(testbed_path)

    for device_name in edge_routers:
        print(f"\n{'=' * 60}")
        print(f"Processing {device_name}")
        print("=" * 60)

        # Generate configuration
        device_config = generate_full_config(campus, device_name)

        if dry_run:
            print("DRY RUN - Configuration that would be applied:")
            print("-" * 60)
            print(device_config)
            print("-" * 60)
            continue

        # Connect and deploy
        if device_name not in testbed.devices:
            print(f"Warning: {device_name} not found in testbed, skipping")
            continue

        device = testbed.devices[device_name]

        try:
            print(f"Connecting to {device_name}...")
            device.connect(log_stdout=False)

            print(f"Deploying configuration...")
            device.configure(device_config)

            print("Saving configuration...")
            device.execute("write memory")

            print(f"Successfully configured {device_name}")

        except Exception as e:
            print(f"Error configuring {device_name}: {e}")

        finally:
            if device.connected:
                device.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Access Layer SVI configuration to Edge routers"
    )
    parser.add_argument(
        "--campus",
        required=True,
        choices=["main", "medical", "research", "all"],
        help="Campus to configure (main, medical, research, or all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show configuration without applying",
    )

    args = parser.parse_args()

    if args.campus == "all":
        for campus in ACCESS_LAYER_SVIS.keys():
            deploy_to_campus(campus, args.dry_run)
    else:
        deploy_to_campus(args.campus, args.dry_run)

    print("\nDone!")


if __name__ == "__main__":
    main()
