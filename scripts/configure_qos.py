#!/usr/bin/env python3
"""
Configure QoS on E-University Edge Routers

QoS Design (VRF-Based Marking):
- MEDICAL-NET: DSCP EF (46) - Priority queue, 20% bandwidth
- STAFF-NET: DSCP AF31 (26) - 25% bandwidth
- RESEARCH-NET: DSCP AF21 (18) - 30% bandwidth
- STUDENT-NET: DSCP 0 (Best Effort) - 20% bandwidth
- GUEST-NET: DSCP CS1 (8) - Scavenger, 5% bandwidth + rate limiting

Policies:
- EUNIV-VRF-MARKING: Applied input on VRF interfaces (marks traffic)
- EUNIV-QOS-QUEUING: Applied output on uplinks (queues traffic)

Usage:
    python configure_qos.py --testbed ../pyats/testbed.yaml
    python configure_qos.py --testbed ../pyats/testbed.yaml --dry-run
    python configure_qos.py --testbed ../pyats/testbed.yaml --verify-only
    python configure_qos.py --testbed ../pyats/testbed.yaml --device EUNIV-MED-EDGE1
"""

import os
import sys
from typing import List, Dict

from genie.testbed import load

# Add current directory to path for intent_data import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intent_data import (
    QOS_VRF_MARKINGS,
    QOS_CLASS_MAPS,
    QOS_POLICY_MAPS,
    QOS_EDGE_DEVICES,
    QOS_EDGE_VRFS,
)


def generate_class_map_config() -> List[str]:
    """Generate class-map configuration lines."""
    config_lines = []

    for class_name, config in QOS_CLASS_MAPS.items():
        match_type = config.get("match_type", "match-any")
        config_lines.append(f"class-map {match_type} {class_name}")

        for criterion in config.get("match_criteria", []):
            if criterion["type"] == "dscp":
                config_lines.append(f" match dscp {criterion['value']}")
            elif criterion["type"] == "vrf":
                # VRF matching is done via interface application, not class-map
                # This is just for documentation - DSCP matching is the key
                pass

        config_lines.append("!")

    return config_lines


def generate_marking_policy_config() -> List[str]:
    """Generate DSCP marking policy-map configuration."""
    config_lines = []

    policy_name = "EUNIV-VRF-MARKING"
    policy_config = QOS_POLICY_MAPS.get(policy_name, {})

    config_lines.append(f"policy-map {policy_name}")

    for class_name, actions in policy_config.get("classes", {}).items():
        config_lines.append(f" class {class_name}")

        # DSCP marking action
        action = actions.get("action", "")
        if action:
            config_lines.append(f"  {action}")

        # Police rate limiting (for GUEST)
        police_rate = actions.get("police_rate")
        if police_rate:
            # Convert rate string to bps (e.g., "50m" -> 50000000)
            rate_value = police_rate.lower()
            if rate_value.endswith('m'):
                rate_bps = int(rate_value[:-1]) * 1000000
            elif rate_value.endswith('k'):
                rate_bps = int(rate_value[:-1]) * 1000
            elif rate_value.endswith('g'):
                rate_bps = int(rate_value[:-1]) * 1000000000
            else:
                rate_bps = int(rate_value)

            # Burst size = rate / 8 (1 second of data)
            burst = rate_bps // 8
            config_lines.append(f"  police cir {rate_bps} bc {burst}")
            config_lines.append(f"   conform-action transmit")
            config_lines.append(f"   exceed-action drop")

    # Default class
    config_lines.append(" class class-default")
    config_lines.append("  set dscp default")
    config_lines.append("!")

    return config_lines


def generate_queuing_policy_config() -> List[str]:
    """Generate queuing policy-map configuration."""
    config_lines = []

    policy_name = "EUNIV-QOS-QUEUING"
    policy_config = QOS_POLICY_MAPS.get(policy_name, {})

    config_lines.append(f"policy-map {policy_name}")

    for class_name, config in policy_config.get("classes", {}).items():
        config_lines.append(f" class {class_name}")

        is_priority = config.get("priority", False)
        bandwidth_pct = config.get("bandwidth_percent", 0)

        if is_priority:
            # Priority queue with percent
            config_lines.append(f"  priority percent {bandwidth_pct}")
        elif bandwidth_pct > 0:
            # Bandwidth allocation
            config_lines.append(f"  bandwidth percent {bandwidth_pct}")

    # Default class gets remaining bandwidth
    config_lines.append(" class class-default")
    config_lines.append("  fair-queue")
    config_lines.append("!")

    return config_lines


