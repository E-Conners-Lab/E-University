#!/usr/bin/env python3
"""
Device Health Validation - AEtest Script

This AEtest script validates device health metrics including:
- CPU utilization
- Memory utilization
- Interface error counters
- NTP synchronization
- Device uptime

Usage:
    # Run directly
    python device_health_aetest.py --testbed ../testbed.yaml

    # Run via jobfile
    pyats run job ../health_job.py --testbed-file ../testbed.yaml

    # With thresholds
    python device_health_aetest.py --testbed ../testbed.yaml --cpu-threshold 80 --memory-threshold 85
"""

import logging
import re
from datetime import datetime, timedelta

from pyats import aetest
from pyats.topology import Testbed
from genie.testbed import load as genie_load

logger = logging.getLogger(__name__)


# =============================================================================
# Thresholds (can be overridden via parameters)
# =============================================================================
DEFAULT_THRESHOLDS = {
    'cpu_warning': 70,       # CPU % warning threshold
    'cpu_critical': 85,      # CPU % critical threshold
    'memory_warning': 75,    # Memory % warning threshold
    'memory_critical': 90,   # Memory % critical threshold
    'crc_errors': 10,        # CRC errors threshold
    'input_errors': 100,     # Input errors threshold
    'output_errors': 100,    # Output errors threshold
    'min_uptime_hours': 1,   # Minimum uptime (detect recent reboots)
}


# =============================================================================
# Common Setup
# =============================================================================
class CommonSetup(aetest.CommonSetup):
    """Common setup tasks - connect to devices."""

    @aetest.subsection
    def check_testbed(self, testbed: Testbed):
        """Verify testbed is loaded."""
        if not testbed or not testbed.devices:
            self.failed("No testbed or devices provided")
        logger.info(f"Testbed has {len(testbed.devices)} devices")

    @aetest.subsection
    def establish_connections(self, testbed: Testbed, steps):
        """Connect to all devices."""
        connected = []
        failed = []

        for device_name, device in testbed.devices.items():
            with steps.start(f"Connect to {device_name}") as step:
                try:
                    device.connect(log_stdout=False, learn_hostname=True)
                    connected.append(device_name)
                    logger.info(f"Connected to {device_name}")
                except Exception as e:
                    step.failed(f"Connection failed: {e}")
                    failed.append(device_name)

        self.parent.parameters['connected_devices'] = connected
        self.parent.parameters['failed_devices'] = failed

        if not connected:
            self.failed("Could not connect to any devices")


