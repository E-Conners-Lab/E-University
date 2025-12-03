#!/usr/bin/env python3
"""
E-University Network - Internet Gateway Deployment
Configures INET-GW1 and INET-GW2 with BGP for internet connectivity

Run: python3 deploy_internet.py
"""

import os
from dotenv import load_dotenv
from pyats.topology import loader
import time

# Load environment variables
load_dotenv()

TESTBED = """
testbed:
  name: E-University-Internet
  credentials:
    default:
      username: "%ENV{{DEVICE_USERNAME}}"
      password: "%ENV{{DEVICE_PASSWORD}}"
    enable:
      password: "%ENV{{DEVICE_ENABLE_PASSWORD}}"

devices:
  EUNIV-CORE1:
    os: iosxe
    type: router
    connections:
      defaults:
        class: unicon.Unicon
      cli:
        protocol: ssh
        ip: 192.168.68.200

  EUNIV-CORE2:
    os: iosxe
    type: router
    connections:
      defaults:
        class: unicon.Unicon
      cli:
        protocol: ssh
        ip: 192.168.68.202

  EUNIV-INET-GW1:
    os: iosxe
    type: router
    connections:
      defaults:
        class: unicon.Unicon
      cli:
        protocol: ssh
        ip: 192.168.68.206

  EUNIV-INET-GW2:
    os: iosxe
    type: router
    connections:
      defaults:
        class: unicon.Unicon
      cli:
        protocol: ssh
        ip: 192.168.68.207
"""

# Configuration for each router
CONFIGS = {
    "EUNIV-CORE1": """
router bgp 65000
 neighbor 10.255.0.11 remote-as 65000
 neighbor 10.255.0.11 description INET-GW1
 neighbor 10.255.0.11 update-source Loopback0
 neighbor 10.255.0.12 remote-as 65000
 neighbor 10.255.0.12 description INET-GW2
 neighbor 10.255.0.12 update-source Loopback0
 address-family ipv4
  neighbor 10.255.0.11 activate
  neighbor 10.255.0.11 route-reflector-client
  neighbor 10.255.0.12 activate
  neighbor 10.255.0.12 route-reflector-client
 exit-address-family
""",

    "EUNIV-CORE2": """
router bgp 65000
 neighbor 10.255.0.11 remote-as 65000
 neighbor 10.255.0.11 description INET-GW1
 neighbor 10.255.0.11 update-source Loopback0
 neighbor 10.255.0.12 remote-as 65000
 neighbor 10.255.0.12 description INET-GW2
 neighbor 10.255.0.12 update-source Loopback0
 address-family ipv4
  neighbor 10.255.0.11 activate
  neighbor 10.255.0.11 route-reflector-client
  neighbor 10.255.0.12 activate
  neighbor 10.255.0.12 route-reflector-client
 exit-address-family
""",

    "EUNIV-INET-GW1": """
interface Loopback100
 description Simulated-Google-DNS
 ip address 8.8.8.8 255.255.255.255
!
interface Loopback101
 description Simulated-Cloudflare-DNS
 ip address 1.1.1.1 255.255.255.255
!
interface Loopback102
 description Simulated-Web-Server
 ip address 93.184.216.34 255.255.255.255
!
interface Loopback201
 description E-University-Public-Prefix
 ip address 198.51.100.1 255.255.255.0
!
interface Loopback0
 ip ospf 1 area 0
!
ip route 0.0.0.0 0.0.0.0 Null0 name INTERNET-DEFAULT
ip route 198.51.100.0 255.255.255.0 Null0 name PUBLIC-PREFIX
!
route-map PRIMARY-OUT permit 10
 set local-preference 200
!
router bgp 65000
 bgp router-id 10.255.0.11
 bgp log-neighbor-changes
 neighbor 10.255.0.1 remote-as 65000
 neighbor 10.255.0.1 description CORE1-RR
 neighbor 10.255.0.1 update-source Loopback0
 neighbor 10.255.0.2 remote-as 65000
 neighbor 10.255.0.2 description CORE2-RR
 neighbor 10.255.0.2 update-source Loopback0
 address-family ipv4
  network 0.0.0.0
  network 8.8.8.8 mask 255.255.255.255
  network 1.1.1.1 mask 255.255.255.255
  network 93.184.216.34 mask 255.255.255.255
  network 198.51.100.0 mask 255.255.255.0
  neighbor 10.255.0.1 activate
  neighbor 10.255.0.2 activate
  neighbor 10.255.0.1 route-map PRIMARY-OUT out
  neighbor 10.255.0.2 route-map PRIMARY-OUT out
 exit-address-family
""",

    "EUNIV-INET-GW2": """
interface Loopback100
 description Simulated-Google-DNS-Secondary
 ip address 8.8.4.4 255.255.255.255
!
interface Loopback101
 description Simulated-Quad9-DNS
 ip address 9.9.9.9 255.255.255.255
!
interface Loopback102
 description Simulated-OpenDNS
 ip address 208.67.222.222 255.255.255.255
!
interface Loopback201
 description E-University-Public-Secondary
 ip address 198.51.100.2 255.255.255.0
!
interface Loopback0
 ip ospf 1 area 0
!
ip route 0.0.0.0 0.0.0.0 Null0 name INTERNET-DEFAULT-BACKUP
ip route 198.51.100.0 255.255.255.0 Null0 name PUBLIC-PREFIX
!
route-map BACKUP-OUT permit 10
 set local-preference 100
!
router bgp 65000
 bgp router-id 10.255.0.12
 bgp log-neighbor-changes
 neighbor 10.255.0.1 remote-as 65000
 neighbor 10.255.0.1 description CORE1-RR
 neighbor 10.255.0.1 update-source Loopback0
 neighbor 10.255.0.2 remote-as 65000
 neighbor 10.255.0.2 description CORE2-RR
 neighbor 10.255.0.2 update-source Loopback0
 address-family ipv4
  network 0.0.0.0
  network 8.8.4.4 mask 255.255.255.255
  network 9.9.9.9 mask 255.255.255.255
  network 208.67.222.222 mask 255.255.255.255
  network 198.51.100.0 mask 255.255.255.0
  neighbor 10.255.0.1 activate
  neighbor 10.255.0.2 activate
  neighbor 10.255.0.1 route-map BACKUP-OUT out
  neighbor 10.255.0.2 route-map BACKUP-OUT out
 exit-address-family
"""
}


