#!/usr/bin/env python3
"""
Add IPv4 BGP peering to all PE routers for internet access
"""

from pyats.topology import loader
import time

TESTBED = """
testbed:
  name: E-University
  credentials:
    default:
      username: admin
      password: REDACTED
    enable:
      password: REDACTED

devices:
  EUNIV-CORE2:
    os: iosxe
    type: router
    connections:
      defaults:
        class: unicon.Unicon
      cli:
        protocol: ssh
        ip: 192.168.68.202

  EUNIV-MAIN-PE1:
    os: iosxe
    type: router
    connections:
      defaults:
        class: unicon.Unicon
      cli:
        protocol: ssh
        ip: 192.168.68.209

  EUNIV-MAIN-PE2:
    os: iosxe
    type: router
    connections:
      defaults:
        class: unicon.Unicon
      cli:
        protocol: ssh
        ip: 192.168.68.210

  EUNIV-MED-PE1:
    os: iosxe
    type: router
    connections:
      defaults:
        class: unicon.Unicon
      cli:
        protocol: ssh
        ip: 192.168.68.212

  EUNIV-MED-PE2:
    os: iosxe
    type: router
    connections:
      defaults:
        class: unicon.Unicon
      cli:
        protocol: ssh
        ip: 192.168.68.213

  EUNIV-RES-PE1:
    os: iosxe
    type: router
    connections:
      defaults:
        class: unicon.Unicon
      cli:
        protocol: ssh
        ip: 192.168.68.215

  EUNIV-RES-PE2:
    os: iosxe
    type: router
    connections:
      defaults:
        class: unicon.Unicon
      cli:
        protocol: ssh
        ip: 192.168.68.216
"""

# PE routers need to peer with both RRs for IPv4
PE_CONFIG = """
router bgp 65000
 neighbor 10.255.0.1 remote-as 65000
 neighbor 10.255.0.1 description CORE1-RR
 neighbor 10.255.0.1 update-source Loopback0
 neighbor 10.255.0.2 remote-as 65000
 neighbor 10.255.0.2 description CORE2-RR
 neighbor 10.255.0.2 update-source Loopback0
 address-family ipv4
  neighbor 10.255.0.1 activate
  neighbor 10.255.0.2 activate
 exit-address-family
"""

