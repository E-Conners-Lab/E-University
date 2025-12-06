#!/usr/bin/env python3
"""
Deploy IPv6 Dual-Stack Configuration on E-University Network

This script deploys IPv6 configuration to all network devices:
- IPv6 unicast routing
- IPv6 addresses on Loopback0 and P2P interfaces
- OSPFv3 for IPv6 IGP routing
- BGP IPv6 unicast address family
- VRF IPv6 address family on PE routers (VPNv6)

Usage:
    # Dry run (show configuration without applying)
    python deploy_ipv6.py --testbed ../pyats/testbed.yaml --dry-run

    # Deploy to all devices
    python deploy_ipv6.py --testbed ../pyats/testbed.yaml

    # Deploy to specific device
    python deploy_ipv6.py --testbed ../pyats/testbed.yaml --device EUNIV-CORE1

    # Verify only (check current IPv6 status)
    python deploy_ipv6.py --testbed ../pyats/testbed.yaml --verify-only
"""

import os
import sys
from pathlib import Path

from genie.testbed import load

# Add scripts directory to path for importing intent_data
sys.path.insert(0, str(Path(__file__).parent))
from intent_data import DEVICES, VRFS


def generate_ipv6_config(device_name: str) -> list[str]:
    """Generate IPv6 configuration lines for a device."""

    device_data = DEVICES.get(device_name)
    if not device_data:
        return []

    config_lines = []
    loopback_ipv6 = device_data.get("loopback_ipv6")

    if not loopback_ipv6:
        return []

    # Enable IPv6 unicast routing globally
    config_lines.append("ipv6 unicast-routing")

    # Configure OSPFv3 process first (must exist before assigning to interfaces)
    config_lines.append("ipv6 router ospf 1")
    config_lines.append(f"router-id {device_data['loopback_ip']}")
    config_lines.append("auto-cost reference-bandwidth 100000")
    config_lines.append("passive-interface Loopback0")
    config_lines.append("passive-interface GigabitEthernet1")
    config_lines.append("log-adjacency-changes detail")
    config_lines.append("exit")

    # Configure Loopback0 with IPv6
    config_lines.append("interface Loopback0")
    config_lines.append(f"ipv6 address {loopback_ipv6}/128")
    config_lines.append("ipv6 ospf 1 area 0")
    config_lines.append("exit")

    # Configure P2P interfaces with IPv6
    for intf in device_data.get("interfaces", []):
        ipv6_addr = intf.get("ipv6")
        if ipv6_addr:
            config_lines.append(f"interface {intf['name']}")
            config_lines.append(f"ipv6 address {ipv6_addr}")
            config_lines.append("ipv6 ospf 1 area 0")
            config_lines.append("ipv6 ospf network point-to-point")
            config_lines.append("exit")

    # Configure BGP IPv6 address family
    bgp_neighbors_v6 = []
    for neighbor in device_data.get("bgp_neighbors", []):
        if "ipv6" in neighbor:
            bgp_neighbors_v6.append(neighbor)

    if bgp_neighbors_v6:
        config_lines.append(f"router bgp {device_data['bgp_asn']}")

        # Add neighbors for IPv6 (same as IPv4 but for the ipv6 unicast AF)
        for neighbor in bgp_neighbors_v6:
            config_lines.append(f"neighbor {neighbor['ipv6']} remote-as {neighbor['remote_as']}")
            config_lines.append(f"neighbor {neighbor['ipv6']} update-source Loopback0")
            config_lines.append(f"neighbor {neighbor['ipv6']} description {neighbor['description']} IPv6")

        # IPv6 unicast address family
        config_lines.append("address-family ipv6 unicast")
        for neighbor in bgp_neighbors_v6:
            config_lines.append(f"neighbor {neighbor['ipv6']} activate")
            config_lines.append(f"neighbor {neighbor['ipv6']} send-community both")
            # Route reflector clients
            if device_data.get("is_route_reflector"):
                config_lines.append(f"neighbor {neighbor['ipv6']} route-reflector-client")
        config_lines.append("exit-address-family")

        # VPNv6 address family (uses IPv4 neighbor addresses for update-source loopback peering)
        if device_data.get("is_route_reflector") or device_data.get("vrfs"):
            config_lines.append("address-family vpnv6 unicast")
            for v4_neighbor in device_data.get("bgp_neighbors", []):
                config_lines.append(f"neighbor {v4_neighbor['ip']} activate")
                config_lines.append(f"neighbor {v4_neighbor['ip']} send-community extended")
                if device_data.get("is_route_reflector"):
                    config_lines.append(f"neighbor {v4_neighbor['ip']} route-reflector-client")
            config_lines.append("exit-address-family")
        config_lines.append("exit")

    # Configure VRF IPv6 address family on PE routers
    vrf_list = device_data.get("vrfs", [])
    if vrf_list:
        for vrf_name in vrf_list:
            vrf_data = VRFS.get(vrf_name, {})
            rt = vrf_data.get("rt", "65000:999")

            # Add IPv6 address family to VRF definition
            config_lines.append(f"vrf definition {vrf_name}")
            config_lines.append("address-family ipv6")
            config_lines.append(f"route-target import {rt}")
            config_lines.append(f"route-target export {rt}")
            config_lines.append("exit-address-family")
            config_lines.append("exit")

        # BGP VRF IPv6 address families
        config_lines.append(f"router bgp {device_data['bgp_asn']}")
        for vrf_name in vrf_list:
            config_lines.append(f"address-family ipv6 vrf {vrf_name}")
            config_lines.append("redistribute connected")
            config_lines.append("exit-address-family")
        config_lines.append("exit")

    return config_lines


