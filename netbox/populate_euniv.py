#!/usr/bin/env python3
"""
E University Network Lab - NetBox Population Script

Populates NetBox with a 16-device multi-campus network:
- 5 Core routers (3 Route Reflectors)
- 3 Aggregation routers
- 6 Edge routers
- 2 Internet Gateways

Usage:
    python populate_euniv.py --action populate   # Create all objects
    python populate_euniv.py --action cleanup    # Remove lab objects
    python populate_euniv.py --action verify     # Check what exists

Environment Variables:
    NETBOX_URL      - NetBox instance URL
    NETBOX_TOKEN    - API token
    PYATS_USER      - Device SSH username (optional)
    PYATS_PASS      - Device SSH password (optional)
"""

import argparse
import os
import sys

from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

try:
    import pynetbox
except ImportError:
    print("Please install pynetbox: pip install pynetbox")
    sys.exit(1)

# =============================================================================
# E UNIVERSITY LAB CONFIGURATION
# =============================================================================

LAB_CONFIG = {
    # -------------------------------------------------------------------------
    # SITE
    # -------------------------------------------------------------------------
    "site": {
        "name": "E-University-Lab",
        "slug": "euniv-lab",
        "description": "E University Multi-Campus Network Lab",
        "physical_address": "100 University Drive, Education City, EC 12345",
        "time_zone": "America/New_York",
        "status": "active"
    },

    # -------------------------------------------------------------------------
    # MANUFACTURER & DEVICE TYPES
    # -------------------------------------------------------------------------
    "manufacturers": [
        {"name": "Cisco", "slug": "cisco"}
    ],

    "device_types": [
        {
            "manufacturer": "cisco",
            "model": "C8000V",
            "slug": "c8000v",
            "part_number": "C8000V-UNIVERSALK9",
            "u_height": 1,
            "is_full_depth": False,
            "comments": "Cisco Catalyst 8000V Edge Software"
        },
        {
            "manufacturer": "cisco",
            "model": "CSR1000V",
            "slug": "csr1000v",
            "part_number": "CSR1000V-AX",
            "u_height": 1,
            "is_full_depth": False,
            "comments": "Cisco Cloud Services Router 1000V"
        }
    ],

    # -------------------------------------------------------------------------
    # DEVICE ROLES
    # -------------------------------------------------------------------------
    "device_roles": [
        {"name": "Core Router", "slug": "core-router", "color": "f44336",
         "description": "Backbone core router"},
        {"name": "Route Reflector", "slug": "route-reflector", "color": "e91e63",
         "description": "BGP Route Reflector"},
        {"name": "Aggregation Router", "slug": "aggregation-router", "color": "9c27b0",
         "description": "Campus aggregation layer"},
        {"name": "Edge Router", "slug": "edge-router", "color": "2196f3",
         "description": "Campus Edge router"},
        {"name": "Internet Gateway", "slug": "internet-gateway", "color": "4caf50",
         "description": "Internet edge / peering router"}
    ],

    # -------------------------------------------------------------------------
    # PLATFORM
    # -------------------------------------------------------------------------
    "platforms": [
        {"name": "IOS-XE", "slug": "iosxe", "manufacturer": "cisco",
         "napalm_driver": "ios", "description": "Cisco IOS-XE"}
    ],

    # -------------------------------------------------------------------------
    # DEVICES - 16 Total
    # -------------------------------------------------------------------------
    "devices": [
        # === GLOBAL CORE (AS 65000) ===
        {
            "name": "EUNIV-CORE1",
            "device_type": "c8000v",
            "role": "route-reflector",
            "serial": "EUNIV-CORE1-SN001",
            "comments": "Core Router 1 - Route Reflector (Cluster 1)",
            "custom_fields": {
                "loopback0_ipv4": "10.255.0.1/32",
                "loopback0_ipv6": "2001:db8:e:0::1/128",
                "bgp_asn": "65000",
                "ospf_router_id": "10.255.0.1",
                "device_function": "route-reflector",
                "rr_cluster_id": "10.255.0.12",
                "region": "backbone"
            }
        },
        {
            "name": "EUNIV-CORE2",
            "device_type": "c8000v",
            "role": "route-reflector",
            "serial": "EUNIV-CORE2-SN001",
            "comments": "Core Router 2 - Route Reflector (Cluster 1)",
            "custom_fields": {
                "loopback0_ipv4": "10.255.0.2/32",
                "loopback0_ipv6": "2001:db8:e:0::2/128",
                "bgp_asn": "65000",
                "ospf_router_id": "10.255.0.2",
                "device_function": "route-reflector",
                "rr_cluster_id": "10.255.0.12",
                "region": "backbone"
            }
        },
        {
            "name": "EUNIV-CORE3",
            "device_type": "c8000v",
            "role": "core-router",
            "serial": "EUNIV-CORE3-SN001",
            "comments": "Core Router 3 - Transit P router",
            "custom_fields": {
                "loopback0_ipv4": "10.255.0.3/32",
                "loopback0_ipv6": "2001:db8:e:0::3/128",
                "bgp_asn": "65000",
                "ospf_router_id": "10.255.0.3",
                "device_function": "p-router",
                "region": "backbone"
            }
        },
        {
            "name": "EUNIV-CORE4",
            "device_type": "c8000v",
            "role": "core-router",
            "serial": "EUNIV-CORE4-SN001",
            "comments": "Core Router 4 - Transit P router",
            "custom_fields": {
                "loopback0_ipv4": "10.255.0.4/32",
                "loopback0_ipv6": "2001:db8:e:0::4/128",
                "bgp_asn": "65000",
                "ospf_router_id": "10.255.0.4",
                "device_function": "p-router",
                "region": "backbone"
            }
        },
        {
            "name": "EUNIV-CORE5",
            "device_type": "c8000v",
            "role": "route-reflector",
            "serial": "EUNIV-CORE5-SN001",
            "comments": "Core Router 5 - Route Reflector (Cluster 2)",
            "custom_fields": {
                "loopback0_ipv4": "10.255.0.5/32",
                "loopback0_ipv6": "2001:db8:e:0::5/128",
                "bgp_asn": "65000",
                "ospf_router_id": "10.255.0.5",
                "device_function": "route-reflector",
                "rr_cluster_id": "10.255.0.5",
                "region": "backbone"
            }
        },

        # === INTERNET GATEWAYS ===
        {
            "name": "EUNIV-INET-GW1",
            "device_type": "c8000v",
            "role": "internet-gateway",
            "serial": "EUNIV-INETGW1-SN001",
            "comments": "Internet Gateway 1 - Primary ISP Peering",
            "custom_fields": {
                "loopback0_ipv4": "10.255.0.101/32",
                "loopback0_ipv6": "2001:db8:e:0::101/128",
                "bgp_asn": "65000",
                "ospf_router_id": "10.255.0.101",
                "device_function": "internet-edge",
                "region": "backbone"
            }
        },
        {
            "name": "EUNIV-INET-GW2",
            "device_type": "c8000v",
            "role": "internet-gateway",
            "serial": "EUNIV-INETGW2-SN001",
            "comments": "Internet Gateway 2 - Secondary ISP Peering",
            "custom_fields": {
                "loopback0_ipv4": "10.255.0.102/32",
                "loopback0_ipv6": "2001:db8:e:0::102/128",
                "bgp_asn": "65000",
                "ospf_router_id": "10.255.0.102",
                "device_function": "internet-edge",
                "region": "backbone"
            }
        },

        # === MAIN CAMPUS (AS 65100) ===
        {
            "name": "EUNIV-MAIN-AGG1",
            "device_type": "c8000v",
            "role": "aggregation-router",
            "serial": "EUNIV-MAIN-AGG1-SN001",
            "comments": "Main Campus Aggregation Router",
            "custom_fields": {
                "loopback0_ipv4": "10.255.1.1/32",
                "loopback0_ipv6": "2001:db8:e:1::1/128",
                "bgp_asn": "65100",
                "ospf_router_id": "10.255.1.1",
                "device_function": "aggregation",
                "region": "main-campus"
            }
        },
        {
            "name": "EUNIV-MAIN-EDGE1",
            "device_type": "c8000v",
            "role": "edge-router",
            "serial": "EUNIV-MAIN-EDGE1-SN001",
            "comments": "Main Campus Edge 1 - L3VPN + CGNAT",
            "custom_fields": {
                "loopback0_ipv4": "10.255.1.11/32",
                "loopback0_ipv6": "2001:db8:e:1::11/128",
                "bgp_asn": "65100",
                "ospf_router_id": "10.255.1.11",
                "device_function": "edge",
                "region": "main-campus",
                "cgnat_inside_pool": "100.64.0.0/18",
                "cgnat_outside_pool": "198.51.100.0/25"
            }
        },
        {
            "name": "EUNIV-MAIN-EDGE2",
            "device_type": "c8000v",
            "role": "edge-router",
            "serial": "EUNIV-MAIN-EDGE2-SN001",
            "comments": "Main Campus Edge 2 - L3VPN + CGNAT (Redundant)",
            "custom_fields": {
                "loopback0_ipv4": "10.255.1.12/32",
                "loopback0_ipv6": "2001:db8:e:1::12/128",
                "bgp_asn": "65100",
                "ospf_router_id": "10.255.1.12",
                "device_function": "edge",
                "region": "main-campus",
                "cgnat_inside_pool": "100.64.64.0/18",
                "cgnat_outside_pool": "198.51.100.128/25"
            }
        },

        # === MEDICAL CAMPUS (AS 65200) ===
        {
            "name": "EUNIV-MED-AGG1",
            "device_type": "c8000v",
            "role": "aggregation-router",
            "serial": "EUNIV-MED-AGG1-SN001",
            "comments": "Medical Campus Aggregation Router",
            "custom_fields": {
                "loopback0_ipv4": "10.255.2.1/32",
                "loopback0_ipv6": "2001:db8:e:2::1/128",
                "bgp_asn": "65200",
                "ospf_router_id": "10.255.2.1",
                "device_function": "aggregation",
                "region": "medical-campus"
            }
        },
        {
            "name": "EUNIV-MED-EDGE1",
            "device_type": "c8000v",
            "role": "edge-router",
            "serial": "EUNIV-MED-EDGE1-SN001",
            "comments": "Medical Campus Edge 1 - HIPAA Compliant",
            "custom_fields": {
                "loopback0_ipv4": "10.255.2.11/32",
                "loopback0_ipv6": "2001:db8:e:2::11/128",
                "bgp_asn": "65200",
                "ospf_router_id": "10.255.2.11",
                "device_function": "edge",
                "region": "medical-campus"
            }
        },
        {
            "name": "EUNIV-MED-EDGE2",
            "device_type": "c8000v",
            "role": "edge-router",
            "serial": "EUNIV-MED-EDGE2-SN001",
            "comments": "Medical Campus Edge 2 - HIPAA Compliant (Redundant)",
            "custom_fields": {
                "loopback0_ipv4": "10.255.2.12/32",
                "loopback0_ipv6": "2001:db8:e:2::12/128",
                "bgp_asn": "65200",
                "ospf_router_id": "10.255.2.12",
                "device_function": "edge",
                "region": "medical-campus"
            }
        },

        # === RESEARCH CAMPUS (AS 65300) ===
        {
            "name": "EUNIV-RES-AGG1",
            "device_type": "c8000v",
            "role": "aggregation-router",
            "serial": "EUNIV-RES-AGG1-SN001",
            "comments": "Research Campus Aggregation Router",
            "custom_fields": {
                "loopback0_ipv4": "10.255.3.1/32",
                "loopback0_ipv6": "2001:db8:e:3::1/128",
                "bgp_asn": "65300",
                "ospf_router_id": "10.255.3.1",
                "device_function": "aggregation",
                "region": "research-campus"
            }
        },
        {
            "name": "EUNIV-RES-EDGE1",
            "device_type": "c8000v",
            "role": "edge-router",
            "serial": "EUNIV-RES-EDGE1-SN001",
            "comments": "Research Campus Edge 1 - HPC & External Partners",
            "custom_fields": {
                "loopback0_ipv4": "10.255.3.11/32",
                "loopback0_ipv6": "2001:db8:e:3::11/128",
                "bgp_asn": "65300",
                "ospf_router_id": "10.255.3.11",
                "device_function": "edge",
                "region": "research-campus"
            }
        },
        {
            "name": "EUNIV-RES-EDGE2",
            "device_type": "c8000v",
            "role": "edge-router",
            "serial": "EUNIV-RES-EDGE2-SN001",
            "comments": "Research Campus Edge 2 - HPC & External Partners (Redundant)",
            "custom_fields": {
                "loopback0_ipv4": "10.255.3.12/32",
                "loopback0_ipv6": "2001:db8:e:3::12/128",
                "bgp_asn": "65300",
                "ospf_router_id": "10.255.3.12",
                "device_function": "edge",
                "region": "research-campus"
            }
        }
    ],

    # -------------------------------------------------------------------------
    # INTERFACES PER DEVICE
    # -------------------------------------------------------------------------
    "interfaces": {
        # Standard interface set for each device type
        "core": [
            {"name": "GigabitEthernet1", "type": "1000base-t", "mgmt_only": True, "description": "Management"},
            {"name": "GigabitEthernet2", "type": "1000base-t", "description": "Core Link 1"},
            {"name": "GigabitEthernet3", "type": "1000base-t", "description": "Core Link 2"},
            {"name": "GigabitEthernet4", "type": "1000base-t", "description": "To Campus/PE"},
            {"name": "GigabitEthernet5", "type": "1000base-t", "description": "To Campus/PE"},
            {"name": "Loopback0", "type": "virtual", "description": "Router-ID / BGP Source"}
        ],
        "aggregation": [
            {"name": "GigabitEthernet1", "type": "1000base-t", "mgmt_only": True, "description": "Management"},
            {"name": "GigabitEthernet2", "type": "1000base-t", "description": "To Core 1"},
            {"name": "GigabitEthernet3", "type": "1000base-t", "description": "To Core 2"},
            {"name": "GigabitEthernet4", "type": "1000base-t", "description": "To Edge 1"},
            {"name": "GigabitEthernet5", "type": "1000base-t", "description": "To Edge 2"},
            {"name": "Loopback0", "type": "virtual", "description": "Router-ID / BGP Source"}
        ],
        "edge": [
            {"name": "GigabitEthernet1", "type": "1000base-t", "mgmt_only": True, "description": "Management"},
            {"name": "GigabitEthernet2", "type": "1000base-t", "description": "To Aggregation"},
            {"name": "GigabitEthernet3", "type": "1000base-t", "description": "To Peer Edge"},
            {"name": "GigabitEthernet4", "type": "1000base-t", "description": "Customer/VRF"},
            {"name": "GigabitEthernet5", "type": "1000base-t", "description": "Customer/VRF"},
            {"name": "GigabitEthernet6", "type": "1000base-t", "description": "Host Link"},
            {"name": "Loopback0", "type": "virtual", "description": "Router-ID / BGP Source"}
        ],
        "internet-gw": [
            {"name": "GigabitEthernet1", "type": "1000base-t", "mgmt_only": True, "description": "Management"},
            {"name": "GigabitEthernet2", "type": "1000base-t", "description": "To Core"},
            {"name": "GigabitEthernet3", "type": "1000base-t", "description": "ISP Peering 1"},
            {"name": "GigabitEthernet4", "type": "1000base-t", "description": "ISP Peering 2"},
            {"name": "Loopback0", "type": "virtual", "description": "Router-ID / BGP Source"}
        ]
    },

    # -------------------------------------------------------------------------
    # CABLES (Physical Topology)
    # -------------------------------------------------------------------------
    "cables": [
        # Core Ring
        {"a_device": "EUNIV-CORE1", "a_interface": "GigabitEthernet2",
         "b_device": "EUNIV-CORE2", "b_interface": "GigabitEthernet2",
         "label": "Core Ring: CORE1-CORE2"},
        {"a_device": "EUNIV-CORE2", "a_interface": "GigabitEthernet3",
         "b_device": "EUNIV-CORE3", "b_interface": "GigabitEthernet2",
         "label": "Core Ring: CORE2-CORE3"},
        {"a_device": "EUNIV-CORE3", "a_interface": "GigabitEthernet3",
         "b_device": "EUNIV-CORE4", "b_interface": "GigabitEthernet2",
         "label": "Core Ring: CORE3-CORE4"},
        {"a_device": "EUNIV-CORE4", "a_interface": "GigabitEthernet3",
         "b_device": "EUNIV-CORE5", "b_interface": "GigabitEthernet2",
         "label": "Core Ring: CORE4-CORE5"},
        {"a_device": "EUNIV-CORE5", "a_interface": "GigabitEthernet3",
         "b_device": "EUNIV-CORE1", "b_interface": "GigabitEthernet3",
         "label": "Core Ring: CORE5-CORE1"},

        # Internet Gateways to Core
        {"a_device": "EUNIV-CORE1", "a_interface": "GigabitEthernet4",
         "b_device": "EUNIV-INET-GW1", "b_interface": "GigabitEthernet2",
         "label": "CORE1 to INET-GW1"},
        {"a_device": "EUNIV-CORE2", "a_interface": "GigabitEthernet4",
         "b_device": "EUNIV-INET-GW2", "b_interface": "GigabitEthernet2",
         "label": "CORE2 to INET-GW2"},

        # Main Campus to Core
        {"a_device": "EUNIV-CORE1", "a_interface": "GigabitEthernet5",
         "b_device": "EUNIV-MAIN-AGG1", "b_interface": "GigabitEthernet2",
         "label": "CORE1 to MAIN-AGG1"},
        {"a_device": "EUNIV-CORE2", "a_interface": "GigabitEthernet5",
         "b_device": "EUNIV-MAIN-AGG1", "b_interface": "GigabitEthernet3",
         "label": "CORE2 to MAIN-AGG1"},

        # Medical Campus to Core
        {"a_device": "EUNIV-CORE2", "a_interface": "GigabitEthernet4",
         "b_device": "EUNIV-MED-AGG1", "b_interface": "GigabitEthernet2",
         "label": "CORE2 to MED-AGG1"},
        {"a_device": "EUNIV-CORE3", "a_interface": "GigabitEthernet4",
         "b_device": "EUNIV-MED-AGG1", "b_interface": "GigabitEthernet3",
         "label": "CORE3 to MED-AGG1"},

        # Research Campus to Core
        {"a_device": "EUNIV-CORE4", "a_interface": "GigabitEthernet4",
         "b_device": "EUNIV-RES-AGG1", "b_interface": "GigabitEthernet2",
         "label": "CORE4 to RES-AGG1"},
        {"a_device": "EUNIV-CORE5", "a_interface": "GigabitEthernet4",
         "b_device": "EUNIV-RES-AGG1", "b_interface": "GigabitEthernet3",
         "label": "CORE5 to RES-AGG1"},

        # Main Campus Internal
        {"a_device": "EUNIV-MAIN-AGG1", "a_interface": "GigabitEthernet4",
         "b_device": "EUNIV-MAIN-EDGE1", "b_interface": "GigabitEthernet2",
         "label": "MAIN-AGG1 to MAIN-EDGE1"},
        {"a_device": "EUNIV-MAIN-AGG1", "a_interface": "GigabitEthernet5",
         "b_device": "EUNIV-MAIN-EDGE2", "b_interface": "GigabitEthernet2",
         "label": "MAIN-AGG1 to MAIN-EDGE2"},
        {"a_device": "EUNIV-MAIN-EDGE1", "a_interface": "GigabitEthernet3",
         "b_device": "EUNIV-MAIN-EDGE2", "b_interface": "GigabitEthernet3",
         "label": "MAIN-EDGE1 to MAIN-EDGE2 (HA)"},

        # Medical Campus Internal
        {"a_device": "EUNIV-MED-AGG1", "a_interface": "GigabitEthernet4",
         "b_device": "EUNIV-MED-EDGE1", "b_interface": "GigabitEthernet2",
         "label": "MED-AGG1 to MED-EDGE1"},
        {"a_device": "EUNIV-MED-AGG1", "a_interface": "GigabitEthernet5",
         "b_device": "EUNIV-MED-EDGE2", "b_interface": "GigabitEthernet2",
         "label": "MED-AGG1 to MED-EDGE2"},
        {"a_device": "EUNIV-MED-EDGE1", "a_interface": "GigabitEthernet3",
         "b_device": "EUNIV-MED-EDGE2", "b_interface": "GigabitEthernet3",
         "label": "MED-EDGE1 to MED-EDGE2 (HA)"},

        # Research Campus Internal
        {"a_device": "EUNIV-RES-AGG1", "a_interface": "GigabitEthernet4",
         "b_device": "EUNIV-RES-EDGE1", "b_interface": "GigabitEthernet2",
         "label": "RES-AGG1 to RES-EDGE1"},
        {"a_device": "EUNIV-RES-AGG1", "a_interface": "GigabitEthernet5",
         "b_device": "EUNIV-RES-EDGE2", "b_interface": "GigabitEthernet2",
         "label": "RES-AGG1 to RES-EDGE2"},
        {"a_device": "EUNIV-RES-EDGE1", "a_interface": "GigabitEthernet3",
         "b_device": "EUNIV-RES-EDGE2", "b_interface": "GigabitEthernet3",
         "label": "RES-EDGE1 to RES-EDGE2 (HA)"}
    ],

    # -------------------------------------------------------------------------
    # VRF DEFINITIONS
    # -------------------------------------------------------------------------
    "vrfs": [
        {
            "name": "STUDENT-NET",
            "rd": "65000:100",
            "description": "Student residential network - CGNAT enabled",
            "enforce_unique": True
        },
        {
            "name": "STAFF-NET",
            "rd": "65000:200",
            "description": "Staff and faculty network",
            "enforce_unique": True
        },
        {
            "name": "RESEARCH-NET",
            "rd": "65000:300",
            "description": "Research network - external partner access",
            "enforce_unique": True
        },
        {
            "name": "MEDICAL-NET",
            "rd": "65000:400",
            "description": "HIPAA compliant medical network - isolated",
            "enforce_unique": True
        },
        {
            "name": "GUEST-NET",
            "rd": "65000:500",
            "description": "Guest/visitor network - internet only",
            "enforce_unique": True
        }
    ],

    # -------------------------------------------------------------------------
    # ROUTE TARGETS
    # -------------------------------------------------------------------------
    "route_targets": [
        {"name": "65000:100", "description": "STUDENT-NET RT"},
        {"name": "65000:200", "description": "STAFF-NET RT"},
        {"name": "65000:300", "description": "RESEARCH-NET RT"},
        {"name": "65000:400", "description": "MEDICAL-NET RT"},
        {"name": "65000:500", "description": "GUEST-NET RT"}
    ]
}

