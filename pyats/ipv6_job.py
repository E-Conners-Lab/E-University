#!/usr/bin/env python3
"""
E-University IPv6 Network Validation Job File

This job file runs the IPv6 validation tests to verify:
- IPv6 interface addressing (Loopback and P2P)
- OSPFv3 neighbor states
- BGP IPv6 unicast sessions
- VPNv6 sessions
- IPv6 end-to-end connectivity
- VRF IPv6 address family configuration

Usage:
    # Run with HTML report
    pyats run job ipv6_job.py --testbed-file testbed.yaml --html-logs ./reports

    # Quick run
    pyats run job ipv6_job.py --testbed-file testbed.yaml

    # Dry run (validate structure)
    pyats run job ipv6_job.py --dry-run
"""

import os
from pathlib import Path

from pyats.easypy import run


def main(runtime):
    """Main job function."""

    # Get the directory containing this job file
    job_dir = Path(__file__).parent

    # Path to the test script
    test_script = job_dir / "tests" / "ipv6_aetest.py"

    # Create reports directory if it doesn't exist
    reports_dir = job_dir / "reports"
    reports_dir.mkdir(exist_ok=True)

    # Run the test script
    run(
        testscript=str(test_script),
        runtime=runtime,
        taskid="IPv6_Validation",
    )


# Metadata for the job
__title__ = "E-University IPv6 Network Validation"
__description__ = """
Validates IPv6 dual-stack deployment across the E-University network:

1. IPv6 Interface Validation
   - Loopback0 IPv6 addresses (/128)
   - Point-to-point link IPv6 addresses (/126)

2. OSPFv3 Validation
   - Neighbor state verification (FULL)
   - Route table verification

3. BGP IPv6 Validation
   - BGP IPv6 unicast session states
   - VPNv6 address family (for L3VPN)

4. Connectivity Validation
   - IPv6 loopback reachability (ping tests)

5. VRF IPv6 Validation
   - IPv6 address family enabled in VRFs

Test Philosophy:
This test suite defines "success criteria" for IPv6 deployment.
Run this BEFORE deployment to see what's missing, then AFTER
deployment to verify success.
"""
__author__ = "Network Automation Team"
__version__ = "1.0.0"
