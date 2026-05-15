#!/usr/bin/env bash
set -euo pipefail

# 1. Grant the active local console user libusb access to the USB instruments.
#    The TAG+="uaccess" attribute makes systemd-logind add an ACL for the
#    active seat user. The rule must run before 73-seat-late.rules so we
#    install it at priority 60.

# Drop the older 99- copy if it exists.
sudo rm -f /etc/udev/rules.d/99-usbtmc.rules

cat <<'EOF' | sudo tee /etc/udev/rules.d/60-usbtmc.rules >/dev/null
# Keithley Instruments
SUBSYSTEM=="usb", ATTRS{idVendor}=="05e6", GROUP="dialout", MODE="0660", TAG+="uaccess"
# ThorLabs (PM100D and friends)
SUBSYSTEM=="usb", ATTRS{idVendor}=="1313", GROUP="dialout", MODE="0660", TAG+="uaccess"
EOF

sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=usb

# 2. Blacklist the kernel `usbtmc` module. pyvisa-py talks to USBTMC instruments
#    over libusb directly; if the kernel driver is bound, it holds the interface
#    and libusb cannot claim it ("Resource busy").
cat <<'EOF' | sudo tee /etc/modprobe.d/blacklist-usbtmc.conf >/dev/null
blacklist usbtmc
EOF

if lsmod | grep -q '^usbtmc'; then
    sudo modprobe -r usbtmc || true
fi

echo "udev rule installed and usbtmc kernel module blacklisted."
echo "Unplug and replug the Keithley 2450 and ThorLabs PM100D to apply."
