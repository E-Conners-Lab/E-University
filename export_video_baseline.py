#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
E-UNIVERSITY NETWORK - COMPLETE BASELINE EXPORT
═══════════════════════════════════════════════════════════════════════════════
One script to:
1. Pull running configs from all 16 routers
2. Save individual .cfg files
3. Create combined reference file
4. Build EVE-NG .unl file with embedded configs

This creates your "video recording baseline" - the exact network state
you can reload anytime.

Author: E-University Network Team
═══════════════════════════════════════════════════════════════════════════════
"""

from netmiko import ConnectHandler
import os
import base64
from datetime import datetime
import zipfile

USERNAME = "admin"
PASSWORD = "REDACTED"
OUTPUT_DIR = "E-University-Baseline"

# All 16 devices with EVE-NG positioning
DEVICES = {
    "EUNIV-CORE1": {"ip": "192.168.68.200", "id": 1, "x": 400, "y": 150, "role": "Route Reflector"},
    "EUNIV-CORE2": {"ip": "192.168.68.202", "id": 2, "x": 400, "y": 300, "role": "Route Reflector"},
    "EUNIV-CORE3": {"ip": "192.168.68.203", "id": 3, "x": 550, "y": 225, "role": "P Router"},
    "EUNIV-CORE4": {"ip": "192.168.68.204", "id": 4, "x": 700, "y": 225, "role": "P Router"},
    "EUNIV-CORE5": {"ip": "192.168.68.205", "id": 5, "x": 850, "y": 225, "role": "P Router"},
    "EUNIV-INET-GW1": {"ip": "192.168.68.206", "id": 6, "x": 300, "y": 50, "role": "Internet Gateway (Primary)"},
    "EUNIV-INET-GW2": {"ip": "192.168.68.207", "id": 7, "x": 500, "y": 50, "role": "Internet Gateway (Backup)"},
    "EUNIV-MAIN-AGG1": {"ip": "192.168.68.208", "id": 8, "x": 475, "y": 400, "role": "Main Campus Aggregation"},
    "EUNIV-MAIN-PE1": {"ip": "192.168.68.209", "id": 9, "x": 425, "y": 500, "role": "Main Campus PE"},
    "EUNIV-MAIN-PE2": {"ip": "192.168.68.210", "id": 10, "x": 525, "y": 500, "role": "Main Campus PE"},
    "EUNIV-MED-AGG1": {"ip": "192.168.68.211", "id": 11, "x": 675, "y": 400, "role": "Medical Campus Aggregation"},
    "EUNIV-MED-PE1": {"ip": "192.168.68.212", "id": 12, "x": 625, "y": 500, "role": "Medical Campus PE"},
    "EUNIV-MED-PE2": {"ip": "192.168.68.213", "id": 13, "x": 725, "y": 500, "role": "Medical Campus PE"},
    "EUNIV-RES-AGG1": {"ip": "192.168.68.214", "id": 14, "x": 875, "y": 400, "role": "Research Campus Aggregation"},
    "EUNIV-RES-PE1": {"ip": "192.168.68.215", "id": 15, "x": 825, "y": 500, "role": "Research Campus PE"},
    "EUNIV-RES-PE2": {"ip": "192.168.68.216", "id": 16, "x": 925, "y": 500, "role": "Research Campus PE"},
}


def connect(name, ip):
    """Connect to device"""
    device = {
        "device_type": "cisco_ios",
        "host": ip,
        "username": USERNAME,
        "password": PASSWORD,
        "secret": PASSWORD,
        "timeout": 30,
    }
    try:
        conn = ConnectHandler(**device)
        conn.enable()
        return conn
    except Exception as e:
        return None


def get_config(conn):
    """Get running config and clean it"""
    config = conn.send_command("show running-config", read_timeout=60)

    lines = config.split('\n')
    clean_lines = []
    skip_cert = False

    for line in lines:
        # Skip header lines
        if any(x in line for x in [
            'Building configuration',
            'Current configuration',
            'Last configuration change',
            'NVRAM config last updated',
        ]):
            continue

        # Skip certificate blocks
        if 'crypto pki certificate' in line:
            skip_cert = True
            continue
        if skip_cert:
            if line.strip() == 'quit':
                skip_cert = False
            continue

        clean_lines.append(line)

    # Remove trailing empty lines but keep structure
    while clean_lines and not clean_lines[-1].strip():
        clean_lines.pop()

    return '\n'.join(clean_lines)


def create_unl_xml(configs):
    """Create EVE-NG .unl XML content"""

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<lab name="E-University-Network-Baseline" version="1" scripttimeout="300" lock="0" author="E-University Network Team">',
        '  <description>E-University Multi-Campus MPLS L3VPN Network - Video Recording Baseline',
        f'Exported: {timestamp}',
        '',
        'Features:',
        '- 16 Cisco IOSv routers',
        '- OSPF Area 0 backbone',
        '- MPLS LDP label distribution',
        '- BGP Route Reflectors (CORE1, CORE2)',
        '- 5 VRFs with VPNv4 route exchange',
        '- HIPAA-compliant MEDICAL-NET isolation',
        '- Dual-homed Internet with automatic failover',
        '- BFD fast failure detection',
        '',
        'Management: 192.168.68.200-216',
        'Credentials: admin / REDACTED</description>',
        '  <topology>',
        '    <nodes>',
    ]

    for name, info in DEVICES.items():
        if name in configs:
            config_b64 = base64.b64encode(configs[name].encode()).decode()
            xml_lines.append(
                f'      <node id="{info["id"]}" name="{name}" type="qemu" template="vios" image="vios-adventerprisek9-m.spa.159-3.m6" console="telnet" cpu="1" cpulimit="0" ram="512" ethernet="9" uuid="a{info["id"]:03d}0-1234-5678-9abc-def012345678" firstmac="50:00:00:{info["id"]:02d}:00:00" icon="Router.png" left="{info["x"]}" top="{info["y"]}" config="1" delay="0">{config_b64}</node>')

    xml_lines.extend([
        '    </nodes>',
        '    <networks>',
        '      <network id="1" type="pnet0" name="Management" left="50" top="50" visibility="1"/>',
        '    </networks>',
        '  </topology>',
        '</lab>',
    ])

    return '\n'.join(xml_lines)


def main():
    print()
    print("█" * 70)
    print("█" + " " * 68 + "█")
    print("█  E-UNIVERSITY NETWORK - BASELINE EXPORT" + " " * 26 + "█")
    print("█  Creating Video Recording Baseline" + " " * 31 + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)
    print()
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(f"{OUTPUT_DIR}/configs", exist_ok=True)

    configs = {}

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 1: Pull configs from all devices
    # ═══════════════════════════════════════════════════════════════════════
    print("─" * 70)
    print("  STEP 1: Pulling Running Configurations")
    print("─" * 70)
    print()

    for name, info in DEVICES.items():
        print(f"  {name:<25}", end=" ", flush=True)
        conn = connect(name, info["ip"])
        if conn:
            config = get_config(conn)
            configs[name] = config
            conn.disconnect()
            print(f"✓ {len(config):,} bytes - {info['role']}")
        else:
            print(f"✗ Connection failed!")

    print()
    print(f"  Successfully exported: {len(configs)}/16 devices")

    if len(configs) == 0:
        print("\n  ERROR: No configs retrieved! Check connectivity.")
        return

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 2: Save individual config files
    # ═══════════════════════════════════════════════════════════════════════
    print()
    print("─" * 70)
    print("  STEP 2: Saving Individual Config Files")
    print("─" * 70)
    print()

    for name, config in configs.items():
        filepath = f"{OUTPUT_DIR}/configs/{name}.cfg"
        with open(filepath, 'w') as f:
            f.write(config)
        print(f"  ✓ {filepath}")

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 3: Create combined reference file
    # ═══════════════════════════════════════════════════════════════════════
    print()
    print("─" * 70)
    print("  STEP 3: Creating Combined Reference File")
    print("─" * 70)
    print()

    combined_path = f"{OUTPUT_DIR}/ALL-CONFIGS-REFERENCE.txt"
    with open(combined_path, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("E-UNIVERSITY NETWORK - COMPLETE CONFIGURATION REFERENCE\n")
        f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n")
        f.write("\nTABLE OF CONTENTS:\n")
        f.write("-" * 40 + "\n")
        for i, name in enumerate(sorted(DEVICES.keys()), 1):
            if name in configs:
                f.write(f"  {i:2}. {name} - {DEVICES[name]['role']}\n")
        f.write("\n")

        for name in sorted(DEVICES.keys()):
            if name in configs:
                f.write("\n" + "=" * 80 + "\n")
                f.write(f"  {name}\n")
                f.write(f"  Role: {DEVICES[name]['role']}\n")
                f.write(f"  Management IP: {DEVICES[name]['ip']}\n")
                f.write("=" * 80 + "\n\n")
                f.write(configs[name])
                f.write("\n")

    print(f"  ✓ {combined_path}")

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 4: Create EVE-NG .unl file
    # ═══════════════════════════════════════════════════════════════════════
    print()
    print("─" * 70)
    print("  STEP 4: Creating EVE-NG .unl File")
    print("─" * 70)
    print()

    unl_content = create_unl_xml(configs)
    unl_path = f"{OUTPUT_DIR}/E-University-Network-Baseline.unl"

    with open(unl_path, 'w') as f:
        f.write(unl_content)

    unl_size = os.path.getsize(unl_path)
    print(f"  ✓ {unl_path} ({unl_size:,} bytes)")

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 5: Create ZIP archive
    # ═══════════════════════════════════════════════════════════════════════
    print()
    print("─" * 70)
    print("  STEP 5: Creating ZIP Archive")
    print("─" * 70)
    print()

    zip_path = f"{OUTPUT_DIR}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(OUTPUT_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, OUTPUT_DIR)
                zf.write(file_path, f"E-University-Baseline/{arc_name}")

    zip_size = os.path.getsize(zip_path)
    print(f"  ✓ {zip_path} ({zip_size:,} bytes)")

    # ═══════════════════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════════════════
    print()
    print("█" * 70)
    print("█" + " " * 68 + "█")
    print("█  BASELINE EXPORT COMPLETE!" + " " * 39 + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)
    print()
    print("  OUTPUT FILES:")
    print("  ─────────────────────────────────────────────────────────────────")
    print(f"  📁 {OUTPUT_DIR}/")
    print(f"     ├── configs/              (16 individual .cfg files)")
    print(f"     ├── ALL-CONFIGS-REFERENCE.txt")
    print(f"     └── E-University-Network-Baseline.unl")
    print()
    print(f"  📦 {zip_path}  (complete archive)")
    print()
    print("  TO RESTORE THIS BASELINE:")
    print("  ─────────────────────────────────────────────────────────────────")
    print("  1. Import .unl file into EVE-NG")
    print("  2. Start all nodes")
    print("  3. Configs auto-load from embedded startup-config")
    print()
    print("  READY FOR VIDEO RECORDING! 🎬")
    print()


if __name__ == "__main__":
    main()