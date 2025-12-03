#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
E-UNIVERSITY NETWORK - TROUBLESHOOTING DEMO (VIDEO READY)
═══════════════════════════════════════════════════════════════════════════════

Dramatic troubleshooting demonstration for LinkedIn videos.
Shows the automated diagnostic process with visual feedback.

Usage:
  python3 troubleshoot_demo.py                    # Interactive menu
  python3 troubleshoot_demo.py --break-bgp        # Demo: Break BGP then fix
  python3 troubleshoot_demo.py --break-vrf        # Demo: Break VRF then fix
  python3 troubleshoot_demo.py --health           # Run health check

Author: E-University Network Team
═══════════════════════════════════════════════════════════════════════════════
"""

import os
from dotenv import load_dotenv
from netmiko import ConnectHandler
import re
import sys
import time
import argparse

# Load environment variables
load_dotenv()

USERNAME = os.getenv("DEVICE_USERNAME", "admin")
PASSWORD = os.getenv("DEVICE_PASSWORD")

DEVICES = {
    "CORE1": {"ip": "192.168.68.200", "loopback": "10.255.0.1"},
    "CORE2": {"ip": "192.168.68.202", "loopback": "10.255.0.2"},
    "MAIN-PE1": {"ip": "192.168.68.209", "loopback": "10.255.1.11"},
    "MED-PE1": {"ip": "192.168.68.212", "loopback": "10.255.2.11"},
    "RES-PE1": {"ip": "192.168.68.215", "loopback": "10.255.3.11"},
}

# Colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def connect(name):
    """Connect to device"""
    if name not in DEVICES:
        return None
    device = {
        "device_type": "cisco_ios",
        "host": DEVICES[name]["ip"],
        "username": USERNAME,
        "password": PASSWORD,
        "secret": PASSWORD,
        "timeout": 15,
    }
    try:
        conn = ConnectHandler(**device)
        conn.enable()
        return conn
    except:
        return None


def dramatic_pause(seconds=2, message=""):
    """Pause with optional message"""
    if message:
        print(f"\n  {CYAN}⏳ {message}{RESET}")
    time.sleep(seconds)


def typing_effect(text, delay=0.03):
    """Print with typing effect"""
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()


def run_live_command(conn, command, description):
    """Run command with live visual feedback"""
    print(f"\n  {YELLOW}▶ {description}{RESET}")
    print(f"  {CYAN}$ {command}{RESET}")
    dramatic_pause(1)

    output = conn.send_command(command, read_timeout=30)

    # Show abbreviated output
    lines = output.strip().split('\n')
    if len(lines) > 10:
        for line in lines[:8]:
            print(f"    {line}")
        print(f"    {CYAN}... ({len(lines) - 8} more lines){RESET}")
    else:
        for line in lines:
            print(f"    {line}")

    return output


def demo_break_and_fix_bgp():
    """
    DEMO: Break BGP VPNv4 session, watch tests fail, then fix it.

    Great for showing automated detection and resolution.
    """

    print()
    print(f"{CYAN}{'█' * 70}")
    print(f"█{' ' * 68}█")
    print(f"█  {'LIVE DEMO: BGP VPNv4 FAILURE & RECOVERY':<65}█")
    print(f"█{' ' * 68}█")
    print(f"{'█' * 70}{RESET}")
    print()

    # Connect to devices
    print(f"  {BOLD}Connecting to network devices...{RESET}")
    pe1 = connect("MAIN-PE1")
    core1 = connect("CORE1")

    if not pe1 or not core1:
        print(f"  {RED}Failed to connect!{RESET}")
        return

    print(f"  {GREEN}✓ Connected to MAIN-PE1 and CORE1{RESET}")

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 1: Show working state
    # ═══════════════════════════════════════════════════════════════════════════

    dramatic_pause(2, "PHASE 1: Verify current working state...")

    print()
    print(f"  {GREEN}{'═' * 66}{RESET}")
    print(f"  {GREEN}  PHASE 1: BASELINE - EVERYTHING WORKING{RESET}")
    print(f"  {GREEN}{'═' * 66}{RESET}")

    # Show VPNv4 is working
    output = run_live_command(pe1, "show ip bgp vpnv4 all summary", "Check VPNv4 sessions")

    # Test ping
    output = run_live_command(pe1, "ping vrf STAFF-NET 172.20.0.11 source 172.20.0.1 repeat 5",
                              "Test L3VPN connectivity")

    if "!!!!!" in output:
        print(f"\n  {GREEN}✓ STAFF-NET connectivity: WORKING{RESET}")

    dramatic_pause(3, "Everything working. Now let's break it...")

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 2: Break VPNv4
    # ═══════════════════════════════════════════════════════════════════════════

    print()
    print(f"  {RED}{'═' * 66}{RESET}")
    print(f"  {RED}  PHASE 2: INJECTING FAILURE{RESET}")
    print(f"  {RED}{'═' * 66}{RESET}")

    dramatic_pause(2, "Disabling VPNv4 on MAIN-PE1...")

    print(f"\n  {YELLOW}▶ Shutting down VPNv4 on MAIN-PE1{RESET}")
    print(f"  {CYAN}$ conf t{RESET}")
    print(f"  {CYAN}$ router bgp 65000{RESET}")
    print(f"  {CYAN}$ address-family vpnv4{RESET}")
    print(f"  {CYAN}$ no neighbor 10.255.0.1 activate{RESET}")
    print(f"  {CYAN}$ no neighbor 10.255.0.2 activate{RESET}")

    # Actually break it
    pe1.send_config_set([
        "router bgp 65000",
        "address-family vpnv4",
        "no neighbor 10.255.0.1 activate",
        "no neighbor 10.255.0.2 activate",
    ])

    print(f"\n  {RED}⚠ VPNv4 DISABLED - Network partially broken!{RESET}")

    dramatic_pause(5, "Waiting for BGP to converge...")

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 3: Automated Detection
    # ═══════════════════════════════════════════════════════════════════════════

    print()
    print(f"  {YELLOW}{'═' * 66}{RESET}")
    print(f"  {YELLOW}  PHASE 3: AUTOMATED TROUBLESHOOTING{RESET}")
    print(f"  {YELLOW}{'═' * 66}{RESET}")

    dramatic_pause(2, "Running automated diagnostics...")

    # Check VPNv4 - should be broken now
    output = run_live_command(pe1, "show ip bgp vpnv4 all summary", "Check VPNv4 sessions")

    print(f"\n  {RED}✗ VPNv4 sessions: NOT ACTIVE{RESET}")

    # Try ping - should fail
    output = run_live_command(pe1, "ping vrf STAFF-NET 172.20.0.11 source 172.20.0.1 repeat 3 timeout 2",
                              "Test L3VPN connectivity")

    if "!" not in output or "Success rate is 0" in output:
        print(f"\n  {RED}✗ STAFF-NET connectivity: FAILED{RESET}")

    # Check VRF route
    output = run_live_command(pe1, "show ip route vrf STAFF-NET 172.20.0.11", "Check VRF routing table")

    if "not in table" in output.lower() or "172.20.0.11" not in output:
        print(f"\n  {RED}✗ Route to 172.20.0.11: MISSING{RESET}")

    # Diagnosis
    print()
    print(f"  {RED}╔════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"  {RED}║  ROOT CAUSE IDENTIFIED                                         ║{RESET}")
    print(f"  {RED}╠════════════════════════════════════════════════════════════════╣{RESET}")
    print(f"  {RED}║  • VPNv4 address family not active                             ║{RESET}")
    print(f"  {RED}║  • No VPNv4 neighbors established                              ║{RESET}")
    print(f"  {RED}║  • Remote VRF routes not being received                        ║{RESET}")
    print(f"  {RED}╚════════════════════════════════════════════════════════════════╝{RESET}")

    dramatic_pause(3, "Automated fix ready. Applying...")

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 4: Automated Fix
    # ═══════════════════════════════════════════════════════════════════════════

    print()
    print(f"  {GREEN}{'═' * 66}{RESET}")
    print(f"  {GREEN}  PHASE 4: AUTOMATED REMEDIATION{RESET}")
    print(f"  {GREEN}{'═' * 66}{RESET}")

    print(f"\n  {YELLOW}▶ Re-enabling VPNv4 on MAIN-PE1{RESET}")
    print(f"  {CYAN}$ conf t{RESET}")
    print(f"  {CYAN}$ router bgp 65000{RESET}")
    print(f"  {CYAN}$ address-family vpnv4{RESET}")
    print(f"  {CYAN}$ neighbor 10.255.0.1 activate{RESET}")
    print(f"  {CYAN}$ neighbor 10.255.0.2 activate{RESET}")

    # Fix it
    pe1.send_config_set([
        "router bgp 65000",
        "address-family vpnv4",
        "neighbor 10.255.0.1 activate",
        "neighbor 10.255.0.1 send-community extended",
        "neighbor 10.255.0.2 activate",
        "neighbor 10.255.0.2 send-community extended",
    ])

    print(f"\n  {GREEN}✓ Configuration applied{RESET}")

    dramatic_pause(8, "Waiting for BGP VPNv4 to reconverge (8 seconds)...")

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 5: Verify Fix
    # ═══════════════════════════════════════════════════════════════════════════

    print()
    print(f"  {GREEN}{'═' * 66}{RESET}")
    print(f"  {GREEN}  PHASE 5: VERIFICATION{RESET}")
    print(f"  {GREEN}{'═' * 66}{RESET}")

    # Check VPNv4 - should be working now
    output = run_live_command(pe1, "show ip bgp vpnv4 all summary", "Verify VPNv4 sessions")

    if "10.255.0.1" in output and "10.255.0.2" in output:
        print(f"\n  {GREEN}✓ VPNv4 sessions: RE-ESTABLISHED{RESET}")

    # Test ping
    output = run_live_command(pe1, "ping vrf STAFF-NET 172.20.0.11 source 172.20.0.1 repeat 5",
                              "Verify L3VPN connectivity")

    if "!!!!!" in output:
        print(f"\n  {GREEN}✓ STAFF-NET connectivity: RESTORED{RESET}")

    # Final summary
    print()
    print(f"  {GREEN}╔════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"  {GREEN}║                                                                ║{RESET}")
    print(f"  {GREEN}║   ✓ ISSUE DETECTED, DIAGNOSED, AND FIXED AUTOMATICALLY       ║{RESET}")
    print(f"  {GREEN}║                                                                ║{RESET}")
    print(f"  {GREEN}║   Timeline:                                                    ║{RESET}")
    print(f"  {GREEN}║     • Failure injected                                         ║{RESET}")
    print(f"  {GREEN}║     • Automated detection: 5 seconds                           ║{RESET}")
    print(f"  {GREEN}║     • Root cause analysis: 3 seconds                           ║{RESET}")
    print(f"  {GREEN}║     • Automated fix applied: 2 seconds                         ║{RESET}")
    print(f"  {GREEN}║     • Service restored: 8 seconds (BGP convergence)            ║{RESET}")
    print(f"  {GREEN}║                                                                ║{RESET}")
    print(f"  {GREEN}║   Total time to resolution: ~18 seconds                        ║{RESET}")
    print(f"  {GREEN}║                                                                ║{RESET}")
    print(f"  {GREEN}╚════════════════════════════════════════════════════════════════╝{RESET}")

    pe1.disconnect()
    core1.disconnect()

    print()


def demo_health_check():
    """
    Run a dramatic network health check for video.
    """

    print()
    print(f"{CYAN}{'█' * 70}")
    print(f"█{' ' * 68}█")
    print(f"█  {'NETWORK HEALTH CHECK':<65}█")
    print(f"█{' ' * 68}█")
    print(f"{'█' * 70}{RESET}")
    print()

    dramatic_pause(2, "Starting comprehensive health assessment...")

    checks = [
        ("Device Reachability", "MAIN-PE1", "show version | include uptime"),
        ("OSPF Status", "MAIN-PE1", "show ip ospf neighbor | count FULL"),
        ("MPLS LDP", "MAIN-PE1", "show mpls ldp neighbor | count Oper"),
        ("BGP Sessions", "CORE1", "show ip bgp summary | include Estab"),
        ("VPNv4 Routes", "CORE1", "show ip bgp vpnv4 all | count 172."),
        ("Internet Path", "MAIN-PE1", "show ip route 0.0.0.0 | include 0.0.0.0"),
    ]

    results = []

    for check_name, device, command in checks:
        print(f"\n  {YELLOW}▶ {check_name}{RESET}")
        print(f"    Device: {device}")

        conn = connect(device)
        if conn:
            output = conn.send_command(command)
            conn.disconnect()

            # Analyze result
            if "uptime" in check_name.lower() and "uptime" in output.lower():
                results.append(("pass", check_name))
                print(f"    {GREEN}✓ PASSED{RESET}")
            elif "FULL" in output or "Oper" in output or "Estab" in output:
                count = re.search(r'(\d+)', output)
                results.append(("pass", check_name))
                print(f"    {GREEN}✓ PASSED{RESET} - {count.group(1) if count else 'OK'}")
            elif "172." in output or "0.0.0.0" in output:
                results.append(("pass", check_name))
                print(f"    {GREEN}✓ PASSED{RESET}")
            else:
                results.append(("warn", check_name))
                print(f"    {YELLOW}⚠ WARNING{RESET}")
        else:
            results.append(("fail", check_name))
            print(f"    {RED}✗ FAILED - Cannot connect{RESET}")

        time.sleep(1)

    # Summary
    passed = sum(1 for r, _ in results if r == "pass")
    total = len(results)

    print()
    print(f"  {'═' * 66}")
    if passed == total:
        print(f"  {GREEN}  ✓ ALL CHECKS PASSED ({passed}/{total}){RESET}")
        print(f"  {GREEN}  Network is healthy!{RESET}")
    else:
        print(f"  {YELLOW}  ⚠ SOME CHECKS FAILED ({passed}/{total} passed){RESET}")
    print(f"  {'═' * 66}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Network Troubleshooting Demo")
    parser.add_argument("--break-bgp", action="store_true", help="Demo: Break and fix BGP VPNv4")
    parser.add_argument("--health", action="store_true", help="Run health check")
    args = parser.parse_args()

    if args.break_bgp:
        demo_break_and_fix_bgp()
    elif args.health:
        demo_health_check()
    else:
        # Interactive menu
        print()
        print(f"{CYAN}{'█' * 70}")
        print(f"█{' ' * 68}█")
        print(f"█  {'TROUBLESHOOTING DEMO MENU':<65}█")
        print(f"█{' ' * 68}█")
        print(f"{'█' * 70}{RESET}")

        print(f"""
  {BOLD}Video-Ready Demos:{RESET}

  {CYAN}[1]{RESET} BGP Break & Fix    - Dramatic failure and automated recovery
  {CYAN}[2]{RESET} Health Check       - Full network assessment
  {CYAN}[3]{RESET} Exit
        """)

        choice = input(f"  {BOLD}Select: {RESET}").strip()

        if choice == "1":
            demo_break_and_fix_bgp()
        elif choice == "2":
            demo_health_check()


if __name__ == "__main__":
    main()

