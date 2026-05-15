import logging
import os
import sys
from functools import partial
from pathlib import Path
from typing import Callable

from pymeasure.experiment import Procedure

from ...cli import parameters_to_db
from ...config import CONFIG, ConfigHandler, configurable
from ...config.defaults import (
    InstrumentConfig,
    ProceduresConfig,
    ScriptsConfig,
    SequencesConfig,
)
from ...instruments import InstrumentManager
from ...procedures import ChipProcedure, Sequence
from ...utils import get_status_message
from .._procedure_groups import _PROCEDURE_GROUPS
from ..Qt import ConsoleWidget, QtCore, QtGui, QtWidgets, Worker
from ..theme import ThemeMode, get_proc_btn_index
from ..theme import manager as theme_manager
from ..widgets import LogsWidget, SQLiteWidget
from ..widgets.camera_widget import CameraWidget
from .experiment_window import ExperimentWindow
from .sequence_window import SequenceWindow
from .settings_dialog import SettingsDialog

log = logging.getLogger(__name__)

# Keyboard shortcuts for the 4 main procedures (consistent with buttons)
_PROCEDURE_SHORTCUTS: dict[str, str] = {
    "IV": "Ctrl+5",
    "IVg": "Ctrl+1",
    "It": "Ctrl+2",
    "VVg": "Ctrl+3",
    "Vt": "Ctrl+4",
    "LaserCalibration": "Ctrl+6",
}


def _set_widget_value(widget, value) -> None:
    """Best-effort value setter for various Qt input widget types."""
    if hasattr(widget, "setCurrentText"):
        widget.setCurrentText(str(value))
    elif hasattr(widget, "setValue"):
        widget.setValue(value)
    elif hasattr(widget, "setText"):
        widget.setText(str(value))
    elif hasattr(widget, "setChecked"):
        widget.setChecked(bool(value))


