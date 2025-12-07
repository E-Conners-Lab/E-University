"""
E University Network - Device Intent Data
==========================================
This is the Source of Truth for device configurations.
In production, this would come from NetBox via API.
"""

import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Enterprise-wide settings
ENTERPRISE = {
    "domain_name": "euniv.edu",
    "dns_servers": ["10.255.255.1", "10.255.255.2"],
    "dns_servers_v6": ["2001:db8:e011:d5::1", "2001:db8:e011:d5::2"],
    "ntp_servers": ["10.255.255.10", "10.255.255.11"],
    "snmp_community": os.getenv("SNMP_COMMUNITY", "CHANGEME-snmp-community"),
    "snmp_location": "E University Data Center",
    "snmp_contact": "noc@euniv.edu",
    "default_gateway": "192.168.68.1",
    "mgmt_mask": "255.255.252.0",
    "username": os.getenv("DEVICE_USERNAME", "admin"),
    "password": os.getenv("DEVICE_PASSWORD"),
    "enable_secret": os.getenv("DEVICE_ENABLE_PASSWORD"),
    # Routing protocol authentication (optional)
    "ospf_auth_key": os.getenv("OSPF_AUTH_KEY"),
    "bgp_auth_key": os.getenv("BGP_AUTH_KEY"),
    # IPv6 Global Settings
    "ipv6_prefix": "2001:db8:e011::/48",
}

# VRF Definitions (Dual-Stack: IPv4 + IPv6)
VRFS = {
    "STUDENT-NET": {
        "rd_suffix": "100",
        "rt": "65000:100",
        "description": "Student residential network",
        "ipv6_prefix": "2001:db8:fab0:100::/56",
    },
    "STAFF-NET": {
        "rd_suffix": "200",
        "rt": "65000:200",
        "description": "Staff and faculty network",
        "ipv6_prefix": "2001:db8:fab0:200::/56",
    },
    "RESEARCH-NET": {
        "rd_suffix": "300",
        "rt": "65000:300",
        "description": "Research partner network",
        "ipv6_prefix": "2001:db8:fab0:300::/56",
    },
    "MEDICAL-NET": {
        "rd_suffix": "400",
        "rt": "65000:400",
        "description": "HIPAA medical network",
        "ipv6_prefix": "2001:db8:fab0:400::/56",
    },
    "GUEST-NET": {
        "rd_suffix": "500",
        "rt": "65000:500",
        "description": "Guest/visitor network",
        "ipv6_prefix": "2001:db8:fab0:500::/56",
    },
}

# IPv6 Link Addressing (P2P /126 subnets)
# Maps link identifier to IPv6 prefix
IPV6_LINKS = {
    # Core Ring Links
    "CORE1-CORE2": {"prefix": "2001:db8:e011:1ace:1::/126", "endpoints": ["EUNIV-CORE1", "EUNIV-CORE2"]},
    "CORE2-CORE3": {"prefix": "2001:db8:e011:1ace:2::/126", "endpoints": ["EUNIV-CORE2", "EUNIV-CORE3"]},
    "CORE3-CORE4": {"prefix": "2001:db8:e011:1ace:3::/126", "endpoints": ["EUNIV-CORE3", "EUNIV-CORE4"]},
    "CORE4-CORE5": {"prefix": "2001:db8:e011:1ace:4::/126", "endpoints": ["EUNIV-CORE4", "EUNIV-CORE5"]},
    "CORE5-CORE1": {"prefix": "2001:db8:e011:1ace:5::/126", "endpoints": ["EUNIV-CORE5", "EUNIV-CORE1"]},
    # Internet Gateway Links
    "CORE1-INETGW1": {"prefix": "2001:db8:e011:1ace:101::/126", "endpoints": ["EUNIV-CORE1", "EUNIV-INET-GW1"]},
    "CORE2-INETGW2": {"prefix": "2001:db8:e011:1ace:102::/126", "endpoints": ["EUNIV-CORE2", "EUNIV-INET-GW2"]},
    # Main Campus Links
    "CORE1-MAINAGG": {"prefix": "2001:db8:e011:1ace:110::/126", "endpoints": ["EUNIV-CORE1", "EUNIV-MAIN-AGG1"]},
    "CORE2-MAINAGG": {"prefix": "2001:db8:e011:1ace:111::/126", "endpoints": ["EUNIV-CORE2", "EUNIV-MAIN-AGG1"]},
    "MAINAGG-PE1": {"prefix": "2001:db8:e011:1ace:112::/126", "endpoints": ["EUNIV-MAIN-AGG1", "EUNIV-MAIN-PE1"]},
    "MAINAGG-PE2": {"prefix": "2001:db8:e011:1ace:113::/126", "endpoints": ["EUNIV-MAIN-AGG1", "EUNIV-MAIN-PE2"]},
    "MAINPE1-PE2": {"prefix": "2001:db8:e011:1ace:114::/126", "endpoints": ["EUNIV-MAIN-PE1", "EUNIV-MAIN-PE2"]},
    # Medical Campus Links
    "CORE2-MEDAGG": {"prefix": "2001:db8:e011:1ace:120::/126", "endpoints": ["EUNIV-CORE2", "EUNIV-MED-AGG1"]},
    "CORE3-MEDAGG": {"prefix": "2001:db8:e011:1ace:121::/126", "endpoints": ["EUNIV-CORE3", "EUNIV-MED-AGG1"]},
    "MEDAGG-PE1": {"prefix": "2001:db8:e011:1ace:122::/126", "endpoints": ["EUNIV-MED-AGG1", "EUNIV-MED-PE1"]},
    "MEDAGG-PE2": {"prefix": "2001:db8:e011:1ace:123::/126", "endpoints": ["EUNIV-MED-AGG1", "EUNIV-MED-PE2"]},
    "MEDPE1-PE2": {"prefix": "2001:db8:e011:1ace:124::/126", "endpoints": ["EUNIV-MED-PE1", "EUNIV-MED-PE2"]},
    # Research Campus Links
    "CORE4-RESAGG": {"prefix": "2001:db8:e011:1ace:130::/126", "endpoints": ["EUNIV-CORE4", "EUNIV-RES-AGG1"]},
    "CORE5-RESAGG": {"prefix": "2001:db8:e011:1ace:131::/126", "endpoints": ["EUNIV-CORE5", "EUNIV-RES-AGG1"]},
    "RESAGG-PE1": {"prefix": "2001:db8:e011:1ace:132::/126", "endpoints": ["EUNIV-RES-AGG1", "EUNIV-RES-PE1"]},
    "RESAGG-PE2": {"prefix": "2001:db8:e011:1ace:133::/126", "endpoints": ["EUNIV-RES-AGG1", "EUNIV-RES-PE2"]},
    "RESPE1-PE2": {"prefix": "2001:db8:e011:1ace:134::/126", "endpoints": ["EUNIV-RES-PE1", "EUNIV-RES-PE2"]},
}

