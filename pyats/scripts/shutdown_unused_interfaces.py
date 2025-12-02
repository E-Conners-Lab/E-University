#!/usr/bin/env python3
"""
E-University Network - Shutdown Unused Interfaces Script

This script administratively shuts down all unused interfaces on network devices.
Unused interfaces are those that:
- Are currently down (operationally)
- Have no IP address configured
- Are not part of a channel-group
- Are not subinterfaces (e.g., Gi0/0.100)

This reduces security exposure and eliminates spurious alerts.

Usage:
    # Dry run - show what would be shutdown (default)
    python shutdown_unused_interfaces.py

    # Actually apply the changes
    python shutdown_unused_interfaces.py --apply

    # Target specific devices
    python shutdown_unused_interfaces.py --apply --devices EUNIV-CORE1 EUNIV-CORE2
"""

import os
import sys
import re
import argparse
from typing import Dict, List, Set

# pyATS imports
try:
    from pyats.topology import loader
    from unicon.core.errors import ConnectionError, SubCommandFailure
except ImportError:
    print("Error: pyATS not installed. Run: pip install pyats[full]")
    sys.exit(1)


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TESTBED_FILE = os.path.join(SCRIPT_DIR, "..", "testbed.yaml")
HOST_TESTBED_FILE = os.path.join(SCRIPT_DIR, "..", "host_testbed.yaml")


# Interface patterns to never shutdown
PROTECTED_PATTERNS = [
    r"^Loopback",
    r"^Null",
    r"^VoIP-Null",
    r"^Vlan",
    r"^Tunnel",
    r"^BVI",
    r"^Management",
    r"^mgmt",
    r"\.\d+$",  # Subinterfaces like Gi0/0.100
]


def is_protected_interface(if_name: str) -> bool:
    """Check if interface should never be shutdown."""
    for pattern in PROTECTED_PATTERNS:
        if re.search(pattern, if_name, re.IGNORECASE):
            return True
    return False


def get_interface_info(device) -> Dict[str, dict]:
    """Get detailed interface information from device."""
    interfaces = {}

    try:
        # Get interface brief to see status
        output = device.execute("show ip interface brief")

        for line in output.splitlines():
            # Skip header lines
            if "Interface" in line and "IP-Address" in line:
                continue
            if not line.strip():
                continue

            parts = line.split()
            if len(parts) >= 5:
                if_name = parts[0]
                ip_addr = parts[1]
                status = parts[4] if len(parts) > 4 else "unknown"
                protocol = parts[5] if len(parts) > 5 else "unknown"

                interfaces[if_name] = {
                    "ip_address": ip_addr if ip_addr != "unassigned" else None,
                    "status": status.lower(),
                    "protocol": protocol.lower(),
                    "has_config": False,
                    "in_channel_group": False,
                    "has_neighbor": False
                }
    except Exception as e:
        print(f"  Error getting interface brief: {e}")
        return interfaces

    # Check for interfaces with meaningful configuration
    try:
        output = device.execute("show running-config | section ^interface")
        current_if = None

        for line in output.splitlines():
            if line.startswith("interface "):
                current_if = line.replace("interface ", "").strip()
            elif current_if and line.strip():
                # Check for meaningful config (not just shutdown or description)
                line_lower = line.strip().lower()
                if current_if in interfaces:
                    # These configs indicate the interface is actively in use
                    # Note: description alone doesn't count as "in use"
                    meaningful_configs = [
                        "ip address",
                        "channel-group",
                        "switchport access",
                        "switchport trunk",
                        "encapsulation",
                        "service-policy",
                        "ip ospf",
                        "vrf forwarding",
                        "mpls ip",
                        "negotiation auto",  # indicates intended use
                    ]
                    for config in meaningful_configs:
                        if config in line_lower:
                            interfaces[current_if]["has_config"] = True
                            if "channel-group" in line_lower:
                                interfaces[current_if]["in_channel_group"] = True
                            break
    except Exception as e:
        print(f"  Error checking running config: {e}")

    # Check for CDP/LLDP neighbors
    try:
        output = device.execute("show cdp neighbors")
        for line in output.splitlines():
            for if_name in interfaces.keys():
                # CDP shows abbreviated interface names
                short_name = if_name.replace("GigabitEthernet", "Gig ")
                short_name = short_name.replace("FastEthernet", "Fas ")
                if short_name in line or if_name in line:
                    interfaces[if_name]["has_neighbor"] = True
    except Exception:
        pass  # CDP might not be enabled

    return interfaces


