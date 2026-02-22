"""Platform-specific system theme detection.

Supports detection of system dark mode on:
- Linux (GNOME, GTK)
- macOS
- Windows 10/11
"""

import logging
import subprocess
import sys

log = logging.getLogger(__name__)


def detect_system_dark_mode() -> bool | None:
    """Detect if the system is using dark mode.

    Returns:
        True if dark mode is detected
        False if light mode is detected
        None if detection failed or not supported
    """
    if sys.platform == "linux":
        return _detect_linux_dark_mode()
    elif sys.platform == "darwin":
        return _detect_macos_dark_mode()
    elif sys.platform == "win32":
        return _detect_windows_dark_mode()
    return None


def _detect_linux_dark_mode() -> bool | None:
    """Detect dark mode on Linux (GNOME/GTK)."""
    # Try GNOME/GTK color scheme first
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            scheme = result.stdout.strip().strip("'")
            return "dark" in scheme.lower()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    # Try GTK theme name fallback
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            theme = result.stdout.strip().strip("'").lower()
            # Common dark theme patterns
            return any(dark in theme for dark in ["dark", "adwaita-dark", "breeze-dark"])
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    return None


def _detect_macos_dark_mode() -> bool | None:
    """Detect dark mode on macOS."""
    try:
        result = subprocess.run(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            capture_output=True,
            text=True,
            timeout=2
        )
        # Returns "Dark" if dark mode, returns error/empty if light mode
        return result.returncode == 0 and "dark" in result.stdout.lower()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def _detect_windows_dark_mode() -> bool | None:
    """Detect dark mode on Windows 10/11."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        # AppsUseLightTheme: 0 = dark mode, 1 = light mode
        return value == 0
    except (ImportError, OSError, FileNotFoundError):
        pass
    return None