# All device definitions
DEVICES = {
    # =========================================================================
    # CORE ROUTERS
    # =========================================================================
    "EUNIV-CORE1": {
        "role": "Core Router / Route Reflector",
        "template": "core_router.j2",
        "mgmt_ip": "192.168.68.200",
        "loopback_ip": "10.255.0.1",
        "loopback_ipv6": "2001:db8:e011::1",
        "bgp_asn": "65000",
        "is_route_reflector": True,
        "rr_cluster_id": "10.255.0.12",
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.0.1", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:1::1/126", "description": "To EUNIV-CORE2"},
            {"name": "GigabitEthernet3", "ip": "10.0.0.18", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:5::2/126", "description": "To EUNIV-CORE5"},
            {"name": "GigabitEthernet4", "ip": "10.0.0.21", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:101::1/126", "description": "To EUNIV-INET-GW1"},
            {"name": "GigabitEthernet5", "ip": "10.0.1.1", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:110::1/126", "description": "To EUNIV-MAIN-AGG1"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.0.2", "ipv6": "2001:db8:e011::2", "remote_as": "65000", "description": "EUNIV-CORE2"},
            {"ip": "10.255.0.3", "ipv6": "2001:db8:e011::3", "remote_as": "65000", "description": "EUNIV-CORE3"},
            {"ip": "10.255.0.4", "ipv6": "2001:db8:e011::4", "remote_as": "65000", "description": "EUNIV-CORE4"},
            {"ip": "10.255.0.5", "ipv6": "2001:db8:e011::5", "remote_as": "65000", "description": "EUNIV-CORE5"},
            {"ip": "10.255.0.101", "ipv6": "2001:db8:e011::101", "remote_as": "65000", "description": "EUNIV-INET-GW1"},
            {"ip": "10.255.1.1", "ipv6": "2001:db8:e011:1::1", "remote_as": "65000", "description": "EUNIV-MAIN-AGG1"},
        ],
    },
    "EUNIV-CORE2": {
        "role": "Core Router / Route Reflector",
        "template": "core_router.j2",
        "mgmt_ip": "192.168.68.202",
        "loopback_ip": "10.255.0.2",
        "loopback_ipv6": "2001:db8:e011::2",
        "bgp_asn": "65000",
        "is_route_reflector": True,
        "rr_cluster_id": "10.255.0.12",
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.0.2", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:1::2/126", "description": "To EUNIV-CORE1"},
            {"name": "GigabitEthernet3", "ip": "10.0.0.5", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:2::1/126", "description": "To EUNIV-CORE3"},
            {"name": "GigabitEthernet4", "ip": "10.0.0.25", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:102::1/126", "description": "To EUNIV-INET-GW2"},
            {"name": "GigabitEthernet5", "ip": "10.0.1.5", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:111::1/126", "description": "To EUNIV-MAIN-AGG1"},
            {"name": "GigabitEthernet6", "ip": "10.0.2.1", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:120::1/126", "description": "To EUNIV-MED-AGG1"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.0.1", "ipv6": "2001:db8:e011::1", "remote_as": "65000", "description": "EUNIV-CORE1"},
            {"ip": "10.255.0.3", "ipv6": "2001:db8:e011::3", "remote_as": "65000", "description": "EUNIV-CORE3"},
            {"ip": "10.255.0.5", "ipv6": "2001:db8:e011::5", "remote_as": "65000", "description": "EUNIV-CORE5"},
            {"ip": "10.255.0.102", "ipv6": "2001:db8:e011::102", "remote_as": "65000", "description": "EUNIV-INET-GW2"},
            {"ip": "10.255.1.1", "ipv6": "2001:db8:e011:1::1", "remote_as": "65000", "description": "EUNIV-MAIN-AGG1"},
            {"ip": "10.255.2.1", "ipv6": "2001:db8:e011:2::1", "remote_as": "65000", "description": "EUNIV-MED-AGG1"},
        ],
    },
    "EUNIV-CORE3": {
        "role": "Core Router / P Router",
        "template": "core_router.j2",
        "mgmt_ip": "192.168.68.203",
        "loopback_ip": "10.255.0.3",
        "loopback_ipv6": "2001:db8:e011::3",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.0.6", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:2::2/126", "description": "To EUNIV-CORE2"},
            {"name": "GigabitEthernet3", "ip": "10.0.0.9", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:3::1/126", "description": "To EUNIV-CORE4"},
            {"name": "GigabitEthernet4", "ip": "10.0.2.5", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:121::1/126", "description": "To EUNIV-MED-AGG1"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.0.1", "ipv6": "2001:db8:e011::1", "remote_as": "65000", "description": "EUNIV-CORE1 (RR)"},
            {"ip": "10.255.0.2", "ipv6": "2001:db8:e011::2", "remote_as": "65000", "description": "EUNIV-CORE2 (RR)"},
        ],
    },
    "EUNIV-CORE4": {
        "role": "Core Router / P Router",
        "template": "core_router.j2",
        "mgmt_ip": "192.168.68.204",
        "loopback_ip": "10.255.0.4",
        "loopback_ipv6": "2001:db8:e011::4",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.0.10", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:3::2/126", "description": "To EUNIV-CORE3"},
            {"name": "GigabitEthernet3", "ip": "10.0.0.13", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:4::1/126", "description": "To EUNIV-CORE5"},
            {"name": "GigabitEthernet4", "ip": "10.0.3.1", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:130::1/126", "description": "To EUNIV-RES-AGG1"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.0.1", "ipv6": "2001:db8:e011::1", "remote_as": "65000", "description": "EUNIV-CORE1 (RR)"},
            {"ip": "10.255.0.5", "ipv6": "2001:db8:e011::5", "remote_as": "65000", "description": "EUNIV-CORE5 (RR)"},
        ],
    },
    "EUNIV-CORE5": {
        "role": "Core Router / Route Reflector",
        "template": "core_router.j2",
        "mgmt_ip": "192.168.68.205",
        "loopback_ip": "10.255.0.5",
        "loopback_ipv6": "2001:db8:e011::5",
        "bgp_asn": "65000",
        "is_route_reflector": True,
        "rr_cluster_id": "10.255.0.5",
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.0.14", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:4::2/126", "description": "To EUNIV-CORE4"},
            {"name": "GigabitEthernet3", "ip": "10.0.0.17", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:5::1/126", "description": "To EUNIV-CORE1"},
            {"name": "GigabitEthernet4", "ip": "10.0.3.5", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:131::1/126", "description": "To EUNIV-RES-AGG1"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.0.1", "ipv6": "2001:db8:e011::1", "remote_as": "65000", "description": "EUNIV-CORE1"},
            {"ip": "10.255.0.2", "ipv6": "2001:db8:e011::2", "remote_as": "65000", "description": "EUNIV-CORE2"},
            {"ip": "10.255.0.4", "ipv6": "2001:db8:e011::4", "remote_as": "65000", "description": "EUNIV-CORE4"},
            {"ip": "10.255.3.1", "ipv6": "2001:db8:e011:3::1", "remote_as": "65000", "description": "EUNIV-RES-AGG1"},
        ],
    },

    # =========================================================================
    # INTERNET GATEWAYS
    # =========================================================================
    "EUNIV-INET-GW1": {
        "role": "Internet Gateway",
        "template": "core_router.j2",
        "mgmt_ip": "192.168.68.206",
        "loopback_ip": "10.255.0.101",
        "loopback_ipv6": "2001:db8:e011::101",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.0.22", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:101::2/126", "description": "To EUNIV-CORE1"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.0.1", "ipv6": "2001:db8:e011::1", "remote_as": "65000", "description": "EUNIV-CORE1 (RR)"},
            {"ip": "10.255.0.2", "ipv6": "2001:db8:e011::2", "remote_as": "65000", "description": "EUNIV-CORE2 (RR)"},
        ],
    },
    "EUNIV-INET-GW2": {
        "role": "Internet Gateway",
        "template": "core_router.j2",
        "mgmt_ip": "192.168.68.207",
        "loopback_ip": "10.255.0.102",
        "loopback_ipv6": "2001:db8:e011::102",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.0.26", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:102::2/126", "description": "To EUNIV-CORE2"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.0.1", "ipv6": "2001:db8:e011::1", "remote_as": "65000", "description": "EUNIV-CORE1 (RR)"},
            {"ip": "10.255.0.2", "ipv6": "2001:db8:e011::2", "remote_as": "65000", "description": "EUNIV-CORE2 (RR)"},
        ],
    },

    # =========================================================================
    # MAIN CAMPUS
    # =========================================================================
    "EUNIV-MAIN-AGG1": {
        "role": "Main Campus Aggregation",
        "template": "core_router.j2",
        "mgmt_ip": "192.168.68.208",
        "loopback_ip": "10.255.1.1",
        "loopback_ipv6": "2001:db8:e011:1::1",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.1.2", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:110::2/126", "description": "To EUNIV-CORE1"},
            {"name": "GigabitEthernet3", "ip": "10.0.1.6", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:111::2/126", "description": "To EUNIV-CORE2"},
            {"name": "GigabitEthernet4", "ip": "10.0.1.9", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:112::1/126", "description": "To EUNIV-MAIN-PE1"},
            {"name": "GigabitEthernet5", "ip": "10.0.1.13", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:113::1/126", "description": "To EUNIV-MAIN-PE2"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.0.1", "ipv6": "2001:db8:e011::1", "remote_as": "65000", "description": "EUNIV-CORE1 (RR)"},
            {"ip": "10.255.0.2", "ipv6": "2001:db8:e011::2", "remote_as": "65000", "description": "EUNIV-CORE2 (RR)"},
            {"ip": "10.255.1.11", "ipv6": "2001:db8:e011:1::11", "remote_as": "65000", "description": "EUNIV-MAIN-PE1"},
            {"ip": "10.255.1.12", "ipv6": "2001:db8:e011:1::12", "remote_as": "65000", "description": "EUNIV-MAIN-PE2"},
        ],
    },
    "EUNIV-MAIN-PE1": {
        "role": "Main Campus PE/BNG",
        "template": "pe_router.j2",
        "mgmt_ip": "192.168.68.209",
        "loopback_ip": "10.255.1.11",
        "loopback_ipv6": "2001:db8:e011:1::11",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.1.10", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:112::2/126", "description": "To EUNIV-MAIN-AGG1"},
            {"name": "GigabitEthernet3", "ip": "10.0.1.17", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:114::1/126", "description": "To EUNIV-MAIN-PE2 (HA)"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.1.1", "ipv6": "2001:db8:e011:1::1", "remote_as": "65000", "description": "EUNIV-MAIN-AGG1"},
        ],
        "vrfs": ["STUDENT-NET", "STAFF-NET", "RESEARCH-NET", "GUEST-NET"],
    },
    "EUNIV-MAIN-PE2": {
        "role": "Main Campus PE/BNG",
        "template": "pe_router.j2",
        "mgmt_ip": "192.168.68.210",
        "loopback_ip": "10.255.1.12",
        "loopback_ipv6": "2001:db8:e011:1::12",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.1.14", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:113::2/126", "description": "To EUNIV-MAIN-AGG1"},
            {"name": "GigabitEthernet3", "ip": "10.0.1.18", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:114::2/126", "description": "To EUNIV-MAIN-PE1 (HA)"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.1.1", "ipv6": "2001:db8:e011:1::1", "remote_as": "65000", "description": "EUNIV-MAIN-AGG1"},
        ],
        "vrfs": ["STUDENT-NET", "STAFF-NET", "RESEARCH-NET", "GUEST-NET"],
    },

    # =========================================================================
    # MEDICAL CAMPUS
    # =========================================================================
    "EUNIV-MED-AGG1": {
        "role": "Medical Campus Aggregation",
        "template": "core_router.j2",
        "mgmt_ip": "192.168.68.211",
        "loopback_ip": "10.255.2.1",
        "loopback_ipv6": "2001:db8:e011:2::1",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.2.2", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:120::2/126", "description": "To EUNIV-CORE2"},
            {"name": "GigabitEthernet3", "ip": "10.0.2.6", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:121::2/126", "description": "To EUNIV-CORE3"},
            {"name": "GigabitEthernet4", "ip": "10.0.2.9", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:122::1/126", "description": "To EUNIV-MED-PE1"},
            {"name": "GigabitEthernet5", "ip": "10.0.2.13", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:123::1/126", "description": "To EUNIV-MED-PE2"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.0.1", "ipv6": "2001:db8:e011::1", "remote_as": "65000", "description": "EUNIV-CORE1 (RR)"},
            {"ip": "10.255.0.2", "ipv6": "2001:db8:e011::2", "remote_as": "65000", "description": "EUNIV-CORE2 (RR)"},
            {"ip": "10.255.2.11", "ipv6": "2001:db8:e011:2::11", "remote_as": "65000", "description": "EUNIV-MED-PE1"},
            {"ip": "10.255.2.12", "ipv6": "2001:db8:e011:2::12", "remote_as": "65000", "description": "EUNIV-MED-PE2"},
        ],
    },
    "EUNIV-MED-PE1": {
        "role": "Medical Campus PE/BNG",
        "template": "pe_router.j2",
        "mgmt_ip": "192.168.68.212",
        "loopback_ip": "10.255.2.11",
        "loopback_ipv6": "2001:db8:e011:2::11",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.2.10", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:122::2/126", "description": "To EUNIV-MED-AGG1"},
            {"name": "GigabitEthernet3", "ip": "10.0.2.17", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:124::1/126", "description": "To EUNIV-MED-PE2 (HA)"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.2.1", "ipv6": "2001:db8:e011:2::1", "remote_as": "65000", "description": "EUNIV-MED-AGG1"},
        ],
        "vrfs": ["STAFF-NET", "RESEARCH-NET", "MEDICAL-NET", "GUEST-NET"],
    },
    "EUNIV-MED-PE2": {
        "role": "Medical Campus PE/BNG",
        "template": "pe_router.j2",
        "mgmt_ip": "192.168.68.213",
        "loopback_ip": "10.255.2.12",
        "loopback_ipv6": "2001:db8:e011:2::12",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.2.14", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:123::2/126", "description": "To EUNIV-MED-AGG1"},
            {"name": "GigabitEthernet3", "ip": "10.0.2.18", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:124::2/126", "description": "To EUNIV-MED-PE1 (HA)"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.2.1", "ipv6": "2001:db8:e011:2::1", "remote_as": "65000", "description": "EUNIV-MED-AGG1"},
        ],
        "vrfs": ["STAFF-NET", "RESEARCH-NET", "MEDICAL-NET", "GUEST-NET"],
    },

    # =========================================================================
    # RESEARCH CAMPUS
    # =========================================================================
    "EUNIV-RES-AGG1": {
        "role": "Research Campus Aggregation",
        "template": "core_router.j2",
        "mgmt_ip": "192.168.68.214",
        "loopback_ip": "10.255.3.1",
        "loopback_ipv6": "2001:db8:e011:3::1",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.3.2", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:130::2/126", "description": "To EUNIV-CORE4"},
            {"name": "GigabitEthernet3", "ip": "10.0.3.6", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:131::2/126", "description": "To EUNIV-CORE5"},
            {"name": "GigabitEthernet4", "ip": "10.0.3.9", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:132::1/126", "description": "To EUNIV-RES-PE1"},
            {"name": "GigabitEthernet5", "ip": "10.0.3.13", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:133::1/126", "description": "To EUNIV-RES-PE2"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.0.1", "ipv6": "2001:db8:e011::1", "remote_as": "65000", "description": "EUNIV-CORE1 (RR)"},
            {"ip": "10.255.0.5", "ipv6": "2001:db8:e011::5", "remote_as": "65000", "description": "EUNIV-CORE5 (RR)"},
            {"ip": "10.255.3.11", "ipv6": "2001:db8:e011:3::11", "remote_as": "65000", "description": "EUNIV-RES-PE1"},
            {"ip": "10.255.3.12", "ipv6": "2001:db8:e011:3::12", "remote_as": "65000", "description": "EUNIV-RES-PE2"},
        ],
    },
    "EUNIV-RES-PE1": {
        "role": "Research Campus PE/BNG",
        "template": "pe_router.j2",
        "mgmt_ip": "192.168.68.215",
        "loopback_ip": "10.255.3.11",
        "loopback_ipv6": "2001:db8:e011:3::11",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.3.10", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:132::2/126", "description": "To EUNIV-RES-AGG1"},
            {"name": "GigabitEthernet3", "ip": "10.0.3.17", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:134::1/126", "description": "To EUNIV-RES-PE2 (HA)"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.3.1", "ipv6": "2001:db8:e011:3::1", "remote_as": "65000", "description": "EUNIV-RES-AGG1"},
        ],
        "vrfs": ["STAFF-NET", "RESEARCH-NET", "GUEST-NET"],
    },
    "EUNIV-RES-PE2": {
        "role": "Research Campus PE/BNG",
        "template": "pe_router.j2",
        "mgmt_ip": "192.168.68.216",
        "loopback_ip": "10.255.3.12",
        "loopback_ipv6": "2001:db8:e011:3::12",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.3.14", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:133::2/126", "description": "To EUNIV-RES-AGG1"},
            {"name": "GigabitEthernet3", "ip": "10.0.3.18", "mask": "255.255.255.252", "ipv6": "2001:db8:e011:1ace:134::2/126", "description": "To EUNIV-RES-PE1 (HA)"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.3.1", "ipv6": "2001:db8:e011:3::1", "remote_as": "65000", "description": "EUNIV-RES-AGG1"},
        ],
        "vrfs": ["STAFF-NET", "RESEARCH-NET", "GUEST-NET"],
    },
}

