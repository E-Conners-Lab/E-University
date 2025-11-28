#!/usr/bin/env python3
"""
E-University Network - BFD Deployment Script (Corrected)
Adds Bidirectional Forwarding Detection for sub-second failover

BFD Timers: 50ms interval x 3 multiplier = 150ms detection

Correctly handles:
- P routers (CORE3, CORE4, CORE5) - OSPF BFD only, no BGP
- Route Reflectors (CORE1, CORE2) - OSPF + BGP BFD
- PE routers - OSPF + BGP BFD
- Aggregation routers - OSPF BFD only
"""

from pyats.topology import loader
import time

# Router classifications
ROUTE_REFLECTORS = ["EUNIV-CORE1", "EUNIV-CORE2"]
P_ROUTERS = ["EUNIV-CORE3", "EUNIV-CORE4", "EUNIV-CORE5"]  # No BGP
PE_ROUTERS = ["EUNIV-MAIN-PE1", "EUNIV-MAIN-PE2",
              "EUNIV-MED-PE1", "EUNIV-MED-PE2",
              "EUNIV-RES-PE1", "EUNIV-RES-PE2"]
AGG_ROUTERS = ["EUNIV-MAIN-AGG1", "EUNIV-MED-AGG1", "EUNIV-RES-AGG1"]  # No BGP
INET_ROUTERS = ["EUNIV-INET-GW1", "EUNIV-INET-GW2"]  # No BGP to internal

ALL_ROUTERS = ROUTE_REFLECTORS + P_ROUTERS + PE_ROUTERS + AGG_ROUTERS + INET_ROUTERS

# BFD-enabled interfaces per router (only interfaces that exist)
ROUTER_INTERFACES = {
    "EUNIV-CORE1": ["GigabitEthernet2", "GigabitEthernet3", "GigabitEthernet4"],
    "EUNIV-CORE2": ["GigabitEthernet2", "GigabitEthernet3", "GigabitEthernet4"],
    "EUNIV-CORE3": ["GigabitEthernet2", "GigabitEthernet3", "GigabitEthernet4"],
    "EUNIV-CORE4": ["GigabitEthernet2", "GigabitEthernet3", "GigabitEthernet4"],
    "EUNIV-CORE5": ["GigabitEthernet2", "GigabitEthernet3", "GigabitEthernet4"],
    "EUNIV-INET-GW1": ["GigabitEthernet2", "GigabitEthernet3"],
    "EUNIV-INET-GW2": ["GigabitEthernet2", "GigabitEthernet3"],
    "EUNIV-MAIN-AGG1": ["GigabitEthernet2", "GigabitEthernet3", "GigabitEthernet4"],
    "EUNIV-MAIN-PE1": ["GigabitEthernet2"],
    "EUNIV-MAIN-PE2": ["GigabitEthernet2"],
    "EUNIV-MED-AGG1": ["GigabitEthernet2", "GigabitEthernet3", "GigabitEthernet4"],
    "EUNIV-MED-PE1": ["GigabitEthernet2"],
    "EUNIV-MED-PE2": ["GigabitEthernet2"],
    "EUNIV-RES-AGG1": ["GigabitEthernet2", "GigabitEthernet3", "GigabitEthernet4"],
    "EUNIV-RES-PE1": ["GigabitEthernet2"],
    "EUNIV-RES-PE2": ["GigabitEthernet2"],
}

# BGP neighbors - ONLY for routers that have BGP peerings
BGP_NEIGHBORS = {
    # Route Reflectors peer with each other and all PEs
    "EUNIV-CORE1": ["10.255.0.2", "10.255.1.11", "10.255.1.12",
                    "10.255.2.11", "10.255.2.12", "10.255.3.11", "10.255.3.12"],
    "EUNIV-CORE2": ["10.255.0.1", "10.255.1.11", "10.255.1.12",
                    "10.255.2.11", "10.255.2.12", "10.255.3.11", "10.255.3.12"],
    # PE routers peer with Route Reflectors only
    "EUNIV-MAIN-PE1": ["10.255.0.1", "10.255.0.2"],
    "EUNIV-MAIN-PE2": ["10.255.0.1", "10.255.0.2"],
    "EUNIV-MED-PE1": ["10.255.0.1", "10.255.0.2"],
    "EUNIV-MED-PE2": ["10.255.0.1", "10.255.0.2"],
    "EUNIV-RES-PE1": ["10.255.0.1", "10.255.0.2"],
    "EUNIV-RES-PE2": ["10.255.0.1", "10.255.0.2"],
    # P routers (CORE3, CORE4, CORE5) - NO BGP
    # AGG routers - NO BGP
    # INET routers - NO internal BGP
}


