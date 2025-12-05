"""
E-University Network Device Inventory for Telemetry Collection
"""

DEVICES = {
    # Core Layer - Route Reflectors and backbone
    "EUNIV-CORE1": {
        "host": "192.168.68.200",
        "role": "core",
        "campus": "backbone",
        "is_rr": True,
    },
    "EUNIV-CORE2": {
        "host": "192.168.68.202",
        "role": "core",
        "campus": "backbone",
        "is_rr": True,
    },
    "EUNIV-CORE3": {
        "host": "192.168.68.203",
        "role": "core",
        "campus": "backbone",
        "is_rr": False,
    },
    "EUNIV-CORE4": {
        "host": "192.168.68.204",
        "role": "core",
        "campus": "backbone",
        "is_rr": False,
    },
    "EUNIV-CORE5": {
        "host": "192.168.68.205",
        "role": "core",
        "campus": "backbone",
        "is_rr": True,
    },
    # Internet Gateways
    "EUNIV-INET-GW1": {
        "host": "192.168.68.206",
        "role": "gateway",
        "campus": "internet",
        "is_rr": False,
    },
    "EUNIV-INET-GW2": {
        "host": "192.168.68.207",
        "role": "gateway",
        "campus": "internet",
        "is_rr": False,
    },
    # Main Campus
    "EUNIV-MAIN-AGG1": {
        "host": "192.168.68.208",
        "role": "aggregation",
        "campus": "main",
        "is_rr": False,
    },
    "EUNIV-MAIN-EDGE1": {
        "host": "192.168.68.209",
        "role": "edge",
        "campus": "main",
        "is_rr": False,
    },
    "EUNIV-MAIN-EDGE2": {
        "host": "192.168.68.210",
        "role": "edge",
        "campus": "main",
        "is_rr": False,
    },
    # Medical Campus
    "EUNIV-MED-AGG1": {
        "host": "192.168.68.211",
        "role": "aggregation",
        "campus": "medical",
        "is_rr": False,
    },
    "EUNIV-MED-EDGE1": {
        "host": "192.168.68.212",
        "role": "edge",
        "campus": "medical",
        "is_rr": False,
    },
    "EUNIV-MED-EDGE2": {
        "host": "192.168.68.213",
        "role": "edge",
        "campus": "medical",
        "is_rr": False,
    },
    # Research Campus
    "EUNIV-RES-AGG1": {
        "host": "192.168.68.214",
        "role": "aggregation",
        "campus": "research",
        "is_rr": False,
    },
    "EUNIV-RES-EDGE1": {
        "host": "192.168.68.215",
        "role": "edge",
        "campus": "research",
        "is_rr": False,
    },
    "EUNIV-RES-EDGE2": {
        "host": "192.168.68.216",
        "role": "edge",
        "campus": "research",
        "is_rr": False,
    },
}