# =============================================================================
# LAYER 2 SECURITY CONFIGURATION
# =============================================================================

# RADIUS Server Configuration
RADIUS_CONFIG = {
    "server_name": "EUNIV-RADIUS",
    "server_ip": os.getenv("RADIUS_SERVER_IP", "192.168.68.69"),  # Docker host IP
    "auth_port": 1812,
    "acct_port": 1813,
    "secret": os.getenv("RADIUS_SECRET", "euniv-radius-secret"),
    "timeout": 5,
    "retransmit": 3,
}

# VLAN Definitions for Access Switches
L2_VLANS = {
    10: {"name": "STAFF", "description": "Staff and faculty network", "vrf": "STAFF-NET"},
    20: {"name": "RESEARCH", "description": "Research partner network", "vrf": "RESEARCH-NET"},
    30: {"name": "MEDICAL", "description": "HIPAA medical network", "vrf": "MEDICAL-NET"},
    40: {"name": "GUEST", "description": "Guest/visitor network", "vrf": "GUEST-NET"},
    99: {"name": "MGMT", "description": "Switch management", "vrf": None},
    100: {"name": "INFRA", "description": "Infrastructure (RADIUS, monitoring)", "vrf": None},
}

# L2 Security Settings
L2_SECURITY = {
    # DHCP Snooping
    "dhcp_snooping_vlans": [10, 20, 30, 40],

    # Dynamic ARP Inspection
    "dai_vlans": [10, 20, 30, 40],

    # Port Security
    "port_security": {
        "max_mac_addresses": 3,
        "violation_action": "restrict",  # protect, restrict, or shutdown
        "aging_time": 120,
    },

    # Storm Control (percentage thresholds)
    "storm_control": {
        "broadcast": 10.0,
        "multicast": 10.0,
        "unicast": 80.0,
    },

    # 802.1X Settings
    "dot1x": {
        "reauth_period": 3600,
        "tx_period": 10,
        "quiet_period": 60,
        "host_mode": "multi-auth",  # single-host, multi-host, multi-domain, multi-auth
    },
}

