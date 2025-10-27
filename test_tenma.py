#!/usr/bin/env python
"""Test script to identify and test TENMA power supply connection."""

import sys
from laser_setup.instruments.tenma import TENMA

# List of potential serial ports on macOS
ports = [
    '/dev/tty.usbmodem0002294704521',
    '/dev/tty.usbmodemSN234567892',
]

# Common baudrates for TENMA power supplies
baudrates = [9600, 115200, 19200, 57600]

print("Testing TENMA connection on available serial ports...\n")

for port in ports:
    print(f"Trying port: {port}")

    for baudrate in baudrates:
        print(f"  Baudrate: {baudrate}")
        try:
            # Try to connect with specific serial settings
            tenma = TENMA(
                port,
                baudrate=baudrate,
                timeout=2,
                write_timeout=2
            )

            # Try to query the device
            print(f"    ✓ Connected successfully!")

            # Try to read voltage
            try:
                voltage = tenma.voltage
                print(f"    ✓ Current voltage: {voltage} V")
            except Exception as e:
                print(f"    ⚠ Could not read voltage: {e}")
                raise

            # Try to read current
            try:
                current = tenma.current
                print(f"    ✓ Current setting: {current} A")
            except Exception as e:
                print(f"    ⚠ Could not read current: {e}")
                raise

            # Try to read output state
            try:
                output = tenma.output
                print(f"    ✓ Output state: {'ON' if output else 'OFF'}")
            except Exception as e:
                print(f"    ⚠ Could not read output state: {e}")
                raise

            print(f"\n✓✓✓ TENMA found on {port} with baudrate {baudrate} ✓✓✓")
            print(f"\nUpdate your config/instruments.yaml:")
            print(f"  adapter: {port}")
            print(f"  kwargs:")
            print(f"    baudrate: {baudrate}")

            tenma.shutdown()
            sys.exit(0)

        except Exception as e:
            print(f"    ✗ Failed: {e}")
            continue

print("No TENMA found on any of the tested ports.")
print("\nTroubleshooting:")
print("1. Check the TENMA is powered on")
print("2. Check the USB cable is connected")
print("3. List all serial ports with: ls /dev/tty.*")
print("4. The TENMA might need specific serial settings (baudrate, etc.)")
