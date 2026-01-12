"""
Test script for Tektronix AFG31000 Arbitrary Function Generator

This script will:
1. List all available VISA instruments
2. Attempt to connect to the AFG31000
3. Test basic functionality
4. Configure and test a simple sine wave output

Usage:
    python tests/test_afg31000_connection.py
"""

import pyvisa
import sys
import time
from pathlib import Path

# Add laser_setup to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from laser_setup.instruments.afg31000 import AFG31000


def list_visa_resources():
    """List all available VISA resources."""
    print("\n" + "="*70)
    print("STEP 1: Listing all VISA instruments")
    print("="*70)

    try:
        rm = pyvisa.ResourceManager()
        resources = rm.list_resources()

        if not resources:
            print("❌ No VISA instruments found!")
            print("\nTroubleshooting:")
            print("  - Is the AFG31000 powered on?")
            print("  - Is it connected via USB/Ethernet/GPIB?")
            print("  - For USB: Try different USB ports")
            print("  - For Ethernet: Check IP address and network connection")
            return None

        print(f"\n✓ Found {len(resources)} VISA resource(s):")
        for i, resource in enumerate(resources, 1):
            print(f"  {i}. {resource}")

            # Try to get IDN for each resource
            try:
                inst = rm.open_resource(resource, timeout=2000)
                idn = inst.query("*IDN?").strip()
                print(f"     IDN: {idn}")
                inst.close()
            except Exception as e:
                print(f"     (Could not query IDN: {e})")

        return resources

    except Exception as e:
        print(f"❌ Error accessing VISA: {e}")
        print("\nMake sure PyVISA and VISA backend are installed:")
        print("  pip install pyvisa pyvisa-py")
        return None


def find_afg31000(resources):
    """Find AFG31000 in the list of resources."""
    print("\n" + "="*70)
    print("STEP 2: Identifying AFG31000")
    print("="*70)

    if not resources:
        return None

    rm = pyvisa.ResourceManager()

    for resource in resources:
        try:
            inst = rm.open_resource(resource, timeout=2000)
            idn = inst.query("*IDN?").strip()
            inst.close()

            # Check if this is a Tektronix AFG
            if "TEKTRONIX" in idn.upper() and "AFG" in idn.upper():
                print(f"✓ Found AFG31000: {resource}")
                print(f"  IDN: {idn}")
                return resource

        except Exception:
            continue

    print("❌ AFG31000 not found in the list")
    print("\nIf you know the correct address, you can enter it manually.")
    return None


def test_connection(visa_address):
    """Test connection and basic functionality."""
    print("\n" + "="*70)
    print("STEP 3: Testing Connection")
    print("="*70)

    try:
        print(f"\nConnecting to: {visa_address}")
        afg = AFG31000(visa_address, timeout=10000)

        # Query identification
        idn = afg.ask("*IDN?")
        print(f"✓ Connected successfully!")
        print(f"  Device: {idn}")

        # Check for errors (ignore "Power on" message which is informational)
        errors = afg.check_errors()
        real_errors = [e for e in errors if "Power on" not in e]
        if real_errors:
            print(f"⚠️  Errors detected: {real_errors}")
        else:
            print("✓ No errors in queue")

        return afg

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None


def test_basic_functionality(afg):
    """Test basic channel configuration."""
    print("\n" + "="*70)
    print("STEP 4: Testing Basic Functionality")
    print("="*70)

    try:
        # Make sure outputs are off
        print("\n1. Turning off all outputs...")
        afg.all_outputs_off()
        print("   ✓ Outputs disabled")

        # Get current configuration for channel 1
        print("\n2. Reading Channel 1 configuration...")
        config = afg.get_channel_config(1)
        print("   Current Channel 1 settings:")
        for key, value in config.items():
            print(f"     {key}: {value}")

        # Configure channel 1 with a simple sine wave
        print("\n3. Configuring Channel 1 (1 kHz sine, 1 Vpp)...")
        afg.configure_channel(
            channel=1,
            function='SINusoid',
            frequency=1000,  # 1 kHz
            amplitude=1.0,   # 1 Vpp
            offset=0.0,
            impedance=50     # 50 ohm impedance
        )
        print("   ✓ Channel 1 configured")

        # Verify configuration
        print("\n4. Verifying configuration...")
        config_after = afg.get_channel_config(1)
        print("   New Channel 1 settings:")
        for key, value in config_after.items():
            print(f"     {key}: {value}")

        # Check for errors
        errors = afg.check_errors()
        if errors:
            print(f"   ⚠️  Errors: {errors}")
            return False

        print("\n" + "="*70)
        print("✓ All tests passed!")
        print("="*70)

        # Ask user if they want to enable output
        print("\n⚠️  Channel 1 is configured but output is OFF")
        print("   Settings: 1 kHz sine wave, 1 Vpp, 50Ω impedance")
        response = input("\nDo you want to enable Channel 1 output? (yes/no): ").strip().lower()

        if response in ['yes', 'y']:
            afg.enable_channel(1)
            print("✓ Channel 1 output ENABLED")
            print("  You should now see a 1 kHz sine wave on an oscilloscope")

            input("\nPress Enter to disable output and exit...")
            afg.disable_channel(1)
            print("✓ Channel 1 output DISABLED")
        else:
            print("Output remained disabled")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_config_entry(visa_address, idn):
    """Generate configuration entry for instruments.yaml"""
    print("\n" + "="*70)
    print("Configuration Entry for instruments.yaml")
    print("="*70)

    config = f"""
# Tektronix AFG31000 Arbitrary Function Generator
AFG31000:
  adapter: {visa_address}
  name: Tektronix AFG31000
  IDN: {idn.strip()}
  target: ${{class:laser_setup.instruments.afg31000.AFG31000}}
  kwargs:
    timeout: 10000
"""
    print(config)
    print("\nCopy the above configuration to config/instruments.yaml")


def main():
    print("="*70)
    print("AFG31000 Connection Test Script")
    print("="*70)

    # Step 1: List resources
    resources = list_visa_resources()

    if not resources:
        print("\n❌ Cannot proceed without VISA resources")
        return

    # Step 2: Find AFG31000
    visa_address = find_afg31000(resources)

    # Allow manual entry if not found
    if not visa_address:
        print("\nAvailable resources:")
        for i, resource in enumerate(resources, 1):
            print(f"  {i}. {resource}")

        choice = input("\nEnter resource number or full VISA address (or 'q' to quit): ").strip()

        if choice.lower() == 'q':
            return

        if choice.isdigit() and 1 <= int(choice) <= len(resources):
            visa_address = resources[int(choice) - 1]
        else:
            visa_address = choice

    # Step 3: Test connection
    afg = test_connection(visa_address)

    if not afg:
        print("\n❌ Connection test failed")
        return

    # Step 4: Test functionality
    success = test_basic_functionality(afg)

    # Generate config entry
    if success:
        idn = afg.ask("*IDN?")
        generate_config_entry(visa_address, idn)

    # Cleanup
    print("\n5. Shutting down...")
    afg.shutdown()
    print("   ✓ Connection closed")

    print("\n" + "="*70)
    print("Test complete!")
    print("="*70)


if __name__ == "__main__":
    main()