# =============================================================================
# CONFIG CONTEXT - Enterprise Standards
# =============================================================================
CONFIG_CONTEXT = {
    "name": "euniv-enterprise-standards",
    "description": "E University enterprise configuration standards",
    "is_active": True,
    "data": {
        "organization": {
            "name": "E University",
            "domain": "euniv.edu",
            "contact": "noc@euniv.edu"
        },
        "dns": {
            "servers": ["10.255.255.1", "10.255.255.2"],
            "domain_name": "euniv.edu",
            "domain_search": ["euniv.edu", "campus.euniv.edu"]
        },
        "ntp": {
            "servers": ["10.255.255.10", "10.255.255.11"],
            "timezone": "EST",
            "timezone_offset": "-5"
        },
        "logging": {
            "servers": [
                {"ip": "10.255.255.20", "protocol": "udp", "port": 514}
            ],
            "facility": "local6",
            "severity": "informational",
            "source_interface": "Loopback0"
        },
        "snmp": {
            "community_ro": "euniv-mon-ro",
            "community_rw": "euniv-mon-rw",
            "location": "E University Data Center",
            "contact": "noc@euniv.edu",
            "trap_server": "10.255.255.25"
        },
        "aaa": {
            "tacacs_servers": ["10.255.255.30", "10.255.255.31"],
            "tacacs_key_encrypted": "094F5A0D1C181F0B",
            "local_user": "admin",
            "enable_secret_encrypted": "05080A2D"
        },
        "banners": {
            "motd": "***********************************************\\n*  E UNIVERSITY NETWORK INFRASTRUCTURE       *\\n*  Authorized Access Only                    *\\n*  All activity is monitored and logged      *\\n***********************************************",
            "login": "UNAUTHORIZED ACCESS PROHIBITED\\nThis system is for authorized users only.",
            "exec": "Welcome to E University Network"
        },
        "ospf": {
            "process_id": 1,
            "area": "0.0.0.0",
            "reference_bandwidth": 100000,
            "auto_cost": True,
            "bfd": True,
            "authentication": "message-digest"
        },
        "bgp": {
            "core_asn": 65000,
            "keepalive": 10,
            "holdtime": 30,
            "password_encrypted": "070C285F",
            "bfd": True,
            "graceful_restart": True
        },
        "mpls": {
            "ldp": True,
            "label_allocation": "per-prefix",
            "php": True
        },
        "qos": {
            "policy_map": "EUNIV-QOS-POLICY",
            "voice_dscp": "ef",
            "video_dscp": "af41",
            "critical_data_dscp": "af31"
        },
        "security": {
            "ssh_version": 2,
            "ssh_timeout": 60,
            "vty_acl": "VTY-ACCESS",
            "copp_policy": "EUNIV-COPP"
        },
        "vrfs": {
            "STUDENT-NET": {
                "rt_import": ["65000:100"],
                "rt_export": ["65000:100"],
                "description": "Student residential"
            },
            "STAFF-NET": {
                "rt_import": ["65000:200"],
                "rt_export": ["65000:200"],
                "description": "Staff/Faculty"
            },
            "RESEARCH-NET": {
                "rt_import": ["65000:300"],
                "rt_export": ["65000:300"],
                "description": "Research partners"
            },
            "MEDICAL-NET": {
                "rt_import": ["65000:400"],
                "rt_export": ["65000:400"],
                "description": "HIPAA medical",
                "isolated": True
            },
            "GUEST-NET": {
                "rt_import": ["65000:500"],
                "rt_export": ["65000:500"],
                "description": "Guest access",
                "internet_only": True
            }
        }
    }
}

