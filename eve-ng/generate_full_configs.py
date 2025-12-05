#!/usr/bin/env python3
"""
Generate full configurations for all E University routers.
Includes: OSPF, BGP, MPLS LDP, VRFs
"""

import os

# ==============================================================================
# DEVICE DATA
# ==============================================================================

DEVICES = {
    # Core Routers
    "EUNIV-CORE1": {
        "mgmt_ip": "192.168.68.200",
        "loopback": "10.255.0.1",
        "asn": "65000",
        "role": "route-reflector",
        "rr_cluster_id": "10.255.0.12",
        "interfaces": {
            "GigabitEthernet2": {"ip": "10.0.0.1/30", "peer": "CORE2", "description": "To EUNIV-CORE2"},
            "GigabitEthernet3": {"ip": "10.0.0.18/30", "peer": "CORE5", "description": "To EUNIV-CORE5"},
            "GigabitEthernet4": {"ip": "10.0.0.21/30", "peer": "INET-GW1", "description": "To EUNIV-INET-GW1"},
            "GigabitEthernet5": {"ip": "10.0.1.1/30", "peer": "MAIN-AGG1", "description": "To EUNIV-MAIN-AGG1"},
        },
        "bgp_neighbors": ["10.255.0.2", "10.255.0.3", "10.255.0.4", "10.255.0.5", "10.255.0.101", "10.255.1.1"]
    },
    "EUNIV-CORE2": {
        "mgmt_ip": "192.168.68.202",
        "loopback": "10.255.0.2",
        "asn": "65000",
        "role": "route-reflector",
        "rr_cluster_id": "10.255.0.12",
        "interfaces": {
            "GigabitEthernet2": {"ip": "10.0.0.2/30", "peer": "CORE1", "description": "To EUNIV-CORE1"},
            "GigabitEthernet3": {"ip": "10.0.0.5/30", "peer": "CORE3", "description": "To EUNIV-CORE3"},
            "GigabitEthernet4": {"ip": "10.0.0.25/30", "peer": "INET-GW2", "description": "To EUNIV-INET-GW2"},
            "GigabitEthernet5": {"ip": "10.0.1.5/30", "peer": "MAIN-AGG1", "description": "To EUNIV-MAIN-AGG1"},
            "GigabitEthernet6": {"ip": "10.0.2.1/30", "peer": "MED-AGG1", "description": "To EUNIV-MED-AGG1"},
        },
        "bgp_neighbors": ["10.255.0.1", "10.255.0.3", "10.255.0.4", "10.255.0.5", "10.255.0.102", "10.255.1.1", "10.255.2.1"]
    },
    "EUNIV-CORE3": {
        "mgmt_ip": "192.168.68.203",
        "loopback": "10.255.0.3",
        "asn": "65000",
        "role": "p-router",
        "interfaces": {
            "GigabitEthernet2": {"ip": "10.0.0.6/30", "peer": "CORE2", "description": "To EUNIV-CORE2"},
            "GigabitEthernet3": {"ip": "10.0.0.9/30", "peer": "CORE4", "description": "To EUNIV-CORE4"},
            "GigabitEthernet4": {"ip": "10.0.2.5/30", "peer": "MED-AGG1", "description": "To EUNIV-MED-AGG1"},
        },
        "bgp_neighbors": ["10.255.0.1", "10.255.0.2"]  # Peers with RRs only
    },
    "EUNIV-CORE4": {
        "mgmt_ip": "192.168.68.204",
        "loopback": "10.255.0.4",
        "asn": "65000",
        "role": "p-router",
        "interfaces": {
            "GigabitEthernet2": {"ip": "10.0.0.10/30", "peer": "CORE3", "description": "To EUNIV-CORE3"},
            "GigabitEthernet3": {"ip": "10.0.0.13/30", "peer": "CORE5", "description": "To EUNIV-CORE5"},
            "GigabitEthernet4": {"ip": "10.0.3.1/30", "peer": "RES-AGG1", "description": "To EUNIV-RES-AGG1"},
        },
        "bgp_neighbors": ["10.255.0.1", "10.255.0.5"]  # Peers with RRs
    },
    "EUNIV-CORE5": {
        "mgmt_ip": "192.168.68.205",
        "loopback": "10.255.0.5",
        "asn": "65000",
        "role": "route-reflector",
        "rr_cluster_id": "10.255.0.5",
        "interfaces": {
            "GigabitEthernet2": {"ip": "10.0.0.14/30", "peer": "CORE4", "description": "To EUNIV-CORE4"},
            "GigabitEthernet3": {"ip": "10.0.0.17/30", "peer": "CORE1", "description": "To EUNIV-CORE1"},
            "GigabitEthernet4": {"ip": "10.0.3.5/30", "peer": "RES-AGG1", "description": "To EUNIV-RES-AGG1"},
        },
        "bgp_neighbors": ["10.255.0.1", "10.255.0.2", "10.255.0.3", "10.255.0.4", "10.255.3.1"]
    },

    # Internet Gateways
    "EUNIV-INET-GW1": {
        "mgmt_ip": "192.168.68.206",
        "loopback": "10.255.0.101",
        "asn": "65000",
        "role": "internet-edge",
        "interfaces": {
            "GigabitEthernet2": {"ip": "10.0.0.22/30", "peer": "CORE1", "description": "To EUNIV-CORE1"},
        },
        "bgp_neighbors": ["10.255.0.1", "10.255.0.2"]
    },
    "EUNIV-INET-GW2": {
        "mgmt_ip": "192.168.68.207",
        "loopback": "10.255.0.102",
        "asn": "65000",
        "role": "internet-edge",
        "interfaces": {
            "GigabitEthernet2": {"ip": "10.0.0.26/30", "peer": "CORE2", "description": "To EUNIV-CORE2"},
        },
        "bgp_neighbors": ["10.255.0.1", "10.255.0.2"]
    },

    # Main Campus
    "EUNIV-MAIN-AGG1": {
        "mgmt_ip": "192.168.68.208",
        "loopback": "10.255.1.1",
        "asn": "65100",
        "role": "aggregation",
        "interfaces": {
            "GigabitEthernet2": {"ip": "10.0.1.2/30", "peer": "CORE1", "description": "To EUNIV-CORE1"},
            "GigabitEthernet3": {"ip": "10.0.1.6/30", "peer": "CORE2", "description": "To EUNIV-CORE2"},
            "GigabitEthernet4": {"ip": "10.0.1.9/30", "peer": "MAIN-PE1", "description": "To EUNIV-MAIN-PE1"},
            "GigabitEthernet5": {"ip": "10.0.1.13/30", "peer": "MAIN-PE2", "description": "To EUNIV-MAIN-PE2"},
        },
        "bgp_neighbors": ["10.255.0.1", "10.255.0.2", "10.255.1.11", "10.255.1.12"]
    },
    "EUNIV-MAIN-PE1": {
        "mgmt_ip": "192.168.68.209",
        "loopback": "10.255.1.11",
        "asn": "65100",
        "role": "pe-bng",
        "interfaces": {
            "GigabitEthernet2": {"ip": "10.0.1.10/30", "peer": "MAIN-AGG1", "description": "To EUNIV-MAIN-AGG1"},
            "GigabitEthernet3": {"ip": "10.0.1.17/30", "peer": "MAIN-PE2", "description": "To EUNIV-MAIN-PE2 (HA)"},
        },
        "bgp_neighbors": ["10.255.1.1"],
        "vrfs": ["STUDENT-NET", "STAFF-NET", "RESEARCH-NET", "GUEST-NET"]
    },
    "EUNIV-MAIN-PE2": {
        "mgmt_ip": "192.168.68.210",
        "loopback": "10.255.1.12",
        "asn": "65100",
        "role": "pe-bng",
        "interfaces": {
            "GigabitEthernet2": {"ip": "10.0.1.14/30", "peer": "MAIN-AGG1", "description": "To EUNIV-MAIN-AGG1"},
            "GigabitEthernet3": {"ip": "10.0.1.18/30", "peer": "MAIN-PE1", "description": "To EUNIV-MAIN-PE1 (HA)"},
        },
        "bgp_neighbors": ["10.255.1.1"],
        "vrfs": ["STUDENT-NET", "STAFF-NET", "RESEARCH-NET", "GUEST-NET"]
    },

    # Medical Campus
    "EUNIV-MED-AGG1": {
        "mgmt_ip": "192.168.68.211",
        "loopback": "10.255.2.1",
        "asn": "65200",
        "role": "aggregation",
        "interfaces": {
            "GigabitEthernet2": {"ip": "10.0.2.2/30", "peer": "CORE2", "description": "To EUNIV-CORE2"},
            "GigabitEthernet3": {"ip": "10.0.2.6/30", "peer": "CORE3", "description": "To EUNIV-CORE3"},
            "GigabitEthernet4": {"ip": "10.0.2.9/30", "peer": "MED-PE1", "description": "To EUNIV-MED-PE1"},
            "GigabitEthernet5": {"ip": "10.0.2.13/30", "peer": "MED-PE2", "description": "To EUNIV-MED-PE2"},
        },
        "bgp_neighbors": ["10.255.0.1", "10.255.0.2", "10.255.2.11", "10.255.2.12"]
    },
    "EUNIV-MED-PE1": {
        "mgmt_ip": "192.168.68.212",
        "loopback": "10.255.2.11",
        "asn": "65200",
        "role": "pe-bng",
        "interfaces": {
            "GigabitEthernet2": {"ip": "10.0.2.10/30", "peer": "MED-AGG1", "description": "To EUNIV-MED-AGG1"},
            "GigabitEthernet3": {"ip": "10.0.2.17/30", "peer": "MED-PE2", "description": "To EUNIV-MED-PE2 (HA)"},
        },
        "bgp_neighbors": ["10.255.2.1"],
        "vrfs": ["STAFF-NET", "RESEARCH-NET", "MEDICAL-NET", "GUEST-NET"]
    },
    "EUNIV-MED-PE2": {
        "mgmt_ip": "192.168.68.213",
        "loopback": "10.255.2.12",
        "asn": "65200",
        "role": "pe-bng",
        "interfaces": {
            "GigabitEthernet2": {"ip": "10.0.2.14/30", "peer": "MED-AGG1", "description": "To EUNIV-MED-AGG1"},
            "GigabitEthernet3": {"ip": "10.0.2.18/30", "peer": "MED-PE1", "description": "To EUNIV-MED-PE1 (HA)"},
        },
        "bgp_neighbors": ["10.255.2.1"],
        "vrfs": ["STAFF-NET", "RESEARCH-NET", "MEDICAL-NET", "GUEST-NET"]
    },

    # Research Campus
    "EUNIV-RES-AGG1": {
        "mgmt_ip": "192.168.68.214",
        "loopback": "10.255.3.1",
        "asn": "65300",
        "role": "aggregation",
        "interfaces": {
            "GigabitEthernet2": {"ip": "10.0.3.2/30", "peer": "CORE4", "description": "To EUNIV-CORE4"},
            "GigabitEthernet3": {"ip": "10.0.3.6/30", "peer": "CORE5", "description": "To EUNIV-CORE5"},
            "GigabitEthernet4": {"ip": "10.0.3.9/30", "peer": "RES-PE1", "description": "To EUNIV-RES-PE1"},
            "GigabitEthernet5": {"ip": "10.0.3.13/30", "peer": "RES-PE2", "description": "To EUNIV-RES-PE2"},
        },
        "bgp_neighbors": ["10.255.0.1", "10.255.0.5", "10.255.3.11", "10.255.3.12"]
    },
    "EUNIV-RES-PE1": {
        "mgmt_ip": "192.168.68.215",
        "loopback": "10.255.3.11",
        "asn": "65300",
        "role": "pe-bng",
        "interfaces": {
            "GigabitEthernet2": {"ip": "10.0.3.10/30", "peer": "RES-AGG1", "description": "To EUNIV-RES-AGG1"},
            "GigabitEthernet3": {"ip": "10.0.3.17/30", "peer": "RES-PE2", "description": "To EUNIV-RES-PE2 (HA)"},
        },
        "bgp_neighbors": ["10.255.3.1"],
        "vrfs": ["STAFF-NET", "RESEARCH-NET", "GUEST-NET"]
    },
    "EUNIV-RES-PE2": {
        "mgmt_ip": "192.168.68.216",
        "loopback": "10.255.3.12",
        "asn": "65300",
        "role": "pe-bng",
        "interfaces": {
            "GigabitEthernet2": {"ip": "10.0.3.14/30", "peer": "RES-AGG1", "description": "To EUNIV-RES-AGG1"},
            "GigabitEthernet3": {"ip": "10.0.3.18/30", "peer": "RES-PE1", "description": "To EUNIV-RES-PE1 (HA)"},
        },
        "bgp_neighbors": ["10.255.3.1"],
        "vrfs": ["STAFF-NET", "RESEARCH-NET", "GUEST-NET"]
    },
}