# Access Switch Definitions
ACCESS_SWITCHES = {
    "EUNIV-MED-ASW1": {
        "role": "Medical Campus Access Switch",
        "platform": "cat9k",
        "mgmt_ip": "192.168.68.217",
        "mgmt_interface": "GigabitEthernet0/0",
        "campus": "medical",
        "uplinks": [
            {
                "interface": "GigabitEthernet1/0/1",
                "description": "Trunk to EUNIV-MED-EDGE1",
                "mode": "trunk",
                "allowed_vlans": "10,20,30,40,99,100",
                "native_vlan": 99,
            },
            {
                "interface": "GigabitEthernet1/0/2",
                "description": "Trunk to EUNIV-MED-EDGE2",
                "mode": "trunk",
                "allowed_vlans": "10,20,30,40,99,100",
                "native_vlan": 99,
            },
        ],
        "access_ports": [
            {
                "interface": "GigabitEthernet1/0/3",
                "description": "RADIUS Server",
                "mode": "access",
                "vlan": 100,
                "dot1x": False,  # Static port for infrastructure
            },
            {
                "interface": "GigabitEthernet1/0/4",
                "description": "802.1X User Port",
                "mode": "access",
                "vlan": 10,  # Default VLAN before auth
                "dot1x": True,
            },
            {
                "interface": "GigabitEthernet1/0/5",
                "description": "802.1X User Port",
                "mode": "access",
                "vlan": 10,
                "dot1x": True,
            },
            {
                "interface": "GigabitEthernet1/0/6",
                "description": "802.1X User Port",
                "mode": "access",
                "vlan": 10,
                "dot1x": True,
            },
            {
                "interface": "GigabitEthernet1/0/7",
                "description": "802.1X User Port",
                "mode": "access",
                "vlan": 10,
                "dot1x": True,
            },
            {
                "interface": "GigabitEthernet1/0/8",
                "description": "802.1X User Port",
                "mode": "access",
                "vlan": 10,
                "dot1x": True,
            },
        ],
    },
    # Main Campus Access Switch
    "EUNIV-MAIN-ASW1": {
        "role": "Main Campus Access Switch",
        "platform": "cat9k",
        "mgmt_ip": "192.168.68.253",
        "mgmt_interface": "GigabitEthernet0/0",
        "campus": "main",
        "uplinks": [
            {
                "interface": "GigabitEthernet1/0/1",
                "description": "Trunk to EUNIV-MAIN-EDGE1",
                "mode": "trunk",
                "allowed_vlans": "10,20,40,99,100",
                "native_vlan": 99,
            },
            {
                "interface": "GigabitEthernet1/0/2",
                "description": "Trunk to EUNIV-MAIN-EDGE2",
                "mode": "trunk",
                "allowed_vlans": "10,20,40,99,100",
                "native_vlan": 99,
            },
        ],
        "access_ports": [
            {
                "interface": "GigabitEthernet1/0/3",
                "description": "Infrastructure Port",
                "mode": "access",
                "vlan": 100,
                "dot1x": False,
            },
            {
                "interface": "GigabitEthernet1/0/4",
                "description": "802.1X User Port",
                "mode": "access",
                "vlan": 10,
                "dot1x": True,
            },
            {
                "interface": "GigabitEthernet1/0/5",
                "description": "802.1X User Port",
                "mode": "access",
                "vlan": 10,
                "dot1x": True,
            },
            {
                "interface": "GigabitEthernet1/0/6",
                "description": "802.1X User Port",
                "mode": "access",
                "vlan": 10,
                "dot1x": True,
            },
            {
                "interface": "GigabitEthernet1/0/7",
                "description": "802.1X User Port",
                "mode": "access",
                "vlan": 10,
                "dot1x": True,
            },
            {
                "interface": "GigabitEthernet1/0/8",
                "description": "802.1X User Port",
                "mode": "access",
                "vlan": 10,
                "dot1x": True,
            },
        ],
    },
    # Research Campus Access Switch
    "EUNIV-RES-ASW1": {
        "role": "Research Campus Access Switch",
        "platform": "cat9k",
        "mgmt_ip": "192.168.68.252",
        "mgmt_interface": "GigabitEthernet0/0",
        "campus": "research",
        "uplinks": [
            {
                "interface": "GigabitEthernet1/0/1",
                "description": "Trunk to EUNIV-RES-EDGE1",
                "mode": "trunk",
                "allowed_vlans": "10,20,40,99,100",
                "native_vlan": 99,
            },
            {
                "interface": "GigabitEthernet1/0/2",
                "description": "Trunk to EUNIV-RES-EDGE2",
                "mode": "trunk",
                "allowed_vlans": "10,20,40,99,100",
                "native_vlan": 99,
            },
        ],
        "access_ports": [
            {
                "interface": "GigabitEthernet1/0/3",
                "description": "Infrastructure Port",
                "mode": "access",
                "vlan": 100,
                "dot1x": False,
            },
            {
                "interface": "GigabitEthernet1/0/4",
                "description": "802.1X User Port",
                "mode": "access",
                "vlan": 20,  # Default to RESEARCH VLAN
                "dot1x": True,
            },
            {
                "interface": "GigabitEthernet1/0/5",
                "description": "802.1X User Port",
                "mode": "access",
                "vlan": 20,
                "dot1x": True,
            },
            {
                "interface": "GigabitEthernet1/0/6",
                "description": "802.1X User Port",
                "mode": "access",
                "vlan": 20,
                "dot1x": True,
            },
            {
                "interface": "GigabitEthernet1/0/7",
                "description": "802.1X User Port",
                "mode": "access",
                "vlan": 20,
                "dot1x": True,
            },
            {
                "interface": "GigabitEthernet1/0/8",
                "description": "802.1X User Port",
                "mode": "access",
                "vlan": 20,
                "dot1x": True,
            },
        ],
    },
}

