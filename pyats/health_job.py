#!/usr/bin/env python3
"""
Device Health Validation Job File

Runs device health checks including CPU, memory, interface errors,
NTP synchronization, and uptime monitoring.

Usage:
    # Basic run
    pyats run job health_job.py --testbed-file testbed.yaml

    # With HTML report
    pyats run job health_job.py --testbed-file testbed.yaml --html-logs ./reports

    # With custom thresholds (via environment variables)
    CPU_THRESHOLD=80 MEMORY_THRESHOLD=85 pyats run job health_job.py --testbed-file testbed.yaml
"""

import logging
import os

from pyats.easypy import run

log = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HEALTH_SCRIPT = os.path.join(SCRIPT_DIR, 'tests', 'device_health_aetest.py')


def main(runtime):
    """Main job entry point."""

    runtime.job.name = "Device Health Validation"

    log.info("=" * 70)
    log.info("DEVICE HEALTH VALIDATION JOB")
    log.info("=" * 70)

    if not os.path.exists(HEALTH_SCRIPT):
        log.error(f"Health script not found: {HEALTH_SCRIPT}")
        return

    # Get thresholds from environment or use defaults
    cpu_threshold = int(os.environ.get('CPU_THRESHOLD', 85))
    memory_threshold = int(os.environ.get('MEMORY_THRESHOLD', 90))

    log.info(f"CPU threshold: {cpu_threshold}%")
    log.info(f"Memory threshold: {memory_threshold}%")

    # Run health tests
    run(
        testscript=HEALTH_SCRIPT,
        runtime=runtime,
        taskid="Device Health Check",
        cpu_critical=cpu_threshold,
        memory_critical=memory_threshold,
    )

    log.info("=" * 70)
    log.info("HEALTH CHECK COMPLETE")
    log.info("=" * 70)