def get_unused_interfaces(interfaces: Dict[str, dict]) -> List[str]:
    """Identify interfaces that can be safely shutdown."""
    unused = []

    for if_name, info in interfaces.items():
        # Skip protected interfaces
        if is_protected_interface(if_name):
            continue

        # An interface is "unused" if:
        # 1. It's operationally down (protocol down)
        # 2. Has no IP address
        # 3. Has no CDP neighbors (nothing connected)
        # 4. Is not in a channel-group
        #
        # Note: We don't check has_config because even unused interfaces
        # might have default configs like "negotiation auto"

        is_unused = (
            info["protocol"] == "down" and
            info["ip_address"] is None and
            not info["has_neighbor"] and
            not info["in_channel_group"]
        )

        if is_unused:
            unused.append(if_name)

    return unused


def shutdown_interfaces(device, interfaces: List[str], dry_run: bool = True) -> Dict[str, str]:
    """Shutdown the specified interfaces."""
    results = {}

    if not interfaces:
        return results

    if dry_run:
        for if_name in interfaces:
            results[if_name] = "would shutdown (dry run)"
        return results

    # Build configuration
    config_lines = []
    for if_name in interfaces:
        config_lines.extend([
            f"interface {if_name}",
            " description UNUSED - Admin shutdown by automation",
            " shutdown"
        ])

    try:
        device.configure(config_lines)
        for if_name in interfaces:
            results[if_name] = "shutdown applied"
    except Exception as e:
        for if_name in interfaces:
            results[if_name] = f"error: {str(e)}"

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Shutdown unused interfaces on E-University network devices"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply changes (default is dry run)"
    )
    parser.add_argument(
        "--devices",
        nargs="+",
        help="Specific devices to process (default: all)"
    )
    parser.add_argument(
        "--skip-hosts",
        action="store_true",
        help="Skip HOST devices (traffic generators)"
    )

    args = parser.parse_args()
    dry_run = not args.apply

    print("=" * 70)
    print("E-University Network - Shutdown Unused Interfaces")
    print("=" * 70)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'APPLY CHANGES'}")
    print()

    # Load testbeds
    testbed = loader.load(TESTBED_FILE)

    if not args.skip_hosts and os.path.exists(HOST_TESTBED_FILE):
        host_testbed = loader.load(HOST_TESTBED_FILE)
        # Merge host devices
        for name, device in host_testbed.devices.items():
            testbed.add_device(device)

    # Filter devices if specified
    if args.devices:
        devices_to_process = [d for d in testbed.devices.values() if d.name in args.devices]
    else:
        devices_to_process = list(testbed.devices.values())

    total_shutdown = 0
    results_summary = {}

    for device in devices_to_process:
        print(f"\n{'='*50}")
        print(f"Processing: {device.name}")
        print(f"{'='*50}")

        try:
            print(f"  Connecting to {device.name}...")
            device.connect(log_stdout=False)

            print(f"  Gathering interface information...")
            interfaces = get_interface_info(device)

            if not interfaces:
                print(f"  No interfaces found, skipping")
                device.disconnect()
                continue

            print(f"  Found {len(interfaces)} interfaces")

            unused = get_unused_interfaces(interfaces)

            if unused:
                print(f"  Identified {len(unused)} unused interfaces:")
                for if_name in sorted(unused):
                    print(f"    - {if_name}")

                print(f"\n  {'Would shutdown' if dry_run else 'Shutting down'} interfaces...")
                results = shutdown_interfaces(device, unused, dry_run)

                results_summary[device.name] = {
                    "total_interfaces": len(interfaces),
                    "unused_interfaces": len(unused),
                    "interfaces": unused,
                    "results": results
                }
                total_shutdown += len(unused)
            else:
                print(f"  No unused interfaces found")
                results_summary[device.name] = {
                    "total_interfaces": len(interfaces),
                    "unused_interfaces": 0,
                    "interfaces": [],
                    "results": {}
                }

            device.disconnect()

        except Exception as e:
            print(f"  ERROR: {e}")
            results_summary[device.name] = {
                "error": str(e)
            }

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Devices processed: {len(results_summary)}")
    print(f"Total interfaces to shutdown: {total_shutdown}")

    if dry_run:
        print("\nThis was a DRY RUN. No changes were made.")
        print("Run with --apply to actually shutdown interfaces.")
    else:
        print("\nChanges have been applied.")
        print("Interfaces are now administratively shutdown.")

    print("\nPer-device breakdown:")
    for device_name, data in results_summary.items():
        if "error" in data:
            print(f"  {device_name}: ERROR - {data['error']}")
        else:
            print(f"  {device_name}: {data['unused_interfaces']} unused interfaces")


if __name__ == "__main__":
    main()
