#!/usr/bin/env python3
"""
Fix VPNv4 route reflection on aggregation routers.
Makes AGG routers reflect VPNv4 routes between PEs and core RRs.
"""

from netmiko import ConnectHandler
from concurrent.futures import ThreadPoolExecutor, as_completed

CREDENTIALS = {
    "username": "admin",
    "password": "REDACTED",
}

# Aggregation router configs
AGG_ROUTERS = {
    "EUNIV-RES-AGG1": {
        "host": "192.168.68.214",
        "pe_neighbors": ["10.255.3.11", "10.255.3.12"],  # RES-PE1, RES-PE2
    },
    "EUNIV-MAIN-AGG1": {
        "host": "192.168.68.208",
        "pe_neighbors": ["10.255.1.11", "10.255.1.12"],  # MAIN-PE1, MAIN-PE2
    },
    "EUNIV-MED-AGG1": {
        "host": "192.168.68.211",
        "pe_neighbors": ["10.255.2.11", "10.255.2.12"],  # MED-PE1, MED-PE2
    },
}


def generate_rr_config(pe_neighbors):
    """Generate route-reflector-client config for PE neighbors under VPNv4."""
    config_lines = [
        "router bgp 65000",
        " address-family vpnv4",
    ]
    for neighbor in pe_neighbors:
        config_lines.append(f"  neighbor {neighbor} route-reflector-client")
    return config_lines


def deploy_config(router_name, config):
    """Deploy configuration to an aggregation router."""
    device = {
        "device_type": "cisco_ios",
        "host": config["host"],
        "username": CREDENTIALS["username"],
        "password": CREDENTIALS["password"],
        "timeout": 30,
    }

    config_lines = generate_rr_config(config["pe_neighbors"])

    try:
        conn = ConnectHandler(**device)
        conn.enable()
        output = conn.send_config_set(config_lines)
        conn.save_config()
        conn.disconnect()
        return {"name": router_name, "success": True, "output": output}
    except Exception as e:
        return {"name": router_name, "success": False, "error": str(e)}


def main():
    print("=" * 60)
    print("Fix VPNv4 Route Reflection on Aggregation Routers")
    print("=" * 60)
    print()

    for router_name, config in AGG_ROUTERS.items():
        config_lines = generate_rr_config(config["pe_neighbors"])
        print(f"[{router_name}] Config:")
        for line in config_lines:
            print(f"    {line}")
        print()

    print("Deploying configurations...")
    print("-" * 60)

    success_count = 0
    fail_count = 0

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(deploy_config, name, cfg): name
            for name, cfg in AGG_ROUTERS.items()
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
    print()
    print("VPNv4 routes should now propagate between campuses.")
    print("Wait ~30 seconds for BGP to converge, then check:")
    print("  show bgp vpnv4 unicast all")
    print("  show ip sla statistics  (on HOST routers)")


if __name__ == "__main__":
    main()