@configurable("Qt.MainWindow", on_definition=False, subclasses=False)
class MainWindow(QtWidgets.QMainWindow):
    """The main window for program. It contains buttons to open
    the experiment windows, sequence windows, and run scripts.
    """

    def __init__(
        self,
        procedures: ProceduresConfig,
        sequences: SequencesConfig,
        scripts: ScriptsConfig,
        instruments: dict[str, InstrumentConfig],
        title: str = "Main Window",
        size: tuple[int, int] = (640, 480),
        widget_size: tuple[int, int] = (640, 480),
        icon: str | None = None,
        readme_file: str | Path = "README.md",
        main_procedures: list | None = None,
        **kwargs,
    ):
        """Initializes the main window with the given procedures, sequences, and scripts.

        :param procedures: List of procedures to display in the Procedures menu.
        :param sequences: Dictionary with the sequences to display in the Sequences menu.
        :param scripts: List of scripts to display in the Scripts menu.
        :param instruments: Dictionary of instrument configurations.
        :param title: Title of the window.
        :param size: Size of the window.
        :param widget_size: Size of the widgets.
        :param icon: Icon of the window.
        :param readme_file: Path to the README file.
        :param main_procedures: Names of procedures to show as main buttons.
        :param kwargs: Additional arguments for the QMainWindow.
        """
        self.widget_size = widget_size
        self.readme_path = Path(readme_file)
        self.procedures = procedures
        self.sequences = sequences
        self.scripts = scripts
        self.instruments = instruments
        self.main_procedures = (
            list(main_procedures)
            if main_procedures
            else ["IVg", "It", "IV", "LaserCalibration"]
        )
        self.config_handler = ConfigHandler(parent=self, config=CONFIG)

        super().__init__(**kwargs)
        self.setWindowTitle(title)
        self.setWindowIcon(
            QtGui.QIcon(icon)
            if icon
            else self.style().standardIcon(
                QtWidgets.QStyle.StandardPixmap.SP_TitleBarMenuButton
            )
        )
        self.setCentralWidget(QtWidgets.QWidget(parent=self))

        self.windows: dict[
            type[Procedure] | type[Sequence] | str, QtWidgets.QMainWindow
        ] = {}
        self._layout = QtWidgets.QGridLayout(self.centralWidget())

        # Store procedure and sequence types before they're popped in create_menu_bar
        self.procedure_types: dict[str, type[Procedure]] = self.procedures.get(
            "_types", {}
        )
        self.sequence_types: dict[str, type[Sequence]] = self.sequences.get(
            "_types", {}
        )

        self.menu_bar = self.create_menu_bar()
        self.status_bar = self.statusBar()

        self._thread = QtCore.QThread(parent=self)
        self._worker = Worker(get_status_message, self._thread)
        self._worker.finished.connect(
            lambda msg: self.status_bar.showMessage(msg, 3000)
        )
        self._worker.finished.connect(lambda _: self._update_laser_indicator())
        self._thread.start()

        # Main procedure buttons (and session context panel)
        self.create_main_buttons()

        # Laser state indicator in status bar
        self._laser_indicator = QtWidgets.QLabel(" LASER OFF ")
        self._laser_indicator.setToolTip("TENMA Laser channel state")
        self._update_laser_indicator()
        self.status_bar.addPermanentWidget(self._laser_indicator)

        # Reload window button
        self.reload = QtWidgets.QPushButton("Reload")
        self.reload.clicked.connect(
            lambda: os.execl(
                sys.executable, sys.executable, "-m", "laser_setup", *sys.argv[1:]
            )
        )  # TODO: fix bug where the terminal misbehaves after reload
        self.reload.setShortcut("Ctrl+R")
        self.status_bar.addPermanentWidget(self.reload)

        self.adjustSize()

    # ------------------------------------------------------------------
    # Main button grid
    # ------------------------------------------------------------------

    def create_main_buttons(self):
        """Creates the main buttons for the most common procedures."""
        procedure_types = self.procedure_types

        # Session context panel (shown when at least one ChipProcedure is available)
        has_chip_proc = any(
            issubclass(cls, ChipProcedure) for cls in procedure_types.values()
        )
        if has_chip_proc:
            from ..widgets.session_context_widget import SessionContextWidget

            self._session_widget = SessionContextWidget(parent=self)
            self._layout.addWidget(self._session_widget)

        # Create a grid for buttons
        self._button_widget = QtWidgets.QWidget(parent=self)
        button_layout = QtWidgets.QGridLayout(self._button_widget)
        button_layout.setSpacing(15)
        button_layout.setContentsMargins(30, 30, 30, 20)

        from ..widgets.procedure_card_widget import ProcedureCardWidget

        # Store card references
        self._proc_buttons: dict[str, ProcedureCardWidget] = {}

        # Create cards in a 2-column grid
        for i, proc_name in enumerate(self.main_procedures):
            if proc_name not in procedure_types:
                continue

            cls = procedure_types[proc_name]
            idx = get_proc_btn_index(proc_name, fallback_index=i)
            shortcut = _PROCEDURE_SHORTCUTS.get(proc_name, "")

            card = ProcedureCardWidget(
                cls, idx, shortcut=shortcut, parent=self._button_widget
            )
            card.clicked.connect(partial(self.open_procedure, cls))
            self._proc_buttons[proc_name] = card

            row = i // 2
            col = i % 2
            button_layout.addWidget(card, row, col)

        theme_manager().theme_changed.connect(self._on_theme_changed)
        self._layout.addWidget(self._button_widget)

    def _on_theme_changed(self, _colors=None):
        self._update_laser_indicator()

    # ------------------------------------------------------------------
    # Menu bar construction
    # ------------------------------------------------------------------

    def create_menu_bar(self) -> QtWidgets.QMenuBar:
        """Creates the menu bar.

        This method can be overridden to add more options.

        :return: The menu bar.
        """
        menu = self.menuBar()
        self.procedures.pop("_types", None)
        self.sequences.pop("_types", None)

        self._add_measurement_menu(menu)
        self._add_sequences_menu(menu)
        self._add_instruments_menu(menu)
        self._add_scripts_menu(menu)
        self._add_view_menu(menu)
        self._add_config_menu(menu)
        self._add_help_menu(menu)

        return menu

    def _add_measurement_menu(self, menu: QtWidgets.QMenuBar):
        """Add grouped &Measurement menu (was flat &Procedures)."""
        proc_menu = menu.addMenu("&Measurement")
        proc_menu.setToolTipsVisible(True)

        bold_font = QtGui.QFont()
        bold_font.setBold(True)

        first_group = True
        for group_name, proc_names in _PROCEDURE_GROUPS:
            # Any procedure in this group that's registered?
            available = [p for p in proc_names if p in self.procedure_types]
            if not available:
                continue

            if not first_group:
                proc_menu.addSeparator()
            first_group = False

            # Disabled bold header
            header = QtGui.QAction(group_name, self)
            header.setEnabled(False)
            header.setFont(bold_font)
            proc_menu.addAction(header)

            for proc_name in available:
                cls = self.procedure_types[proc_name]
                display_name = getattr(cls, "name", cls.__name__)
                action = QtGui.QAction(display_name, self)
                doc = (cls.__doc__ or "").replace("    ", "").strip()
                action.triggered.connect(partial(self.open_procedure, cls))
                action.setToolTip(doc)
                action.setStatusTip(doc)
                if proc_name in _PROCEDURE_SHORTCUTS:
                    action.setShortcut(_PROCEDURE_SHORTCUTS[proc_name])
                proc_menu.addAction(action)

        # Recent submenu (rebuilt on every open)
        proc_menu.addSeparator()
        self._recent_menu = proc_menu.addMenu("Recent")
        proc_menu.aboutToShow.connect(self._rebuild_recent_menu)
        self._rebuild_recent_menu()

    def _add_sequences_menu(self, menu: QtWidgets.QMenuBar):
        """Add Se&quences menu."""
        sequence_menu = menu.addMenu("Se&quences")
        sequence_menu.setToolTipsVisible(True)

        for key, item in self.sequences.items():
            if key not in self.sequence_types:
                log.warning(
                    f"Sequence '{key}' not found in _types, skipping menu entry"
                )
                continue
            cls = self.sequence_types[key]
            name = getattr(item, "name", cls.__name__)
            action = QtGui.QAction(key, self)
            doc = getattr(
                item, "description", (cls.__doc__ or "").replace("    ", "").strip()
            )
            action.triggered.connect(partial(self.open_sequence, cls))
            action.setToolTip(doc)
            action.setStatusTip(doc)
            action.setShortcut(f"Ctrl+Shift+{len(sequence_menu.actions()) + 1}")
            sequence_menu.addAction(action)

        sequence_menu.addSeparator()
        new_seq = QtGui.QAction("New Sequence...", self)
        new_seq.triggered.connect(self.open_sequence_creator)
        new_seq.setShortcut("Ctrl+N")
        new_seq.setToolTip("Create a new procedure sequence")
        new_seq.setStatusTip("Create a new procedure sequence")
        sequence_menu.addAction(new_seq)

        edit_seq = QtGui.QAction("Edit Sequence...", self)
        edit_seq.triggered.connect(self.open_sequence_editor)
        edit_seq.setShortcut("Ctrl+E")
        edit_seq.setToolTip("Edit an existing procedure sequence")
        edit_seq.setStatusTip("Edit an existing procedure sequence")
        sequence_menu.addAction(edit_seq)

    def _add_instruments_menu(self, menu: QtWidgets.QMenuBar):
        """Add &Instruments menu with live connection status icons."""
        inst_menu = menu.addMenu("&Instruments")
        inst_menu.setToolTipsVisible(True)

        self._instrument_actions: dict[str, QtGui.QAction] = {}
        for key, item in self.instruments.items():
            display_name = getattr(item, "name", None) or key
            action = QtGui.QAction(display_name, self)
            action.setEnabled(False)  # Status display only
            inst_menu.addAction(action)
            self._instrument_actions[key] = action

        inst_menu.addSeparator()

        setup_action = QtGui.QAction("Setup Adapters...", self)
        setup_action.setStatusTip("Detect and configure instrument adapters")
        if "setup_adapters" in self.scripts:
            func = self.scripts["setup_adapters"].target
            setup_action.triggered.connect(partial(self.run_script, func))
        inst_menu.addAction(setup_action)

        shutdown_action = QtGui.QAction("Shutdown All", self)
        shutdown_action.setStatusTip("Shut down all connected instruments")
        shutdown_action.triggered.connect(self._shutdown_all_instruments)
        inst_menu.addAction(shutdown_action)

        inst_menu.addSeparator()

        # Instrument help submenu (moved from Help)
        help_sub = inst_menu.addMenu("Help")
        unique_instruments = {i.target for i in self.instruments.values()}
        for cls in unique_instruments:
            name = getattr(cls, "name", cls.__name__)
            ha = QtGui.QAction(name, self)
            ha.triggered.connect(
                partial(
                    self.text_window, name, InstrumentManager.help(cls, return_str=True)
                )
            )
            help_sub.addAction(ha)

        # Refresh icons when menu opens
        inst_menu.aboutToShow.connect(self._refresh_instrument_status)
        self._refresh_instrument_status()

    def _add_scripts_menu(self, menu: QtWidgets.QMenuBar):
        """Add &Scripts menu."""
        script_menu = menu.addMenu("&Scripts")
        script_menu.setToolTipsVisible(True)
        for key, item in self.scripts.items():
            func: Callable = item.target
            action = QtGui.QAction(item.name or func.__doc__, self)
            doc = (
                (sys.modules[func.__module__].__doc__ or "").replace("    ", "").strip()
            )
            action.triggered.connect(partial(self.run_script, func, **item.kwargs))
            action.setToolTip(doc)
            action.setStatusTip(doc)
            action.setShortcut(f"Alt+{len(script_menu.actions()) + 1}")
            script_menu.addAction(action)

    def _add_view_menu(self, menu: QtWidgets.QMenuBar):
        """Add &View menu with dark mode toggle and shortcut hints."""
        view_menu = menu.addMenu("&View")

        db_action = view_menu.addAction(
            "Parameter Database", partial(self.open_database, CONFIG.Dir.database)
        )
        db_action.setShortcut("Ctrl+Shift+B")

        video_action = view_menu.addAction("Cameras", self.open_camera)
        video_action.setShortcut("Ctrl+Shift+C")

        self.log_widget = LogsWidget(parent=self)
        self.log_widget.setWindowFlags(QtCore.Qt.WindowType.Dialog)
        self.log = logging.getLogger("laser_setup")
        self.log.addHandler(self.log_widget.handler)

        log_action = view_menu.addAction(
            "Logs", partial(self.open_widget, self.log_widget, "Logs")
        )
        log_action.setShortcut("Ctrl+Shift+L")

        console_action = view_menu.addAction("Terminal", self.open_terminal)
        console_action.setShortcut("Ctrl+Shift+T")

        view_menu.addSeparator()

        dark_toggle = QtGui.QAction("Toggle Light/Dark", self)
        dark_toggle.setShortcut("Ctrl+Shift+D")
        dark_toggle.setStatusTip("Switch between light and dark theme")
        dark_toggle.triggered.connect(self._toggle_dark_mode)
        view_menu.addAction(dark_toggle)

        theme_menu = view_menu.addMenu("Theme")
        self._theme_action_group = QtGui.QActionGroup(self)
        self._theme_action_group.setExclusive(True)
        # (label, light_mode, dark_mode)
        _THEME_FAMILIES = [
            ("Default",    ThemeMode.DEFAULT_LIGHT,   ThemeMode.DEFAULT_DARK),
            ("Tokyo Night", ThemeMode.LIGHT,          ThemeMode.DARK),
            ("Dracula",    ThemeMode.DRACULA_LIGHT,   ThemeMode.DRACULA),
            ("Catppuccin", ThemeMode.CATPPUCCIN_LIGHT, ThemeMode.CATPPUCCIN),
            ("Solarized",  ThemeMode.SOLARIZED_LIGHT, ThemeMode.SOLARIZED_DARK),
            ("Gruvbox",    ThemeMode.GRUVBOX_LIGHT,   ThemeMode.GRUVBOX),
            ("Monokai",    ThemeMode.MONOKAI_LIGHT,   ThemeMode.MONOKAI),
        ]
        tm = theme_manager()
        # Map frozenset({light_mode, dark_mode}) → QAction for checkmark updates
        self._theme_family_actions: dict[frozenset, QtGui.QAction] = {}
        for label, light_mode, dark_mode in _THEME_FAMILIES:
            act = QtGui.QAction(label, self, checkable=True)
            act.setChecked(tm.mode in (light_mode, dark_mode))
            act.triggered.connect(partial(self._select_theme_family, light_mode, dark_mode))
            self._theme_action_group.addAction(act)
            theme_menu.addAction(act)
            self._theme_family_actions[frozenset([light_mode, dark_mode])] = act
        tm.theme_changed.connect(self._update_theme_family_checks)

        view_menu.addSeparator()

        # Visible shortcut hints for zoom and fullscreen (handled by ShortcutFilter)
        zoom_in = view_menu.addAction("Zoom In", lambda: self._app_zoom(1))
        zoom_in.setShortcut("Ctrl++")

        zoom_out = view_menu.addAction("Zoom Out", lambda: self._app_zoom(-1))
        zoom_out.setShortcut("Ctrl+-")

        fullscreen = view_menu.addAction("Toggle Fullscreen", self._toggle_fullscreen)
        fullscreen.setShortcut("F11")

    def _add_config_menu(self, menu: QtWidgets.QMenuBar):
        """Add &Config menu."""
        config_menu = menu.addMenu("&Config")
        self._settings_dialog = SettingsDialog(
            config_handler=self.config_handler, parent=self
        )
        edit_action = config_menu.addAction("Edit config", self._open_settings)
        edit_action.setShortcut("Ctrl+,")
        edit_action.setStatusTip("Open the settings dialog")
        config_menu.addSeparator()
        config_menu.addAction("Load config", self.config_handler.import_config)
        config_menu.addAction("Open config file", self.config_handler.edit_config)

    def _open_settings(self) -> None:
        """Show the settings dialog, raising it if already visible."""
        if self._settings_dialog.isVisible():
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
        else:
            self._settings_dialog.show()

    def _add_help_menu(self, menu: QtWidgets.QMenuBar):
        """Add &Help menu."""
        help_menu = menu.addMenu("&Help")
        help_menu.setToolTipsVisible(True)
        # Instrument docs moved to Instruments > Help submenu
        # Keep help menu for future use / README
        readme_action = QtGui.QAction("README", self)
        readme_action.setStatusTip("Open the README file")
        readme_action.triggered.connect(self._open_readme)
        help_menu.addAction(readme_action)

    # ------------------------------------------------------------------
    # Instrument status helpers
    # ------------------------------------------------------------------

    def _get_connected_instrument_ids(self) -> set:
        """Collect all instrument IDs currently held in any procedure's manager."""
        connected: set = set()
        for cls in self.procedure_types.values():
            mgr = getattr(cls, "instruments", None)
            if isinstance(mgr, InstrumentManager):
                connected.update(mgr.instrument_dict.keys())
        return connected

    def _make_status_icon(self, connected: bool) -> QtGui.QIcon:
        """Create a 12×12 colored circle icon for instrument connection status."""
        c = theme_manager().colors
        color_hex = c.green if connected else c.comment
        pixmap = QtGui.QPixmap(12, 12)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(color_hex)))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 12, 12)
        painter.end()
        return QtGui.QIcon(pixmap)

    def _refresh_instrument_status(self):
        """Update status icons on instrument menu actions."""
        connected_ids = self._get_connected_instrument_ids()
        for key, action in self._instrument_actions.items():
            item = self.instruments[key]
            idn = getattr(item, "IDN", None)
            target = getattr(item, "target", None)
            target_name = getattr(target, "__name__", "") if target else key
            adapter = getattr(item, "adapter", "")

            # Check by IDN first, then by "{ClassName}/{adapter}" pattern
            if idn and idn in connected_ids:
                connected = True
            elif any(target_name in cid for cid in connected_ids):
                connected = True
            elif f"{target_name}/{adapter}" in connected_ids:
                connected = True
            else:
                connected = False

            action.setIcon(self._make_status_icon(connected))

    def _shutdown_all_instruments(self):
        """Shut down all instruments across all procedure managers."""
        for cls in self.procedure_types.values():
            mgr = getattr(cls, "instruments", None)
            if isinstance(mgr, InstrumentManager):
                mgr.shutdown_all(remove_from_cache=True)
        self._refresh_instrument_status()
        self._update_laser_indicator()

    # ------------------------------------------------------------------
    # Laser safety indicator
    # ------------------------------------------------------------------

    def _is_laser_on(self) -> bool:
        """Return True if the TENMA laser channel reports output=True."""
        for cls in self.procedure_types.values():
            mgr = getattr(cls, "instruments", None)
            if not isinstance(mgr, InstrumentManager):
                continue
            for key, inst in mgr.instrument_dict.items():
                if "TENMALASER" in key or "tenma_laser" in key.lower():
                    return bool(getattr(inst, "output", False))
        return False

    def _update_laser_indicator(self):
        """Refresh laser status label colours."""
        if not hasattr(self, "_laser_indicator"):
            return
        c = theme_manager().colors
        if self._is_laser_on():
            self._laser_indicator.setText(" LASER ON ")
            self._laser_indicator.setStyleSheet(
                f"background-color: {c.red}; color: white; font-weight: bold;"
            )
        else:
            self._laser_indicator.setText(" LASER OFF ")
            self._laser_indicator.setStyleSheet(
                f"background-color: {c.comment}; color: {c.bg};"
            )

    # ------------------------------------------------------------------
    # MRU (recently used) procedures
    # ------------------------------------------------------------------

    def _record_recent(self, name: str):
        """Persist procedure name in QSettings MRU list (up to 5 entries)."""
        settings = QtCore.QSettings("LaserSetup", "LaserSetup")
        recent = settings.value("recent_procedures", []) or []
        if isinstance(recent, str):
            recent = [recent]
        recent = [n for n in recent if n != name][:4]
        settings.setValue("recent_procedures", [name] + recent)

    def _rebuild_recent_menu(self):
        """Repopulate the Recent submenu from QSettings."""
        if not hasattr(self, "_recent_menu"):
            return
        self._recent_menu.clear()
        settings = QtCore.QSettings("LaserSetup", "LaserSetup")
        recent = settings.value("recent_procedures", []) or []
        if isinstance(recent, str):
            recent = [recent]
        if not recent:
            none_action = QtGui.QAction("(none yet)", self)
            none_action.setEnabled(False)
            self._recent_menu.addAction(none_action)
            return
        for name in recent:
            cls = self.procedure_types.get(name)
            if cls is None:
                continue
            display = getattr(cls, "name", cls.__name__)
            action = QtGui.QAction(display, self)
            action.triggered.connect(partial(self.open_procedure, cls))
            self._recent_menu.addAction(action)

    # ------------------------------------------------------------------
    # Session context pre-fill
    # ------------------------------------------------------------------

    def _apply_session_context(self, window, cls: type[Procedure]):
        """Pre-fill matching parameter widgets in a newly opened ExperimentWindow."""
        if not hasattr(self, "_session_widget"):
            return
        if not issubclass(cls, ChipProcedure):
            return

        ctx = self._session_widget.get_context()
        inputs = getattr(window, "inputs", None)
        if inputs is None:
            return

        # Try parameter_widgets property (newer PyMeasure) then direct attr access
        param_widgets = getattr(inputs, "parameter_widgets", None)
        if param_widgets is None:
            param_widgets = {name: getattr(inputs, name, None) for name in ctx.keys()}

        for param_name, value in ctx.items():
            widget = param_widgets.get(param_name) if param_widgets else None
            if widget is None:
                continue
            try:
                _set_widget_value(widget, value)
            except Exception as exc:
                log.debug(f"Could not set {param_name}={value!r}: {exc}")

    # ------------------------------------------------------------------
    # Theme helpers
    # ------------------------------------------------------------------

    def _toggle_dark_mode(self):
        """Toggle between the light and dark variant of the current theme family."""
        tm = theme_manager()
        _PAIRS = {
            ThemeMode.DEFAULT_LIGHT:   ThemeMode.DEFAULT_DARK,
            ThemeMode.DEFAULT_DARK:    ThemeMode.DEFAULT_LIGHT,
            ThemeMode.LIGHT:           ThemeMode.DARK,
            ThemeMode.DARK:            ThemeMode.LIGHT,
            ThemeMode.DRACULA_LIGHT:   ThemeMode.DRACULA,
            ThemeMode.DRACULA:         ThemeMode.DRACULA_LIGHT,
            ThemeMode.CATPPUCCIN_LIGHT: ThemeMode.CATPPUCCIN,
            ThemeMode.CATPPUCCIN:      ThemeMode.CATPPUCCIN_LIGHT,
            ThemeMode.SOLARIZED_LIGHT: ThemeMode.SOLARIZED_DARK,
            ThemeMode.SOLARIZED_DARK:  ThemeMode.SOLARIZED_LIGHT,
            ThemeMode.GRUVBOX_LIGHT:   ThemeMode.GRUVBOX,
            ThemeMode.GRUVBOX:         ThemeMode.GRUVBOX_LIGHT,
            ThemeMode.MONOKAI_LIGHT:   ThemeMode.MONOKAI,
            ThemeMode.MONOKAI:         ThemeMode.MONOKAI_LIGHT,
        }
        new_mode = _PAIRS.get(tm.mode, ThemeMode.DEFAULT_LIGHT if tm.is_dark else ThemeMode.DEFAULT_DARK)
        tm.set_mode(new_mode)

    def _select_theme_family(self, light_mode: ThemeMode, dark_mode: ThemeMode):
        """Switch to a theme family, preserving the current light/dark polarity."""
        tm = theme_manager()
        tm.set_mode(dark_mode if tm.is_dark else light_mode)

    def _update_theme_family_checks(self, _colors):
        """Sync theme menu checkmarks after any theme change."""
        tm = theme_manager()
        for family_modes, act in self._theme_family_actions.items():
            act.setChecked(tm.mode in family_modes)

    def _app_zoom(self, factor: int):
        """Zoom the whole application font size."""
        font = QtWidgets.QApplication.instance().font()
        new_size = font.pointSize() + factor
        if 8 <= new_size <= 32:
            font.setPointSize(new_size)
            QtWidgets.QApplication.instance().setFont(font)

    def _toggle_fullscreen(self):
        """Toggle maximized state of the active window."""
        w = QtWidgets.QApplication.activeWindow() or self
        if w.isMaximized():
            w.showNormal()
        else:
            w.showMaximized()

    # ------------------------------------------------------------------
    # Window management
    # ------------------------------------------------------------------

    def open_sequence(self, cls: type[Sequence]):
        self.windows[cls] = SequenceWindow(cls, parent=self)
        self.windows[cls].show()

    def open_sequence_creator(self):
        """Opens the sequence creator window."""
        from .sequence_creator_window import SequenceCreatorWindow

        if "sequence_creator" not in self.windows:
            self.windows["sequence_creator"] = SequenceCreatorWindow(parent=self)
        self.windows["sequence_creator"].show()
        self.windows["sequence_creator"].raise_()

    def open_sequence_editor(self):
        """Opens a dialog to select a sequence to edit."""
        from .sequence_creator_window import SequenceCreatorWindow

        sequence_names = [
            name
            for name in self.sequences.keys()
            if name != "_types" and name in self.sequence_types
        ]

        if not sequence_names:
            QtWidgets.QMessageBox.information(
                self, "No Sequences", "No sequences available to edit."
            )
            return

        sequence_name, ok = QtWidgets.QInputDialog.getItem(
            self,
            "Edit Sequence",
            "Select a sequence to edit:",
            sequence_names,
            0,
            False,
        )

        if ok and sequence_name:
            if "sequence_creator" in self.windows:
                self.windows["sequence_creator"].close()
                del self.windows["sequence_creator"]

            self.windows["sequence_creator"] = SequenceCreatorWindow(
                parent=self, sequence_name=sequence_name
            )
            self.windows["sequence_creator"].show()
            self.windows["sequence_creator"].raise_()

    def open_procedure(self, cls: type[Procedure]):
        self._record_recent(cls.__name__)
        self.windows[cls] = ExperimentWindow(cls)
        self.windows[cls].show()
        self._apply_session_context(self.windows[cls], cls)
        self._update_laser_indicator()

    def run_script(self, f: Callable, **kwargs):
        """Runs the given script function in the main thread."""
        try:
            f(parent=self, **kwargs)
        except TypeError:
            f(**kwargs)
        self.suggest_reload()

    def open_widget(self, widget: QtWidgets.QWidget, title: str):
        """Opens a widget in a new window."""
        widget.setWindowFlags(QtCore.Qt.WindowType.Window)
        widget.setWindowTitle(title)
        widget.resize(*self.widget_size)
        widget.show()

    def suggest_reload(self):
        self.reload.setStyleSheet("background-color: red;")
        self.reload.setText("Reload to apply changes")
        self.reload.setShortcut("Ctrl+R")

    def error_dialog(self, message: str):
        error_dialog = QtWidgets.QMessageBox(parent=self)
        error_dialog.setText(
            f"An error occurred:\n{message}\nPlease reload the program."
        )
        error_dialog.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        self.open_widget(error_dialog, "Error")
        error_dialog.exec()
        self.reload.click()

    def select_from_list(
        self, title: str, items: list[str], label: str = ""
    ) -> str | None:
        item, ok = QtWidgets.QInputDialog.getItem(self, title, label, items, 0, False)
        if ok:
            return item
        return None

    def question_box(self, title: str, text: str) -> bool:
        MessageBox = QtWidgets.QMessageBox
        buttons = MessageBox.StandardButton.Yes | MessageBox.StandardButton.No
        reply = MessageBox.question(self, title, text, buttons)
        return reply == MessageBox.StandardButton.Yes

    def text_window(self, title: str, text: str):
        """Displays a text window with the given title and text."""
        text_edit = QtWidgets.QTextEdit(parent=self)
        text_edit.setReadOnly(True)
        text_edit.setMarkdown(text)
        self.open_widget(text_edit, title)

    def open_camera(self):
        """Opens the camera widget."""
        self.camera_widget = CameraWidget(parent=self)
        self.open_widget(self.camera_widget, "Cameras")

    def open_terminal(self):
        """Opens an interactive console. Loads common modules and instruments."""
        from ...instruments import FakeAdapter  # noqa: F401

        instruments = InstrumentManager()

        header = (
            "Interactive console. To instantiate an instrument, use the "
            "'instruments.connect' method.\n"
        )
        if "-d" in sys.argv or "--debug" in sys.argv:
            header += (
                "\nDebug mode (the InstrumentManager will use a FakeAdapter if "
                "it can't connect to an instrument).\n"
            )
        self.console_widget = ConsoleWidget(
            namespace=globals() | locals(), text=header, parent=self
        )
        self.open_widget(self.console_widget, "Console")

    def open_database(self, db_name: str):
        db_path = Path(CONFIG.Dir.data_dir) / db_name
        if not db_path.exists():
            ans = self.question_box(
                "Database not found",
                f"Database {db_path} not found. Create new database?",
            )
            if not ans:
                return
            parameters_to_db.create_db(parent=self)

        self.db_widget = SQLiteWidget(db_path.as_posix(), parent=self)
        self.open_widget(self.db_widget, db_name)

    def _open_readme(self):
        """Open the README file as a text window."""
        try:
            text = self.readme_path.read_text()
        except Exception:
            text = f"Could not read {self.readme_path}"
        self.text_window("README", text)

    def closeEvent(self, event):
        """Ensures all running threads are properly stopped."""
        for child in self.findChildren(QtCore.QThread):
            if child.isRunning():
                child.quit()
                child.wait()
        super().closeEvent(event)
