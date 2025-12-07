#!/usr/bin/env python3
"""
E-University INET-GW and VRF Internet Connectivity Validation Job

This jobfile orchestrates INET-GW NAT and VRF internet connectivity tests.
Validates that VRFs can reach the internet via the INET-GW routers.

Usage:
    pyats run job inet_gw_job.py --testbed-file testbed.yaml

    # With HTML reports
    pyats run job inet_gw_job.py --testbed-file testbed.yaml --html-logs ./reports/inet_gw

    # Dry-run (validate job structure)
    pyats run job inet_gw_job.py --dry-run

Example:
    cd pyats
    source ../.env  # Load credentials
    pyats run job inet_gw_job.py --testbed-file testbed.yaml --html-logs ./reports/inet_gw
"""

import logging
import os

from pyats.easypy import run
from dotenv import load_dotenv

# Get logger
log = logging.getLogger(__name__)

# Define the test script location (relative to this jobfile)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AETEST_SCRIPT = os.path.join(SCRIPT_DIR, 'tests', 'inet_gw_aetest.py')
load_dotenv()


def main(runtime):
    """
    Main job execution entry point.

    This function is called by pyats easypy when running:
        pyats run job inet_gw_job.py

    Args:
        runtime: pyATS runtime object containing job configuration
    """

    # Job information
    runtime.job.name = "E-University INET-GW and VRF Internet Connectivity"

    # Log job start
    log.info("=" * 70)
    log.info("E-UNIVERSITY INET-GW VALIDATION JOB")
    log.info("=" * 70)
    log.info("")
    log.info("INET-GW Design:")
    log.info("  - Internet Gateway Routers: INET-GW1 (10.255.0.101), INET-GW2 (10.255.0.102)")
    log.info("  - VRFs with Internet Access:")
    log.info("    - STAFF-NET: Staff network")
    log.info("    - RESEARCH-NET: Research network")
    log.info("    - MEDICAL-NET: Medical network")
    log.info("    - GUEST-NET: Guest network")
    log.info("  - NAT: VRF-aware PAT on Gi1 (outside interface)")
    log.info("  - Default Route: BGP VPNv4 with default-information originate")
    log.info("")

    # Verify AEtest script exists
    if not os.path.exists(AETEST_SCRIPT):
        log.error(f"AEtest script not found: {AETEST_SCRIPT}")
        return

    log.info(f"Running test script: {AETEST_SCRIPT}")

    # Run the AEtest script
    run(
        testscript=AETEST_SCRIPT,
        runtime=runtime,
        taskid="INET-GW Validation"
    )

    log.info("=" * 70)
    log.info("JOB COMPLETE")
    log.info("=" * 70)