# VRF Definitions
VRFS = {
    "STUDENT-NET": {"rd_suffix": "100", "rt": "65000:100", "description": "Student residential network"},
    "STAFF-NET": {"rd_suffix": "200", "rt": "65000:200", "description": "Staff and faculty network"},
    "RESEARCH-NET": {"rd_suffix": "300", "rt": "65000:300", "description": "Research partner network"},
    "MEDICAL-NET": {"rd_suffix": "400", "rt": "65000:400", "description": "HIPAA medical network"},
    "GUEST-NET": {"rd_suffix": "500", "rt": "65000:500", "description": "Guest/visitor network"},
}


def generate_config(hostname, data):
    """Generate full configuration for a device."""

    config = f"""!
! =====================================================================
! {hostname} - Full Configuration
! Role: {data['role']}
! ASN: {data['asn']}
! Generated for E University Network Lab
! =====================================================================
!
hostname {hostname}
!
! --- Services ---
service timestamps debug datetime msec localtime show-timezone
service timestamps log datetime msec localtime show-timezone
service password-encryption
no service pad
!
enable secret admin
username admin privilege 15 secret admin
!
! --- Logging ---
logging buffered 65536 informational
logging console informational
!
ip domain-name euniv.edu
ip name-server 10.255.255.1
ip name-server 10.255.255.2
!
! --- SSH ---
crypto key generate rsa modulus 2048
ip ssh version 2
!
! --- NTP ---
ntp server 10.255.255.10
ntp server 10.255.255.11
clock timezone EST -5 0
!
! --- SNMP ---
snmp-server community euniv-mon-ro RO
snmp-server location E University Data Center
snmp-server contact noc@euniv.edu
!
! --- Banner ---
banner motd ^
***********************************************
*  E UNIVERSITY NETWORK INFRASTRUCTURE       *
*  {hostname:^40} *
*  Authorized Access Only                    *
***********************************************
^
!
"""

    # VRF Definitions (for PE routers)
    if data.get("vrfs"):
        config += "! =====================================================================\n"
        config += "! VRF DEFINITIONS\n"
        config += "! =====================================================================\n"
        for vrf_name in data["vrfs"]:
            vrf = VRFS[vrf_name]
            config += f"""!
vrf definition {vrf_name}
 description {vrf['description']}
 rd {data['loopback']}:{vrf['rd_suffix']}
 !
 address-family ipv4
  route-target import {vrf['rt']}
  route-target export {vrf['rt']}
 exit-address-family
!
"""

    # Loopback Interface
    config += """! =====================================================================
! LOOPBACK INTERFACE
! =====================================================================
!
interface Loopback0
 description Router-ID / BGP Source
"""
    config += f" ip address {data['loopback']} 255.255.255.255\n"
    config += " ip ospf 1 area 0\n"
    config += " no shutdown\n!\n"

    # Management Interface
    config += """! =====================================================================
! MANAGEMENT INTERFACE
! =====================================================================
!
interface GigabitEthernet1
 description Management
"""
    config += f" ip address {data['mgmt_ip']} 255.255.252.0\n"
    config += " no shutdown\n!\n"

    # Core Interfaces
    config += """! =====================================================================
! CORE INTERFACES
! =====================================================================
"""
    for intf_name, intf_data in data.get("interfaces", {}).items():
        ip_parts = intf_data["ip"].split("/")
        ip = ip_parts[0]
        mask = "255.255.255.252"  # /30
        config += f"""!
interface {intf_name}
 description {intf_data['description']}
 ip address {ip} {mask}
 ip ospf 1 area 0
 ip ospf network point-to-point
 mpls ip
 no shutdown
"""

    # OSPF Configuration
    config += f"""!
! =====================================================================
! OSPF CONFIGURATION
! =====================================================================
!
router ospf 1
 router-id {data['loopback']}
 auto-cost reference-bandwidth 100000
 passive-interface Loopback0
 passive-interface GigabitEthernet1
 log-adjacency-changes detail
!
"""

    # MPLS Configuration
    config += """! =====================================================================
! MPLS CONFIGURATION
! =====================================================================
!
mpls ldp router-id Loopback0 force
mpls label protocol ldp
!
"""

    # BGP Configuration
    config += f"""! =====================================================================
! BGP CONFIGURATION
! =====================================================================
!
router bgp {data['asn']}
 bgp router-id {data['loopback']}
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
!
"""

    # BGP Neighbors
    for neighbor in data.get("bgp_neighbors", []):
        # Determine if iBGP or eBGP based on ASN
        # Core (65000), Main (65100), Medical (65200), Research (65300)
        neighbor_asn = data['asn']  # Default to same ASN (iBGP)

        config += f" neighbor {neighbor} remote-as {neighbor_asn}\n"
        config += f" neighbor {neighbor} update-source Loopback0\n"

    # Address family IPv4
    config += " !\n address-family ipv4\n"
    for neighbor in data.get("bgp_neighbors", []):
        config += f"  neighbor {neighbor} activate\n"
        config += f"  neighbor {neighbor} send-community both\n"
        if data["role"] == "route-reflector":
            config += f"  neighbor {neighbor} route-reflector-client\n"
    config += " exit-address-family\n"

    # Address family VPNv4 (for core/aggregation routers)
    if data["role"] in ["route-reflector", "p-router", "aggregation"]:
        config += " !\n address-family vpnv4\n"
        for neighbor in data.get("bgp_neighbors", []):
            config += f"  neighbor {neighbor} activate\n"
            config += f"  neighbor {neighbor} send-community extended\n"
            if data["role"] == "route-reflector":
                config += f"  neighbor {neighbor} route-reflector-client\n"
        config += " exit-address-family\n"

    # VRF address families for PE routers
    if data.get("vrfs"):
        for vrf_name in data["vrfs"]:
            config += f""" !
 address-family ipv4 vrf {vrf_name}
  redistribute connected
 exit-address-family
"""

    # Route Reflector cluster-id
    if data["role"] == "route-reflector" and data.get("rr_cluster_id"):
        config += f" bgp cluster-id {data['rr_cluster_id']}\n"

    config += "!\n"

    # Default route
    config += """!
! =====================================================================
! DEFAULT ROUTE & SECURITY
! =====================================================================
!
ip route 0.0.0.0 0.0.0.0 192.168.68.1
!
ip access-list standard VTY-ACCESS
 permit 10.0.0.0 0.255.255.255
 permit 192.168.68.0 0.0.3.255
 deny any log
!
line con 0
 logging synchronous
 exec-timeout 30 0
line vty 0 15
 access-class VTY-ACCESS in
 login local
 transport input ssh
 exec-timeout 30 0
!
end
"""

    return config


def main():
    output_dir = "eve-ng/full-configs"
    os.makedirs(output_dir, exist_ok=True)

    for hostname, data in DEVICES.items():
        config = generate_config(hostname, data)

        filepath = os.path.join(output_dir, f"{hostname}.cfg")
        with open(filepath, "w") as f:
            f.write(config)
        print(f"✓ Created: {filepath}")

    print(f"\n✓ Generated {len(DEVICES)} full configurations")


if __name__ == "__main__":
    main()
