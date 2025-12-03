#!/usr/bin/env python3
"""
E-University Network - Internet Connectivity Verification
Verifies BGP sessions, default routes, and internet reachability
"""

import os
from dotenv import load_dotenv
from pyats.topology import loader
import re

# Load environment variables
load_dotenv()

TESTBED = """
testbed:
  name: E-University-Verify
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

  EUNIV-INET-GW1:
    os: iosxe
    type: router
    connections:
      defaults:
        class: unicon.Unicon
      cli:
        protocol: ssh
        ip: 192.168.68.206

  EUNIV-MAIN-PE1:
    os: iosxe
    type: router
    connections:
      defaults:
        class: unicon.Unicon
      cli:
        protocol: ssh
        ip: 192.168.68.209
"""


def main():
    import tempfile
    import os

    print("=" * 70)
    print("E-UNIVERSITY - INTERNET CONNECTIVITY VERIFICATION")
    print("=" * 70)

    # Write testbed to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(TESTBED)
        testbed_file = f.name

    try:
        testbed = loader.load(testbed_file)
    finally:
        os.unlink(testbed_file)

    # =========================================================================
    # TEST 1: Check BGP on CORE1 (Route Reflector)
    # =========================================================================
    print("\n" + "─" * 70)
    print("TEST 1: BGP Sessions on CORE1 (Route Reflector)")
    print("─" * 70)

    try:
        device = testbed.devices["EUNIV-CORE1"]
        device.connect(log_stdout=False, learn_hostname=True)

        output = device.execute("show ip bgp summary")
        print(output)

        # Check for INET-GW neighbors (actual IPs are .101 and .102)
        if "10.255.0.101" in output and "10.255.0.102" in output:
            print("\n✅ INET-GW1 (10.255.0.101) and INET-GW2 (10.255.0.102) are BGP neighbors")
        elif "10.255.0.101" in output:
            print("\n⚠️  Only INET-GW1 (10.255.0.101) is a neighbor - check INET-GW2")
        elif "10.255.0.102" in output:
            print("\n⚠️  Only INET-GW2 (10.255.0.102) is a neighbor - check INET-GW1")
        else:
            print("\n⚠️  INET-GW neighbors may not be configured")

        # Check default route
        print("\n" + "─" * 70)
        print("TEST 2: Default Route on CORE1")
        print("─" * 70)

        output = device.execute("show ip bgp 0.0.0.0/0")
        print(output)

        if "10.255.0.101" in output or "10.255.0.11)" in output:
            print("\n✅ Default route received from INET-GW1")
        if "10.255.0.102" in output or "10.255.0.12)" in output:
            print("✅ Default route received from INET-GW2")
        if "localpref 200" in output:
            print("✅ Primary path (local-pref 200) detected")

        device.disconnect()

    except Exception as e:
        print(f"❌ Error connecting to CORE1: {e}")

    # =========================================================================
    # TEST 3: Check BGP on INET-GW1
    # =========================================================================
    print("\n" + "─" * 70)
    print("TEST 3: BGP Sessions on INET-GW1 (Primary Gateway)")
    print("─" * 70)

    try:
        device = testbed.devices["EUNIV-INET-GW1"]
        device.connect(log_stdout=False, learn_hostname=True)

        output = device.execute("show ip bgp summary")
        print(output)

        # Check for RR neighbors
        has_core1 = "10.255.0.1 " in output or "10.255.0.1\n" in output
        has_core2 = "10.255.0.2 " in output or "10.255.0.2\n" in output

        if has_core1 and has_core2:
            print("\n✅ INET-GW1 peering with both Route Reflectors (CORE1 & CORE2)")
        elif has_core1:
            print("\n⚠️  INET-GW1 only peering with CORE1 - check CORE2 session")
        elif has_core2:
            print("\n⚠️  INET-GW1 only peering with CORE2 - check CORE1 session")
        else:
            print("\n❌ INET-GW1 not peering with any Route Reflectors!")
        # Check advertised routes
        print("\n" + "─" * 70)
        print("TEST 4: Routes Advertised by INET-GW1")
        print("─" * 70)

        output = device.execute("show ip bgp")
        print(output)

        routes_check = {
            "0.0.0.0": "Default route",
            "8.8.8.8": "Google DNS",
            "1.1.1.1": "Cloudflare DNS",
            "198.51.100.0": "Public prefix"
        }

        for route, desc in routes_check.items():
            if route in output:
                print(f"✅ {desc} ({route}) in BGP table")
            else:
                print(f"⚠️  {desc} ({route}) NOT in BGP table")

        device.disconnect()

    except Exception as e:
        print(f"❌ Error connecting to INET-GW1: {e}")

    # =========================================================================
    # TEST 5: Check PE Router receives default route
    # =========================================================================
    print("\n" + "─" * 70)
    print("TEST 5: Default Route on MAIN-PE1 (Customer Edge)")
    print("─" * 70)

    try:
        device = testbed.devices["EUNIV-MAIN-PE1"]
        device.connect(log_stdout=False, learn_hostname=True)

        output = device.execute("show ip route 0.0.0.0")
        print(output)

        # Check if BGP default route is installed (learned from RRs)
        if "bgp" in output.lower() and "0.0.0.0/0" in output:
            print("\n✅ Default route received via BGP")
            if "10.255.0.1" in output or "10.255.0.2" in output:
                print("✅ Learned from Route Reflector (CORE1/CORE2)")
        elif "10.255.0.11" in output or "10.255.0.101" in output:
            print("\n✅ Default route pointing to INET-GW1 (PRIMARY)")
        elif "10.255.0.12" in output or "10.255.0.102" in output:
            print("\n⚠️  Default route pointing to INET-GW2 (BACKUP) - check INET-GW1")
        elif "static" in output.lower():
            print("\n⚠️  Static default route (not BGP) - consider removing it")
        else:
            print("\n❌ No default route received!")

        # Test connectivity to simulated internet
        print("\n" + "─" * 70)
        print("TEST 6: Connectivity to Simulated Internet")
        print("─" * 70)

        targets = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]

        for target in targets:
            output = device.execute(f"ping {target} repeat 3 timeout 2")
            print(f"\nPing {target}:")

            # Extract success rate
            if "Success rate is 100" in output:
                print(f"  ✅ {target} - 100% success")
            elif "Success rate is 0" in output:
                print(f"  ❌ {target} - 0% success (FAILED)")
            else:
                # Extract actual success rate
                match = re.search(r'Success rate is (\d+) percent', output)
                if match:
                    rate = match.group(1)
                    print(f"  ⚠️  {target} - {rate}% success")
                else:
                    print(f"  ? {target} - Unknown result")
                    print(output)

        device.disconnect()

    except Exception as e:
        print(f"❌ Error connecting to MAIN-PE1: {e}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)
    print("""
Expected Results:
  ✅ CORE1 has BGP sessions with INET-GW1 (10.255.0.101) and INET-GW2 (10.255.0.102)
  ✅ Default route (0.0.0.0/0) received from both gateways
  ✅ Primary path via INET-GW1 (local-pref 200)
  ✅ PE routers receive default via BGP from Route Reflectors
  ✅ PE routers can ping 8.8.8.8, 1.1.1.1, 9.9.9.9

If ping fails but BGP is up:
  • Check OSPF is advertising INET-GW loopbacks
  • Verify: show ip route 10.255.0.101 (should be via OSPF)

Failover Test:
  On INET-GW1: conf t → int Gi2 → shutdown
  On PE: show ip bgp 0.0.0.0/0 (should now prefer INET-GW2)
""")


if __name__ == "__main__":
    main()