# =============================================================================
# QoS CONFIGURATION (VRF-Based Marking)
# =============================================================================

# DSCP markings per VRF - traffic marked at PE ingress
QOS_VRF_MARKINGS = {
    "MEDICAL-NET": {
        "dscp": "ef",           # DSCP 46 - Expedited Forwarding
        "dscp_value": 46,
        "description": "HIPAA critical medical applications",
        "priority": 1,          # Highest priority
        "bandwidth_percent": 20,  # Guaranteed bandwidth
        "queue": "PRIORITY",
    },
    "STAFF-NET": {
        "dscp": "af31",         # DSCP 26 - Assured Forwarding Class 3
        "dscp_value": 26,
        "description": "Business-critical staff applications",
        "priority": 2,
        "bandwidth_percent": 25,
        "queue": "AF3",
    },
    "RESEARCH-NET": {
        "dscp": "af21",         # DSCP 18 - Assured Forwarding Class 2
        "dscp_value": 18,
        "description": "Research data transfers and collaboration",
        "priority": 3,
        "bandwidth_percent": 30,  # Higher bandwidth for bulk transfers
        "queue": "AF2",
    },
    "STUDENT-NET": {
        "dscp": "default",      # DSCP 0 - Best Effort
        "dscp_value": 0,
        "description": "General student network traffic",
        "priority": 4,
        "bandwidth_percent": 20,
        "queue": "BE",
    },
    "GUEST-NET": {
        "dscp": "cs1",          # DSCP 8 - Scavenger/Bulk
        "dscp_value": 8,
        "description": "Guest/visitor low-priority traffic",
        "priority": 5,          # Lowest priority
        "bandwidth_percent": 5,
        "queue": "SCAVENGER",
    },
}

