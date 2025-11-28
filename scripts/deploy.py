#!/usr/bin/env python3
"""
Config Deployment Script
========================
Deploys generated configurations to devices with:
- Config diff preview
- Staged rollout (one device at a time)
- Automatic backup before changes
- Rollback capability

Usage:
    python deploy.py --diff                       # Show what would change
    python deploy.py --device EUNIV-CORE1         # Deploy to single device
    python deploy.py --deploy                     # Deploy to all devices
    python deploy.py --backup                     # Backup current configs
    python deploy.py --rollback EUNIV-CORE1       # Rollback device
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from pyats.topology import loader


class ConfigDeployer:
    """Handles configuration deployment to network devices."""
    
    def __init__(self, testbed_path: str = "pyats/testbed.yaml"):
        self.testbed = loader.load(testbed_path)
        
        # Paths
        self.base_dir = Path(__file__).parent.parent
        self.config_dir = self.base_dir / "configs" / "generated"
        self.backup_dir = self.base_dir / "configs" / "backups"
        
        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Stats
        self.deployed = []
        self.failed = []
        self.skipped = []
    
    def get_config_file(self, device_name: str) -> Optional[Path]:
        """Get the generated config file for a device."""
        config_file = self.config_dir / f"{device_name}.cfg"
        if config_file.exists():
            return config_file
        return None
    
    def backup_device(self, device_name: str) -> Optional[Path]:
        """Backup current running config from device."""
        device = self.testbed.devices.get(device_name)
        if not device:
            return None
        
        try:
            device.connect(log_stdout=False)
            running_config = device.execute("show running-config")
            device.disconnect()
            
            # Save with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"{device_name}_{timestamp}.cfg"
            backup_file.write_text(running_config)
            
            return backup_file
            
        except Exception as e:
            print(f"  ✗ Backup failed for {device_name}: {e}")
            return None
    
    def get_diff(self, device_name: str) -> str:
        """Get diff between running config and generated config."""
        config_file = self.get_config_file(device_name)
        if not config_file:
            return f"No generated config found for {device_name}"
        
        device = self.testbed.devices.get(device_name)
        if not device:
            return f"Device {device_name} not in testbed"
        
        try:
            device.connect(log_stdout=False)
            running = device.execute("show running-config")
            device.disconnect()
            
            # Simple line-by-line comparison
            generated = config_file.read_text()
            
            running_lines = set(running.strip().split('\n'))
            generated_lines = set(generated.strip().split('\n'))
            
            # Find differences
            to_add = generated_lines - running_lines
            to_remove = running_lines - generated_lines
            
            diff = []
            if to_add:
                diff.append("\n+ Lines to ADD:")
                for line in sorted(to_add):
                    if line.strip() and not line.startswith('!'):
                        diff.append(f"  + {line}")
            
            if to_remove:
                diff.append("\n- Lines to REMOVE:")
                for line in sorted(to_remove):
                    if line.strip() and not line.startswith('!') and not line.startswith('Building'):
                        diff.append(f"  - {line}")
            
            return '\n'.join(diff) if diff else "No significant differences"
            
        except Exception as e:
            return f"Error getting diff: {e}"
    
    def deploy_device(self, device_name: str, dry_run: bool = False) -> bool:
        """Deploy configuration to a single device."""
        config_file = self.get_config_file(device_name)
        if not config_file:
            print(f"  ✗ No config file for {device_name}")
            self.skipped.append(device_name)
            return False
        
        device = self.testbed.devices.get(device_name)
        if not device:
            print(f"  ✗ Device {device_name} not in testbed")
            self.skipped.append(device_name)
            return False
        
        if dry_run:
            print(f"\n--- Diff for {device_name} ---")
            print(self.get_diff(device_name))
            return True
        
        try:
            # Connect
            print(f"  → Connecting to {device_name}...")
            device.connect(log_stdout=False)
            
            # Backup first
            print(f"  → Backing up current config...")
            running_config = device.execute("show running-config")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"{device_name}_{timestamp}.cfg"
            backup_file.write_text(running_config)
            
            # Read and apply new config
            print(f"  → Applying new configuration...")
            new_config = config_file.read_text()
            
            # Extract just the config commands (skip hostname and other applied items)
            config_lines = []
            for line in new_config.split('\n'):
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('!'):
                    continue
                # Skip end statement
                if line == 'end':
                    continue
                config_lines.append(line)
            
            # Apply configuration
            device.configure('\n'.join(config_lines))
            
            # Save config
            print(f"  → Saving configuration...")
            device.execute("write memory")
            
            device.disconnect()
            
            print(f"  ✓ {device_name} deployed successfully")
            self.deployed.append(device_name)
            return True
            
        except Exception as e:
            print(f"  ✗ {device_name} failed: {e}")
            self.failed.append(device_name)
            try:
                device.disconnect()
            except:
                pass
            return False
    
    def deploy_all(self, dry_run: bool = False):
        """Deploy to all devices in staged rollout."""
        devices = list(self.testbed.devices.keys())
        
        print("=" * 70)
        print("CONFIGURATION DEPLOYMENT")
        print("=" * 70)
        print(f"Mode:       {'DRY RUN (no changes)' if dry_run else 'LIVE DEPLOYMENT'}")
        print(f"Devices:    {len(devices)}")
        print(f"Config Dir: {self.config_dir}")
        print("=" * 70)
        
        if not dry_run:
            print("\n⚠️  This will modify device configurations!")
            confirm = input("Type 'yes' to continue: ")
            if confirm.lower() != 'yes':
                print("Deployment cancelled.")
                return
        
        # Deploy in order: Core first, then Aggregation, then PE
        deploy_order = [
            # Core routers first
            "EUNIV-CORE1", "EUNIV-CORE2", "EUNIV-CORE3", "EUNIV-CORE4", "EUNIV-CORE5",
            # Internet gateways
            "EUNIV-INET-GW1", "EUNIV-INET-GW2",
            # Aggregation
            "EUNIV-MAIN-AGG1", "EUNIV-MED-AGG1", "EUNIV-RES-AGG1",
            # PE routers last
            "EUNIV-MAIN-PE1", "EUNIV-MAIN-PE2",
            "EUNIV-MED-PE1", "EUNIV-MED-PE2",
            "EUNIV-RES-PE1", "EUNIV-RES-PE2",
        ]
        
        for device_name in deploy_order:
            if device_name in devices:
                print(f"\n[{deploy_order.index(device_name) + 1}/{len(deploy_order)}] {device_name}")
                self.deploy_device(device_name, dry_run)
                
                if not dry_run and device_name in self.failed:
                    print("\n⚠️  Deployment failed! Stopping to prevent cascade failures.")
                    print("    Review the error and consider rollback before continuing.")
                    break
        
        # Summary
        print("\n" + "=" * 70)
        print("DEPLOYMENT SUMMARY")
        print("=" * 70)
        print(f"Deployed: {len(self.deployed)}")
        print(f"Failed:   {len(self.failed)}")
        print(f"Skipped:  {len(self.skipped)}")
        
        if self.failed:
            print(f"\nFailed devices: {', '.join(self.failed)}")
        print()
    
    def rollback_device(self, device_name: str) -> bool:
        """Rollback device to most recent backup."""
        # Find most recent backup
        backups = sorted(self.backup_dir.glob(f"{device_name}_*.cfg"), reverse=True)
        
        if not backups:
            print(f"  ✗ No backups found for {device_name}")
            return False
        
        backup_file = backups[0]
        print(f"  → Rolling back to: {backup_file.name}")
        
        device = self.testbed.devices.get(device_name)
        if not device:
            print(f"  ✗ Device {device_name} not in testbed")
            return False
        
        try:
            device.connect(log_stdout=False)
            
            # Apply backup config
            backup_config = backup_file.read_text()
            device.configure(backup_config)
            device.execute("write memory")
            
            device.disconnect()
            
            print(f"  ✓ {device_name} rolled back successfully")
            return True
            
        except Exception as e:
            print(f"  ✗ Rollback failed: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Config Deployment Script")
    parser.add_argument("--diff", action="store_true", help="Show config diff without deploying")
    parser.add_argument("--deploy", action="store_true", help="Deploy configs to all devices")
    parser.add_argument("--device", "-d", help="Deploy to single device")
    parser.add_argument("--backup", action="store_true", help="Backup all devices")
    parser.add_argument("--rollback", help="Rollback specified device")
    parser.add_argument("--testbed", default="pyats/testbed.yaml", help="Testbed file path")
    
    args = parser.parse_args()
    
    deployer = ConfigDeployer(args.testbed)
    
    if args.backup:
        print("Backing up all devices...")
        for name in deployer.testbed.devices:
            backup = deployer.backup_device(name)
            if backup:
                print(f"  ✓ {name} -> {backup.name}")
        return
    
    if args.rollback:
        print(f"Rolling back {args.rollback}...")
        deployer.rollback_device(args.rollback)
        return
    
    if args.device:
        deployer.deploy_device(args.device, dry_run=args.diff)
    elif args.deploy or args.diff:
        deployer.deploy_all(dry_run=args.diff)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
