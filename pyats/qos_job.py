#!/usr/bin/env python3
"""
E-University QoS Validation Job File

This jobfile orchestrates QoS validation tests for PE routers.
Run this AFTER implementing QoS configuration to verify policies are working.

QoS Design (VRF-Based Marking at PE Routers):
  - MEDICAL-NET: DSCP EF (46) - Priority queue, 20% bandwidth
  - STAFF-NET: DSCP AF31 (26) - 25% bandwidth
  - RESEARCH-NET: DSCP AF21 (18) - 30% bandwidth
  - STUDENT-NET: DSCP 0 (Best Effort) - 20% bandwidth
  - GUEST-NET: DSCP CS1 (8) - Scavenger, 5% bandwidth + rate limiting

Usage:
    # Standard validation
    pyats run job qos_job.py --testbed-file testbed.yaml

    # With HTML reports
    pyats run job qos_job.py --testbed-file testbed.yaml --html-logs ./reports/qos

    # Dry-run (validate job structure)
    pyats run job qos_job.py --dry-run

Example:
    cd pyats
    source ../.env  # Load credentials
    pyats run job qos_job.py --testbed-file testbed.yaml --html-logs ./reports/qos
"""

import logging
import os

from pyats.easypy import run
from dotenv import load_dotenv

# Get logger
log = logging.getLogger(__name__)

# Define the test script location (relative to this jobfile)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AETEST_SCRIPT = os.path.join(SCRIPT_DIR, 'tests', 'qos_aetest.py')
load_dotenv()


def main(runtime):
    """
    Main job execution entry point.

    This function is called by pyats easypy when running:
        pyats run job qos_job.py

    Args:
        runtime: pyATS runtime object containing job configuration
    """

    # Job information
    runtime.job.name = "E-University QoS Validation"

    # Log job start
    log.info("=" * 70)
    log.info("E-UNIVERSITY QoS VALIDATION JOB")
    log.info("=" * 70)
    log.info("")
    log.info("QoS Design (VRF-Based Marking):")
    log.info("  Target Devices: Edge routers (MAIN-EDGE1/2, MED-EDGE1/2, RES-EDGE1/2)")
    log.info("")
    log.info("  DSCP Markings by VRF:")
    log.info("    - MEDICAL-NET: DSCP EF (46)   - Priority queue, 20% BW")
    log.info("    - STAFF-NET:   DSCP AF31 (26) - Assured FWD, 25% BW")
    log.info("    - RESEARCH-NET: DSCP AF21 (18) - Assured FWD, 30% BW")
    log.info("    - STUDENT-NET: DSCP 0 (BE)    - Best Effort, 20% BW")
    log.info("    - GUEST-NET:   DSCP CS1 (8)   - Scavenger, 5% BW + police")
    log.info("")
    log.info("  Policies:")
    log.info("    - EUNIV-VRF-MARKING: Input marking on VRF interfaces")
    log.info("    - EUNIV-QOS-QUEUING: Output queuing on uplinks")
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
        taskid="QoS Validation"
    )

    log.info("=" * 70)
    log.info("JOB COMPLETE")
    log.info("=" * 70)
