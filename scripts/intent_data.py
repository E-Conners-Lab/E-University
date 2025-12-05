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
    "ntp_servers": ["10.255.255.10", "10.255.255.11"],
    "snmp_community": "euniv-mon-ro",
    "snmp_location": "E University Data Center",
    "snmp_contact": "noc@euniv.edu",
    "default_gateway": "192.168.68.1",
    "mgmt_mask": "255.255.252.0",
    "username": os.getenv("DEVICE_USERNAME", "admin"),
    "password": os.getenv("DEVICE_PASSWORD"),
    "enable_secret": os.getenv("DEVICE_ENABLE_PASSWORD"),
}

# VRF Definitions
VRFS = {
    "STUDENT-NET": {"rd_suffix": "100", "rt": "65000:100", "description": "Student residential network"},
    "STAFF-NET": {"rd_suffix": "200", "rt": "65000:200", "description": "Staff and faculty network"},
    "RESEARCH-NET": {"rd_suffix": "300", "rt": "65000:300", "description": "Research partner network"},
    "MEDICAL-NET": {"rd_suffix": "400", "rt": "65000:400", "description": "HIPAA medical network"},
    "GUEST-NET": {"rd_suffix": "500", "rt": "65000:500", "description": "Guest/visitor network"},
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
        "bgp_asn": "65000",
        "is_route_reflector": True,
        "rr_cluster_id": "10.255.0.12",
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.0.1", "mask": "255.255.255.252", "description": "To EUNIV-CORE2"},
            {"name": "GigabitEthernet3", "ip": "10.0.0.18", "mask": "255.255.255.252", "description": "To EUNIV-CORE5"},
            {"name": "GigabitEthernet4", "ip": "10.0.0.21", "mask": "255.255.255.252", "description": "To EUNIV-INET-GW1"},
            {"name": "GigabitEthernet5", "ip": "10.0.1.1", "mask": "255.255.255.252", "description": "To EUNIV-MAIN-AGG1"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.0.2", "remote_as": "65000", "description": "EUNIV-CORE2"},
            {"ip": "10.255.0.3", "remote_as": "65000", "description": "EUNIV-CORE3"},
            {"ip": "10.255.0.4", "remote_as": "65000", "description": "EUNIV-CORE4"},
            {"ip": "10.255.0.5", "remote_as": "65000", "description": "EUNIV-CORE5"},
            {"ip": "10.255.0.101", "remote_as": "65000", "description": "EUNIV-INET-GW1"},
            {"ip": "10.255.1.1", "remote_as": "65000", "description": "EUNIV-MAIN-AGG1"},
        ],
    },
    "EUNIV-CORE2": {
        "role": "Core Router / Route Reflector",
        "template": "core_router.j2",
        "mgmt_ip": "192.168.68.202",
        "loopback_ip": "10.255.0.2",
        "bgp_asn": "65000",
        "is_route_reflector": True,
        "rr_cluster_id": "10.255.0.12",
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.0.2", "mask": "255.255.255.252", "description": "To EUNIV-CORE1"},
            {"name": "GigabitEthernet3", "ip": "10.0.0.5", "mask": "255.255.255.252", "description": "To EUNIV-CORE3"},
            {"name": "GigabitEthernet4", "ip": "10.0.0.25", "mask": "255.255.255.252", "description": "To EUNIV-INET-GW2"},
            {"name": "GigabitEthernet5", "ip": "10.0.1.5", "mask": "255.255.255.252", "description": "To EUNIV-MAIN-AGG1"},
            {"name": "GigabitEthernet6", "ip": "10.0.2.1", "mask": "255.255.255.252", "description": "To EUNIV-MED-AGG1"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.0.1", "remote_as": "65000", "description": "EUNIV-CORE1"},
            {"ip": "10.255.0.3", "remote_as": "65000", "description": "EUNIV-CORE3"},
            {"ip": "10.255.0.4", "remote_as": "65000", "description": "EUNIV-CORE4"},
            {"ip": "10.255.0.5", "remote_as": "65000", "description": "EUNIV-CORE5"},
            {"ip": "10.255.0.102", "remote_as": "65000", "description": "EUNIV-INET-GW2"},
            {"ip": "10.255.1.1", "remote_as": "65000", "description": "EUNIV-MAIN-AGG1"},
            {"ip": "10.255.2.1", "remote_as": "65000", "description": "EUNIV-MED-AGG1"},
        ],
    },
    "EUNIV-CORE3": {
        "role": "Core Router / P Router",
        "template": "core_router.j2",
        "mgmt_ip": "192.168.68.203",
        "loopback_ip": "10.255.0.3",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.0.6", "mask": "255.255.255.252", "description": "To EUNIV-CORE2"},
            {"name": "GigabitEthernet3", "ip": "10.0.0.9", "mask": "255.255.255.252", "description": "To EUNIV-CORE4"},
            {"name": "GigabitEthernet4", "ip": "10.0.2.5", "mask": "255.255.255.252", "description": "To EUNIV-MED-AGG1"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.0.1", "remote_as": "65000", "description": "EUNIV-CORE1 (RR)"},
            {"ip": "10.255.0.2", "remote_as": "65000", "description": "EUNIV-CORE2 (RR)"},
        ],
    },
    "EUNIV-CORE4": {
        "role": "Core Router / P Router",
        "template": "core_router.j2",
        "mgmt_ip": "192.168.68.204",
        "loopback_ip": "10.255.0.4",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.0.10", "mask": "255.255.255.252", "description": "To EUNIV-CORE3"},
            {"name": "GigabitEthernet3", "ip": "10.0.0.13", "mask": "255.255.255.252", "description": "To EUNIV-CORE5"},
            {"name": "GigabitEthernet4", "ip": "10.0.3.1", "mask": "255.255.255.252", "description": "To EUNIV-RES-AGG1"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.0.1", "remote_as": "65000", "description": "EUNIV-CORE1 (RR)"},
            {"ip": "10.255.0.5", "remote_as": "65000", "description": "EUNIV-CORE5 (RR)"},
        ],
    },
    "EUNIV-CORE5": {
        "role": "Core Router / Route Reflector",
        "template": "core_router.j2",
        "mgmt_ip": "192.168.68.205",
        "loopback_ip": "10.255.0.5",
        "bgp_asn": "65000",
        "is_route_reflector": True,
        "rr_cluster_id": "10.255.0.5",
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.0.14", "mask": "255.255.255.252", "description": "To EUNIV-CORE4"},
            {"name": "GigabitEthernet3", "ip": "10.0.0.17", "mask": "255.255.255.252", "description": "To EUNIV-CORE1"},
            {"name": "GigabitEthernet4", "ip": "10.0.3.5", "mask": "255.255.255.252", "description": "To EUNIV-RES-AGG1"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.0.1", "remote_as": "65000", "description": "EUNIV-CORE1"},
            {"ip": "10.255.0.2", "remote_as": "65000", "description": "EUNIV-CORE2"},
            {"ip": "10.255.0.3", "remote_as": "65000", "description": "EUNIV-CORE3"},
            {"ip": "10.255.0.4", "remote_as": "65000", "description": "EUNIV-CORE4"},
            {"ip": "10.255.3.1", "remote_as": "65000", "description": "EUNIV-RES-AGG1"},
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
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.0.22", "mask": "255.255.255.252", "description": "To EUNIV-CORE1"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.0.1", "remote_as": "65000", "description": "EUNIV-CORE1 (RR)"},
            {"ip": "10.255.0.2", "remote_as": "65000", "description": "EUNIV-CORE2 (RR)"},
        ],
    },
    "EUNIV-INET-GW2": {
        "role": "Internet Gateway",
        "template": "core_router.j2",
        "mgmt_ip": "192.168.68.207",
        "loopback_ip": "10.255.0.102",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.0.26", "mask": "255.255.255.252", "description": "To EUNIV-CORE2"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.0.1", "remote_as": "65000", "description": "EUNIV-CORE1 (RR)"},
            {"ip": "10.255.0.2", "remote_as": "65000", "description": "EUNIV-CORE2 (RR)"},
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
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.1.2", "mask": "255.255.255.252", "description": "To EUNIV-CORE1"},
            {"name": "GigabitEthernet3", "ip": "10.0.1.6", "mask": "255.255.255.252", "description": "To EUNIV-CORE2"},
            {"name": "GigabitEthernet4", "ip": "10.0.1.9", "mask": "255.255.255.252", "description": "To EUNIV-MAIN-PE1"},
            {"name": "GigabitEthernet5", "ip": "10.0.1.13", "mask": "255.255.255.252", "description": "To EUNIV-MAIN-PE2"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.0.1", "remote_as": "65000", "description": "EUNIV-CORE1 (RR)"},
            {"ip": "10.255.0.2", "remote_as": "65000", "description": "EUNIV-CORE2 (RR)"},
            {"ip": "10.255.1.11", "remote_as": "65000", "description": "EUNIV-MAIN-PE1"},
            {"ip": "10.255.1.12", "remote_as": "65000", "description": "EUNIV-MAIN-PE2"},
        ],
    },
    "EUNIV-MAIN-PE1": {
        "role": "Main Campus PE/BNG",
        "template": "pe_router.j2",
        "mgmt_ip": "192.168.68.209",
        "loopback_ip": "10.255.1.11",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.1.10", "mask": "255.255.255.252", "description": "To EUNIV-MAIN-AGG1"},
            {"name": "GigabitEthernet3", "ip": "10.0.1.17", "mask": "255.255.255.252", "description": "To EUNIV-MAIN-PE2 (HA)"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.1.1", "remote_as": "65000", "description": "EUNIV-MAIN-AGG1"},
        ],
        "vrfs": ["STUDENT-NET", "STAFF-NET", "RESEARCH-NET", "GUEST-NET"],
    },
    "EUNIV-MAIN-PE2": {
        "role": "Main Campus PE/BNG",
        "template": "pe_router.j2",
        "mgmt_ip": "192.168.68.210",
        "loopback_ip": "10.255.1.12",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.1.14", "mask": "255.255.255.252", "description": "To EUNIV-MAIN-AGG1"},
            {"name": "GigabitEthernet3", "ip": "10.0.1.18", "mask": "255.255.255.252", "description": "To EUNIV-MAIN-PE1 (HA)"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.1.1", "remote_as": "65000", "description": "EUNIV-MAIN-AGG1"},
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
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.2.2", "mask": "255.255.255.252", "description": "To EUNIV-CORE2"},
            {"name": "GigabitEthernet3", "ip": "10.0.2.6", "mask": "255.255.255.252", "description": "To EUNIV-CORE3"},
            {"name": "GigabitEthernet4", "ip": "10.0.2.9", "mask": "255.255.255.252", "description": "To EUNIV-MED-PE1"},
            {"name": "GigabitEthernet5", "ip": "10.0.2.13", "mask": "255.255.255.252", "description": "To EUNIV-MED-PE2"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.0.1", "remote_as": "65000", "description": "EUNIV-CORE1 (RR)"},
            {"ip": "10.255.0.2", "remote_as": "65000", "description": "EUNIV-CORE2 (RR)"},
            {"ip": "10.255.2.11", "remote_as": "65000", "description": "EUNIV-MED-PE1"},
            {"ip": "10.255.2.12", "remote_as": "65000", "description": "EUNIV-MED-PE2"},
        ],
    },
    "EUNIV-MED-PE1": {
        "role": "Medical Campus PE/BNG",
        "template": "pe_router.j2",
        "mgmt_ip": "192.168.68.212",
        "loopback_ip": "10.255.2.11",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.2.10", "mask": "255.255.255.252", "description": "To EUNIV-MED-AGG1"},
            {"name": "GigabitEthernet3", "ip": "10.0.2.17", "mask": "255.255.255.252", "description": "To EUNIV-MED-PE2 (HA)"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.2.1", "remote_as": "65000", "description": "EUNIV-MED-AGG1"},
        ],
        "vrfs": ["STAFF-NET", "RESEARCH-NET", "MEDICAL-NET", "GUEST-NET"],
    },
    "EUNIV-MED-PE2": {
        "role": "Medical Campus PE/BNG",
        "template": "pe_router.j2",
        "mgmt_ip": "192.168.68.213",
        "loopback_ip": "10.255.2.12",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.2.14", "mask": "255.255.255.252", "description": "To EUNIV-MED-AGG1"},
            {"name": "GigabitEthernet3", "ip": "10.0.2.18", "mask": "255.255.255.252", "description": "To EUNIV-MED-PE1 (HA)"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.2.1", "remote_as": "65000", "description": "EUNIV-MED-AGG1"},
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
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.3.2", "mask": "255.255.255.252", "description": "To EUNIV-CORE4"},
            {"name": "GigabitEthernet3", "ip": "10.0.3.6", "mask": "255.255.255.252", "description": "To EUNIV-CORE5"},
            {"name": "GigabitEthernet4", "ip": "10.0.3.9", "mask": "255.255.255.252", "description": "To EUNIV-RES-PE1"},
            {"name": "GigabitEthernet5", "ip": "10.0.3.13", "mask": "255.255.255.252", "description": "To EUNIV-RES-PE2"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.0.1", "remote_as": "65000", "description": "EUNIV-CORE1 (RR)"},
            {"ip": "10.255.0.5", "remote_as": "65000", "description": "EUNIV-CORE5 (RR)"},
            {"ip": "10.255.3.11", "remote_as": "65000", "description": "EUNIV-RES-PE1"},
            {"ip": "10.255.3.12", "remote_as": "65000", "description": "EUNIV-RES-PE2"},
        ],
    },
    "EUNIV-RES-PE1": {
        "role": "Research Campus PE/BNG",
        "template": "pe_router.j2",
        "mgmt_ip": "192.168.68.215",
        "loopback_ip": "10.255.3.11",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.3.10", "mask": "255.255.255.252", "description": "To EUNIV-RES-AGG1"},
            {"name": "GigabitEthernet3", "ip": "10.0.3.17", "mask": "255.255.255.252", "description": "To EUNIV-RES-PE2 (HA)"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.3.1", "remote_as": "65000", "description": "EUNIV-RES-AGG1"},
        ],
        "vrfs": ["STAFF-NET", "RESEARCH-NET", "GUEST-NET"],
    },
    "EUNIV-RES-PE2": {
        "role": "Research Campus PE/BNG",
        "template": "pe_router.j2",
        "mgmt_ip": "192.168.68.216",
        "loopback_ip": "10.255.3.12",
        "bgp_asn": "65000",
        "is_route_reflector": False,
        "rr_cluster_id": None,
        "interfaces": [
            {"name": "GigabitEthernet2", "ip": "10.0.3.14", "mask": "255.255.255.252", "description": "To EUNIV-RES-AGG1"},
            {"name": "GigabitEthernet3", "ip": "10.0.3.18", "mask": "255.255.255.252", "description": "To EUNIV-RES-PE1 (HA)"},
        ],
        "bgp_neighbors": [
            {"ip": "10.255.3.1", "remote_as": "65000", "description": "EUNIV-RES-AGG1"},
        ],
        "vrfs": ["STAFF-NET", "RESEARCH-NET", "GUEST-NET"],
    },
}
