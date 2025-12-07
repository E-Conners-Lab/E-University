"""
Pytest configuration for E-University network tests.
"""

import pytest


def pytest_addoption(parser):
    """Add command-line options for test selection."""
    parser.addoption(
        "--switch",
        action="store",
        default=None,
        help="Specific switch to test (e.g., EUNIV-MED-ASW1). If not specified, uses default.",
    )
    parser.addoption(
        "--campus",
        action="store",
        default="main",
        help="Campus to test: main, medical, research, or all (default: main)",
    )
