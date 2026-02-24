import sys
from pathlib import Path

from pymeasure.experiment import Procedure

from .. import __version__
from ..config import CONFIG, DefaultPaths
from ..patches import patch_results_dialog
from ..utils import remove_empty_data
from .Qt import QtCore, QtGui, QtWidgets, make_app
from .theme import manager as theme_manager

_app_id = "NanoLabFCFM.LaserSetup.v" + __version__


class ShortcutFilter(QtCore.QObject):
    """Event filter for the application to handle shortcuts.
    """
    fontsize_range = range(8, 32)
    zoom_in_keys = (QtCore.Qt.Key.Key_Plus, QtCore.Qt.Key.Key_Equal)
    zoom_out_keys = (QtCore.Qt.Key.Key_Minus, QtCore.Qt.Key.Key_Underscore)
    maximize_keys = (QtCore.Qt.Key.Key_F11,)
    close_keys = (QtCore.Qt.Key.Key_W,)
    command_palette_key = QtCore.Qt.Key.Key_P

    def __init__(self, app: QtWidgets.QApplication):
        super().__init__()
        self.app = app

    def eventFilter(self, obj, event: QtCore.QEvent) -> bool:
        window = self.app.activeWindow()
        if isinstance(event, QtGui.QKeyEvent) and event.type() == QtCore.QEvent.Type.KeyPress:
            key = event.key()
            if event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
                if key in self.close_keys and window is not None:
                    window.close()
                    return True
                elif key in self.zoom_in_keys:
                    self.app_zoom(1)
                    return True
                elif key in self.zoom_out_keys:
                    self.app_zoom(-1)
                    return True
                elif key == self.command_palette_key:
                    from .windows.main_window import MainWindow
                    from .widgets.command_palette import CommandPaletteDialog
                    mw = next(
                        (w for w in self.app.topLevelWidgets() if isinstance(w, MainWindow)),
                        None
                    )
                    if mw:
                        CommandPaletteDialog(mw).exec()
                    return True

            if key in self.maximize_keys:
                if window:
                    if window.isMaximized():
                        window.showNormal()
                    else:
                        window.showMaximized()

                return True

        return super().eventFilter(obj, event)

    def app_zoom(self, factor: int = 1):
        """Zooms the whole application in or out by the given factor."""
        font: QtGui.QFont = self.app.font()
        if not (new_size := font.pointSize() + factor) in self.fontsize_range:
            return

        font.setPointSize(new_size)
        self.app.setFont(font)


def get_dark_palette():
    palette = QtGui.QPalette()
    palette_dict = {
        'Window': (50, 50, 50),
        'WindowText': (200, 200, 200),
        'Text': (200, 200, 200),
        'Button': (30, 30, 30),
        'ButtonText': (200, 200, 200),
        'Base': (35, 35, 35),
        'AlternateBase': (45, 45, 45),
        'Link': (42, 130, 218),
        'Highlight': (42, 130, 218),
        'HighlightedText': (240, 240, 240),
    }

    for role, color in palette_dict.items():
        palette.setColor(
            getattr(QtGui.QPalette.ColorRole, role), QtGui.QColor(*color)
        )
    return palette


def display_window(procedure: type[Procedure] | None = None, **kwargs):
    """If no procedure is given, display the main window. Otherwise, display
    the experiment window with the given procedure.

    The window style and palette are set according to the configuration file.
    A splash screen is shown while the window is loading.

    :param procedure: The procedure to display in the experiment window.
    :param kwargs: Additional keyword arguments to pass to the window.
    """
    _patch_taskbar_icon()
    patch_results_dialog()  # Apply deferred patches now that display is needed
    app = make_app()
    shortcut_filter = ShortcutFilter(app)
    app.installEventFilter(shortcut_filter)

    if not (splash_image := Path(CONFIG.Qt.GUI.splash_image)).is_file():
        splash_image = DefaultPaths.splash

    pixmap = QtGui.QPixmap(splash_image.as_posix())
    if pixmap.isNull():
        # If loading as pixmap fails, try loading as icon first
        pixmap = QtGui.QIcon(splash_image.as_posix()).pixmap(QtCore.QSize(300, 300))
    else:
        # Scale down the image to a reasonable size
        pixmap = pixmap.scaled(300, 300, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                               QtCore.Qt.TransformationMode.SmoothTransformation)

    import time
    splash_start_time = time.time()

    splash = QtWidgets.QSplashScreen(pixmap, QtCore.Qt.WindowType.WindowStaysOnTopHint)
    splash.show()

    # Get available styles with QtWidgets.QStyleFactory.keys()
    app.setStyle(CONFIG.Qt.GUI.style)

    # Initialize theme system
    theme = theme_manager()
    theme.restore_from_settings(fallback_theme=CONFIG.Qt.GUI.theme_mode)
    theme.ensure_applied()
    QtCore.QLocale.setDefault(QtCore.QLocale(
        QtCore.QLocale.Language.English,
        QtCore.QLocale.Country.UnitedStates
    ))
    font = app.font()
    if CONFIG.Qt.GUI.font:
        font.setFamily(CONFIG.Qt.GUI.font)
    font.setPointSize(CONFIG.Qt.GUI.font_size)
    app.setFont(font)

    if procedure is None:
        from .windows.main_window import MainWindow
        Window = MainWindow

    elif issubclass(procedure, Procedure):
        from .windows.experiment_window import ExperimentWindow
        Window = ExperimentWindow
        kwargs['cls'] = procedure

    else:
        raise ValueError(f"Invalid procedure: {procedure}")

    window = Window(**kwargs)

    # Keep splash visible for at least 1 second
    elapsed = time.time() - splash_start_time
    remaining = max(0, 1000 - int(elapsed * 1000))  # 1000ms = 1 second

    splash_timer = QtCore.QTimer()
    splash_timer.setSingleShot(True)
    splash_timer.timeout.connect(lambda: (splash.finish(window), window.show()))
    splash_timer.start(remaining)

    app.exec()
    remove_empty_data()


def _patch_taskbar_icon():
    """Patches the taskbar icon for Windows to show the application icon."""
    if sys.platform != 'win32':
        return

    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(_app_id)