def main():
    import tempfile
    import os

    print("=" * 70)
    print("E-UNIVERSITY - INTERNET GATEWAY DEPLOYMENT")
    print("=" * 70)

    # Write testbed to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(TESTBED)
        testbed_file = f.name

    try:
        testbed = loader.load(testbed_file)
    finally:
        os.unlink(testbed_file)

    # Deploy order matters - RRs first, then INET-GWs
    deploy_order = ["EUNIV-CORE1", "EUNIV-CORE2", "EUNIV-INET-GW1", "EUNIV-INET-GW2"]

    results = {"success": [], "failed": []}

    for router in deploy_order:
        print(f"\n{'─' * 70}")
        print(f"Configuring: {router}")
        print(f"{'─' * 70}")

        try:
            device = testbed.devices[router]
            device.connect(log_stdout=False, learn_hostname=True)

            config = CONFIGS[router]
            output = device.configure(config)

            print(f"✅ {router} configured successfully")
            results["success"].append(router)

            device.disconnect()

        except Exception as e:
            print(f"❌ {router} failed: {e}")
            results["failed"].append(router)

        # Small delay between routers
        time.sleep(2)

    # Summary
    print("\n" + "=" * 70)
    print("DEPLOYMENT SUMMARY")
    print("=" * 70)
    print(f"✅ Successful: {len(results['success'])}")
    print(f"❌ Failed: {len(results['failed'])}")

    if results["failed"]:
        print(f"\nFailed routers: {', '.join(results['failed'])}")

    print("""
VERIFICATION COMMANDS:
─────────────────────
On CORE1:
  show ip bgp summary
  show ip bgp 0.0.0.0/0

On any PE router:
  show ip route 0.0.0.0
  ping 8.8.8.8
  ping 1.1.1.1

EXPECTED RESULT:
  • Default route via 10.255.0.11 (INET-GW1) with local-pref 200
  • Backup via 10.255.0.12 (INET-GW2) with local-pref 100
  • Ping to 8.8.8.8 and 1.1.1.1 should work from all routers
""")


if __name__ == "__main__":
    main()