#!/usr/bin/env python3
"""
E-University Network - Host Interface Deployment Script
Configures GigabitEthernet6 on Edge routers for host switch connectivity

Host Layout (actual connections):
- RES-EDGE1  Gi6 -> HOST1 - 172.18.1.0/24 (HOST1 mgmt: 192.168.68.55)
- RES-EDGE2  Gi6 -> HOST2 - 172.18.2.0/24 (HOST2 mgmt: 192.168.68.74)
- MAIN-EDGE1 Gi6 -> HOST3 - 172.16.1.0/24 (HOST3 mgmt: 192.168.68.77)
- MAIN-EDGE2 Gi6 -> HOST4 - 172.16.2.0/24 (HOST4 mgmt: 192.168.68.78)
- MED-EDGE2  Gi6 -> HOST5 - 172.17.2.0/24 (HOST5 mgmt: 192.168.68.79)
- MED-EDGE1  Gi6 -> HOST6 - 172.17.1.0/24 (HOST6 mgmt: 192.168.68.80)
"""

from netmiko import ConnectHandler
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Default credentials
CREDENTIALS = {
    "username": "admin",
    "password": "REDACTED",
}

# Edge router Gi6 configurations
EDGE_HOST_CONFIG = {
    "EUNIV-RES-PE1": {
        "host": "192.168.68.215",
        "ip": "172.18.1.1",
        "mask": "255.255.255.0",
        "description": "HOST1",
    },
    "EUNIV-RES-PE2": {
        "host": "192.168.68.216",
        "ip": "172.18.2.1",
        "mask": "255.255.255.0",
        "description": "HOST2",
    },
    "EUNIV-MAIN-PE1": {
        "host": "192.168.68.209",
        "ip": "172.16.1.1",
        "mask": "255.255.255.0",
        "description": "HOST3",
    },
    "EUNIV-MAIN-PE2": {
        "host": "192.168.68.210",
        "ip": "172.16.2.1",
        "mask": "255.255.255.0",
        "description": "HOST4",
    },
    "EUNIV-MED-PE2": {
        "host": "192.168.68.213",
        "ip": "172.17.2.1",
        "mask": "255.255.255.0",
        "description": "HOST5",
    },
    "EUNIV-MED-PE1": {
        "host": "192.168.68.212",
        "ip": "172.17.1.1",
        "mask": "255.255.255.0",
        "description": "HOST6",
    },
}


def generate_gi6_config(router_name):
    """Generate Gi6 interface configuration for an Edge router"""
    config = EDGE_HOST_CONFIG.get(router_name)
    if not config:
        return None

    return [
        f"interface GigabitEthernet6",
        f" no ip address",
        f" vrf forwarding STAFF-NET",
        f" ip address {config['ip']} {config['mask']}",
        f" description Link to {config['description']}",
        f" no shutdown",
    ]


def deploy_config(router_name, config_lines):
    """Deploy configuration to a device using netmiko"""
    cfg = EDGE_HOST_CONFIG[router_name]

    device = {
        "device_type": "cisco_ios",
        "host": cfg["host"],
        "username": CREDENTIALS["username"],
        "password": CREDENTIALS["password"],
        "secret": CREDENTIALS["password"],
    }

    try:
        connection = ConnectHandler(**device)
        connection.enable()
        output = connection.send_config_set(config_lines)
        connection.save_config()
        connection.disconnect()
        return {"name": router_name, "success": True, "output": output}
    except Exception as e:
        return {"name": router_name, "success": False, "error": str(e)}


def main():
    print("=" * 60)
    print("E-University Network - Host Interface Deployment")
    print("=" * 60)
    print()

    # Build deployment tasks
    tasks = []
    for router_name in EDGE_HOST_CONFIG.keys():
        config_lines = generate_gi6_config(router_name)
        if config_lines:
            tasks.append((router_name, config_lines))
            print(f"[{router_name}] Config prepared:")
            for line in config_lines:
                print(f"    {line}")
            print()

    # Deploy in parallel
    print("Deploying configurations...")
    print("-" * 60)

    success_count = 0
    fail_count = 0

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(deploy_config, name, cfg): name
            for name, cfg in tasks
        }

        for future in as_completed(futures):
            result = future.result()
            if result["success"]:
                print(f"  ✓ {result['name']}: Configuration applied")
                success_count += 1
            else:
                print(f"  ✗ {result['name']}: {result['error']}")
                fail_count += 1

    print()
    print("=" * 60)
    print(f"Deployment Complete: {success_count} success, {fail_count} failed")
    print("=" * 60)

    # Print host IP configuration summary
    print()
    print("Host Configuration Summary:")
    print("-" * 70)
    print(f"{'Host':<20} {'IP Address':<18} {'Gateway':<18} {'Mgmt IP'}")
    print("-" * 70)
    print(f"{'HOST1 (RES-EDGE1)':<20} {'172.18.1.10/24':<18} {'172.18.1.1':<18} 192.168.68.55")
    print(f"{'HOST2 (RES-EDGE2)':<20} {'172.18.2.10/24':<18} {'172.18.2.1':<18} 192.168.68.74")
    print(f"{'HOST3 (MAIN-EDGE1)':<20} {'172.16.1.10/24':<18} {'172.16.1.1':<18} 192.168.68.77")
    print(f"{'HOST4 (MAIN-EDGE2)':<20} {'172.16.2.10/24':<18} {'172.16.2.1':<18} 192.168.68.78")
    print(f"{'HOST5 (MED-EDGE2)':<20} {'172.17.2.10/24':<18} {'172.17.2.1':<18} 192.168.68.79")
    print(f"{'HOST6 (MED-EDGE1)':<20} {'172.17.1.10/24':<18} {'172.17.1.1':<18} 192.168.68.80")


if __name__ == "__main__":
    main()
