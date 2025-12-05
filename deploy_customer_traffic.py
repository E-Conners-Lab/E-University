#!/usr/bin/env python3
"""
E-University Network - Customer Traffic Deployment Script (Fixed)

This version first establishes BGP neighbors before activating VPNv4.
"""

import os
import time

from pyats.topology import loader

# Configuration for Route Reflectors - adds PE neighbors + VPNv4
RR_CONFIGS = {
    "EUNIV-CORE1": """
router bgp 65000
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
 !
 address-family ipv4
  neighbor 10.255.1.11 activate
  neighbor 10.255.1.11 route-reflector-client
  neighbor 10.255.1.12 activate
  neighbor 10.255.1.12 route-reflector-client
  neighbor 10.255.2.11 activate
  neighbor 10.255.2.11 route-reflector-client
  neighbor 10.255.2.12 activate
  neighbor 10.255.2.12 route-reflector-client
  neighbor 10.255.3.11 activate
  neighbor 10.255.3.11 route-reflector-client
  neighbor 10.255.3.12 activate
  neighbor 10.255.3.12 route-reflector-client
 exit-address-family
 !
 address-family vpnv4
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
""",
    "EUNIV-CORE2": """
router bgp 65000
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
 !
 address-family ipv4
  neighbor 10.255.1.11 activate
  neighbor 10.255.1.11 route-reflector-client
  neighbor 10.255.1.12 activate
  neighbor 10.255.1.12 route-reflector-client
  neighbor 10.255.2.11 activate
  neighbor 10.255.2.11 route-reflector-client
  neighbor 10.255.2.12 activate
  neighbor 10.255.2.12 route-reflector-client
  neighbor 10.255.3.11 activate
  neighbor 10.255.3.11 route-reflector-client
  neighbor 10.255.3.12 activate
  neighbor 10.255.3.12 route-reflector-client
 exit-address-family
 !
 address-family vpnv4
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
}

# PE Router configurations - BGP to RRs + VRFs + Customer interfaces
PE_CONFIGS = {
    "EUNIV-MAIN-PE1": """
router bgp 65000
 neighbor 10.255.0.1 remote-as 65000
 neighbor 10.255.0.1 description CORE1-RR
 neighbor 10.255.0.1 update-source Loopback0
 neighbor 10.255.0.2 remote-as 65000
 neighbor 10.255.0.2 description CORE2-RR
 neighbor 10.255.0.2 update-source Loopback0
 !
 address-family ipv4
  neighbor 10.255.0.1 activate
  neighbor 10.255.0.2 activate
 exit-address-family
 !
 address-family vpnv4
  neighbor 10.255.0.1 activate
  neighbor 10.255.0.1 send-community both
  neighbor 10.255.0.2 activate
  neighbor 10.255.0.2 send-community both
 exit-address-family
!
vrf definition STUDENT-NET
 description Student Network - Main Campus
 rd 10.255.1.11:100
 address-family ipv4
  route-target export 65000:100
  route-target import 65000:100
 exit-address-family
!
vrf definition STAFF-NET
 description Staff Network - All Campuses
 rd 10.255.1.11:200
 address-family ipv4
  route-target export 65000:200
  route-target import 65000:200
 exit-address-family
!
vrf definition RESEARCH-NET
 description Research Network - All Campuses
 rd 10.255.1.11:300
 address-family ipv4
  route-target export 65000:300
  route-target import 65000:300
 exit-address-family
!
vrf definition GUEST-NET
 description Guest Network - All Campuses
 rd 10.255.1.11:500
 address-family ipv4
  route-target export 65000:500
  route-target import 65000:500
 exit-address-family
!
interface Loopback110
 description STUDENT-NET Customer Endpoint
 vrf forwarding STUDENT-NET
 ip address 172.10.0.1 255.255.255.255
!
interface Loopback120
 description STAFF-NET Customer Endpoint
 vrf forwarding STAFF-NET
 ip address 172.20.0.1 255.255.255.255
!
interface Loopback130
 description RESEARCH-NET Customer Endpoint
 vrf forwarding RESEARCH-NET
 ip address 172.30.0.1 255.255.255.255
!
interface Loopback150
 description GUEST-NET Customer Endpoint
 vrf forwarding GUEST-NET
 ip address 172.50.0.1 255.255.255.255
!
router bgp 65000
 address-family ipv4 vrf STUDENT-NET
  redistribute connected
 exit-address-family
 address-family ipv4 vrf STAFF-NET
  redistribute connected
 exit-address-family
 address-family ipv4 vrf RESEARCH-NET
  redistribute connected
 exit-address-family
 address-family ipv4 vrf GUEST-NET
  redistribute connected
 exit-address-family
""",
    "EUNIV-MAIN-PE2": """
router bgp 65000
 neighbor 10.255.0.1 remote-as 65000
 neighbor 10.255.0.1 description CORE1-RR
 neighbor 10.255.0.1 update-source Loopback0
 neighbor 10.255.0.2 remote-as 65000
 neighbor 10.255.0.2 description CORE2-RR
 neighbor 10.255.0.2 update-source Loopback0
 !
 address-family ipv4
  neighbor 10.255.0.1 activate
  neighbor 10.255.0.2 activate
 exit-address-family
 !
 address-family vpnv4
  neighbor 10.255.0.1 activate
  neighbor 10.255.0.1 send-community both
  neighbor 10.255.0.2 activate
  neighbor 10.255.0.2 send-community both
 exit-address-family
!
vrf definition STUDENT-NET
 description Student Network - Main Campus
 rd 10.255.1.12:100
 address-family ipv4
  route-target export 65000:100
  route-target import 65000:100
 exit-address-family
!
vrf definition STAFF-NET
 description Staff Network - All Campuses
 rd 10.255.1.12:200
 address-family ipv4
  route-target export 65000:200
  route-target import 65000:200
 exit-address-family
!
vrf definition RESEARCH-NET
 description Research Network - All Campuses
 rd 10.255.1.12:300
 address-family ipv4
  route-target export 65000:300
  route-target import 65000:300
 exit-address-family
!
vrf definition GUEST-NET
 description Guest Network - All Campuses
 rd 10.255.1.12:500
 address-family ipv4
  route-target export 65000:500
  route-target import 65000:500
 exit-address-family
!
interface Loopback110
 description STUDENT-NET Customer Endpoint
 vrf forwarding STUDENT-NET
 ip address 172.10.0.2 255.255.255.255
!
interface Loopback120
 description STAFF-NET Customer Endpoint
 vrf forwarding STAFF-NET
 ip address 172.20.0.2 255.255.255.255
!
interface Loopback130
 description RESEARCH-NET Customer Endpoint
 vrf forwarding RESEARCH-NET
 ip address 172.30.0.2 255.255.255.255
!
interface Loopback150
 description GUEST-NET Customer Endpoint
 vrf forwarding GUEST-NET
 ip address 172.50.0.2 255.255.255.255
!
router bgp 65000
 address-family ipv4 vrf STUDENT-NET
  redistribute connected
 exit-address-family
 address-family ipv4 vrf STAFF-NET
  redistribute connected
 exit-address-family
 address-family ipv4 vrf RESEARCH-NET
  redistribute connected
 exit-address-family
 address-family ipv4 vrf GUEST-NET
  redistribute connected
 exit-address-family
""",
    "EUNIV-MED-PE1": """
router bgp 65000
 neighbor 10.255.0.1 remote-as 65000
 neighbor 10.255.0.1 description CORE1-RR
 neighbor 10.255.0.1 update-source Loopback0
 neighbor 10.255.0.2 remote-as 65000
 neighbor 10.255.0.2 description CORE2-RR
 neighbor 10.255.0.2 update-source Loopback0
 !
 address-family ipv4
  neighbor 10.255.0.1 activate
  neighbor 10.255.0.2 activate
 exit-address-family
 !
 address-family vpnv4
  neighbor 10.255.0.1 activate
  neighbor 10.255.0.1 send-community both
  neighbor 10.255.0.2 activate
  neighbor 10.255.0.2 send-community both
 exit-address-family
!
vrf definition STAFF-NET
 description Staff Network - All Campuses
 rd 10.255.2.11:200
 address-family ipv4
  route-target export 65000:200
  route-target import 65000:200
 exit-address-family
!
vrf definition RESEARCH-NET
 description Research Network - All Campuses
 rd 10.255.2.11:300
 address-family ipv4
  route-target export 65000:300
  route-target import 65000:300
 exit-address-family
!
vrf definition MEDICAL-NET
 description Medical/HIPAA Network - Medical Campus Only
 rd 10.255.2.11:400
 address-family ipv4
  route-target export 65000:400
  route-target import 65000:400
 exit-address-family
!
vrf definition GUEST-NET
 description Guest Network - All Campuses
 rd 10.255.2.11:500
 address-family ipv4
  route-target export 65000:500
  route-target import 65000:500
 exit-address-family
!
interface Loopback120
 description STAFF-NET Customer Endpoint
 vrf forwarding STAFF-NET
 ip address 172.20.0.11 255.255.255.255
!
interface Loopback130
 description RESEARCH-NET Customer Endpoint
 vrf forwarding RESEARCH-NET
 ip address 172.30.0.11 255.255.255.255
!
interface Loopback140
 description MEDICAL-NET Customer Endpoint
 vrf forwarding MEDICAL-NET
 ip address 172.40.0.11 255.255.255.255
!
interface Loopback150
 description GUEST-NET Customer Endpoint
 vrf forwarding GUEST-NET
 ip address 172.50.0.11 255.255.255.255
!
router bgp 65000
 address-family ipv4 vrf STAFF-NET
  redistribute connected
 exit-address-family
 address-family ipv4 vrf RESEARCH-NET
  redistribute connected
 exit-address-family
 address-family ipv4 vrf MEDICAL-NET
  redistribute connected
 exit-address-family
 address-family ipv4 vrf GUEST-NET
  redistribute connected
 exit-address-family
""",
    "EUNIV-MED-PE2": """
router bgp 65000
 neighbor 10.255.0.1 remote-as 65000
 neighbor 10.255.0.1 description CORE1-RR
 neighbor 10.255.0.1 update-source Loopback0
 neighbor 10.255.0.2 remote-as 65000
 neighbor 10.255.0.2 description CORE2-RR
 neighbor 10.255.0.2 update-source Loopback0
 !
 address-family ipv4
  neighbor 10.255.0.1 activate
  neighbor 10.255.0.2 activate
 exit-address-family
 !
 address-family vpnv4
  neighbor 10.255.0.1 activate
  neighbor 10.255.0.1 send-community both
  neighbor 10.255.0.2 activate
  neighbor 10.255.0.2 send-community both
 exit-address-family
!
vrf definition STAFF-NET
 description Staff Network - All Campuses
 rd 10.255.2.12:200
 address-family ipv4
  route-target export 65000:200
  route-target import 65000:200
 exit-address-family
!
vrf definition RESEARCH-NET
 description Research Network - All Campuses
 rd 10.255.2.12:300
 address-family ipv4
  route-target export 65000:300
  route-target import 65000:300
 exit-address-family
!
vrf definition MEDICAL-NET
 description Medical/HIPAA Network - Medical Campus Only
 rd 10.255.2.12:400
 address-family ipv4
  route-target export 65000:400
  route-target import 65000:400
 exit-address-family
!
vrf definition GUEST-NET
 description Guest Network - All Campuses
 rd 10.255.2.12:500
 address-family ipv4
  route-target export 65000:500
  route-target import 65000:500
 exit-address-family
!
interface Loopback120
 description STAFF-NET Customer Endpoint
 vrf forwarding STAFF-NET
 ip address 172.20.0.12 255.255.255.255
!
interface Loopback130
 description RESEARCH-NET Customer Endpoint
 vrf forwarding RESEARCH-NET
 ip address 172.30.0.12 255.255.255.255
!
interface Loopback140
 description MEDICAL-NET Customer Endpoint
 vrf forwarding MEDICAL-NET
 ip address 172.40.0.12 255.255.255.255
!
interface Loopback150
 description GUEST-NET Customer Endpoint
 vrf forwarding GUEST-NET
 ip address 172.50.0.12 255.255.255.255
!
router bgp 65000
 address-family ipv4 vrf STAFF-NET
  redistribute connected
 exit-address-family
 address-family ipv4 vrf RESEARCH-NET
  redistribute connected
 exit-address-family
 address-family ipv4 vrf MEDICAL-NET
  redistribute connected
 exit-address-family
 address-family ipv4 vrf GUEST-NET
  redistribute connected
 exit-address-family
""",
    "EUNIV-RES-PE1": """
router bgp 65000
 neighbor 10.255.0.1 remote-as 65000
 neighbor 10.255.0.1 description CORE1-RR
 neighbor 10.255.0.1 update-source Loopback0
 neighbor 10.255.0.2 remote-as 65000
 neighbor 10.255.0.2 description CORE2-RR
 neighbor 10.255.0.2 update-source Loopback0
 !
 address-family ipv4
  neighbor 10.255.0.1 activate
  neighbor 10.255.0.2 activate
 exit-address-family
 !
 address-family vpnv4
  neighbor 10.255.0.1 activate
  neighbor 10.255.0.1 send-community both
  neighbor 10.255.0.2 activate
  neighbor 10.255.0.2 send-community both
 exit-address-family
!
vrf definition STAFF-NET
 description Staff Network - All Campuses
 rd 10.255.3.11:200
 address-family ipv4
  route-target export 65000:200
  route-target import 65000:200
 exit-address-family
!
vrf definition RESEARCH-NET
 description Research Network - All Campuses
 rd 10.255.3.11:300
 address-family ipv4
  route-target export 65000:300
  route-target import 65000:300
 exit-address-family
!
vrf definition GUEST-NET
 description Guest Network - All Campuses
 rd 10.255.3.11:500
 address-family ipv4
  route-target export 65000:500
  route-target import 65000:500
 exit-address-family
!
interface Loopback120
 description STAFF-NET Customer Endpoint
 vrf forwarding STAFF-NET
 ip address 172.20.0.21 255.255.255.255
!
interface Loopback130
 description RESEARCH-NET Customer Endpoint
 vrf forwarding RESEARCH-NET
 ip address 172.30.0.21 255.255.255.255
!
interface Loopback150
 description GUEST-NET Customer Endpoint
 vrf forwarding GUEST-NET
 ip address 172.50.0.21 255.255.255.255
!
router bgp 65000
 address-family ipv4 vrf STAFF-NET
  redistribute connected
 exit-address-family
 address-family ipv4 vrf RESEARCH-NET
  redistribute connected
 exit-address-family
 address-family ipv4 vrf GUEST-NET
  redistribute connected
 exit-address-family
""",
    "EUNIV-RES-PE2": """
router bgp 65000
 neighbor 10.255.0.1 remote-as 65000
 neighbor 10.255.0.1 description CORE1-RR
 neighbor 10.255.0.1 update-source Loopback0
 neighbor 10.255.0.2 remote-as 65000
 neighbor 10.255.0.2 description CORE2-RR
 neighbor 10.255.0.2 update-source Loopback0
 !
 address-family ipv4
  neighbor 10.255.0.1 activate
  neighbor 10.255.0.2 activate
 exit-address-family
 !
 address-family vpnv4
  neighbor 10.255.0.1 activate
  neighbor 10.255.0.1 send-community both
  neighbor 10.255.0.2 activate
  neighbor 10.255.0.2 send-community both
 exit-address-family
!
vrf definition STAFF-NET
 description Staff Network - All Campuses
 rd 10.255.3.12:200
 address-family ipv4
  route-target export 65000:200
  route-target import 65000:200
 exit-address-family
!
vrf definition RESEARCH-NET
 description Research Network - All Campuses
 rd 10.255.3.12:300
 address-family ipv4
  route-target export 65000:300
  route-target import 65000:300
 exit-address-family
!
vrf definition GUEST-NET
 description Guest Network - All Campuses
 rd 10.255.3.12:500
 address-family ipv4
  route-target export 65000:500
  route-target import 65000:500
 exit-address-family
!
interface Loopback120
 description STAFF-NET Customer Endpoint
 vrf forwarding STAFF-NET
 ip address 172.20.0.22 255.255.255.255
!
interface Loopback130
 description RESEARCH-NET Customer Endpoint
 vrf forwarding RESEARCH-NET
 ip address 172.30.0.22 255.255.255.255
!
interface Loopback150
 description GUEST-NET Customer Endpoint
 vrf forwarding GUEST-NET
 ip address 172.50.0.22 255.255.255.255
!
router bgp 65000
 address-family ipv4 vrf STAFF-NET
  redistribute connected
 exit-address-family
 address-family ipv4 vrf RESEARCH-NET
  redistribute connected
 exit-address-family
 address-family ipv4 vrf GUEST-NET
  redistribute connected
 exit-address-family
"""
}


def main():
    testbed_path = "testbed.yaml"
    if not os.path.exists(testbed_path):
        print("ERROR: testbed.yaml not found!")
        return

    print("=" * 60)
    print("E-UNIVERSITY NETWORK - Customer Traffic Deployment")
    print("=" * 60)

    testbed = loader.load(testbed_path)

    # Phase 1: Configure Route Reflectors
    print("\n" + "=" * 60)
    print("PHASE 1: Configuring Route Reflectors")
    print("=" * 60)

    for device_name, config in RR_CONFIGS.items():
        print(f"\n  Configuring: {device_name}")
        try:
            device = testbed.devices[device_name]
            device.connect(log_stdout=False)
            device.configure(config)
            print("    ✅ BGP neighbors + VPNv4 configured")
            device.disconnect()
        except Exception as e:
            print(f"    ❌ Error: {e}")

    print("\n  ⏳ Waiting 10 seconds for BGP to establish...")
    time.sleep(10)

    # Phase 2: Configure PE Routers
    print("\n" + "=" * 60)
    print("PHASE 2: Configuring PE Routers")
    print("=" * 60)

    for device_name, config in PE_CONFIGS.items():
        print(f"\n  Configuring: {device_name}")
        try:
            device = testbed.devices[device_name]
            device.connect(log_stdout=False)
            device.configure(config)
            print("    ✅ VRFs + Customer interfaces configured")
            device.disconnect()
        except Exception as e:
            print(f"    ❌ Error: {e}")

    print("\n" + "=" * 60)
    print("DEPLOYMENT COMPLETE!")
    print("=" * 60)

    print("""
Verification Commands:

On CORE1 or CORE2:
  show ip bgp vpnv4 all summary
  show ip bgp vpnv4 all

On any PE (e.g., MAIN-PE1):
  show vrf
  show ip route vrf STAFF-NET
  show ip bgp vpnv4 vrf STAFF-NET

Test L3VPN Connectivity (from MAIN-PE1):
  ping vrf STAFF-NET 172.20.0.11 source 172.20.0.1
  ping vrf STAFF-NET 172.20.0.21 source 172.20.0.1
  traceroute vrf STAFF-NET 172.20.0.11 source 172.20.0.1
""")


if __name__ == "__main__":
    main()
