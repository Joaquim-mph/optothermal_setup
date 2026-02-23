"""Theme manager singleton with Qt signal support.

Provides centralized theme management with automatic palette application
and theme change notifications.
"""

import logging
from enum import Enum, auto
from typing import TYPE_CHECKING

from ..Qt import QtCore, QtGui, QtWidgets
from .colors import (ThemeColors, create_dark_theme, create_light_theme,
                     create_dracula_theme, create_catppuccin_theme,
                     create_solarized_dark_theme, create_gruvbox_theme,
                     create_monokai_theme)
from .detection import detect_system_dark_mode

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)


class ThemeMode(Enum):
    """Theme mode options."""
    AUTO = auto()           # Follow system preference
    LIGHT = auto()          # Force light theme
    DARK = auto()           # Tokyo Night Dark
    DRACULA = auto()        # Dracula
    CATPPUCCIN = auto()     # Catppuccin Mocha
    SOLARIZED_DARK = auto() # Solarized Dark
    GRUVBOX = auto()        # Gruvbox Dark
    MONOKAI = auto()        # Monokai Dark


class ThemeManager(QtCore.QObject):
    """Singleton theme manager with Qt signal support.

    Manages theme state, applies Qt palette changes, and emits signals
    when the theme changes.

    Usage:
        from .theme import manager
        theme = manager()  # Get singleton instance
        theme.set_mode(ThemeMode.DARK)
        theme.theme_changed.connect(my_widget.on_theme_changed)
    """

    theme_changed = QtCore.Signal(object)  # Emits ThemeColors

    _instance: "ThemeManager | None" = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True

        self._mode = ThemeMode.AUTO
        self._current_colors: ThemeColors | None = None
        self._light_theme = create_light_theme()
        self._dark_theme = create_dark_theme()
        self._dracula_theme = create_dracula_theme()
        self._catppuccin_theme = create_catppuccin_theme()
        self._solarized_dark_theme = create_solarized_dark_theme()
        self._gruvbox_theme = create_gruvbox_theme()
        self._monokai_theme = create_monokai_theme()

    @property
    def mode(self) -> ThemeMode:
        """Current theme mode setting."""
        return self._mode

    @property
    def colors(self) -> ThemeColors:
        """Current theme colors. Computes if not yet set."""
        if self._current_colors is None:
            self._current_colors = self._resolve_colors()
        return self._current_colors

    @property
    def is_dark(self) -> bool:
        """Whether the current theme is dark."""
        return self.colors.is_dark

    def set_mode(self, mode: ThemeMode) -> None:
        """Set the theme mode and apply changes.

        Args:
            mode: ThemeMode.AUTO, ThemeMode.LIGHT, or ThemeMode.DARK
        """
        old_colors = self._current_colors
        self._mode = mode
        self._current_colors = self._resolve_colors()

        if old_colors is None or old_colors.name != self._current_colors.name:
            self._apply_palette()
            self.theme_changed.emit(self._current_colors)
            log.info(f"Theme changed to: {self._current_colors.name}")

        self._save_to_settings(mode)

    def _save_to_settings(self, mode: ThemeMode) -> None:
        """Persist theme mode to QSettings."""
        if QtWidgets.QApplication.instance() is None:
            return
        settings = QtCore.QSettings('LaserSetup', 'LaserSetup')
        settings.setValue('theme_mode', mode.name)

    def restore_from_settings(self, fallback_dark: bool = False) -> None:
        """Restore theme from QSettings, falling back to a config default.

        Args:
            fallback_dark: Used when no saved theme exists; True → DARK, False → LIGHT
        """
        settings = QtCore.QSettings('LaserSetup', 'LaserSetup')
        saved = settings.value('theme_mode')
        if saved:
            try:
                mode = ThemeMode[saved]
                self.set_mode(mode)
                return
            except KeyError:
                log.warning(f"Unknown saved theme mode '{saved}', using default")
        self.set_mode_from_config(fallback_dark)

    def set_mode_from_config(self, dark_mode: bool) -> None:
        """Set theme mode from config boolean (backwards compatibility).

        Args:
            dark_mode: True for dark mode, False for light mode
        """
        mode = ThemeMode.DARK if dark_mode else ThemeMode.LIGHT
        self.set_mode(mode)

    def ensure_applied(self) -> None:
        """Ensure the theme is applied to the application.

        Call this after the QApplication is fully initialized.
        """
        if self._current_colors is None:
            self._current_colors = self._resolve_colors()
        self._apply_palette()
        log.debug(f"Theme applied: {self._current_colors.name}")

    def color(self, name: str) -> str:
        """Get a specific color by name.

        Args:
            name: Color attribute name (e.g., 'fg', 'blue')

        Returns:
            Hex color string

        Raises:
            AttributeError: If color name doesn't exist
        """
        return getattr(self.colors, name)

    def _resolve_colors(self) -> ThemeColors:
        """Resolve current colors based on mode and system preference."""
        _map = {
            ThemeMode.LIGHT:          self._light_theme,
            ThemeMode.DARK:           self._dark_theme,
            ThemeMode.DRACULA:        self._dracula_theme,
            ThemeMode.CATPPUCCIN:     self._catppuccin_theme,
            ThemeMode.SOLARIZED_DARK: self._solarized_dark_theme,
            ThemeMode.GRUVBOX:        self._gruvbox_theme,
            ThemeMode.MONOKAI:        self._monokai_theme,
        }
        if self._mode in _map:
            return _map[self._mode]
        # AUTO
        system_dark = detect_system_dark_mode()
        if system_dark is None:
            return self._light_theme
        return self._dark_theme if system_dark else self._light_theme

    def _apply_palette(self) -> None:
        """Apply current theme as Qt palette to the application."""
        app = QtWidgets.QApplication.instance()
        if app is None:
            log.warning("No QApplication instance found, cannot apply palette")
            return

        colors = self.colors
        qt_roles = {
            'Window':          colors.bg,
            'WindowText':      colors.fg,
            'Text':            colors.fg,
            'Button':          colors.bg_highlight,
            'ButtonText':      colors.fg,
            'Base':            colors.bg,
            'AlternateBase':   colors.bg_sidebar,
            'Link':            colors.blue,
            'Highlight':       colors.blue,
            'HighlightedText': '#FFFFFF',
            'PlaceholderText': colors.comment,
        }
        palette = QtGui.QPalette()
        for role, hex_color in qt_roles.items():
            palette.setColor(
                getattr(QtGui.QPalette.ColorRole, role),
                QtGui.QColor(hex_color),
            )
        app.setPalette(palette)

        # Apply full QSS stylesheet so every widget is covered globally
        from .qss import build_stylesheet
        app.setStyleSheet(build_stylesheet(colors.as_palette_dict()))


# Module-level singleton accessor
_manager: ThemeManager | None = None


def manager() -> ThemeManager:
    """Get the ThemeManager singleton instance.

    Returns:
        The global ThemeManager instance
    """
    global _manager
    if _manager is None:
        _manager = ThemeManager()
    return _manager
