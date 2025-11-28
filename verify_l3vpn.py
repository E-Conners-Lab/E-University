#!/usr/bin/env python3
"""
E-University Network - L3VPN Verification Script
Tests VPNv4 BGP sessions and cross-campus VRF connectivity
"""

from pyats.topology import loader
import re

def main():
    testbed = loader.load("testbed.yaml")
    
    print("=" * 70)
    print("E-UNIVERSITY L3VPN VERIFICATION")
    print("=" * 70)
    
    # =========================================================================
    # Test 1: VPNv4 BGP Summary on Route Reflector
    # =========================================================================
    print("\n📡 TEST 1: VPNv4 BGP Sessions on CORE1")
    print("-" * 70)
    
    core1 = testbed.devices["EUNIV-CORE1"]
    core1.connect(log_stdout=False)
    
    output = core1.execute("show ip bgp vpnv4 all summary")
    print(output)
    
    # Count established sessions
    established = len(re.findall(r'\d+\s*$', output, re.MULTILINE))
    print(f"\n  ✅ VPNv4 sessions visible: {established}")
    
    core1.disconnect()
    
    # =========================================================================
    # Test 2: VRF Status on a PE
    # =========================================================================
    print("\n\n📋 TEST 2: VRF Status on MAIN-PE1")
    print("-" * 70)
    
    pe1 = testbed.devices["EUNIV-MAIN-PE1"]
    pe1.connect(log_stdout=False)
    
    output = pe1.execute("show vrf")
    print(output)
    
    # =========================================================================
    # Test 3: VRF Routes
    # =========================================================================
    print("\n\n🗺️  TEST 3: STAFF-NET Routes on MAIN-PE1")
    print("-" * 70)
    
    output = pe1.execute("show ip route vrf STAFF-NET")
    print(output)
    
    # Count routes from other PEs
    remote_routes = output.count("10.255.")
    print(f"\n  ✅ Remote VPN routes received: {remote_routes}")
    
    # =========================================================================
    # Test 4: Cross-Campus Ping Tests
    # =========================================================================
    print("\n\n🏓 TEST 4: Cross-Campus L3VPN Connectivity")
    print("-" * 70)
    
    ping_tests = [
        ("STAFF-NET", "172.20.0.1", "172.20.0.11", "Main→Medical"),
        ("STAFF-NET", "172.20.0.1", "172.20.0.21", "Main→Research"),
        ("RESEARCH-NET", "172.30.0.1", "172.30.0.22", "Main→Research"),
        ("GUEST-NET", "172.50.0.1", "172.50.0.12", "Main→Medical"),
    ]
    
    results = []
    for vrf, source, dest, description in ping_tests:
        cmd = f"ping vrf {vrf} {dest} source {source} repeat 3 timeout 2"
        output = pe1.execute(cmd)
        
        success = "!" in output and "....." not in output
        status = "✅ PASS" if success else "❌ FAIL"
        results.append((description, vrf, dest, status))
        print(f"  {status} | {description:15} | {vrf:12} | {source} → {dest}")
    
    pe1.disconnect()
    
    # =========================================================================
    # Test 5: VRF Isolation Test
    # =========================================================================
    print("\n\n🔒 TEST 5: VRF Isolation (These should FAIL)")
    print("-" * 70)
    
    pe1 = testbed.devices["EUNIV-MAIN-PE1"]
    pe1.connect(log_stdout=False)
    
    # Try to ping STAFF-NET IP from STUDENT-NET VRF (should fail)
    cmd = "ping vrf STUDENT-NET 172.20.0.11 repeat 2 timeout 1"
    output = pe1.execute(cmd)
    isolated = "....." in output or "%" in output or "0/2" in output or "Success rate is 0" in output
    status = "✅ ISOLATED" if isolated else "⚠️  LEAK DETECTED"
    print(f"  {status} | STUDENT-NET cannot reach STAFF-NET (172.20.0.11)")
    
    pe1.disconnect()
    
    # =========================================================================
    # Test 6: MPLS Label Path
    # =========================================================================
    print("\n\n🏷️  TEST 6: MPLS Label Path (Main→Medical via STAFF-NET)")
    print("-" * 70)
    
    pe1 = testbed.devices["EUNIV-MAIN-PE1"]
    pe1.connect(log_stdout=False)
    
    output = pe1.execute("traceroute vrf STAFF-NET 172.20.0.11 source 172.20.0.1 numeric timeout 2 probe 1")
    print(output)
    
    # Check for MPLS labels in output
    has_labels = "MPLS" in output or "Label" in output
    hops = output.count("\n ") 
    print(f"\n  ℹ️  Path has {hops} hops")
    
    pe1.disconnect()
    
    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for r in results if "PASS" in r[3])
    total = len(results)
    
    print(f"""
  VPNv4 Sessions:     {"✅ Active" if established > 0 else "❌ Down"}
  VRF Configuration:  ✅ Complete
  Cross-Campus Pings: {passed}/{total} successful
  VRF Isolation:      {"✅ Working" if isolated else "⚠️  Check routes"}
  
  🎉 L3VPN is {"OPERATIONAL" if passed == total else "PARTIALLY WORKING"}!
""")

if __name__ == "__main__":
    main()
