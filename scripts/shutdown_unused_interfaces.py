#!/usr/bin/env python3
"""
Shutdown unused interfaces on E-University devices.

GigabitEthernet4 is not connected on EDGE devices and causes
interface down alerts. This script administratively shuts them down.
"""

import os

from dotenv import load_dotenv
from genie.testbed import load as load_testbed

# Load environment variables from .env file
load_dotenv()

# Devices and interfaces to shutdown
SHUTDOWN_CONFIG = {
    'EUNIV-MAIN-EDGE1': ['GigabitEthernet4'],
    'EUNIV-MAIN-EDGE2': ['GigabitEthernet4'],
    'EUNIV-MED-EDGE1': ['GigabitEthernet4'],
    'EUNIV-MED-EDGE2': ['GigabitEthernet4'],
    'EUNIV-RES-EDGE1': ['GigabitEthernet4'],
    'EUNIV-RES-EDGE2': ['GigabitEthernet4'],
}


def shutdown_interfaces(testbed_file: str, dry_run: bool = False):
    """Shutdown unused interfaces on devices."""

    # Credentials loaded from .env via dotenv

    print("Loading testbed...")
    testbed = load_testbed(testbed_file)

    results = {'success': [], 'failed': [], 'skipped': []}

    for device_name, interfaces in SHUTDOWN_CONFIG.items():
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

            for intf in interfaces:
                config = [
                    f"interface {intf}",
                    " description UNUSED - Administratively Shutdown",
                    " shutdown",
                ]

                print(f"  Interface: {intf}")
                for line in config:
                    print(f"    {line}")

                if dry_run:
                    print(f"  [DRY RUN] Would shutdown {intf}")
                else:
                    device.configure("\n".join(config))
                    print(f"  Shutdown {intf} successfully")

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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Shutdown unused interfaces")
    parser.add_argument("--testbed", default="../pyats/testbed.yaml", help="Testbed YAML file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")

    args = parser.parse_args()
    shutdown_interfaces(args.testbed, dry_run=args.dry_run)
