# Linux Installation Guide for Laser Setup

This guide provides step-by-step instructions for installing and configuring the Laser Setup application on Linux systems.

## Table of Contents

- [System Requirements](#system-requirements)
- [Prerequisites](#prerequisites)
- [Installation Steps](#installation-steps)
- [USB Device Permissions](#usb-device-permissions)
- [Configuration](#configuration)
- [Verifying Installation](#verifying-installation)
- [Troubleshooting](#troubleshooting)

## System Requirements

- **Operating System**: Linux (tested on Fedora, Ubuntu, Debian)
- **Python Version**: Python 3.10 or higher (3.13 recommended)
- **RAM**: 4GB minimum, 8GB recommended
- **Disk Space**: 500MB for installation and dependencies

## Prerequisites

### 1. Install Python and Development Tools

#### Fedora/RHEL/CentOS
```bash
sudo dnf install python3 python3-pip python3-devel gcc
```

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3 python3-pip python3-dev build-essential
```

#### Arch Linux
```bash
sudo pacman -S python python-pip base-devel
```

### 2. Install System Libraries

The application requires USB and GUI libraries:

#### Fedora/RHEL/CentOS
```bash
sudo dnf install libusb libusb-devel qt6-qtbase qt6-qtbase-devel
```

#### Ubuntu/Debian
```bash
sudo apt install libusb-1.0-0 libusb-1.0-0-dev qt6-base-dev
```

#### Arch Linux
```bash
sudo pacman -S libusb qt6-base
```

### 3. Install uv (Optional but Recommended)

`uv` is a fast Python package installer and resolver:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or using pip:
```bash
pip install uv
```

## Installation Steps

### 1. Clone the Repository

```bash
cd ~
git clone <repository-url> optothermal_setup
cd optothermal_setup
```

### 2. Create Virtual Environment

#### Using venv (standard method)
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Using uv (faster)
```bash
uv venv
source .venv/bin/activate
```

### 3. Install the Package

Install in editable mode for development:

#### Using pip
```bash
pip install -e .
```

#### Using uv (faster)
```bash
uv pip install -e .
```

### 4. Initialize Configuration

Run the initialization command to create config files:

```bash
laser_setup init
```

This will create:
- `config/config.yaml` - Main application settings
- `config/instruments.yaml` - Instrument configurations
- `config/procedures.yaml` - Procedure parameter overrides
- `config/sequences.yaml` - Sequence definitions
- `config/parameters.yaml` - Global parameter configurations

## USB Device Permissions

To access USB instruments (Keithley, Thorlabs, etc.) without root privileges, you need to configure udev rules.

### 1. Create udev Rules File

Create a new file for instrument permissions:

```bash
sudo nano /etc/udev/rules.d/99-lab-instruments.rules
```

### 2. Add Device Rules

Add rules for your specific instruments. Here are common examples:

```bash
# Keithley 2450 SourceMeter
SUBSYSTEM=="usb", ATTR{idVendor}=="05e6", ATTR{idProduct}=="2450", MODE="0666", GROUP="plugdev"

# Thorlabs PM100D Power Meter
SUBSYSTEM=="usb", ATTR{idVendor}=="1313", ATTR{idProduct}=="8078", MODE="0666", GROUP="plugdev"

# Bentham Light Source
SUBSYSTEM=="usb", ATTR{idVendor}=="04d8", ATTR{idProduct}=="1705", MODE="0666", GROUP="plugdev"

# Generic USBTMC devices
SUBSYSTEM=="usb", ATTR{idVendor}=="*", ATTR{idProduct}=="*", MODE="0666", GROUP="plugdev", ENV{DEVTYPE}=="usb_device"
```

**Finding your device IDs**: Run `lsusb` to see connected USB devices and their vendor/product IDs.

### 3. Add User to plugdev Group

```bash
sudo usermod -a -G plugdev $USER
```

### 4. Reload udev Rules

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### 5. Log Out and Back In

You must log out and back in for group membership changes to take effect.

## Configuration

### 1. Configure Instruments

Edit `config/instruments.yaml` to match your hardware setup:

```yaml
Keithley2450:
  adapter: USB0::0x05E6::0x2450::04448996::0::INSTR
  name: Keithley 2450
  IDN: KEITHLEY
  target: ${class:laser_setup.instruments.keithley.Keithley2450}

TENMALASER:
  adapter: /dev/ttyACM0  # Update to your serial port
  IDN: TENMA 72-2715 V6.6 SN:37793899
  target: ${class:laser_setup.instruments.tenma.TENMA}
  kwargs:
    baudrate: 9600
    timeout: 2
```

**Finding serial ports**: Run `ls /dev/tty*` to list available serial ports. Common ports include:
- `/dev/ttyUSB0`, `/dev/ttyUSB1`, etc. - USB-to-serial adapters
- `/dev/ttyACM0`, `/dev/ttyACM1`, etc. - USB CDC devices
- `/dev/ttyS0`, `/dev/ttyS1`, etc. - Built-in serial ports

### 2. Verify USB Connections

Check that instruments are detected:

```bash
# List USB devices
lsusb

# Check VISA resources (if pyvisa is installed)
python -m pyvisa info

# Check USB permissions
ls -l /dev/bus/usb/*/*
```

### 3. Test Serial Ports

For serial instruments, verify port permissions:

```bash
# Check port permissions
ls -l /dev/ttyACM0

# Test reading from port (Ctrl+C to exit)
cat /dev/ttyACM0
```

## Verifying Installation

### 1. Check Installation

```bash
laser_setup --version
laser_setup --help
```

### 2. Test Launch

Launch the GUI:

```bash
laser_setup
```

### 3. Debug Mode

If you don't have instruments connected, use debug mode to test with simulated data:

```bash
laser_setup --debug
```

### 4. Run a Test Procedure

Run a specific procedure from command line:

```bash
laser_setup IV
```

## Troubleshooting

### Import Errors After Code Changes

After modifying any code, always rebuild:

```bash
rm -rf build/
pip install -e .
```

### USB Permission Denied Errors

```
Error: [Errno 13] Permission denied: '/dev/bus/usb/...'
```

**Solution**:
1. Verify udev rules are in place: `cat /etc/udev/rules.d/99-lab-instruments.rules`
2. Check you're in the plugdev group: `groups`
3. Log out and back in
4. Reconnect USB devices

### USB Resource Busy Error

```
Error: [Errno 16] Resource busy
```

**Solution**: The instrument connection is already open. This should not happen with the current version, but if it does:
1. Close the application completely
2. Unplug and replug the USB device
3. Restart the application

### Serial Port Access Denied

```
Error: [Errno 13] Permission denied: '/dev/ttyACM0'
```

**Solution**:
```bash
# Add user to dialout group (for serial ports)
sudo usermod -a -G dialout $USER

# Log out and back in
```

### Missing Config Files

```
File not found: config/instruments.yaml
```

**Solution**:
```bash
laser_setup init
```

Or manually copy from templates:
```bash
cp config/templates/*.yaml config/
```

### Qt Platform Plugin Error

```
qt.qpa.plugin: Could not load the Qt platform plugin "xcb"
```

**Solution** (Ubuntu/Debian):
```bash
sudo apt install libxcb-xinerama0 libxcb-cursor0
```

**Solution** (Fedora):
```bash
sudo dnf install xcb-util-cursor
```

### Import Error: No module named 'laser_setup'

**Solution**: Make sure virtual environment is activated and package is installed:
```bash
source .venv/bin/activate
pip install -e .
```

### PyQt6 Installation Fails

If PyQt6 installation fails, try installing system Qt packages first (see Prerequisites).

For older systems that don't have Qt6:
1. Install PyQt5 instead: `pip install PyQt5`
2. The application uses `qtpy` which will automatically use PyQt5 as a fallback

## Development Installation

For development with additional tools:

```bash
pip install -e ".[dev]"
```

This includes:
- `flake8` for linting
- Additional testing tools

## Environment Variables

Optional environment variables:

```bash
# Custom config file location
export CONFIG=/path/to/custom/config.yaml

# Enable debug logging
export LASER_SETUP_DEBUG=1
```

## Getting Help

- **Documentation**: See `CLAUDE.md` for architecture details
- **Issues**: Report bugs at the project's issue tracker
- **Logs**: Check application logs for detailed error messages

## Quick Reference

```bash
# Activate environment
source .venv/bin/activate

# Launch GUI
laser_setup

# Launch in debug mode (simulated instruments)
laser_setup --debug

# Run specific procedure
laser_setup IV

# Rebuild after code changes
rm -rf build/ && pip install -e .

# Check version
laser_setup --version
```

---

**Last Updated**: November 2025
**Tested On**: Fedora 42, Ubuntu 22.04, Debian 12
