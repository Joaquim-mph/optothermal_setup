#!/usr/bin/env python
"""Test script to verify instrument connections."""

import sys
from pymeasure.adapters import SerialAdapter
from laser_setup.instruments.keithley import Keithley2450
from laser_setup.instruments.tenma import TENMA

def test_instrument(name, instrument_class, adapter, is_serial=False, **kwargs):
    """Test connection to a single instrument."""
    print(f"\n{'='*60}")
    print(f"Testing {name}...")
    print(f"Adapter: {adapter}")
    if kwargs:
        print(f"Kwargs: {kwargs}")
    print(f"{'='*60}")

    try:
        # For serial instruments, create SerialAdapter first
        if is_serial:
            serial_kwargs = {}
            for key in ['baudrate', 'timeout', 'write_timeout', 'parity', 'stopbits', 'bytesize']:
                if key in kwargs:
                    serial_kwargs[key] = kwargs.pop(key)
            adapter_obj = SerialAdapter(adapter, **serial_kwargs)
            instrument = instrument_class(adapter_obj, **kwargs)
        else:
            instrument = instrument_class(adapter, **kwargs)

        # Try to get identification
        try:
            idn = instrument.id
            print(f"✓ Connection successful!")
            print(f"  ID: {idn}")

            # Additional tests based on instrument type
            if isinstance(instrument, TENMA):
                try:
                    voltage = instrument.voltage
                    current = instrument.current
                    print(f"  Voltage Setting: {voltage:.3f} V")
                    print(f"  Current Setting: {current:.3f} A")
                    try:
                        output = instrument.output
                        print(f"  Output: {'ON' if output else 'OFF'}")
                    except:
                        print(f"  Output: (unable to read state)")
                except Exception as e:
                    print(f"  Note: Could not read all settings: {e}")

            # Close connection
            instrument.shutdown()
            return True

        except Exception as e:
            print(f"✗ Connected but failed to read: {e}")
            try:
                instrument.shutdown()
            except:
                pass
            return False

    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

def main():
    """Test all configured instruments."""
    print("\n" + "="*60)
    print("INSTRUMENT CONNECTION TEST")
    print("="*60)

    results = {}

    # Test Keithley 2450
    results['Keithley2450'] = test_instrument(
        "Keithley 2450 SourceMeter",
        Keithley2450,
        "USB0::0x05E6::0x2450::04448996::0::INSTR"
    )

    # Test TENMA NEG
    results['TENMANEG'] = test_instrument(
        "TENMA NEG (/dev/ttyACM0)",
        TENMA,
        "/dev/ttyACM0",
        is_serial=True,
        baudrate=9600,
        timeout=2
    )

    # Test TENMA POS
    results['TENMAPOS'] = test_instrument(
        "TENMA POS (/dev/ttyACM1)",
        TENMA,
        "/dev/ttyACM1",
        is_serial=True,
        baudrate=9600,
        timeout=2
    )

    # Summary
    print(f"\n\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    for name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{name:20s}: {status}")

    all_pass = all(results.values())
    print(f"\n{'='*60}")
    if all_pass:
        print("✓ ALL INSTRUMENTS CONNECTED SUCCESSFULLY!")
    else:
        print("✗ SOME INSTRUMENTS FAILED TO CONNECT")
    print(f"{'='*60}\n")

    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(main())