# =============================================================================
# Test Case: CPU Utilization
# =============================================================================
class CPUUtilization(aetest.Testcase):
    """Monitor CPU utilization across devices."""

    @aetest.setup
    def setup(self, testbed):
        """Get list of connected devices."""
        self.devices = [
            name for name in self.parent.parameters.get('connected_devices', [])
            if name in testbed.devices
        ]
        if not self.devices:
            self.skipped("No devices to test")

        # Get thresholds
        self.cpu_warning = self.parent.parameters.get('cpu_warning', DEFAULT_THRESHOLDS['cpu_warning'])
        self.cpu_critical = self.parent.parameters.get('cpu_critical', DEFAULT_THRESHOLDS['cpu_critical'])

    @aetest.test
    def test_cpu_utilization(self, testbed, steps):
        """Check CPU utilization on all devices."""

        for device_name in self.devices:
            with steps.start(f"CPU check: {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    # Parse CPU info
                    cpu_data = device.parse("show processes cpu")

                    # Get 5-minute CPU average
                    cpu_5min = cpu_data.get('five_min_cpu', 0)
                    cpu_1min = cpu_data.get('one_min_cpu', 0)
                    cpu_5sec = cpu_data.get('five_sec_cpu', 0)

                    # Use 5-minute average for stability
                    cpu_pct = cpu_5min

                    if cpu_pct >= self.cpu_critical:
                        step.failed(f"CPU CRITICAL: {cpu_pct}% (5min avg) - threshold: {self.cpu_critical}%")
                    elif cpu_pct >= self.cpu_warning:
                        step.passed(f"CPU WARNING: {cpu_pct}% (5min avg) - approaching threshold")
                    else:
                        step.passed(f"CPU OK: {cpu_pct}% (5min: {cpu_5min}%, 1min: {cpu_1min}%, 5sec: {cpu_5sec}%)")

                except Exception as e:
                    # Try alternative command
                    try:
                        output = device.execute("show processes cpu | include CPU")
                        match = re.search(r'five minutes:\s*(\d+)%', output)
                        if match:
                            cpu_pct = int(match.group(1))
                            if cpu_pct >= self.cpu_critical:
                                step.failed(f"CPU CRITICAL: {cpu_pct}%")
                            else:
                                step.passed(f"CPU OK: {cpu_pct}%")
                        else:
                            step.failed(f"Could not parse CPU: {e}")
                    except Exception as e2:
                        step.failed(f"CPU check failed: {e2}")


# =============================================================================
# Test Case: Memory Utilization
# =============================================================================
class MemoryUtilization(aetest.Testcase):
    """Monitor memory utilization across devices."""

    @aetest.setup
    def setup(self, testbed):
        """Get list of connected devices."""
        self.devices = [
            name for name in self.parent.parameters.get('connected_devices', [])
            if name in testbed.devices
        ]
        if not self.devices:
            self.skipped("No devices to test")

        self.mem_warning = self.parent.parameters.get('memory_warning', DEFAULT_THRESHOLDS['memory_warning'])
        self.mem_critical = self.parent.parameters.get('memory_critical', DEFAULT_THRESHOLDS['memory_critical'])

    @aetest.test
    def test_memory_utilization(self, testbed, steps):
        """Check memory utilization on all devices."""

        for device_name in self.devices:
            with steps.start(f"Memory check: {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    # Parse memory info
                    mem_data = device.parse("show memory statistics")

                    # Calculate processor memory usage
                    proc_mem = mem_data.get('processor_pool', {})
                    total = proc_mem.get('total', 0)
                    used = proc_mem.get('used', 0)
                    free = proc_mem.get('free', 0)

                    if total > 0:
                        mem_pct = (used / total) * 100
                    else:
                        mem_pct = 0

                    if mem_pct >= self.mem_critical:
                        step.failed(f"MEMORY CRITICAL: {mem_pct:.1f}% used ({used:,} / {total:,} bytes)")
                    elif mem_pct >= self.mem_warning:
                        step.passed(f"MEMORY WARNING: {mem_pct:.1f}% used - approaching threshold")
                    else:
                        step.passed(f"MEMORY OK: {mem_pct:.1f}% used (Free: {free:,} bytes)")

                except Exception as e:
                    # Try alternative parsing
                    try:
                        output = device.execute("show memory summary")
                        # Look for "Processor" line with Total/Used/Free
                        match = re.search(r'Processor\s+(\d+)\s+(\d+)\s+(\d+)', output)
                        if match:
                            total = int(match.group(1))
                            used = int(match.group(2))
                            if total > 0:
                                mem_pct = (used / total) * 100
                                if mem_pct >= self.mem_critical:
                                    step.failed(f"MEMORY CRITICAL: {mem_pct:.1f}%")
                                else:
                                    step.passed(f"MEMORY OK: {mem_pct:.1f}%")
                            else:
                                step.failed("Could not calculate memory")
                        else:
                            step.failed(f"Memory check failed: {e}")
                    except Exception as e2:
                        step.failed(f"Memory check failed: {e2}")


# =============================================================================
# Test Case: Interface Errors
# =============================================================================
class InterfaceErrors(aetest.Testcase):
    """Check interface error counters."""

    @aetest.setup
    def setup(self, testbed):
        """Get list of connected devices."""
        self.devices = [
            name for name in self.parent.parameters.get('connected_devices', [])
            if name in testbed.devices
        ]
        if not self.devices:
            self.skipped("No devices to test")

        self.crc_threshold = self.parent.parameters.get('crc_errors', DEFAULT_THRESHOLDS['crc_errors'])
        self.input_threshold = self.parent.parameters.get('input_errors', DEFAULT_THRESHOLDS['input_errors'])
        self.output_threshold = self.parent.parameters.get('output_errors', DEFAULT_THRESHOLDS['output_errors'])

    @aetest.test
    def test_interface_errors(self, testbed, steps):
        """Check for interface errors on all devices."""

        for device_name in self.devices:
            with steps.start(f"Interface errors: {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    intf_data = device.parse("show interfaces")

                    interfaces_with_errors = []
                    clean_interfaces = 0

                    for intf_name, intf_info in intf_data.items():
                        # Skip non-physical interfaces
                        if any(x in intf_name.lower() for x in ['loopback', 'null', 'vlan', 'nve']):
                            continue

                        counters = intf_info.get('counters', {})

                        # Get error counters
                        in_errors = counters.get('in_errors', 0)
                        out_errors = counters.get('out_errors', 0)
                        in_crc_errors = counters.get('in_crc_errors', 0)
                        in_frame = counters.get('in_frame', 0)  # Framing errors

                        errors = []
                        if in_crc_errors > self.crc_threshold:
                            errors.append(f"CRC:{in_crc_errors}")
                        if in_errors > self.input_threshold:
                            errors.append(f"IN:{in_errors}")
                        if out_errors > self.output_threshold:
                            errors.append(f"OUT:{out_errors}")
                        if in_frame > self.crc_threshold:
                            errors.append(f"FRAME:{in_frame}")

                        if errors:
                            interfaces_with_errors.append(f"{intf_name} ({', '.join(errors)})")
                        else:
                            clean_interfaces += 1

                    if interfaces_with_errors:
                        step.failed(f"Interfaces with errors: {'; '.join(interfaces_with_errors[:5])}")
                    else:
                        step.passed(f"{clean_interfaces} interfaces checked - no significant errors")

                except Exception as e:
                    step.failed(f"Interface error check failed: {e}")


# =============================================================================
# Test Case: NTP Synchronization
# =============================================================================
class NTPSynchronization(aetest.Testcase):
    """Verify NTP synchronization status."""

    @aetest.setup
    def setup(self, testbed):
        """Get list of connected devices."""
        self.devices = [
            name for name in self.parent.parameters.get('connected_devices', [])
            if name in testbed.devices
        ]
        if not self.devices:
            self.skipped("No devices to test")

    @aetest.test
    def test_ntp_sync(self, testbed, steps):
        """Check NTP synchronization on all devices."""

        for device_name in self.devices:
            with steps.start(f"NTP check: {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show ntp status")

                    if "Clock is synchronized" in output:
                        # Extract stratum if available
                        stratum_match = re.search(r'stratum\s+(\d+)', output)
                        stratum = stratum_match.group(1) if stratum_match else "unknown"
                        step.passed(f"NTP synchronized (stratum {stratum})")

                    elif "Clock is unsynchronized" in output:
                        step.failed("NTP NOT synchronized")

                    else:
                        # Try show ntp associations
                        assoc_output = device.execute("show ntp associations")

                        # Look for * (synchronized) or + (candidate)
                        if re.search(r'^\s*\*', assoc_output, re.MULTILINE):
                            step.passed("NTP synchronized (found sync peer)")
                        elif re.search(r'^\s*\+', assoc_output, re.MULTILINE):
                            step.passed("NTP has candidate peers")
                        elif "No association" in assoc_output:
                            step.failed("No NTP associations configured")
                        else:
                            step.failed("NTP status unclear - may not be synchronized")

                except Exception as e:
                    step.failed(f"NTP check failed: {e}")


# =============================================================================
# Test Case: Device Uptime
# =============================================================================
class DeviceUptime(aetest.Testcase):
    """Monitor device uptime to detect recent reboots."""

    @aetest.setup
    def setup(self, testbed):
        """Get list of connected devices."""
        self.devices = [
            name for name in self.parent.parameters.get('connected_devices', [])
            if name in testbed.devices
        ]
        if not self.devices:
            self.skipped("No devices to test")

        self.min_uptime_hours = self.parent.parameters.get('min_uptime_hours', DEFAULT_THRESHOLDS['min_uptime_hours'])

    @aetest.test
    def test_uptime(self, testbed, steps):
        """Check device uptime on all devices."""

        for device_name in self.devices:
            with steps.start(f"Uptime check: {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show version | include uptime")

                    # Parse uptime string: "router uptime is X weeks, Y days, Z hours, W minutes"
                    uptime_match = re.search(
                        r'uptime is\s*(?:(\d+)\s*years?)?,?\s*'
                        r'(?:(\d+)\s*weeks?)?,?\s*'
                        r'(?:(\d+)\s*days?)?,?\s*'
                        r'(?:(\d+)\s*hours?)?,?\s*'
                        r'(?:(\d+)\s*minutes?)?',
                        output
                    )

                    if uptime_match:
                        years = int(uptime_match.group(1) or 0)
                        weeks = int(uptime_match.group(2) or 0)
                        days = int(uptime_match.group(3) or 0)
                        hours = int(uptime_match.group(4) or 0)
                        minutes = int(uptime_match.group(5) or 0)

                        total_hours = (years * 365 * 24) + (weeks * 7 * 24) + (days * 24) + hours

                        # Build readable string
                        uptime_str = ""
                        if years > 0:
                            uptime_str += f"{years}y "
                        if weeks > 0:
                            uptime_str += f"{weeks}w "
                        if days > 0:
                            uptime_str += f"{days}d "
                        if hours > 0:
                            uptime_str += f"{hours}h "
                        if minutes > 0:
                            uptime_str += f"{minutes}m"
                        uptime_str = uptime_str.strip() or "< 1 minute"

                        if total_hours < self.min_uptime_hours:
                            step.failed(f"RECENT REBOOT detected! Uptime: {uptime_str}")
                        else:
                            step.passed(f"Uptime: {uptime_str}")
                    else:
                        step.failed(f"Could not parse uptime from: {output[:100]}")

                except Exception as e:
                    step.failed(f"Uptime check failed: {e}")


# =============================================================================
# Test Case: Hardware Status (Environment)
# =============================================================================
class HardwareStatus(aetest.Testcase):
    """Check hardware environment (fans, power, temperature)."""

    @aetest.setup
    def setup(self, testbed):
        """Get list of connected devices."""
        self.devices = [
            name for name in self.parent.parameters.get('connected_devices', [])
            if name in testbed.devices
        ]
        if not self.devices:
            self.skipped("No devices to test")

    @aetest.test
    def test_environment(self, testbed, steps):
        """Check environmental status on all devices."""

        for device_name in self.devices:
            with steps.start(f"Hardware status: {device_name}") as step:
                device = testbed.devices[device_name]

                try:
                    output = device.execute("show environment all")

                    issues = []

                    # Check for common failure keywords
                    if re.search(r'\b(FAIL|CRITICAL|FAULT|NOT OK|NOT PRESENT)\b', output, re.IGNORECASE):
                        # Find the problematic lines
                        for line in output.splitlines():
                            if re.search(r'\b(FAIL|CRITICAL|FAULT|NOT OK)\b', line, re.IGNORECASE):
                                issues.append(line.strip()[:60])

                    # Check temperature warnings
                    temp_matches = re.findall(r'(\d+)\s*[Cc].*(?:Yellow|Critical|Warning)', output)
                    if temp_matches:
                        issues.append(f"Temperature warnings detected")

                    if issues:
                        step.failed(f"Hardware issues: {'; '.join(issues[:3])}")
                    else:
                        step.passed("Hardware environment OK")

                except Exception as e:
                    # Environment command may not be supported on all platforms
                    step.skipped(f"Environment check not available: {e}")


# =============================================================================
# Common Cleanup
# =============================================================================
class CommonCleanup(aetest.CommonCleanup):
    """Disconnect from all devices."""

    @aetest.subsection
    def disconnect_devices(self, testbed):
        """Disconnect from all devices."""
        for device_name, device in testbed.devices.items():
            try:
                if device.is_connected():
                    device.disconnect()
            except Exception:
                pass


# =============================================================================
# Main - Standalone execution
# =============================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Device Health AEtest")
    parser.add_argument("--testbed", required=True, help="Testbed YAML file")
    parser.add_argument("--cpu-threshold", type=int, default=85, help="CPU critical threshold %%")
    parser.add_argument("--memory-threshold", type=int, default=90, help="Memory critical threshold %%")
    args = parser.parse_args()

    # Load testbed
    testbed = genie_load(args.testbed)

    # Run tests with custom thresholds
    aetest.main(
        testbed=testbed,
        cpu_critical=args.cpu_threshold,
        memory_critical=args.memory_threshold
    )
