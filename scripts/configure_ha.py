#!/usr/bin/env python3
"""
Configure HSRP High Availability on E-University PE Router Pairs

This script configures HSRP (Hot Standby Router Protocol) on the PE router pairs
to provide gateway redundancy for customer-facing VRF interfaces.

Design:
- HSRP runs on GigabitEthernet3 subinterfaces (the existing inter-PE link)
- dot1q tagged HSRP traffic rides over the same physical link as native OSPF/MPLS
- No additional L2 switch required between PE pairs
- HSRP provides a virtual IP that floats between PE1 (active) and PE2 (standby)
- PE1 has higher priority (110) and preempt enabled
- PE2 has default priority (100) as standby

HSRP Groups by VRF:
- VLAN 100 / Group 100: STUDENT-NET
- VLAN 200 / Group 200: STAFF-NET
- VLAN 300 / Group 300: RESEARCH-NET
- VLAN 400 / Group 400: MEDICAL-NET (MED campus only)
- VLAN 500 / Group 500: GUEST-NET
"""

import os

from dotenv import load_dotenv
from genie.testbed import load

# Load environment variables from .env file
load_dotenv()

# HSRP Configuration per campus
# Format: {device_name: {vlan: (vrf, ip_address, virtual_ip, priority, is_preempt)}}
# Note: Testbed uses EDGE naming, actual hostnames are PE (learn_hostname handles this)
HSRP_CONFIG = {
    # Main Campus
    'EUNIV-MAIN-EDGE1': {  # Actual hostname: EUNIV-MAIN-PE1
        100: ('STUDENT-NET', '10.100.1.2', '10.100.1.1', 110, True),
        200: ('STAFF-NET', '10.100.2.2', '10.100.2.1', 110, True),
        300: ('RESEARCH-NET', '10.100.3.2', '10.100.3.1', 110, True),
        500: ('GUEST-NET', '10.100.5.2', '10.100.5.1', 110, True),
    },
    'EUNIV-MAIN-EDGE2': {  # Actual hostname: EUNIV-MAIN-PE2
        100: ('STUDENT-NET', '10.100.1.3', '10.100.1.1', 100, False),
        200: ('STAFF-NET', '10.100.2.3', '10.100.2.1', 100, False),
        300: ('RESEARCH-NET', '10.100.3.3', '10.100.3.1', 100, False),
        500: ('GUEST-NET', '10.100.5.3', '10.100.5.1', 100, False),
    },

    # Medical Campus
    'EUNIV-MED-EDGE1': {  # Actual hostname: EUNIV-MED-PE1
        200: ('STAFF-NET', '10.200.2.2', '10.200.2.1', 110, True),
        300: ('RESEARCH-NET', '10.200.3.2', '10.200.3.1', 110, True),
        400: ('MEDICAL-NET', '10.200.4.2', '10.200.4.1', 110, True),
        500: ('GUEST-NET', '10.200.5.2', '10.200.5.1', 110, True),
    },
    'EUNIV-MED-EDGE2': {  # Actual hostname: EUNIV-MED-PE2
        200: ('STAFF-NET', '10.200.2.3', '10.200.2.1', 100, False),
        300: ('RESEARCH-NET', '10.200.3.3', '10.200.3.1', 100, False),
        400: ('MEDICAL-NET', '10.200.4.3', '10.200.4.1', 100, False),
        500: ('GUEST-NET', '10.200.5.3', '10.200.5.1', 100, False),
    },

    # Research Campus (using 10.103.x.x to avoid 10.300 which is invalid)
    'EUNIV-RES-EDGE1': {  # Actual hostname: EUNIV-RES-PE1
        200: ('STAFF-NET', '10.103.2.2', '10.103.2.1', 110, True),
        300: ('RESEARCH-NET', '10.103.3.2', '10.103.3.1', 110, True),
        500: ('GUEST-NET', '10.103.5.2', '10.103.5.1', 110, True),
    },
    'EUNIV-RES-EDGE2': {  # Actual hostname: EUNIV-RES-PE2
        200: ('STAFF-NET', '10.103.2.3', '10.103.2.1', 100, False),
        300: ('RESEARCH-NET', '10.103.3.3', '10.103.3.1', 100, False),
        500: ('GUEST-NET', '10.103.5.3', '10.103.5.1', 100, False),
    },
}

# Peer mapping for descriptions
PEER_MAP = {
    'EUNIV-MAIN-EDGE1': 'EUNIV-MAIN-PE2',
    'EUNIV-MAIN-EDGE2': 'EUNIV-MAIN-PE1',
    'EUNIV-MED-EDGE1': 'EUNIV-MED-PE2',
    'EUNIV-MED-EDGE2': 'EUNIV-MED-PE1',
    'EUNIV-RES-EDGE1': 'EUNIV-RES-PE2',
    'EUNIV-RES-EDGE2': 'EUNIV-RES-PE1',
}