# QoS Class-Map definitions (used by policy-maps)
QOS_CLASS_MAPS = {
    "MEDICAL-TRAFFIC": {
        "match_type": "match-any",
        "match_criteria": [
            {"type": "vrf", "value": "MEDICAL-NET"},
            {"type": "dscp", "value": "ef"},
        ],
    },
    "STAFF-TRAFFIC": {
        "match_type": "match-any",
        "match_criteria": [
            {"type": "vrf", "value": "STAFF-NET"},
            {"type": "dscp", "value": "af31"},
        ],
    },
    "RESEARCH-TRAFFIC": {
        "match_type": "match-any",
        "match_criteria": [
            {"type": "vrf", "value": "RESEARCH-NET"},
            {"type": "dscp", "value": "af21"},
        ],
    },
    "STUDENT-TRAFFIC": {
        "match_type": "match-any",
        "match_criteria": [
            {"type": "vrf", "value": "STUDENT-NET"},
            {"type": "dscp", "value": "default"},
        ],
    },
    "GUEST-TRAFFIC": {
        "match_type": "match-any",
        "match_criteria": [
            {"type": "vrf", "value": "GUEST-NET"},
            {"type": "dscp", "value": "cs1"},
        ],
    },
}

# QoS Policy-Map definitions
QOS_POLICY_MAPS = {
    # Ingress marking policy (applied to VRF interfaces)
    "EUNIV-VRF-MARKING": {
        "description": "Mark traffic based on source VRF",
        "direction": "input",
        "classes": {
            "MEDICAL-TRAFFIC": {"action": "set dscp ef", "police_rate": None},
            "STAFF-TRAFFIC": {"action": "set dscp af31", "police_rate": None},
            "RESEARCH-TRAFFIC": {"action": "set dscp af21", "police_rate": None},
            "STUDENT-TRAFFIC": {"action": "set dscp default", "police_rate": None},
            "GUEST-TRAFFIC": {"action": "set dscp cs1", "police_rate": "50m"},  # Rate limit guests
        },
    },
    # Egress queuing policy (applied to uplinks)
    "EUNIV-QOS-QUEUING": {
        "description": "Queue traffic based on DSCP markings",
        "direction": "output",
        "classes": {
            "MEDICAL-TRAFFIC": {"bandwidth_percent": 20, "priority": True},
            "STAFF-TRAFFIC": {"bandwidth_percent": 25, "priority": False},
            "RESEARCH-TRAFFIC": {"bandwidth_percent": 30, "priority": False},
            "STUDENT-TRAFFIC": {"bandwidth_percent": 20, "priority": False},
            "GUEST-TRAFFIC": {"bandwidth_percent": 5, "priority": False},
        },
    },
}

