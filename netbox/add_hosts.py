#!/usr/bin/env python3
"""
E University Network Lab - Add Host Routers to NetBox

Adds the 6 IOSv host routers used for traffic generation to NetBox inventory.

Usage:
    python add_hosts.py

Environment Variables:
    NETBOX_URL      - NetBox instance URL
    NETBOX_TOKEN    - API token
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

try:
    import pynetbox
except ImportError:
    print("Please install pynetbox: pip install pynetbox")
    sys.exit(1)

# Host router configuration
HOST_ROUTERS = {
    "HOST1": {
        "mgmt_ip": "192.168.68.55/22",
        "host_ip": "172.18.1.10/24",
        "gateway": "172.18.1.1",
        "connected_to": "EUNIV-RES-EDGE1",
        "connected_interface": "GigabitEthernet6",
        "campus": "research-campus",
        "comments": "Traffic generator connected to RES-EDGE1",
    },
    "HOST2": {
        "mgmt_ip": "192.168.68.74/22",
        "host_ip": "172.18.2.10/24",
        "gateway": "172.18.2.1",
        "connected_to": "EUNIV-RES-EDGE2",
        "connected_interface": "GigabitEthernet6",
        "campus": "research-campus",
        "comments": "Traffic generator connected to RES-EDGE2",
    },
    "HOST3": {
        "mgmt_ip": "192.168.68.77/22",
        "host_ip": "172.16.1.10/24",
        "gateway": "172.16.1.1",
        "connected_to": "EUNIV-MAIN-EDGE1",
        "connected_interface": "GigabitEthernet4",
        "campus": "main-campus",
        "comments": "Traffic generator connected to MAIN-EDGE1",
    },
    "HOST4": {
        "mgmt_ip": "192.168.68.78/22",
        "host_ip": "172.16.2.10/24",
        "gateway": "172.16.2.1",
        "connected_to": "EUNIV-MAIN-EDGE2",
        "connected_interface": "GigabitEthernet6",
        "campus": "main-campus",
        "comments": "Traffic generator connected to MAIN-EDGE2",
    },
    "HOST5": {
        "mgmt_ip": "192.168.68.79/22",
        "host_ip": "172.17.2.10/24",
        "gateway": "172.17.2.1",
        "connected_to": "EUNIV-MED-EDGE2",
        "connected_interface": "GigabitEthernet6",
        "campus": "medical-campus",
        "comments": "Traffic generator connected to MED-EDGE2",
    },
    "HOST6": {
        "mgmt_ip": "192.168.68.80/22",
        "host_ip": "172.17.1.10/24",
        "gateway": "172.17.1.1",
        "connected_to": "EUNIV-MED-EDGE1",
        "connected_interface": "GigabitEthernet6",
        "campus": "medical-campus",
        "comments": "Traffic generator connected to MED-EDGE1",
    },
}


def add_hosts_to_netbox(url: str, token: str):
    """Add host routers to NetBox."""
    nb = pynetbox.api(url, token=token)
    nb.http_session.verify = True
    print(f"Connected to NetBox: {url}\n")

    # Get required objects
    site = nb.dcim.sites.get(slug="euniv-lab")
    if not site:
        print("Error: Site 'euniv-lab' not found. Run populate_euniv.py first.")
        sys.exit(1)

    # Get or create device type for IOSv
    device_type = nb.dcim.device_types.get(slug="iosv")
    if not device_type:
        # Create IOSv device type
        manufacturer = nb.dcim.manufacturers.get(slug="cisco")
        if not manufacturer:
            print("Error: Cisco manufacturer not found")
            sys.exit(1)
        device_type = nb.dcim.device_types.create({
            "manufacturer": manufacturer.id,
            "model": "IOSv",
            "slug": "iosv",
            "u_height": 1,
            "is_full_depth": False,
            "comments": "Cisco IOSv Virtual Router"
        })
        print("Created device type: IOSv")

    # Get or create device role for host/traffic generator
    device_role = nb.dcim.device_roles.get(slug="host")
    if not device_role:
        device_role = nb.dcim.device_roles.create({
            "name": "Host",
            "slug": "host",
            "color": "607d8b",
            "description": "Traffic generator / host device"
        })
        print("Created device role: Host")

    # Get platform
    platform = nb.dcim.platforms.get(slug="iosxe")

    print("=" * 60)
    print("Adding Host Routers to NetBox")
    print("=" * 60)

    for host_name, config in HOST_ROUTERS.items():
        print(f"\n[{host_name}]")

        # Check if device exists
        existing = nb.dcim.devices.get(name=host_name)
        if existing:
            print(f"  -> Device already exists, updating...")
            device = existing
        else:
            # Create device
            device_data = {
                "name": host_name,
                "device_type": device_type.id,
                "role": device_role.id,
                "site": site.id,
                "status": "active",
                "comments": config["comments"],
                "custom_fields": {
                    "region": config["campus"]
                }
            }
            if platform:
                device_data["platform"] = platform.id

            device = nb.dcim.devices.create(device_data)
            print(f"  + Created device")

        # Create interfaces if they don't exist
        interfaces_to_create = [
            {"name": "GigabitEthernet0/0", "type": "1000base-t", "description": f"Uplink to {config['connected_to']}"},
            {"name": "GigabitEthernet0/1", "type": "1000base-t", "description": "Management", "mgmt_only": True},
        ]

        for intf_data in interfaces_to_create:
            existing_intf = nb.dcim.interfaces.get(device_id=device.id, name=intf_data["name"])
            if not existing_intf:
                nb.dcim.interfaces.create({
                    "device": device.id,
                    "name": intf_data["name"],
                    "type": intf_data["type"],
                    "description": intf_data.get("description", ""),
                    "mgmt_only": intf_data.get("mgmt_only", False)
                })
                print(f"  + Created interface: {intf_data['name']}")

        # Create management IP
        mgmt_intf = nb.dcim.interfaces.get(device_id=device.id, name="GigabitEthernet0/1")
        if mgmt_intf:
            existing_ip = nb.ipam.ip_addresses.get(address=config["mgmt_ip"])
            if not existing_ip:
                ip_obj = nb.ipam.ip_addresses.create({
                    "address": config["mgmt_ip"],
                    "assigned_object_type": "dcim.interface",
                    "assigned_object_id": mgmt_intf.id,
                    "description": f"{host_name} Management"
                })
                print(f"  + Created management IP: {config['mgmt_ip']}")
            else:
                ip_obj = existing_ip
                print(f"  -> Management IP exists: {config['mgmt_ip']}")

            # Set as primary IP
            device.primary_ip4 = ip_obj.id
            device.save()
            print(f"  + Set primary IP: {config['mgmt_ip']}")

        # Create host network IP on Gi0/0
        host_intf = nb.dcim.interfaces.get(device_id=device.id, name="GigabitEthernet0/0")
        if host_intf:
            existing_host_ip = nb.ipam.ip_addresses.get(address=config["host_ip"])
            if not existing_host_ip:
                nb.ipam.ip_addresses.create({
                    "address": config["host_ip"],
                    "assigned_object_type": "dcim.interface",
                    "assigned_object_id": host_intf.id,
                    "description": f"{host_name} Host Network (STAFF-NET VRF)"
                })
                print(f"  + Created host IP: {config['host_ip']}")
            else:
                print(f"  -> Host IP exists: {config['host_ip']}")

        # Create cable connection to Edge router
        edge_device = nb.dcim.devices.get(name=config["connected_to"])
        if edge_device:
            edge_intf = nb.dcim.interfaces.get(device_id=edge_device.id, name=config["connected_interface"])
            if not edge_intf:
                # Create interface on Edge if it doesn't exist
                edge_intf = nb.dcim.interfaces.create({
                    "device": edge_device.id,
                    "name": config["connected_interface"],
                    "type": "1000base-t",
                    "description": f"Link to {host_name}"
                })
                print(f"  + Created interface on {config['connected_to']}: {config['connected_interface']}")

            # Check if already cabled
            if host_intf and edge_intf and not host_intf.cable and not edge_intf.cable:
                try:
                    nb.dcim.cables.create({
                        "a_terminations": [{"object_type": "dcim.interface", "object_id": host_intf.id}],
                        "b_terminations": [{"object_type": "dcim.interface", "object_id": edge_intf.id}],
                        "label": f"{host_name} to {config['connected_to']}",
                        "status": "connected"
                    })
                    print(f"  + Created cable: {host_name} Gi0/0 <-> {config['connected_to']} {config['connected_interface']}")
                except Exception as e:
                    print(f"  ! Cable error: {e}")
            else:
                print(f"  -> Cable already exists or interfaces not ready")

    print("\n" + "=" * 60)
    print("Host router addition complete!")
    print("=" * 60)
    print("\nSummary:")
    print(f"  - Added {len(HOST_ROUTERS)} host routers to NetBox")
    print("  - Created management and host network IPs")
    print("  - Created cable connections to Edge routers")
    print("\nNext: Run deploy_host_switches.py to configure the devices")


def main():
    url = os.getenv("NETBOX_URL")
    token = os.getenv("NETBOX_TOKEN")

    if not url or not token:
        print("Error: NETBOX_URL and NETBOX_TOKEN environment variables required")
        sys.exit(1)

    add_hosts_to_netbox(url, token)


if __name__ == "__main__":
    main()
