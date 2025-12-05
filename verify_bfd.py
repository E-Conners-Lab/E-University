#!/usr/bin/env python3
"""
E-University Network - BFD Verification & Failover Test
Demonstrates sub-second failover with BFD
"""


from pyats.topology import loader


def main():
    testbed = loader.load("testbed.yaml")

    print("=" * 70)
    print("E-UNIVERSITY BFD VERIFICATION")
    print("=" * 70)

    # =========================================================================
    # Test 1: Check BFD Neighbors on Core Router
    # =========================================================================
    print("\n📡 TEST 1: BFD Neighbors on CORE1")
    print("-" * 70)

    core1 = testbed.devices["EUNIV-CORE1"]
    core1.connect(log_stdout=False)

    output = core1.execute("show bfd neighbors")
    print(output)

    # Count BFD sessions
    bfd_up = output.count("Up")
    print(f"\n  ✅ BFD sessions UP: {bfd_up}")

    core1.disconnect()

    # =========================================================================
    # Test 2: Verify OSPF BFD Status
    # =========================================================================
    print("\n\n🔗 TEST 2: OSPF BFD Status on CORE1")
    print("-" * 70)

    core1 = testbed.devices["EUNIV-CORE1"]
    core1.connect(log_stdout=False)

    output = core1.execute("show ip ospf interface brief")
    print(output)

    output = core1.execute("show ip ospf interface GigabitEthernet2 | include BFD")
    print(f"\nBFD on Gi2: {output.strip()}")

    core1.disconnect()

    # =========================================================================
    # Test 3: Verify BGP BFD Status
    # =========================================================================
    print("\n\n🌐 TEST 3: BGP BFD Status on MAIN-PE1")
    print("-" * 70)

    pe1 = testbed.devices["EUNIV-MAIN-PE1"]
    pe1.connect(log_stdout=False)

    output = pe1.execute("show ip bgp neighbors | include neighbor|BFD")
    print(output)

    pe1.disconnect()

    # =========================================================================
    # Test 4: BFD Timers Verification
    # =========================================================================
    print("\n\n⏱️  TEST 4: BFD Timer Details")
    print("-" * 70)

    core1 = testbed.devices["EUNIV-CORE1"]
    core1.connect(log_stdout=False)

    output = core1.execute("show bfd neighbors details | include Neighbor|State|Interval")
    print(output)

    core1.disconnect()

    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 70)
    print("BFD STATUS SUMMARY")
    print("=" * 70)
    print(f"""
  BFD Sessions Active:  {bfd_up}
  Detection Time:       ~150ms (50ms x 3)
  
  Without BFD:  OSPF dead-interval = 40 seconds
  With BFD:     Detection = 150 milliseconds
  
  ⚡ Improvement: ~267x faster failover!
""")

    # =========================================================================
    # Optional: Live Failover Test
    # =========================================================================
    print("=" * 70)
    print("READY FOR FAILOVER TEST")
    print("=" * 70)
    print("""
To test BFD failover:

  TERMINAL 1 - Start continuous ping:
  -------------------------------------
  ssh admin@192.168.68.209   (MAIN-PE1)
  ping vrf STAFF-NET 172.20.0.11 source 172.20.0.1 repeat 10000
  
  TERMINAL 2 - Trigger failover:
  -------------------------------------
  ssh admin@192.168.68.200   (CORE1)
  conf t
  interface GigabitEthernet2
    shutdown
  
  OBSERVE: Only 1-3 pings should fail (~150-450ms)
  
  RESTORE:
  -------------------------------------
  no shutdown
  end
  
  Compare: Without BFD, you'd lose ~40 seconds of traffic!
""")

if __name__ == "__main__":
    main()