# Edge devices where QoS policies should be applied
QOS_EDGE_DEVICES = [
    "EUNIV-MAIN-EDGE1", "EUNIV-MAIN-EDGE2",
    "EUNIV-MED-EDGE1", "EUNIV-MED-EDGE2",
    "EUNIV-RES-EDGE1", "EUNIV-RES-EDGE2",
]

# VRFs per Edge device (which VRFs need marking on each device)
QOS_EDGE_VRFS = {
    "EUNIV-MAIN-EDGE1": ["STUDENT-NET", "STAFF-NET", "RESEARCH-NET", "GUEST-NET"],
    "EUNIV-MAIN-EDGE2": ["STUDENT-NET", "STAFF-NET", "RESEARCH-NET", "GUEST-NET"],
    "EUNIV-MED-EDGE1": ["STAFF-NET", "RESEARCH-NET", "MEDICAL-NET", "GUEST-NET"],
    "EUNIV-MED-EDGE2": ["STAFF-NET", "RESEARCH-NET", "MEDICAL-NET", "GUEST-NET"],
    "EUNIV-RES-EDGE1": ["STAFF-NET", "RESEARCH-NET", "GUEST-NET"],
    "EUNIV-RES-EDGE2": ["STAFF-NET", "RESEARCH-NET", "GUEST-NET"],
}