def generate_bfd_config(router_name):
    """Generate BFD configuration for a router"""

    config_lines = [
        "! BFD Template for consistent timers",
        "bfd-template single-hop BFD-FAST",
        " interval min-tx 50 min-rx 50 multiplier 3",
        "!",
    ]

    # Interface BFD configuration
    interfaces = ROUTER_INTERFACES.get(router_name, [])
    for intf in interfaces:
        config_lines.extend([
            f"interface {intf}",
            " bfd template BFD-FAST",
            "!",
        ])

    # OSPF BFD - enable on all interfaces (all routers have OSPF)
    config_lines.extend([
        "router ospf 1",
        " bfd all-interfaces",
        "!",
    ])

    # BGP BFD - ONLY if router has BGP neighbors defined
    neighbors = BGP_NEIGHBORS.get(router_name, [])
    if neighbors:
        config_lines.append("router bgp 65000")
        for neighbor in neighbors:
            config_lines.append(f" neighbor {neighbor} fall-over bfd")
        config_lines.append("!")

    return "\n".join(config_lines)


def main():
    testbed = loader.load("testbed.yaml")

    print("=" * 70)
    print("E-UNIVERSITY NETWORK - BFD DEPLOYMENT")
    print("=" * 70)
    print("""
BFD Configuration:
  • Interval: 50ms transmit / 50ms receive
  • Multiplier: 3
  • Detection Time: 150ms (vs ~40 seconds without BFD)

This enables sub-second failover for both OSPF and BGP!
""")

    success_count = 0
    fail_count = 0

    for router_name in ALL_ROUTERS:
        # Determine router type for display
        if router_name in ROUTE_REFLECTORS:
            role = "Route Reflector"
            protocols = "OSPF + BGP"
        elif router_name in P_ROUTERS:
            role = "P Router"
            protocols = "OSPF only"
        elif router_name in PE_ROUTERS:
            role = "PE Router"
            protocols = "OSPF + BGP"
        elif router_name in AGG_ROUTERS:
            role = "Aggregation"
            protocols = "OSPF only"
        else:
            role = "Gateway"
            protocols = "OSPF only"

        print(f"\n  Configuring: {router_name} ({role})")

        try:
            device = testbed.devices[router_name]
            device.connect(log_stdout=False)

            config = generate_bfd_config(router_name)
            device.configure(config)

            print(f"    ✅ BFD enabled ({protocols})")
            success_count += 1

            device.disconnect()

        except Exception as e:
            print(f"    ❌ Error: {str(e)[:60]}")
            fail_count += 1

    print("\n" + "=" * 70)
    print("BFD DEPLOYMENT COMPLETE")
    print("=" * 70)
    print(f"""
  Results: {success_count} succeeded, {fail_count} failed

Router Types:
  • Route Reflectors (CORE1-2):  OSPF + BGP BFD
  • P Routers (CORE3-5):         OSPF BFD only
  • PE Routers (6 total):        OSPF + BGP BFD  
  • Aggregation Routers (3):     OSPF BFD only
  • Internet Gateways (2):       OSPF BFD only

Verification Commands:

  ! Check BFD neighbors
  show bfd neighbors

  ! Verify OSPF is using BFD
  show ip ospf interface GigabitEthernet2 | include BFD

  ! Verify BGP is using BFD (on PE/RR only)
  show ip bgp neighbors | include BFD

Failover Test:

  1. Start a continuous ping across the network:
     ping vrf STAFF-NET 172.20.0.11 source 172.20.0.1 repeat 10000

  2. Shut down an interface:
     conf t
     interface GigabitEthernet2
       shutdown

  3. Watch ping - should only lose 1-2 packets (~150ms detection)

  4. Bring interface back up:
     no shutdown
     end
""")


if __name__ == "__main__":
    main()