# CORE2 needs all PEs as neighbors
CORE2_CONFIG = """
router bgp 65000
 neighbor 10.255.0.1 remote-as 65000
 neighbor 10.255.0.1 description CORE1-RR
 neighbor 10.255.0.1 update-source Loopback0
 neighbor 10.255.0.101 remote-as 65000
 neighbor 10.255.0.101 description INET-GW1
 neighbor 10.255.0.101 update-source Loopback0
 neighbor 10.255.0.102 remote-as 65000
 neighbor 10.255.0.102 description INET-GW2
 neighbor 10.255.0.102 update-source Loopback0
 neighbor 10.255.1.11 remote-as 65000
 neighbor 10.255.1.11 description MAIN-PE1
 neighbor 10.255.1.11 update-source Loopback0
 neighbor 10.255.1.12 remote-as 65000
 neighbor 10.255.1.12 description MAIN-PE2
 neighbor 10.255.1.12 update-source Loopback0
 neighbor 10.255.2.11 remote-as 65000
 neighbor 10.255.2.11 description MED-PE1
 neighbor 10.255.2.11 update-source Loopback0
 neighbor 10.255.2.12 remote-as 65000
 neighbor 10.255.2.12 description MED-PE2
 neighbor 10.255.2.12 update-source Loopback0
 neighbor 10.255.3.11 remote-as 65000
 neighbor 10.255.3.11 description RES-PE1
 neighbor 10.255.3.11 update-source Loopback0
 neighbor 10.255.3.12 remote-as 65000
 neighbor 10.255.3.12 description RES-PE2
 neighbor 10.255.3.12 update-source Loopback0
 address-family ipv4
  neighbor 10.255.0.1 activate
  neighbor 10.255.0.1 send-community both
  neighbor 10.255.0.101 activate
  neighbor 10.255.0.101 send-community both
  neighbor 10.255.0.101 route-reflector-client
  neighbor 10.255.0.102 activate
  neighbor 10.255.0.102 send-community both
  neighbor 10.255.0.102 route-reflector-client
  neighbor 10.255.1.11 activate
  neighbor 10.255.1.11 send-community both
  neighbor 10.255.1.11 route-reflector-client
  neighbor 10.255.1.12 activate
  neighbor 10.255.1.12 send-community both
  neighbor 10.255.1.12 route-reflector-client
  neighbor 10.255.2.11 activate
  neighbor 10.255.2.11 send-community both
  neighbor 10.255.2.11 route-reflector-client
  neighbor 10.255.2.12 activate
  neighbor 10.255.2.12 send-community both
  neighbor 10.255.2.12 route-reflector-client
  neighbor 10.255.3.11 activate
  neighbor 10.255.3.11 send-community both
  neighbor 10.255.3.11 route-reflector-client
  neighbor 10.255.3.12 activate
  neighbor 10.255.3.12 send-community both
  neighbor 10.255.3.12 route-reflector-client
 exit-address-family
 address-family vpnv4
  neighbor 10.255.0.1 activate
  neighbor 10.255.0.1 send-community both
  neighbor 10.255.1.11 activate
  neighbor 10.255.1.11 send-community both
  neighbor 10.255.1.11 route-reflector-client
  neighbor 10.255.1.12 activate
  neighbor 10.255.1.12 send-community both
  neighbor 10.255.1.12 route-reflector-client
  neighbor 10.255.2.11 activate
  neighbor 10.255.2.11 send-community both
  neighbor 10.255.2.11 route-reflector-client
  neighbor 10.255.2.12 activate
  neighbor 10.255.2.12 send-community both
  neighbor 10.255.2.12 route-reflector-client
  neighbor 10.255.3.11 activate
  neighbor 10.255.3.11 send-community both
  neighbor 10.255.3.11 route-reflector-client
  neighbor 10.255.3.12 activate
  neighbor 10.255.3.12 send-community both
  neighbor 10.255.3.12 route-reflector-client
 exit-address-family
"""


def main():
    import tempfile
    import os

    print("=" * 60)
    print("ADDING IPv4 BGP PEERING FOR INTERNET ACCESS")
    print("=" * 60)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(TESTBED)
        testbed_file = f.name

    try:
        testbed = loader.load(testbed_file)
    finally:
        os.unlink(testbed_file)

    # Configure CORE2 first
    print("\n[1/7] Configuring CORE2...")
    try:
        device = testbed.devices["EUNIV-CORE2"]
        device.connect(log_stdout=False, learn_hostname=True)
        device.configure(CORE2_CONFIG)
        print("  ✅ CORE2 configured")
        device.disconnect()
    except Exception as e:
        print(f"  ❌ CORE2 failed: {e}")

    time.sleep(2)

    # Configure all PE routers
    pe_routers = [
        "EUNIV-MAIN-PE1", "EUNIV-MAIN-PE2",
        "EUNIV-MED-PE1", "EUNIV-MED-PE2",
        "EUNIV-RES-PE1", "EUNIV-RES-PE2"
    ]

    for i, router in enumerate(pe_routers, 2):
        print(f"\n[{i}/7] Configuring {router}...")
        try:
            device = testbed.devices[router]
            device.connect(log_stdout=False, learn_hostname=True)
            device.configure(PE_CONFIG)

            # Remove static default if present
            try:
                device.configure("no ip route 0.0.0.0 0.0.0.0 192.168.68.1")
            except:
                pass

            print(f"  ✅ {router} configured")
            device.disconnect()
        except Exception as e:
            print(f"  ❌ {router} failed: {e}")

        time.sleep(1)

    print("\n" + "=" * 60)
    print("COMPLETE!")
    print("=" * 60)
    print("""
Verify on any PE router:
  show ip bgp summary
  show ip bgp 0.0.0.0/0
  ping 8.8.8.8
""")


if __name__ == "__main__":
    main()