# =============================================================================
# MANAGEMENT IP MAPPING
# Update these with your actual lab management IPs
# =============================================================================
MANAGEMENT_IPS = {
    # These should be updated with your actual CML/lab IP addresses
    # Format: "DEVICE_NAME": "IP/PREFIX"
    "EUNIV-CORE1": "192.168.68.201/22",
    "EUNIV-CORE2": "192.168.68.202/22",
    "EUNIV-CORE3": "192.168.68.203/22",
    "EUNIV-CORE4": "192.168.68.204/22",
    "EUNIV-CORE5": "192.168.68.205/22",
    "EUNIV-INET-GW1": "192.168.68.206/22",
    "EUNIV-INET-GW2": "192.168.68.207/22",
    "EUNIV-MAIN-AGG1": "192.168.68.208/22",
    "EUNIV-MAIN-EDGE1": "192.168.68.209/22",
    "EUNIV-MAIN-EDGE2": "192.168.68.210/22",
    "EUNIV-MED-AGG1": "192.168.68.211/22",
    "EUNIV-MED-EDGE1": "192.168.68.212/22",
    "EUNIV-MED-EDGE2": "192.168.68.213/22",
    "EUNIV-RES-AGG1": "192.168.68.214/22",
    "EUNIV-RES-EDGE1": "192.168.68.215/22",
    "EUNIV-RES-EDGE2": "192.168.68.216/22",
}


