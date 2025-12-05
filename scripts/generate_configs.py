#!/usr/bin/env python3
"""
Config Generator - Generates router configurations from Jinja2 templates
=========================================================================
This script reads intent data (source of truth) and generates configs
using Jinja2 templates. In production, intent data would come from NetBox.

Usage:
    python generate_configs.py                    # Generate all configs
    python generate_configs.py --device EUNIV-CORE1  # Generate single device
    python generate_configs.py --diff             # Show what would change
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intent_data import DEVICES, ENTERPRISE, VRFS


class ConfigGenerator:
    def __init__(self):
        # Set up paths
        self.base_dir = Path(__file__).parent.parent
        self.template_dir = self.base_dir / "templates"
        self.output_dir = self.base_dir / "configs" / "generated"

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set up Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate_config(self, hostname: str) -> str:
        """Generate configuration for a single device."""
        if hostname not in DEVICES:
            raise ValueError(f"Unknown device: {hostname}")

        device = DEVICES[hostname]
        template_name = device.get("template", "core_router.j2")

        try:
            template = self.env.get_template(template_name)
        except Exception as e:
            raise ValueError(f"Template not found: {template_name}") from e

        # Build template context
        context = {
            "hostname": hostname,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **ENTERPRISE,
            **device,
        }

        # Add VRF definitions for PE routers
        if device.get("vrfs"):
            context["vrfs"] = [
                {"name": vrf_name, **VRFS[vrf_name]}
                for vrf_name in device["vrfs"]
            ]

        # Render template
        return template.render(**context)

    def save_config(self, hostname: str, config: str) -> Path:
        """Save generated config to file."""
        filepath = self.output_dir / f"{hostname}.cfg"
        filepath.write_text(config)
        return filepath

    def generate_all(self, show_diff: bool = False) -> dict:
        """Generate configs for all devices."""
        results = {"success": [], "failed": []}

        print("=" * 70)
        print("CONFIG GENERATION - E University Network")
        print("=" * 70)
        print(f"Template Directory: {self.template_dir}")
        print(f"Output Directory:   {self.output_dir}")
        print(f"Timestamp:          {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print()

        for hostname in DEVICES:
            try:
                config = self.generate_config(hostname)

                if show_diff:
                    filepath = self.output_dir / f"{hostname}.cfg"
                    if filepath.exists():
                        existing = filepath.read_text()
                        if existing != config:
                            print(f"  ~ {hostname} - config changed")
                        else:
                            print(f"  = {hostname} - no changes")
                    else:
                        print(f"  + {hostname} - new config")
                else:
                    filepath = self.save_config(hostname, config)
                    print(f"  ✓ {hostname} -> {filepath.name}")

                results["success"].append(hostname)

            except Exception as e:
                print(f"  ✗ {hostname} - ERROR: {e}")
                results["failed"].append(hostname)

        print()
        print("=" * 70)
        print(f"Generated: {len(results['success'])}/{len(DEVICES)} configs")
        if results["failed"]:
            print(f"Failed:    {', '.join(results['failed'])}")
        print("=" * 70)

        return results


def main():
    parser = argparse.ArgumentParser(
        description="Generate router configurations from Jinja2 templates"
    )
    parser.add_argument(
        "--device", "-d",
        help="Generate config for a specific device"
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Show what would change without writing files"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available devices"
    )

    args = parser.parse_args()

    generator = ConfigGenerator()

    if args.list:
        print("\nAvailable devices:")
        for hostname, data in DEVICES.items():
            print(f"  {hostname:25} - {data['role']}")
        print()
        return

    if args.device:
        try:
            config = generator.generate_config(args.device)
            if args.diff:
                print(config)
            else:
                filepath = generator.save_config(args.device, config)
                print(f"✓ Generated: {filepath}")
        except ValueError as e:
            print(f"✗ Error: {e}")
            sys.exit(1)
    else:
        generator.generate_all(show_diff=args.diff)


if __name__ == "__main__":
    main()