def generate_interface_service_policy(device_name: str) -> List[str]:
    """Generate service-policy application on interfaces."""
    config_lines = []
    device_vrfs = QOS_EDGE_VRFS.get(device_name, [])

    # Apply marking policy to each VRF's interface
    # In real deployment, you'd need to know which interface has which VRF
    # For this lab, we apply to subinterfaces on Gi3

    # Map VRF to VLAN for subinterface naming
    vrf_to_vlan = {
        "STUDENT-NET": 100,
        "STAFF-NET": 200,
        "RESEARCH-NET": 300,
        "MEDICAL-NET": 400,
        "GUEST-NET": 500,
    }

    for vrf in device_vrfs:
        vlan = vrf_to_vlan.get(vrf)
        if vlan:
            config_lines.append(f"interface GigabitEthernet3.{vlan}")
            config_lines.append(f" service-policy input EUNIV-VRF-MARKING")
            config_lines.append("!")

    # Apply queuing policy to uplink (Gi2)
    config_lines.append("interface GigabitEthernet2")
    config_lines.append(" service-policy output EUNIV-QOS-QUEUING")
    config_lines.append("!")

    return config_lines


def generate_full_qos_config(device_name: str) -> List[str]:
    """Generate complete QoS configuration for an Edge device."""
    config_lines = []

    # Class-maps
    config_lines.append("! === CLASS-MAPS ===")
    config_lines.extend(generate_class_map_config())

    # Marking policy-map
    config_lines.append("! === MARKING POLICY ===")
    config_lines.extend(generate_marking_policy_config())

    # Queuing policy-map
    config_lines.append("! === QUEUING POLICY ===")
    config_lines.extend(generate_queuing_policy_config())

    # Service-policy application
    config_lines.append("! === SERVICE-POLICY APPLICATION ===")
    config_lines.extend(generate_interface_service_policy(device_name))

    return config_lines


def configure_qos(testbed_file: str, dry_run: bool = False, target_device: str = None):
    """Configure QoS on Edge devices."""

    print("Loading testbed...")
    testbed = load(testbed_file)

    results = {'success': [], 'failed': [], 'skipped': []}

    # Determine which devices to configure
    devices_to_configure = QOS_EDGE_DEVICES
    if target_device:
        if target_device in QOS_EDGE_DEVICES:
            devices_to_configure = [target_device]
        else:
            print(f"ERROR: {target_device} is not a valid Edge device")
            print(f"Valid devices: {', '.join(QOS_EDGE_DEVICES)}")
            return

    print(f"\n{'='*70}")
    print("E-UNIVERSITY QoS CONFIGURATION")
    print(f"{'='*70}")
    print("\nQoS Design:")
    print("  - MEDICAL-NET: DSCP EF (46) - Priority 20%")
    print("  - STAFF-NET:   DSCP AF31 (26) - BW 25%")
    print("  - RESEARCH-NET: DSCP AF21 (18) - BW 30%")
    print("  - STUDENT-NET: DSCP 0 (BE) - BW 20%")
    print("  - GUEST-NET:   DSCP CS1 (8) - BW 5% + Police 50Mbps")

    for device_name in devices_to_configure:
        print(f"\n{'-'*60}")
        print(f"Device: {device_name}")
        print(f"VRFs: {', '.join(QOS_EDGE_VRFS.get(device_name, []))}")
        print(f"{'-'*60}")

        if device_name not in testbed.devices:
            print(f"  WARNING: {device_name} not in testbed, skipping")
            results['skipped'].append(device_name)
            continue

        device = testbed.devices[device_name]
        config_lines = generate_full_qos_config(device_name)

        if not config_lines:
            print(f"  ERROR: Could not generate config for {device_name}")
            results['failed'].append(device_name)
            continue

        print("\n  Configuration to apply:")
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

            # Verify QoS status
            print("\n  Verifying QoS configuration...")

            print("\n  Class-maps:")
            output = device.execute("show class-map | include Class Map")
            for line in output.splitlines()[:10]:
                print(f"    {line}")

            print("\n  Policy-maps:")
            output = device.execute("show policy-map | include Policy Map")
            for line in output.splitlines()[:10]:
                print(f"    {line}")

            print("\n  Service-policy application:")
            output = device.execute("show policy-map interface brief")
            if output.strip():
                for line in output.splitlines()[:15]:
                    print(f"    {line}")
            else:
                # Try alternative command
                output = device.execute("show run | include service-policy")
                for line in output.splitlines()[:10]:
                    print(f"    {line}")

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
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"  Successful: {len(results['success'])} - {', '.join(results['success']) or 'None'}")
    print(f"  Failed:     {len(results['failed'])} - {', '.join(results['failed']) or 'None'}")
    print(f"  Skipped:    {len(results['skipped'])} - {', '.join(results['skipped']) or 'None'}")

    if results['success']:
        print("\nNext steps:")
        print("  1. Run QoS validation: pyats run job qos_job.py --testbed-file testbed.yaml")
        print("  2. Generate traffic to see QoS in action")
        print("  3. Check stats: show policy-map interface")

    return results