class EUnivNetBoxSetup:
    """Manage E University lab objects in NetBox."""

    def __init__(self, url: str, token: str):
        """Initialize NetBox API connection."""
        self.nb = pynetbox.api(url, token=token)
        self.nb.http_session.verify = True
        print(f"✓ Connected to NetBox: {url}")

    def _get_interface_type(self, device_name: str) -> str:
        """Determine interface type based on device role."""
        if "CORE" in device_name:
            return "core"
        elif "AGG" in device_name:
            return "aggregation"
        elif "EDGE" in device_name:
            return "edge"
        elif "INET" in device_name:
            return "internet-gw"
        return "core"

    def create_custom_fields(self):
        """Create custom fields for device metadata."""
        print("\n[1/10] Creating Custom Fields...")

        # NetBox 3.5+ uses object_types instead of content_types
        custom_fields = [
            {"name": "loopback0_ipv4", "type": "text", "label": "Loopback0 IPv4",
             "object_types": ["dcim.device"], "description": "Loopback0 IPv4 address with mask"},
            {"name": "loopback0_ipv6", "type": "text", "label": "Loopback0 IPv6",
             "object_types": ["dcim.device"], "description": "Loopback0 IPv6 address with mask"},
            {"name": "bgp_asn", "type": "text", "label": "BGP ASN",
             "object_types": ["dcim.device"], "description": "BGP Autonomous System Number"},
            {"name": "ospf_router_id", "type": "text", "label": "OSPF Router ID",
             "object_types": ["dcim.device"], "description": "OSPF Router ID"},
            {"name": "device_function", "type": "text", "label": "Device Function",
             "object_types": ["dcim.device"], "description": "Functional role (route-reflector, pe-bng, etc)"},
            {"name": "rr_cluster_id", "type": "text", "label": "RR Cluster ID",
             "object_types": ["dcim.device"], "description": "BGP Route Reflector Cluster ID"},
            {"name": "region", "type": "text", "label": "Region",
             "object_types": ["dcim.device"], "description": "Network region/campus"},
            {"name": "cgnat_inside_pool", "type": "text", "label": "CGNAT Inside Pool",
             "object_types": ["dcim.device"], "description": "RFC6598 CGNAT inside address pool"},
            {"name": "cgnat_outside_pool", "type": "text", "label": "CGNAT Outside Pool",
             "object_types": ["dcim.device"], "description": "Public CGNAT outside address pool"},
        ]

        for cf in custom_fields:
            try:
                existing = self.nb.extras.custom_fields.get(name=cf["name"])
                if not existing:
                    self.nb.extras.custom_fields.create(cf)
                    print(f"  ✓ Created: {cf['name']}")
                else:
                    print(f"  → Exists: {cf['name']}")
            except Exception as e:
                print(f"  ✗ Error with {cf['name']}: {e}")

    def create_site(self):
        """Create the lab site."""
        print("\n[2/10] Creating Site...")
        site_data = LAB_CONFIG["site"]

        existing = self.nb.dcim.sites.get(slug=site_data["slug"])
        if existing:
            print(f"  → Exists: {site_data['name']}")
            return existing

        site = self.nb.dcim.sites.create(site_data)
        print(f"  ✓ Created: {site_data['name']}")
        return site

    def create_manufacturers(self):
        """Create manufacturers."""
        print("\n[3/10] Creating Manufacturers...")

        for mfg_data in LAB_CONFIG["manufacturers"]:
            existing = self.nb.dcim.manufacturers.get(slug=mfg_data["slug"])
            if existing:
                print(f"  → Exists: {mfg_data['name']}")
            else:
                self.nb.dcim.manufacturers.create(mfg_data)
                print(f"  ✓ Created: {mfg_data['name']}")

    def create_device_types(self):
        """Create device types."""
        print("\n[4/10] Creating Device Types...")

        for dt_data in LAB_CONFIG["device_types"]:
            mfg = self.nb.dcim.manufacturers.get(slug=dt_data["manufacturer"])
            if not mfg:
                print(f"  ✗ Manufacturer not found: {dt_data['manufacturer']}")
                continue

            existing = self.nb.dcim.device_types.get(slug=dt_data["slug"])
            if existing:
                print(f"  → Exists: {dt_data['model']}")
            else:
                create_data = {**dt_data, "manufacturer": mfg.id}
                del create_data["manufacturer"]
                create_data["manufacturer"] = mfg.id
                self.nb.dcim.device_types.create(create_data)
                print(f"  ✓ Created: {dt_data['model']}")

    def create_device_roles(self):
        """Create device roles."""
        print("\n[5/10] Creating Device Roles...")

        for role_data in LAB_CONFIG["device_roles"]:
            existing = self.nb.dcim.device_roles.get(slug=role_data["slug"])
            if existing:
                print(f"  → Exists: {role_data['name']}")
            else:
                self.nb.dcim.device_roles.create(role_data)
                print(f"  ✓ Created: {role_data['name']}")

    def create_platforms(self):
        """Create platforms."""
        print("\n[6/10] Creating Platforms...")

        for plat_data in LAB_CONFIG["platforms"]:
            existing = self.nb.dcim.platforms.get(slug=plat_data["slug"])
            if existing:
                print(f"  → Exists: {plat_data['name']}")
            else:
                mfg = self.nb.dcim.manufacturers.get(slug=plat_data.get("manufacturer", "cisco"))
                create_data = {**plat_data}
                if mfg:
                    create_data["manufacturer"] = mfg.id
                else:
                    del create_data["manufacturer"]
                self.nb.dcim.platforms.create(create_data)
                print(f"  ✓ Created: {plat_data['name']}")

    def create_devices(self, site):
        """Create all devices."""
        print("\n[7/10] Creating Devices...")

        platform = self.nb.dcim.platforms.get(slug="iosxe")

        for dev_data in LAB_CONFIG["devices"]:
            existing = self.nb.dcim.devices.get(name=dev_data["name"])
            if existing:
                print(f"  → Exists: {dev_data['name']}")
                continue

            device_type = self.nb.dcim.device_types.get(slug=dev_data["device_type"])
            device_role = self.nb.dcim.device_roles.get(slug=dev_data["role"])

            if not device_type or not device_role:
                print(f"  ✗ Missing type/role for: {dev_data['name']}")
                continue

            create_data = {
                "name": dev_data["name"],
                "device_type": device_type.id,
                "role": device_role.id,
                "site": site.id,
                "serial": dev_data.get("serial", ""),
                "comments": dev_data.get("comments", ""),
                "status": "active"
            }

            if platform:
                create_data["platform"] = platform.id

            if dev_data.get("custom_fields"):
                create_data["custom_fields"] = dev_data["custom_fields"]

            device = self.nb.dcim.devices.create(create_data)
            print(f"  ✓ Created: {dev_data['name']}")

            # Create interfaces
            self._create_device_interfaces(device, dev_data["name"])

    def _create_device_interfaces(self, device, device_name: str):
        """Create interfaces for a device."""
        intf_type = self._get_interface_type(device_name)
        interfaces = LAB_CONFIG["interfaces"].get(intf_type, [])

        for intf_data in interfaces:
            existing = self.nb.dcim.interfaces.filter(device_id=device.id, name=intf_data["name"])
            if list(existing):
                continue

            create_data = {
                "device": device.id,
                "name": intf_data["name"],
                "type": intf_data["type"],
                "description": intf_data.get("description", ""),
                "mgmt_only": intf_data.get("mgmt_only", False)
            }

            self.nb.dcim.interfaces.create(create_data)

    def create_management_ips(self):
        """Create management IP addresses and set as primary."""
        print("\n[8/10] Creating Management IPs...")

        for device_name, ip_address in MANAGEMENT_IPS.items():
            device = self.nb.dcim.devices.get(name=device_name)
            if not device:
                print(f"  ✗ Device not found: {device_name}")
                continue

            # Find management interface
            mgmt_intf = None
            interfaces = self.nb.dcim.interfaces.filter(device_id=device.id)
            for intf in interfaces:
                if intf.mgmt_only or "GigabitEthernet1" in intf.name:
                    mgmt_intf = intf
                    break

            if not mgmt_intf:
                print(f"  ✗ No management interface for: {device_name}")
                continue

            # Check if IP exists
            existing_ip = self.nb.ipam.ip_addresses.get(address=ip_address)
            if existing_ip:
                print(f"  → IP exists: {ip_address}")
                ip_obj = existing_ip
            else:
                # Create IP
                ip_obj = self.nb.ipam.ip_addresses.create({
                    "address": ip_address,
                    "assigned_object_type": "dcim.interface",
                    "assigned_object_id": mgmt_intf.id,
                    "description": f"{device_name} Management"
                })
                print(f"  ✓ Created IP: {ip_address} for {device_name}")

            # Set as primary
            device.primary_ip4 = ip_obj.id
            device.save()

    def create_cables(self):
        """Create cable connections."""
        print("\n[9/10] Creating Cables...")

        for cable_data in LAB_CONFIG["cables"]:
            a_device = self.nb.dcim.devices.get(name=cable_data["a_device"])
            b_device = self.nb.dcim.devices.get(name=cable_data["b_device"])

            if not a_device or not b_device:
                print(f"  ✗ Device not found for cable: {cable_data['label']}")
                continue

            a_intf = self.nb.dcim.interfaces.get(device_id=a_device.id, name=cable_data["a_interface"])
            b_intf = self.nb.dcim.interfaces.get(device_id=b_device.id, name=cable_data["b_interface"])

            if not a_intf or not b_intf:
                print(f"  ✗ Interface not found for cable: {cable_data['label']}")
                continue

            # Check if already cabled
            if a_intf.cable or b_intf.cable:
                print(f"  → Already cabled: {cable_data['label']}")
                continue

            try:
                self.nb.dcim.cables.create({
                    "a_terminations": [{"object_type": "dcim.interface", "object_id": a_intf.id}],
                    "b_terminations": [{"object_type": "dcim.interface", "object_id": b_intf.id}],
                    "label": cable_data["label"],
                    "status": "connected"
                })
                print(f"  ✓ Created: {cable_data['label']}")
            except Exception as e:
                print(f"  ✗ Error creating cable {cable_data['label']}: {e}")

    def create_config_context(self, site):
        """Create configuration context with enterprise standards."""
        print("\n[10/10] Creating Config Context...")

        existing = self.nb.extras.config_contexts.get(name=CONFIG_CONTEXT["name"])
        if existing:
            print(f"  → Exists: {CONFIG_CONTEXT['name']}")
            return existing

        context = self.nb.extras.config_contexts.create({
            "name": CONFIG_CONTEXT["name"],
            "description": CONFIG_CONTEXT["description"],
            "is_active": CONFIG_CONTEXT["is_active"],
            "data": CONFIG_CONTEXT["data"],
            "sites": [site.id]
        })
        print(f"  ✓ Created: {CONFIG_CONTEXT['name']}")
        return context

    def populate(self):
        """Run full population process."""
        print("\n" + "=" * 70)
        print("E University Network Lab - NetBox Population")
        print("=" * 70)

        self.create_custom_fields()
        site = self.create_site()
        self.create_manufacturers()
        self.create_device_types()
        self.create_device_roles()
        self.create_platforms()
        self.create_devices(site)
        self.create_management_ips()
        self.create_cables()
        self.create_config_context(site)

        print("\n" + "=" * 70)
        print("✓ NetBox population complete!")
        print("=" * 70)
        print(f"\nDevices created: {len(LAB_CONFIG['devices'])}")
        print(f"Cables created: {len(LAB_CONFIG['cables'])}")
        print("\nNext steps:")
        print("  1. Verify in NetBox UI: Devices → Devices")
        print("  2. Generate testbed: pyats create testbed netbox ...")
        print("  3. Generate configs: python pyats/scripts/generate_configs.py")

    def cleanup(self):
        """Remove all lab objects from NetBox."""
        print("\n" + "=" * 70)
        print("E University Network Lab - Cleanup")
        print("=" * 70)

        # Delete devices (cascades to interfaces, IPs, cables)
        print("\nDeleting devices...")
        for dev_data in LAB_CONFIG["devices"]:
            device = self.nb.dcim.devices.get(name=dev_data["name"])
            if device:
                device.delete()
                print(f"  ✓ Deleted: {dev_data['name']}")

        # Delete site
        print("\nDeleting site...")
        site = self.nb.dcim.sites.get(slug=LAB_CONFIG["site"]["slug"])
        if site:
            site.delete()
            print(f"  ✓ Deleted: {LAB_CONFIG['site']['name']}")

        # Delete config context
        print("\nDeleting config context...")
        context = self.nb.extras.config_contexts.get(name=CONFIG_CONTEXT["name"])
        if context:
            context.delete()
            print(f"  ✓ Deleted: {CONFIG_CONTEXT['name']}")

        print("\n✓ Cleanup complete!")

    def verify(self):
        """Verify what exists in NetBox."""
        print("\n" + "=" * 70)
        print("E University Network Lab - Verification")
        print("=" * 70)

        # Check site
        site = self.nb.dcim.sites.get(slug=LAB_CONFIG["site"]["slug"])
        print(f"\nSite: {'✓ Found' if site else '✗ Not found'}")

        # Check devices
        print("\nDevices:")
        for dev_data in LAB_CONFIG["devices"]:
            device = self.nb.dcim.devices.get(name=dev_data["name"])
            status = "✓" if device else "✗"
            primary_ip = device.primary_ip if device else None
            ip_status = f"(Primary IP: {primary_ip})" if primary_ip else "(No Primary IP)"
            print(f"  {status} {dev_data['name']} {ip_status if device else ''}")


def main():
    parser = argparse.ArgumentParser(description="E University NetBox Population Script")
    parser.add_argument("--action", choices=["populate", "cleanup", "verify"],
                        default="populate", help="Action to perform")
    parser.add_argument("--netbox-url", help="NetBox URL (or set NETBOX_URL env var)")
    parser.add_argument("--token", help="NetBox API token (or set NETBOX_TOKEN env var)")
    args = parser.parse_args()

    # Get credentials
    url = args.netbox_url or os.getenv("NETBOX_URL")
    token = args.token or os.getenv("NETBOX_TOKEN")

    if not url or not token:
        print("Error: NetBox URL and token required")
        print("Set NETBOX_URL and NETBOX_TOKEN environment variables, or use --netbox-url and --token")
        sys.exit(1)

    # Run
    setup = EUnivNetBoxSetup(url, token)

    if args.action == "populate":
        setup.populate()
    elif args.action == "cleanup":
        setup.cleanup()
    elif args.action == "verify":
        setup.verify()


if __name__ == "__main__":
    main()
