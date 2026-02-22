"""Theme color definitions with semantic naming.

This module defines color palettes for light and dark themes with improved
contrast ratios for accessibility.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeColors:
    """Semantic color definitions for a theme.

    Colors are organized by purpose rather than visual appearance,
    allowing consistent theming across the application.
    """

    # Mode identifier
    name: str

    # Foreground colors (text)
    fg_primary: str      # Main text
    fg_secondary: str    # Subdued text, labels
    fg_disabled: str     # Disabled text

    # Background colors
    bg_primary: str      # Main background
    bg_secondary: str    # Cards, panels
    bg_tertiary: str     # Inputs, nested elements

    # Accent colors
    accent_primary: str    # Primary actions, links
    accent_primary_hover: str
    accent_secondary: str  # Secondary accent

    # Semantic colors
    success: str
    success_hover: str
    warning: str
    warning_hover: str
    danger: str
    danger_hover: str
    info: str

    # Border colors
    border_primary: str
    border_secondary: str
    border_focus: str

    # Procedure-specific colors (for main buttons)
    proc_ivg: str        # Blue - IVg
    proc_ivg_hover: str
    proc_it: str         # Green - It
    proc_it_hover: str
    proc_iv: str         # Red - IV
    proc_iv_hover: str
    proc_laser: str      # Orange - Laser
    proc_laser_hover: str


def create_light_theme() -> ThemeColors:
    """Create light theme with improved contrast.

    Key fix: Uses darker blue (#2563EB) instead of #4A90E2 for better
    contrast on light backgrounds.
    """
    return ThemeColors(
        name="light",
        # Foreground - dark text for light backgrounds
        fg_primary="#1A1A1A",        # Near-black for main text
        fg_secondary="#495057",      # Dark gray for secondary text
        fg_disabled="#9CA3AF",       # Light gray for disabled

        # Background - light colors
        bg_primary="#FFFFFF",        # White
        bg_secondary="#F8F9FA",      # Very light gray
        bg_tertiary="#E9ECEF",       # Light gray for inputs

        # Accent - darker blue for better contrast
        accent_primary="#2563EB",    # Darker blue (was #4A90E2)
        accent_primary_hover="#1D4ED8",
        accent_secondary="#6366F1",  # Indigo

        # Semantic colors
        success="#16A34A",           # Green
        success_hover="#15803D",
        warning="#D97706",           # Amber
        warning_hover="#B45309",
        danger="#DC2626",            # Red
        danger_hover="#B91C1C",
        info="#2563EB",              # Same as accent for consistency

        # Borders
        border_primary="#D1D5DB",    # Medium gray
        border_secondary="#E5E7EB",  # Light gray
        border_focus="#2563EB",      # Accent color

        # Procedure buttons
        proc_ivg="#2563EB",          # Blue
        proc_ivg_hover="#1D4ED8",
        proc_it="#16A34A",           # Green
        proc_it_hover="#15803D",
        proc_iv="#DC2626",           # Red
        proc_iv_hover="#B91C1C",
        proc_laser="#D97706",        # Orange/Amber
        proc_laser_hover="#B45309",
    )


def create_dark_theme() -> ThemeColors:
    """Create dark theme optimized for low-light environments."""
    return ThemeColors(
        name="dark",
        # Foreground - light text for dark backgrounds
        fg_primary="#E5E7EB",        # Light gray
        fg_secondary="#9CA3AF",      # Medium gray
        fg_disabled="#6B7280",       # Dark gray for disabled

        # Background - dark colors
        bg_primary="#1F1F1F",        # Near-black
        bg_secondary="#2D2D2D",      # Dark gray for cards
        bg_tertiary="#3D3D3D",       # Lighter gray for inputs

        # Accent - brighter for dark backgrounds
        accent_primary="#4A90E2",    # Original blue works well on dark
        accent_primary_hover="#60A5FA",
        accent_secondary="#818CF8",  # Lighter indigo

        # Semantic colors - brighter for dark backgrounds
        success="#22C55E",           # Bright green
        success_hover="#4ADE80",
        warning="#F59E0B",           # Bright amber
        warning_hover="#FBBF24",
        danger="#EF4444",            # Bright red
        danger_hover="#F87171",
        info="#4A90E2",              # Same as accent

        # Borders
        border_primary="#4B5563",    # Medium gray
        border_secondary="#374151",  # Darker gray
        border_focus="#4A90E2",      # Accent color

        # Procedure buttons - brighter for dark mode
        proc_ivg="#4A90E2",          # Blue
        proc_ivg_hover="#60A5FA",
        proc_it="#22C55E",           # Green
        proc_it_hover="#4ADE80",
        proc_iv="#EF4444",           # Red
        proc_iv_hover="#F87171",
        proc_laser="#F59E0B",        # Orange/Amber
        proc_laser_hover="#FBBF24",
    )
