"""Theme system for laser_setup GUI.

Provides centralized theme management with support for light and dark modes,
automatic system theme detection, and Qt palette integration.

Usage:
    from laser_setup.display.theme import manager, colors, qss

    # Get the theme manager singleton
    theme = manager()
    theme.set_mode_from_config(dark_mode=True)

    # Get current colors
    current_colors = colors()
    print(current_colors.fg)

    # Get a specific color
    accent = color('blue')

    # Get QSS for a named style
    button_style = qss('button_primary')

    # Connect to theme changes
    theme.theme_changed.connect(my_widget.on_theme_changed)
"""

from .colors import (ThemeColors, create_default_dark_theme, create_default_light_theme,
                     create_dark_theme, create_light_theme,
                     create_dracula_theme, create_catppuccin_theme,
                     create_solarized_dark_theme, create_gruvbox_theme,
                     create_monokai_theme,
                     create_dracula_light_theme, create_catppuccin_latte_theme,
                     create_solarized_light_theme, create_gruvbox_light_theme,
                     create_monokai_light_theme)
from .manager import ThemeManager, ThemeMode, manager
from .qss import qss, get_procedure_button_style, build_stylesheet, get_proc_btn_index


def colors() -> ThemeColors:
    """Get current theme colors.

    Returns:
        ThemeColors dataclass with all color definitions
    """
    return manager().colors


def color(name: str) -> str:
    """Get a specific color by name.

    Args:
        name: Color attribute name (e.g., 'fg_primary', 'accent_primary')

    Returns:
        Hex color string
    """
    return manager().color(name)


__all__ = [
    # Manager
    'ThemeManager',
    'ThemeMode',
    'manager',
    # Colors
    'ThemeColors',
    'colors',
    'color',
    'create_default_light_theme',
    'create_default_dark_theme',
    'create_light_theme',
    'create_dark_theme',
    'create_dracula_light_theme',
    'create_dracula_theme',
    'create_catppuccin_latte_theme',
    'create_catppuccin_theme',
    'create_solarized_light_theme',
    'create_solarized_dark_theme',
    'create_gruvbox_light_theme',
    'create_gruvbox_theme',
    'create_monokai_light_theme',
    'create_monokai_theme',
    # QSS
    'qss',
    'get_procedure_button_style',
    'build_stylesheet',
    'get_proc_btn_index',
]