# =============================================================================
# ACCESS LAYER SVI CONFIGURATION (Edge Router Downstream Interfaces)
# =============================================================================
# These are the subinterfaces on Gi4 (downstream to access switches)
# They provide the gateway for end users and run HSRP for redundancy

# Interface facing access switches
ACCESS_DOWNSTREAM_INTERFACE = "GigabitEthernet4"

# DHCP Server for ip helper-address (Docker host)
DHCP_SERVER_IP = os.getenv("DHCP_SERVER_IP", "192.168.68.69")

# HSRP Configuration
HSRP_CONFIG = {
    "priority_active": 110,      # Priority for designated active router
    "priority_standby": 100,     # Default priority (standby)
    "hello_interval": 1,         # Fast hello timer (seconds)
    "hold_time": 3,              # Fast hold timer (seconds)
    "preempt": True,             # Enable preemption for failback
    "version": 2,                # HSRP version 2 (recommended)
}

# Access Layer SVI Configuration per Campus
# Maps VLAN ID to VRF and HSRP active router for load balancing
ACCESS_LAYER_SVIS = {
    "main": {
        "edge1": "EUNIV-MAIN-EDGE1",
        "edge2": "EUNIV-MAIN-EDGE2",
        "subnet_prefix": "10.1",  # 10.1.VLAN.0/24
        "vlans": {
            10: {
                "name": "STAFF",
                "vrf": "STAFF-NET",
                "hsrp_active": "edge1",  # EDGE1 is active for VLAN 10
                "hsrp_group": 10,
            },
            20: {
                "name": "RESEARCH",
                "vrf": "RESEARCH-NET",
                "hsrp_active": "edge2",  # EDGE2 is active for VLAN 20 (load balance)
                "hsrp_group": 20,
            },
            40: {
                "name": "GUEST",
                "vrf": "GUEST-NET",
                "hsrp_active": "edge1",  # EDGE1 is active for VLAN 40
                "hsrp_group": 40,
            },
        },
    },
    "medical": {
        "edge1": "EUNIV-MED-EDGE1",
        "edge2": "EUNIV-MED-EDGE2",
        "subnet_prefix": "10.2",  # 10.2.VLAN.0/24
        "vlans": {
            10: {
                "name": "STAFF",
                "vrf": "STAFF-NET",
                "hsrp_active": "edge1",
                "hsrp_group": 10,
            },
            20: {
                "name": "RESEARCH",
                "vrf": "RESEARCH-NET",
                "hsrp_active": "edge2",
                "hsrp_group": 20,
            },
            30: {
                "name": "MEDICAL",
                "vrf": "MEDICAL-NET",
                "hsrp_active": "edge2",  # EDGE2 active for MEDICAL (critical traffic)
                "hsrp_group": 30,
            },
            40: {
                "name": "GUEST",
                "vrf": "GUEST-NET",
                "hsrp_active": "edge1",
                "hsrp_group": 40,
            },
        },
    },
    "research": {
        "edge1": "EUNIV-RES-EDGE1",
        "edge2": "EUNIV-RES-EDGE2",
        "subnet_prefix": "10.3",  # 10.3.VLAN.0/24
        "vlans": {
            10: {
                "name": "STAFF",
                "vrf": "STAFF-NET",
                "hsrp_active": "edge1",
                "hsrp_group": 10,
            },
            20: {
                "name": "RESEARCH",
                "vrf": "RESEARCH-NET",
                "hsrp_active": "edge2",
                "hsrp_group": 20,
            },
            40: {
                "name": "GUEST",
                "vrf": "GUEST-NET",
                "hsrp_active": "edge1",
                "hsrp_group": 40,
            },
        },
    },
}


def get_svi_ip(campus: str, vlan_id: int, router: str) -> str:
    """
    Calculate IP address for an access layer SVI.

    Addressing scheme:
    - HSRP VIP:  <prefix>.<vlan>.1  (e.g., 10.1.10.1)
    - EDGE1:     <prefix>.<vlan>.2  (e.g., 10.1.10.2)
    - EDGE2:     <prefix>.<vlan>.3  (e.g., 10.1.10.3)

    Args:
        campus: Campus name (main, medical, research)
        vlan_id: VLAN ID (10, 20, 30, 40)
        router: "vip", "edge1", or "edge2"

    Returns:
        IP address string
    """
    config = ACCESS_LAYER_SVIS[campus]
    prefix = config["subnet_prefix"]

    if router == "vip":
        return f"{prefix}.{vlan_id}.1"
    elif router == "edge1":
        return f"{prefix}.{vlan_id}.2"
    elif router == "edge2":
        return f"{prefix}.{vlan_id}.3"
    else:
        raise ValueError(f"Unknown router type: {router}")
