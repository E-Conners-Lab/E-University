#!/usr/bin/env python3
"""
E-University Network - Host Switch Deployment Script
Configures L2 IOSv switches as traffic generators connected to Edge routers

Host Layout (actual connections):
- HOST1 -> RES-EDGE1  Gi6 - 172.18.1.0/24 (Management: 192.168.68.55)
- HOST2 -> RES-EDGE2  Gi6 - 172.18.2.0/24 (Management: 192.168.68.74)
- HOST3 -> MAIN-EDGE1 Gi6 - 172.16.1.0/24 (Management: 192.168.68.77)
- HOST4 -> MAIN-EDGE2 Gi6 - 172.16.2.0/24 (Management: 192.168.68.78)
- HOST5 -> MED-EDGE2  Gi6 - 172.17.2.0/24 (Management: 192.168.68.79)
- HOST6 -> MED-EDGE1  Gi6 - 172.17.1.0/24 (Management: 192.168.68.80)
"""

from netmiko import ConnectHandler
from concurrent.futures import ThreadPoolExecutor, as_completed

# Default credentials
CREDENTIALS = {
    "username": "admin",
    "password": "REDACTED",
}

# Host switch configurations (corrected mapping)
HOST_CONFIG = {
    "HOST1": {
        "mgmt_ip": "192.168.68.55",
        "ip": "172.18.1.10",
        "mask": "255.255.255.0",
        "gateway": "172.18.1.1",
        "description": "RES-HOST1",
        "edge_router": "RES-EDGE1",
        "targets": ["172.18.2.10", "172.16.1.10", "172.17.1.10"],
    },
    "HOST2": {
        "mgmt_ip": "192.168.68.74",
        "ip": "172.18.2.10",
        "mask": "255.255.255.0",
        "gateway": "172.18.2.1",
        "description": "RES-HOST2",
        "edge_router": "RES-EDGE2",
        "targets": ["172.18.1.10", "172.16.2.10", "172.17.2.10"],
    },
    "HOST3": {
        "mgmt_ip": "192.168.68.77",
        "ip": "172.16.1.10",
        "mask": "255.255.255.0",
        "gateway": "172.16.1.1",
        "description": "MAIN-HOST3",
        "edge_router": "MAIN-EDGE1",
        "targets": ["172.16.2.10", "172.17.1.10", "172.18.1.10"],
    },
    "HOST4": {
        "mgmt_ip": "192.168.68.78",
        "ip": "172.16.2.10",
        "mask": "255.255.255.0",
        "gateway": "172.16.2.1",
        "description": "MAIN-HOST4",
        "edge_router": "MAIN-EDGE2",
        "targets": ["172.16.1.10", "172.17.2.10", "172.18.2.10"],
    },
    "HOST5": {
        "mgmt_ip": "192.168.68.79",
        "ip": "172.17.2.10",
        "mask": "255.255.255.0",
        "gateway": "172.17.2.1",
        "description": "MED-HOST5",
        "edge_router": "MED-EDGE2",
        "targets": ["172.17.1.10", "172.16.1.10", "172.18.1.10"],
    },
    "HOST6": {
        "mgmt_ip": "192.168.68.80",
        "ip": "172.17.1.10",
        "mask": "255.255.255.0",
        "gateway": "172.17.1.1",
        "description": "MED-HOST6",
        "edge_router": "MED-EDGE1",
        "targets": ["172.17.2.10", "172.16.2.10", "172.18.2.10"],
    },
}


def generate_host_config(host_name):
    """Generate configuration for a host switch"""
    config = HOST_CONFIG.get(host_name)
    if not config:
        return None

    # Base config for IOSv router (not L2 switch)
    config_lines = [
        f"hostname {host_name}",
        "no ip domain-lookup",
        "interface GigabitEthernet0/0",
        f" description Uplink to Edge Router",
        f" ip address {config['ip']} {config['mask']}",
        " no shutdown",
        f"ip route 0.0.0.0 0.0.0.0 {config['gateway']}",
    ]

    # Add IP SLA probes for traffic generation
    for i, target in enumerate(config["targets"], start=1):
        config_lines.extend([
            f"ip sla {i}",
            f" icmp-echo {target}",
            " frequency 30",
            f"ip sla schedule {i} start-time now life forever",
        ])

    return config_lines


def deploy_config(host_name):
    """Deploy configuration to a host switch using netmiko"""
    cfg = HOST_CONFIG[host_name]
    config_lines = generate_host_config(host_name)

    device = {
        "device_type": "cisco_ios",
        "host": cfg["mgmt_ip"],
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
        return {"name": host_name, "success": True, "output": output}
    except Exception as e:
        return {"name": host_name, "success": False, "error": str(e)}


def main():
    print("=" * 60)
    print("E-University Network - Host Switch Deployment")
    print("=" * 60)
    print()

    # Show config preview
    for host_name in HOST_CONFIG.keys():
        config_lines = generate_host_config(host_name)
        print(f"[{host_name}] Config prepared ({len(config_lines)} lines)")

    print()
    print("Deploying configurations...")
    print("-" * 60)

    success_count = 0
    fail_count = 0

    # Deploy in parallel
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(deploy_config, name): name
            for name in HOST_CONFIG.keys()
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

    # Print connectivity test summary
    print()
    print("Host Connectivity Summary:")
    print("-" * 70)
    print(f"{'Host':<10} {'IP Address':<18} {'Gateway':<18} {'Targets'}")
    print("-" * 70)
    for host, cfg in HOST_CONFIG.items():
        targets = ", ".join(cfg["targets"][:2]) + "..."
        print(f"{host:<10} {cfg['ip']:<18} {cfg['gateway']:<18} {targets}")

    print()
    print("IP SLA probes configured - hosts will ping each other every 30 seconds")
    print("Use 'show ip sla statistics' on any host to verify traffic flow")


if __name__ == "__main__":
    main()
