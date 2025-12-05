#!/usr/bin/env python3
"""
Configure HSRP on E-University Edge Routers

HSRP Design:
- Interface: GigabitEthernet3 subinterfaces (Gi3.100, Gi3.200, etc.)
- IP Scheme: 10.{vlan}.{campus}.0/24
  - Campus: Main=1, Med=2, Res=3
  - EDGE1 IP: .1, EDGE2 IP: .2, Virtual IP: .254
- Load Balancing:
  - EDGE1 Active: VLAN 100 (STUDENT), 300 (RESEARCH) - priority 150
  - EDGE2 Active: VLAN 200 (STAFF), 400 (MEDICAL), 500 (GUEST) - priority 150
- HSRP Settings: version 2, timers 1/3, preempt delay 30s

Usage:
    python configure_hsrp.py --testbed ../pyats/testbed.yaml
    python configure_hsrp.py --testbed ../pyats/testbed.yaml --dry-run
    python configure_hsrp.py --testbed ../pyats/testbed.yaml --verify-only
"""

import os
from genie.testbed import load

# Campus identifier for IP addressing (10.VLAN.CAMPUS.x)
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

# EDGE1 is Active (priority 150) for these VLANs
# EDGE2 is Active (priority 150) for all other VLANs
EDGE1_ACTIVE_VLANS = [100, 300]  # STUDENT-NET, RESEARCH-NET

# Edge device pairs per campus
EDGE_DEVICES = {
    'MAIN': {
        'EDGE1': 'EUNIV-MAIN-EDGE1',
        'EDGE2': 'EUNIV-MAIN-EDGE2',
    },
    'MED': {
        'EDGE1': 'EUNIV-MED-EDGE1',
        'EDGE2': 'EUNIV-MED-EDGE2',
    },
    'RES': {
        'EDGE1': 'EUNIV-RES-EDGE1',
        'EDGE2': 'EUNIV-RES-EDGE2',
    },
}


def get_campus(device_name: str) -> str:
    """Extract campus from device name."""
    if 'MAIN' in device_name:
        return 'MAIN'
    elif 'MED' in device_name:
        return 'MED'
    elif 'RES' in device_name:
        return 'RES'
    return None


def is_edge1(device_name: str) -> bool:
    """Check if device is EDGE1 in the campus pair."""
    return 'EDGE1' in device_name or 'PE1' in device_name


def vlan_to_subnet(vlan: int) -> int:
    """Convert VLAN to valid subnet octet (divide by 10 for VLANs > 255)."""
    # VLAN 100 -> 10, VLAN 200 -> 20, VLAN 300 -> 30, etc.
    return vlan // 10


def generate_hsrp_config(device_name: str) -> list:
    """Generate HSRP configuration for a device."""
    campus = get_campus(device_name)
    if not campus:
        return []

    campus_id = CAMPUS_ID[campus]
    vlans = CAMPUS_VLANS.get(campus, {})
    is_primary = is_edge1(device_name)

    config_lines = []

    # First, ensure Gi3 base interface is up (no IP, just enabled)
    config_lines.append("interface GigabitEthernet3")
    config_lines.append(" no shutdown")

    for vlan, vrf in vlans.items():
        # Calculate IPs
        # Scheme: 10.{subnet}.{campus_id}.{host}/24
        # Where subnet = VLAN/10 (100->10, 200->20, 300->30, etc.)
        subnet = vlan_to_subnet(vlan)
        network = f"10.{subnet}.{campus_id}"
        if is_primary:
            my_ip = f"{network}.1"
        else:
            my_ip = f"{network}.2"
        virtual_ip = f"{network}.254"

        # Determine priority - active device gets 150, standby gets 100
        if vlan in EDGE1_ACTIVE_VLANS:
            priority = 150 if is_primary else 100
        else:
            priority = 100 if is_primary else 150

        # Generate subinterface config
        config_lines.append(f"!")
        config_lines.append(f"interface GigabitEthernet3.{vlan}")
        config_lines.append(f" description {vrf} Gateway - VLAN {vlan}")
        config_lines.append(f" encapsulation dot1Q {vlan}")
        config_lines.append(f" vrf forwarding {vrf}")
        config_lines.append(f" ip address {my_ip} 255.255.255.0")
        config_lines.append(f" no shutdown")
        config_lines.append(f" standby version 2")
        config_lines.append(f" standby {vlan} ip {virtual_ip}")
        config_lines.append(f" standby {vlan} priority {priority}")
        config_lines.append(f" standby {vlan} preempt delay minimum 30")
        config_lines.append(f" standby {vlan} timers 1 3")

    return config_lines


def configure_hsrp(testbed_file: str, dry_run: bool = False):
    """Configure HSRP on all edge devices."""

    # Use keychain or environment credentials
    print("Loading testbed...")
    testbed = load(testbed_file)

    results = {'success': [], 'failed': [], 'skipped': []}

    # Process each campus
    for campus, devices in EDGE_DEVICES.items():
        print(f"\n{'='*60}")
        print(f"Campus: {campus}")
        print(f"{'='*60}")

        for role, device_name in devices.items():
            print(f"\n{'-'*40}")
            print(f"Device: {device_name} ({role})")
            print(f"{'-'*40}")

            if device_name not in testbed.devices:
                print(f"  WARNING: {device_name} not in testbed, skipping")
                results['skipped'].append(device_name)
                continue

            device = testbed.devices[device_name]
            config_lines = generate_hsrp_config(device_name)

            if not config_lines:
                print(f"  ERROR: Could not generate config for {device_name}")
                results['failed'].append(device_name)
                continue

            print("  Configuration to apply:")
            for line in config_lines:
                print(f"    {line}")

            if dry_run:
                print("\n  [DRY RUN] Would apply configuration")
                results['success'].append(device_name)
                continue

            try:
                print(f"\n  Connecting to {device_name}...")
                device.connect(log_stdout=False)

                print("  Applying configuration...")
                config = "\n".join(config_lines)
                device.configure(config)
                print("  Configuration applied successfully!")

                # Verify HSRP status
                print("\n  Verifying HSRP status...")
                output = device.execute("show standby brief")
                if output.strip():
                    print("  HSRP Status:")
                    for line in output.splitlines():
                        print(f"    {line}")
                else:
                    print("  No HSRP groups found (peer may not be configured yet)")

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
    """Verify HSRP status on all edge devices."""

    print("Loading testbed...")
    testbed = load(testbed_file)

    print("\nHSRP Status Summary:")
    print("="*80)

    for campus, devices in EDGE_DEVICES.items():
        print(f"\n{campus} Campus:")
        print("-"*40)

        for role, device_name in devices.items():
            if device_name not in testbed.devices:
                print(f"  {device_name}: NOT IN TESTBED")
                continue

            device = testbed.devices[device_name]

            try:
                device.connect(log_stdout=False)
                output = device.execute("show standby brief")

                print(f"\n  {device_name}:")
                if output.strip():
                    for line in output.splitlines():
                        print(f"    {line}")
                else:
                    print("    No HSRP configured")

                device.disconnect()

            except Exception as e:
                print(f"\n  {device_name}: ERROR - {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Configure HSRP on E-University edge routers")
    parser.add_argument("--testbed", default="../pyats/testbed.yaml", help="Testbed YAML file")
    parser.add_argument("--dry-run", action="store_true", help="Show config without applying")
    parser.add_argument("--verify-only", action="store_true", help="Only verify HSRP status")

    args = parser.parse_args()

    if args.verify_only:
        verify_hsrp(args.testbed)
    else:
        configure_hsrp(args.testbed, dry_run=args.dry_run)
