#!/usr/bin/env python3
"""
E-University Network Chaos Validation Job File

This job validates network state before and after chaos tests.
Use this to establish a baseline and verify recovery.

Usage:
    # Baseline check before chaos
    pyats run job chaos_job.py --testbed-file testbed.yaml --html-logs ./reports

    # After chaos test to verify recovery
    pyats run job chaos_job.py --testbed-file testbed.yaml
"""

import os
from pathlib import Path

from pyats.easypy import run


def main(runtime):
    """Main job function - runs comprehensive network validation."""

    job_dir = Path(__file__).parent
    reports_dir = job_dir / "reports"
    reports_dir.mkdir(exist_ok=True)

    # Run the main network validation suite
    # This provides baseline for chaos testing
    run(
        testscript=str(job_dir / "tests" / "euniv_aetest.py"),
        runtime=runtime,
        taskid="Pre_Chaos_Validation",
    )


__title__ = "E-University Chaos Test Validation"
__description__ = """
Validates network state for chaos testing:
- OSPF neighbor states
- BGP sessions
- MPLS LDP neighbors
- VRF configuration
- Interface status
- End-to-end connectivity
- BFD neighbors

Run this BEFORE and AFTER chaos tests to verify:
1. Pre-chaos baseline is healthy
2. Post-chaos recovery is complete
"""
