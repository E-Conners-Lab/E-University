#!/usr/bin/env python3
"""
E-University Network Validation Job File

This jobfile orchestrates the E-University network validation tests.
It runs the AEtest script with proper configuration and generates reports.

Usage:
    # Full validation (connects to all devices)
    pyats run job euniv_job.py --testbed-file testbed.yaml

    # Dry-run (validate job structure without connecting)
    pyats run job euniv_job.py --dry-run

    # Generate HTML report
    pyats run job euniv_job.py --testbed-file testbed.yaml --html-logs ./reports

    # Run with specific log level
    pyats run job euniv_job.py --testbed-file testbed.yaml --loglevel DEBUG

    # Archive results
    pyats run job euniv_job.py --testbed-file testbed.yaml --archive ./archives

Example with all options:
    pyats run job euniv_job.py \\
        --testbed-file testbed.yaml \\
        --html-logs ./reports \\
        --archive ./archives \\
        --job-uid euniv-$(date +%Y%m%d-%H%M%S)
"""

import logging
import os

from pyats.easypy import run
from dotenv import load_dotenv
# Get logger
log = logging.getLogger(__name__)

# Define the test script location (relative to this jobfile)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AETEST_SCRIPT = os.path.join(SCRIPT_DIR, 'tests', 'euniv_aetest.py')
load_dotenv()

def main(runtime):
    """
    Main job execution entry point.

    This function is called by pyats easypy when running:
        pyats run job euniv_job.py

    Args:
        runtime: pyATS runtime object containing job configuration
    """

    # Job information
    runtime.job.name = "E-University Network Validation"

    # Log job start
    log.info("=" * 70)
    log.info("E-UNIVERSITY NETWORK VALIDATION JOB")
    log.info("=" * 70)

    # Verify AEtest script exists
    if not os.path.exists(AETEST_SCRIPT):
        log.error(f"AEtest script not found: {AETEST_SCRIPT}")
        return

    log.info(f"Running test script: {AETEST_SCRIPT}")

    # Run the AEtest script
    # The testbed is automatically passed from --testbed-file argument
    run(
        testscript=AETEST_SCRIPT,
        runtime=runtime,
        taskid="E-University Validation"
    )

    log.info("=" * 70)
    log.info("JOB COMPLETE")
    log.info("=" * 70)
