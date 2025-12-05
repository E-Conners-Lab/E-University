#!/usr/bin/env python3
"""Quick Unicon connection test."""
from genie.testbed import load
from dotenv import load_dotenv

load_dotenv()

tb = load('testbed.yaml')
dev = tb.devices['EUNIV-CORE1']
print(f"Connecting to {dev.name} at {dev.connections.cli.ip}...")
dev.connect(log_stdout=True)
print("Connected!")
dev.disconnect()