def verify_qos(testbed_file: str, target_device: str = None):
    """Verify QoS status on Edge devices."""

    print("Loading testbed...")
    testbed = load(testbed_file)

    devices_to_check = QOS_EDGE_DEVICES
    if target_device:
        devices_to_check = [target_device]

    print("\nQoS Status Summary:")
    print("="*80)

    for device_name in devices_to_check:
        print(f"\n{device_name}:")
        print("-"*60)

        if device_name not in testbed.devices:
            print("  NOT IN TESTBED")
            continue

        device = testbed.devices[device_name]

        try:
            device.connect(log_stdout=False)

            # Check class-maps
            print("\n  Class-maps:")
            output = device.execute("show class-map | include Class Map")
            if output.strip():
                for line in output.splitlines():
                    print(f"    {line}")
            else:
                print("    No class-maps configured")

            # Check policy-maps
            print("\n  Policy-maps:")
            output = device.execute("show policy-map | include Policy Map")
            if output.strip():
                for line in output.splitlines():
                    print(f"    {line}")
            else:
                print("    No policy-maps configured")

            # Check interface policies
            print("\n  Interface Service-Policies:")
            output = device.execute("show run | include service-policy")
            if output.strip():
                for line in output.splitlines():
                    print(f"    {line}")
            else:
                print("    No service-policies applied")

            # Check statistics
            print("\n  QoS Statistics (summary):")
            output = device.execute("show policy-map interface | include packets")
            if output.strip():
                for line in output.splitlines()[:10]:
                    print(f"    {line}")
            else:
                print("    No statistics available")

            device.disconnect()

        except Exception as e:
            print(f"  ERROR: {e}")


def remove_qos(testbed_file: str, dry_run: bool = False, target_device: str = None):
    """Remove QoS configuration from Edge devices."""

    print("Loading testbed...")
    testbed = load(testbed_file)

    devices_to_configure = QOS_EDGE_DEVICES
    if target_device:
        devices_to_configure = [target_device]

    print(f"\n{'='*70}")
    print("REMOVING QoS CONFIGURATION")
    print(f"{'='*70}")

    results = {'success': [], 'failed': [], 'skipped': []}

    for device_name in devices_to_configure:
        print(f"\n{'-'*60}")
        print(f"Device: {device_name}")
        print(f"{'-'*60}")

        if device_name not in testbed.devices:
            print(f"  WARNING: {device_name} not in testbed, skipping")
            results['skipped'].append(device_name)
            continue

        device = testbed.devices[device_name]
        device_vrfs = QOS_EDGE_VRFS.get(device_name, [])

        # VRF to VLAN mapping
        vrf_to_vlan = {
            "STUDENT-NET": 100,
            "STAFF-NET": 200,
            "RESEARCH-NET": 300,
            "MEDICAL-NET": 400,
            "GUEST-NET": 500,
        }

        # Generate removal config
        config_lines = []

        # Remove service-policies from interfaces first
        for vrf in device_vrfs:
            vlan = vrf_to_vlan.get(vrf)
            if vlan:
                config_lines.append(f"interface GigabitEthernet3.{vlan}")
                config_lines.append(f" no service-policy input")

        config_lines.append("interface GigabitEthernet2")
        config_lines.append(" no service-policy output")

        # Remove policy-maps
        config_lines.append("no policy-map EUNIV-VRF-MARKING")
        config_lines.append("no policy-map EUNIV-QOS-QUEUING")

        # Remove class-maps
        for class_name in QOS_CLASS_MAPS.keys():
            config_lines.append(f"no class-map {class_name}")

        print("  Configuration to remove:")
        for line in config_lines:
            print(f"    {line}")

        if dry_run:
            print("\n  [DRY RUN] Would remove configuration")
            results['success'].append(device_name)
            continue

        try:
            print(f"\n  Connecting to {device_name}...")
            device.connect(log_stdout=False)

            print("  Removing configuration...")
            config = "\n".join(config_lines)
            device.configure(config)
            print("  Configuration removed successfully!")

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
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"  Successful: {len(results['success'])} - {', '.join(results['success']) or 'None'}")
    print(f"  Failed:     {len(results['failed'])} - {', '.join(results['failed']) or 'None'}")
    print(f"  Skipped:    {len(results['skipped'])} - {', '.join(results['skipped']) or 'None'}")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Configure QoS on E-University Edge routers")
    parser.add_argument("--testbed", default="../pyats/testbed.yaml", help="Testbed YAML file")
    parser.add_argument("--dry-run", action="store_true", help="Show config without applying")
    parser.add_argument("--verify-only", action="store_true", help="Only verify QoS status")
    parser.add_argument("--remove", action="store_true", help="Remove QoS configuration")
    parser.add_argument("--device", help="Target specific device (e.g., EUNIV-MED-EDGE1)")

    args = parser.parse_args()

    if args.verify_only:
        verify_qos(args.testbed, target_device=args.device)
    elif args.remove:
        remove_qos(args.testbed, dry_run=args.dry_run, target_device=args.device)
    else:
        configure_qos(args.testbed, dry_run=args.dry_run, target_device=args.device)
