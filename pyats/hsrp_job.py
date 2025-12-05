#!/usr/bin/env python3
"""
E-University HSRP Validation Job File

This jobfile orchestrates HSRP validation tests for edge/PE routers.
Run this BEFORE and AFTER implementing HSRP to verify configuration.

Usage:
    # Pre-deployment check (verify interfaces ready)
    pyats run job hsrp_job.py --testbed-file testbed.yaml

    # Full validation after HSRP deployment
    pyats run job hsrp_job.py --testbed-file testbed.yaml --html-logs ./reports

    # Dry-run (validate job structure)
    pyats run job hsrp_job.py --dry-run

Example:
    cd pyats
    source ../.env  # Load credentials
    pyats run job hsrp_job.py --testbed-file testbed.yaml --html-logs ./reports/hsrp
"""

import logging
import os

from pyats.easypy import run
from dotenv import load_dotenv

# Get logger
log = logging.getLogger(__name__)

# Define the test script location (relative to this jobfile)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AETEST_SCRIPT = os.path.join(SCRIPT_DIR, 'tests', 'hsrp_aetest.py')
load_dotenv()


def main(runtime):
    """
    Main job execution entry point.

    This function is called by pyats easypy when running:
        pyats run job hsrp_job.py

    Args:
        runtime: pyATS runtime object containing job configuration
    """

    # Job information
    runtime.job.name = "E-University HSRP Validation"

    # Log job start
    log.info("=" * 70)
    log.info("E-UNIVERSITY HSRP VALIDATION JOB")
    log.info("=" * 70)
    log.info("")
    log.info("HSRP Design:")
    log.info("  - Interface: GigabitEthernet3 subinterfaces")
    log.info("  - Load Balancing:")
    log.info("    - PE1/EDGE1 Active: VLAN 100 (STUDENT), 300 (RESEARCH)")
    log.info("    - PE2/EDGE2 Active: VLAN 200 (STAFF), 400 (MEDICAL), 500 (GUEST)")
    log.info("  - Virtual IPs: 10.{VLAN}.{Campus}.254")
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
        taskid="HSRP Validation"
    )

    log.info("=" * 70)
    log.info("JOB COMPLETE")
    log.info("=" * 70)
