#!/usr/bin/env python
"""Simple script to test TENMA voltage ramping."""

import time
from pymeasure.adapters import SerialAdapter
from laser_setup.instruments.tenma import TENMA

def main():
    print("\n" + "="*60)
    print("TENMA VOLTAGE RAMP TEST")
    print("="*60)

    # Connect to TENMA
    print("\nConnecting to TENMA at /dev/ttyACM0...")
    adapter = SerialAdapter("/dev/ttyACM0", baudrate=9600, timeout=2)
    tenma = TENMA(adapter)

    print(f"Connected! ID: {tenma.id}")

    # Turn on output
    print("\nTurning on output...")
    tenma.output = True
    time.sleep(0.5)

    # Ramp up from 0V to 5V
    print("\nRamping UP from 0V to 5V...")
    for voltage in [0, 1, 2, 3, 4, 5]:
        print(f"Setting voltage to {voltage}V...")
        tenma.voltage = voltage
        time.sleep(1)

        # Read back the voltage
        actual_voltage = tenma.voltage
        actual_current = tenma.current
        print(f"  Measured: {actual_voltage:.3f}V, {actual_current:.3f}A")

    print("\nHolding at 5V for 2 seconds...")
    time.sleep(2)

    # Ramp down from 5V to 0V
    print("\nRamping DOWN from 5V to 0V...")
    for voltage in [4, 3, 2, 1, 0]:
        print(f"Setting voltage to {voltage}V...")
        tenma.voltage = voltage
        time.sleep(1)

        # Read back the voltage
        actual_voltage = tenma.voltage
        actual_current = tenma.current
        print(f"  Measured: {actual_voltage:.3f}V, {actual_current:.3f}A")

    # Turn off output
    print("\nTurning off output...")
    tenma.output = False
    time.sleep(0.5)

    # Close connection
    print("Closing connection...")
    tenma.shutdown()

    print("\n" + "="*60)
    print("✓ RAMP TEST COMPLETE!")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
