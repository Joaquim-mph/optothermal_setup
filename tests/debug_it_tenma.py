#!/usr/bin/env python
"""Debug script to test It procedure with TENMA."""

import logging
import sys

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(levelname)s - %(message)s'
)

print("Testing It procedure instrument initialization...\n")

try:
    from laser_setup.procedures.It import It
    from laser_setup.instruments import InstrumentManager

    print("✓ Imported It procedure")

    # Create a minimal It procedure instance
    print("\nCreating It procedure instance...")
    params = {
        'chip_group': 'TEST',
        'chip_number': 1,
        'sample': 'A',
        'vds': 0.1,
        'vg': 0.0,
        'laser_toggle': True,  # This will try to use TENMALASER
        'laser_v': 0.5,
        'laser_T': 60,
        'target_T': 0,
        'sense_T': False,  # Disable temperature sensor
        'vg_toggle': False,  # Disable gate voltage TENMAs
    }

    procedure = It(**params)
    print("✓ It procedure created")

    # Try to connect instruments
    print("\nConnecting instruments...")
    print(f"Laser toggle: {procedure.laser_toggle}")
    print(f"Vg toggle: {procedure.vg_toggle}")
    print(f"Sense T: {procedure.sense_T}")

    procedure.connect_instruments()
    print("✓ Instruments connected")

    # Check TENMA laser
    print(f"\nTENMA Laser type: {type(procedure.tenma_laser)}")
    print(f"TENMA Laser: {procedure.tenma_laser}")

    # Try to read voltage
    print("\nTrying to read TENMA voltage...")
    voltage = procedure.tenma_laser.voltage
    print(f"✓ TENMA voltage: {voltage} V")

    # Shutdown
    print("\nShutting down...")
    procedure.shutdown()
    print("✓ Shutdown complete")

    print("\n✓✓✓ It procedure with TENMA works! ✓✓✓")

except Exception as e:
    print(f"\n✗✗✗ ERROR ✗✗✗")
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