def build_hsrp_config(device_name: str) -> list:
    """Build the HSRP configuration for a device as list of config blocks.

    HSRP runs on Gi3 subinterfaces (the existing inter-PE link) using dot1q
    encapsulation. This allows HSRP peers to communicate without requiring
    an additional L2 switch between PE pairs.
    """
    if device_name not in HSRP_CONFIG:
        return []

    config_blocks = []
    vlans = HSRP_CONFIG[device_name]
    peer = PEER_MAP.get(device_name, 'peer')

    # Configure each subinterface with HSRP on Gi3 (inter-PE link)
    for vlan, (vrf, ip_addr, virtual_ip, priority, preempt) in sorted(vlans.items()):
        block = [
            f"interface GigabitEthernet3.{vlan}",
            f" description {vrf} Gateway (HSRP with {peer})",
            f" encapsulation dot1Q {vlan}",
            f" vrf forwarding {vrf}",
            f" ip address {ip_addr} 255.255.255.0",
            " standby version 2",
            f" standby {vlan} ip {virtual_ip}",
            f" standby {vlan} priority {priority}",
        ]
        if preempt:
            block.append(f" standby {vlan} preempt delay minimum 30")
        block.append(f" standby {vlan} timers 1 3")
        config_blocks.append(block)

    return config_blocks


def configure_hsrp(testbed_file: str, dry_run: bool = False):
    """Configure HSRP on all PE devices."""

    # Credentials loaded from .env via dotenv

    print("Loading testbed...")
    testbed = load(testbed_file)

    results = {'success': [], 'failed': [], 'skipped': []}

    for device_name in HSRP_CONFIG.keys():
        print(f"\n{'='*60}")
        print(f"Device: {device_name}")
        print(f"{'='*60}")

        if device_name not in testbed.devices:
            print(f"  WARNING: {device_name} not in testbed, skipping")
            results['skipped'].append(device_name)
            continue

        device = testbed.devices[device_name]
        config_blocks = build_hsrp_config(device_name)

        if not config_blocks:
            print(f"  No HSRP configuration for {device_name}")
            results['skipped'].append(device_name)
            continue

        try:
            print(f"  Connecting to {device_name}...")
            device.connect(log_stdout=False)

            print("  Configuration to apply:")
            for block in config_blocks:
                for line in block:
                    print(f"    {line}")
                print()

            if dry_run:
                print("  [DRY RUN] Would apply configuration")
            else:
                print("  Applying configuration...")
                # Apply each config block separately to avoid issues
                for block in config_blocks:
                    config_str = "\n".join(block)
                    device.configure(config_str)
                print("  Configuration applied successfully")

            # Verify HSRP status
            if not dry_run:
                print("  Verifying HSRP status...")
                output = device.execute("show standby brief")
                if output.strip():
                    print("  HSRP Status:")
                    for line in output.splitlines():
                        print(f"    {line}")
                else:
                    print("  No HSRP groups found yet")

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
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Successful: {len(results['success'])} - {', '.join(results['success']) or 'None'}")
    print(f"  Failed:     {len(results['failed'])} - {', '.join(results['failed']) or 'None'}")
    print(f"  Skipped:    {len(results['skipped'])} - {', '.join(results['skipped']) or 'None'}")

    return results


def verify_hsrp(testbed_file: str):
    """Verify HSRP status on all PE devices."""

    # Credentials loaded from .env via dotenv

    print("Loading testbed...")
    testbed = load(testbed_file)

    print("\nHSRP Status:")
    print("="*80)

    for device_name in HSRP_CONFIG.keys():
        if device_name not in testbed.devices:
            continue

        device = testbed.devices[device_name]

        try:
            device.connect(log_stdout=False)

            print(f"\n{device_name}:")
            print("-" * 40)

            # Show brief status
            output = device.execute("show standby brief")
            if output.strip():
                for line in output.splitlines():
                    print(f"  {line}")
            else:
                print("  No HSRP groups configured")

            device.disconnect()

        except Exception as e:
            print(f"\n{device_name}: ERROR - {e}")


def show_design():
    """Display the HSRP design without connecting to devices."""
    print("\nHSRP High Availability Design")
    print("="*80)
    print()
    print("Interface: GigabitEthernet3 subinterfaces (inter-PE link)")
    print("Protocol: HSRPv2 with dot1q encapsulation")
    print()
    print("PE Pairs and HSRP Configuration:")
    print("-"*80)

    for device_name, vlans in HSRP_CONFIG.items():
        print(f"\n{device_name}:")
        print(f"  {'VLAN':<8} {'VRF':<15} {'IP Address':<16} {'Virtual IP':<16} {'Priority':<10} {'Preempt'}")
        print(f"  {'-'*8} {'-'*15} {'-'*16} {'-'*16} {'-'*10} {'-'*7}")
        for vlan, (vrf, ip, vip, pri, preempt) in sorted(vlans.items()):
            print(f"  {vlan:<8} {vrf:<15} {ip:<16} {vip:<16} {pri:<10} {'Yes' if preempt else 'No'}")

    print("\n" + "="*80)
    print("HSRP Timers: Hello 1s, Hold 3s")
    print("Preempt Delay: 30 seconds (PE1 only)")
    print("="*80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Configure HSRP on E-University PE routers")
    parser.add_argument("--testbed", default="../pyats/testbed.yaml", help="Testbed YAML file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be configured without applying")
    parser.add_argument("--verify-only", action="store_true", help="Only verify HSRP status, don't configure")
    parser.add_argument("--show-design", action="store_true", help="Display the HSRP design")

    args = parser.parse_args()

    if args.show_design:
        show_design()
    elif args.verify_only:
        verify_hsrp(args.testbed)
    else:
        configure_hsrp(args.testbed, dry_run=args.dry_run)
