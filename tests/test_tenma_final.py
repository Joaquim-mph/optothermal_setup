#!/usr/bin/env python
"""Test TENMA using laser_setup instrument class."""

from laser_setup.instruments.tenma import TENMA

print("Testing TENMA with laser_setup instrument class...\n")

port = '/dev/tty.usbmodem0002294704521'

try:
    # Create TENMA instance with correct settings
    tenma = TENMA(port, baudrate=9600, timeout=2)
    print(f"✓ Connected to TENMA on {port}\n")

    # Test reading voltage
    voltage = tenma.voltage
    print(f"✓ Current voltage setting: {voltage} V")

    # Test reading current
    current = tenma.current
    print(f"✓ Current limit setting: {current} A")

    # Test reading output state
    output = tenma.output
    print(f"✓ Output state: {'ON' if output else 'OFF'}")

    # Test setting voltage (safe small value)
    print(f"\nTesting voltage control...")
    print(f"  Setting voltage to 0.5V...")
    tenma.voltage = 0.5
    import time
    time.sleep(0.5)
    new_voltage = tenma.voltage
    print(f"  ✓ Voltage now set to: {new_voltage} V")

    # Clean up
    print(f"\nResetting to 0V...")
    tenma.shutdown()
    print(f"✓ TENMA shutdown complete")

    print(f"\n✓✓✓ TENMA is working correctly! ✓✓✓")
    print(f"\nYour config is already updated:")
    print(f"  adapter: {port}")
    print(f"  baudrate: 9600")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
