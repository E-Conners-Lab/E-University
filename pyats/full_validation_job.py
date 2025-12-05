#!/usr/bin/env python3
"""
E-University Full Network Validation Job

Comprehensive validation of all network features:
- Network Protocols: OSPF, BGP, MPLS/LDP, VRF, BFD
- High Availability: HSRP gateway redundancy
- Device Health: CPU, memory, reachability

Usage:
    # Full validation (all tests)
    ./run.sh full_validation_job.py --testbed-file testbed.yaml

    # Generate HTML report
    ./run.sh full_validation_job.py --testbed-file testbed.yaml --html-logs ./reports

    # Archive results for comparison
    ./run.sh full_validation_job.py --testbed-file testbed.yaml --archive ./archives
"""

import logging
import os

from pyats.easypy import run
from dotenv import load_dotenv

log = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Test script locations
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TESTS_DIR = os.path.join(SCRIPT_DIR, 'tests')

# Test scripts to run (in order)
TEST_SCRIPTS = [
    {
        'script': os.path.join(TESTS_DIR, 'euniv_aetest.py'),
        'taskid': 'Network Protocols',
        'description': 'OSPF, BGP, MPLS/LDP, VRF, BFD, Interfaces, Connectivity'
    },
    {
        'script': os.path.join(TESTS_DIR, 'hsrp_aetest.py'),
        'taskid': 'HSRP Validation',
        'description': 'HSRP configuration, state, redundancy, load balancing'
    },
    {
        'script': os.path.join(TESTS_DIR, 'device_health_aetest.py'),
        'taskid': 'Device Health',
        'description': 'CPU utilization, memory usage, device reachability'
    },
]


def main(runtime):
    """
    Main job execution - runs all validation test scripts.
    """
    runtime.job.name = "E-University Full Network Validation"

    log.info("=" * 70)
    log.info("E-UNIVERSITY FULL NETWORK VALIDATION")
    log.info("=" * 70)
    log.info("")
    log.info("This job runs comprehensive validation across all network features:")
    for test in TEST_SCRIPTS:
        log.info(f"  - {test['taskid']}: {test['description']}")
    log.info("")
    log.info("=" * 70)

    # Run each test script
    for test in TEST_SCRIPTS:
        script_path = test['script']

        if not os.path.exists(script_path):
            log.warning(f"Test script not found, skipping: {script_path}")
            continue

        log.info("")
        log.info("-" * 70)
        log.info(f"RUNNING: {test['taskid']}")
        log.info(f"Script: {os.path.basename(script_path)}")
        log.info(f"Description: {test['description']}")
        log.info("-" * 70)

        run(
            testscript=script_path,
            runtime=runtime,
            taskid=test['taskid']
        )

    log.info("")
    log.info("=" * 70)
    log.info("FULL VALIDATION COMPLETE")
    log.info("=" * 70)
    log.info("")
    log.info("View results with: pyats logs view")
    log.info("Generate report:   pyats logs view --html")
