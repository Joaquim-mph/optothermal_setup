#!/usr/bin/env python
"""Raw serial test for TENMA power supply."""

import serial
import time

ports = [
    '/dev/tty.usbmodem0002294704521',
    '/dev/tty.usbmodemSN234567892',
]

baudrates = [9600, 115200]

print("Testing TENMA with raw serial communication...\n")

for port in ports:
    print(f"Port: {port}")

    for baudrate in baudrates:
        print(f"  Baudrate: {baudrate}")

        try:
            # Open serial connection
            ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=1,
                write_timeout=1,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )

            time.sleep(0.1)  # Wait for connection
            print(f"    ✓ Serial port opened")

            # Flush buffers
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            # Try to send a simple query (VSET1? - query voltage)
            command = b"VSET1?\n"
            print(f"    Sending: {command}")
            ser.write(command)
            ser.flush()

            time.sleep(0.2)

            # Try to read response
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"    ✓ Response: {response}")
                print(f"\n✓✓✓ TENMA found on {port} with baudrate {baudrate} ✓✓✓\n")

                ser.close()
                exit(0)
            else:
                print(f"    ✗ No response")

            ser.close()

        except serial.SerialException as e:
            print(f"    ✗ Serial error: {e}")
        except Exception as e:
            print(f"    ✗ Error: {e}")

        print()

print("\nNo TENMA found. Possible issues:")
print("1. Wrong port - check with: ls /dev/tty.*")
print("2. TENMA not powered on")
print("3. Different command protocol")
print("\nTry manually with screen:")
print(f"  screen {ports[0]} 9600")
print("  Then type: VSET1?")
