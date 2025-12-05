#!/usr/bin/env python3
"""
Generate startup configs for all E University routers.
These are minimal configs to get management connectivity.
"""

import os

# Device definitions with management IPs and loopbacks
DEVICES = {
    "EUNIV-CORE1": {"mgmt_ip": "192.168.68.200", "loopback": "10.255.0.1", "role": "Core Router / Route Reflector"},
    "EUNIV-CORE2": {"mgmt_ip": "192.168.68.202", "loopback": "10.255.0.2", "role": "Core Router / Route Reflector"},
    "EUNIV-CORE3": {"mgmt_ip": "192.168.68.203", "loopback": "10.255.0.3", "role": "Core Router / P Router"},
    "EUNIV-CORE4": {"mgmt_ip": "192.168.68.204", "loopback": "10.255.0.4", "role": "Core Router / P Router"},
    "EUNIV-CORE5": {"mgmt_ip": "192.168.68.205", "loopback": "10.255.0.5", "role": "Core Router / Route Reflector"},
    "EUNIV-INET-GW1": {"mgmt_ip": "192.168.68.206", "loopback": "10.255.0.101", "role": "Internet Gateway"},
    "EUNIV-INET-GW2": {"mgmt_ip": "192.168.68.207", "loopback": "10.255.0.102", "role": "Internet Gateway"},
    "EUNIV-MAIN-AGG1": {"mgmt_ip": "192.168.68.208", "loopback": "10.255.1.1", "role": "Main Campus Aggregation"},
    "EUNIV-MAIN-PE1": {"mgmt_ip": "192.168.68.209", "loopback": "10.255.1.11", "role": "Main Campus PE/BNG"},
    "EUNIV-MAIN-PE2": {"mgmt_ip": "192.168.68.210", "loopback": "10.255.1.12", "role": "Main Campus PE/BNG"},
    "EUNIV-MED-AGG1": {"mgmt_ip": "192.168.68.211", "loopback": "10.255.2.1", "role": "Medical Campus Aggregation"},
    "EUNIV-MED-PE1": {"mgmt_ip": "192.168.68.212", "loopback": "10.255.2.11", "role": "Medical Campus PE/BNG"},
    "EUNIV-MED-PE2": {"mgmt_ip": "192.168.68.213", "loopback": "10.255.2.12", "role": "Medical Campus PE/BNG"},
    "EUNIV-RES-AGG1": {"mgmt_ip": "192.168.68.214", "loopback": "10.255.3.1", "role": "Research Campus Aggregation"},
    "EUNIV-RES-PE1": {"mgmt_ip": "192.168.68.215", "loopback": "10.255.3.11", "role": "Research Campus PE/BNG"},
    "EUNIV-RES-PE2": {"mgmt_ip": "192.168.68.216", "loopback": "10.255.3.12", "role": "Research Campus PE/BNG"},
}

STARTUP_TEMPLATE = """!
! {hostname} - Startup Configuration
! Role: {role}
! Management IP: {mgmt_ip}
!
hostname {hostname}
!
enable secret admin
!
username admin privilege 15 secret admin
!
ip domain-name euniv.edu
!
crypto key generate rsa modulus 2048
!
interface GigabitEthernet1
 description Management
 ip address {mgmt_ip} 255.255.252.0
 no shutdown
!
interface Loopback0
 description Router-ID / BGP Source
 ip address {loopback} 255.255.255.255
 no shutdown
!
ip route 0.0.0.0 0.0.0.0 192.168.68.1
!
ip ssh version 2
!
line con 0
 logging synchronous
line vty 0 15
 login local
 transport input ssh
!
end
"""

def main():
    output_dir = "eve-ng/startup-configs"
    os.makedirs(output_dir, exist_ok=True)

    for hostname, data in DEVICES.items():
        config = STARTUP_TEMPLATE.format(
            hostname=hostname,
            role=data["role"],
            mgmt_ip=data["mgmt_ip"],
            loopback=data["loopback"]
        )

        filepath = os.path.join(output_dir, f"{hostname}.cfg")
        with open(filepath, "w") as f:
            f.write(config)
        print(f"✓ Created: {filepath}")

    print(f"\n✓ Generated {len(DEVICES)} startup configs")

if __name__ == "__main__":
    main()