def deploy_ipv6(testbed_file: str, dry_run: bool = False, device_filter: str = None):
    """Deploy IPv6 configuration to devices."""

    # Set credentials from environment
    os.environ.setdefault('DEVICE_USERNAME', 'admin')

    print("Loading testbed...")
    testbed = load(testbed_file)

    results = {'success': [], 'failed': [], 'skipped': []}

    # Determine which devices to configure
    devices_to_configure = list(DEVICES.keys())
    if device_filter:
        devices_to_configure = [d for d in devices_to_configure if device_filter in d]

    for device_name in devices_to_configure:
        print(f"\n{'='*60}")
        print(f"Device: {device_name}")
        print(f"{'='*60}")

        # Generate configuration
        config_lines = generate_ipv6_config(device_name)

        if not config_lines:
            print(f"  No IPv6 configuration for {device_name}")
            results['skipped'].append(device_name)
            continue

        # Check if device exists in testbed
        if device_name not in testbed.devices:
            print(f"  WARNING: {device_name} not in testbed, skipping")
            results['skipped'].append(device_name)
            continue

        device = testbed.devices[device_name]

        print("  Configuration to apply:")
        for line in config_lines[:30]:  # Show first 30 lines
            print(f"    {line}")
        if len(config_lines) > 30:
            print(f"    ... ({len(config_lines) - 30} more lines)")

        if dry_run:
            print("  [DRY RUN] Would apply configuration")
            results['success'].append(device_name)
            continue

        try:
            print(f"  Connecting to {device_name}...")
            device.connect(log_stdout=False)

            print("  Applying configuration...")
            config_str = "\n".join(config_lines)
            device.configure(config_str)
            print("  Configuration applied successfully")

            # Quick verification
            print("  Verifying IPv6 status...")
            output = device.execute("show ipv6 interface brief | include up")
            ipv6_count = len([l for l in output.splitlines() if l.strip()])
            print(f"  IPv6-enabled interfaces: {ipv6_count}")

            device.disconnect()
            results['success'].append(device_name)

        except Exception as e:
            print(f"  ERROR: {e}")
            results['failed'].append(device_name)
            try:
                device.disconnect()
            except:
                pass

    # Summary
    print(f"\n{'='*60}")
    print("DEPLOYMENT SUMMARY")
    print(f"{'='*60}")
    print(f"  Successful: {len(results['success'])} - {', '.join(results['success']) or 'None'}")
    print(f"  Failed:     {len(results['failed'])} - {', '.join(results['failed']) or 'None'}")
    print(f"  Skipped:    {len(results['skipped'])} - {', '.join(results['skipped']) or 'None'}")

    if not dry_run and results['success']:
        print("\n  Next steps:")
        print("  1. Run validation: pyats run job pyats/ipv6_job.py --testbed-file pyats/testbed.yaml")
        print("  2. Verify OSPFv3: show ipv6 ospf neighbor")
        print("  3. Verify BGP: show bgp ipv6 unicast summary")

    return results


def verify_ipv6(testbed_file: str):
    """Verify IPv6 status on all devices."""

    os.environ.setdefault('DEVICE_USERNAME', 'admin')

    print("Loading testbed...")
    testbed = load(testbed_file)

    print("\nIPv6 Status Verification:")
    print("="*80)

    for device_name in DEVICES.keys():
        if device_name not in testbed.devices:
            continue

        device_data = DEVICES[device_name]
        if not device_data.get("loopback_ipv6"):
            continue

        device = testbed.devices[device_name]

        try:
            device.connect(log_stdout=False)

            print(f"\n{device_name}:")
            print("-" * 40)

            # Check IPv6 interfaces
            output = device.execute("show ipv6 interface brief")
            ipv6_intfs = [l for l in output.splitlines() if "2001:" in l]
            print(f"  IPv6 Interfaces: {len(ipv6_intfs)}")

            # Check OSPFv3 neighbors
            output = device.execute("show ipv6 ospf neighbor")
            ospf_neighbors = len([l for l in output.splitlines() if "FULL" in l])
            print(f"  OSPFv3 Neighbors (FULL): {ospf_neighbors}")

            # Check BGP IPv6 sessions
            output = device.execute("show bgp ipv6 unicast summary")
            if "not active" not in output.lower():
                bgp_established = len([l for l in output.splitlines()
                                      if l.strip() and l.strip()[0].isdigit()])
                print(f"  BGP IPv6 Sessions: {bgp_established}")
            else:
                print("  BGP IPv6: Not active")

            device.disconnect()

        except Exception as e:
            print(f"\n{device_name}: ERROR - {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Deploy IPv6 on E-University network")
    parser.add_argument("--testbed", default="../pyats/testbed.yaml", help="Testbed YAML file")
    parser.add_argument("--dry-run", action="store_true", help="Show config without applying")
    parser.add_argument("--device", type=str, help="Deploy to specific device only")
    parser.add_argument("--verify-only", action="store_true", help="Only verify IPv6 status")

    args = parser.parse_args()

    if args.verify_only:
        verify_ipv6(args.testbed)
    else:
        deploy_ipv6(args.testbed, dry_run=args.dry_run, device_filter=args.device)
