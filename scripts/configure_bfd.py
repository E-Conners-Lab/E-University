#!/usr/bin/env python3
"""
Configure BFD on E-University Network

BFD is configured on edge links only (not inside MPLS core):
- Core <-> INET-GW links (for fast upstream failover)
- AGG <-> Edge (PE) links (for fast PE failover)

BFD Settings:
- Interval: 100ms
- Min RX: 100ms
- Multiplier: 3 (300ms detection time)
"""

import os
import sys
from genie.testbed import load

# BFD configuration to apply
BFD_TEMPLATE = """
interface {interface}
 bfd interval 100 min_rx 100 multiplier 3
"""

# Define which interfaces get BFD on each device
# Format: device_name: [list of interfaces]
BFD_CONFIG = {
    # Core to INET-GW links
    'EUNIV-CORE1': ['GigabitEthernet4'],      # To INET-GW1
    'EUNIV-CORE2': ['GigabitEthernet4'],      # To INET-GW2
    'EUNIV-INET-GW1': ['GigabitEthernet2'],   # To CORE1
    'EUNIV-INET-GW2': ['GigabitEthernet2'],   # To CORE2

    # AGG to Edge links - Main Campus
    'EUNIV-MAIN-AGG1': ['GigabitEthernet4', 'GigabitEthernet5'],  # To PE1, PE2
    'EUNIV-MAIN-EDGE1': ['GigabitEthernet2'],  # To AGG1
    'EUNIV-MAIN-EDGE2': ['GigabitEthernet2'],  # To AGG1

    # AGG to Edge links - Medical Campus
    'EUNIV-MED-AGG1': ['GigabitEthernet4', 'GigabitEthernet5'],   # To PE1, PE2
    'EUNIV-MED-EDGE1': ['GigabitEthernet2'],   # To AGG1
    'EUNIV-MED-EDGE2': ['GigabitEthernet2'],   # To AGG1

    # AGG to Edge links - Research Campus
    'EUNIV-RES-AGG1': ['GigabitEthernet4', 'GigabitEthernet5'],   # To PE1, PE2
    'EUNIV-RES-EDGE1': ['GigabitEthernet2'],   # To AGG1
    'EUNIV-RES-EDGE2': ['GigabitEthernet2'],   # To AGG1
}


def configure_bfd(testbed_file: str, dry_run: bool = False):
    """Configure BFD on all specified devices and interfaces."""

    # Set credentials from environment or use defaults
    os.environ.setdefault('DEVICE_USERNAME', 'admin')
    os.environ.setdefault('DEVICE_PASSWORD', 'Pass2885!')
    os.environ.setdefault('DEVICE_ENABLE_PASSWORD', 'Pass2885!')

    print("Loading testbed...")
    testbed = load(testbed_file)

    results = {'success': [], 'failed': [], 'skipped': []}

    for device_name, interfaces in BFD_CONFIG.items():
        print(f"\n{'='*60}")
        print(f"Device: {device_name}")
        print(f"{'='*60}")

        if device_name not in testbed.devices:
            print(f"  WARNING: {device_name} not in testbed, skipping")
            results['skipped'].append(device_name)
            continue

        device = testbed.devices[device_name]

        try:
            print(f"  Connecting to {device_name}...")
            device.connect(log_stdout=False)

            # Build config for all interfaces
            config_lines = []
            for intf in interfaces:
                config_lines.append(f"interface {intf}")
                config_lines.append(" bfd interval 100 min_rx 100 multiplier 3")

            # Enable BFD on OSPF
            config_lines.append("router ospf 1")
            config_lines.append(" bfd all-interfaces")

            config = "\n".join(config_lines)

            print(f"  Interfaces to configure: {', '.join(interfaces)}")
            print(f"  Configuration:")
            for line in config_lines:
                print(f"    {line}")

            if dry_run:
                print(f"  [DRY RUN] Would apply configuration")
            else:
                print(f"  Applying configuration...")
                device.configure(config)
                print(f"  Configuration applied successfully")

            # Verify BFD is enabled
            print(f"  Verifying BFD status...")
            output = device.execute("show bfd neighbors")
            if output.strip():
                print(f"  BFD neighbors found:")
                for line in output.splitlines()[:10]:
                    print(f"    {line}")
            else:
                print(f"  No BFD neighbors yet (peer may not be configured)")

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


def verify_bfd(testbed_file: str):
    """Verify BFD neighbors on all configured devices."""

    os.environ.setdefault('DEVICE_USERNAME', 'admin')
    os.environ.setdefault('DEVICE_PASSWORD', 'Pass2885!')
    os.environ.setdefault('DEVICE_ENABLE_PASSWORD', 'Pass2885!')

    print("Loading testbed...")
    testbed = load(testbed_file)

    print("\nBFD Neighbor Status:")
    print("="*80)

    for device_name in BFD_CONFIG.keys():
        if device_name not in testbed.devices:
            continue

        device = testbed.devices[device_name]

        try:
            device.connect(log_stdout=False)
            output = device.execute("show bfd neighbors")

            print(f"\n{device_name}:")
            if output.strip():
                for line in output.splitlines():
                    print(f"  {line}")
            else:
                print("  No BFD neighbors")

            device.disconnect()

        except Exception as e:
            print(f"\n{device_name}: ERROR - {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Configure BFD on E-University network")
    parser.add_argument("--testbed", default="../pyats/testbed.yaml", help="Testbed YAML file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be configured without applying")
    parser.add_argument("--verify-only", action="store_true", help="Only verify BFD status, don't configure")

    args = parser.parse_args()

    if args.verify_only:
        verify_bfd(args.testbed)
    else:
        configure_bfd(args.testbed, dry_run=args.dry_run)
