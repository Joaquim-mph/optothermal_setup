import logging
import os
import sys
from functools import partial
from importlib.metadata import metadata
from pathlib import Path
from typing import Callable

from pymeasure.experiment import Procedure

from ...cli import parameters_to_db
from ...config import ConfigHandler, CONFIG, configurable
from ...config.defaults import ProceduresConfig, SequencesConfig, ScriptsConfig, InstrumentConfig
from ...instruments import InstrumentManager
from ...procedures import Sequence
from ...utils import get_status_message
from ..Qt import ConsoleWidget, QtCore, QtGui, QtWidgets, Worker
from ..theme import manager as theme_manager, get_procedure_button_style
from ..widgets import ConfigWidget, LogsWidget, SQLiteWidget
from ..widgets.camera_widget import CameraWidget
from .experiment_window import ExperimentWindow
from .sequence_window import SequenceWindow

log = logging.getLogger(__name__)


@configurable('Qt.MainWindow', on_definition=False, subclasses=False)
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
        title: str = 'Main Window',
        size: tuple[int, int] = (640, 480),
        widget_size: tuple[int, int] = (640, 480),
        icon: str | None = None,
        readme_file: str | Path = 'README.md',
        **kwargs
    ):
        """Initializes the main window with the given procedures, sequences, and scripts.

        :param procedures: List of procedures to display in the Procedures menu.
        :param sequences: Dictionary with the sequences to display in the Sequences menu.
        :param scripts: List of scripts to display in the Scripts menu.
        :param title: Title of the window.
        :param size: Size of the window.
        :param widget_size: Size of the widgets.
        :param icon: Icon of the window.
        :param readme_file: Path to the README file.
        :param kwargs: Additional arguments for the QMainWindow.
        """
        self.widget_size = widget_size
        self.readme_path = Path(readme_file)
        self.procedures = procedures
        self.sequences = sequences
        self.scripts = scripts
        self.instruments = instruments
        self.config_handler = ConfigHandler(parent=self, config=CONFIG)

        super().__init__(**kwargs)
        self.setWindowTitle(title)
        self.setWindowIcon(QtGui.QIcon(icon) if icon else self.style().standardIcon(
            QtWidgets.QStyle.StandardPixmap.SP_TitleBarMenuButton
        ))
        self.resize(*size)
        self.setCentralWidget(QtWidgets.QWidget(parent=self))

        self.windows: dict[
            type[Procedure] | type[Sequence] | str, QtWidgets.QMainWindow
        ] = {}
        self._layout = QtWidgets.QGridLayout(self.centralWidget())

        # Store procedure and sequence types before they're popped in create_menu_bar
        self.procedure_types: dict[str, type[Procedure]] = self.procedures.get('_types', {})
        self.sequence_types: dict[str, type[Sequence]] = self.sequences.get('_types', {})

        self.menu_bar = self.create_menu_bar()
        self.status_bar = self.statusBar()

        self._thread = QtCore.QThread(parent=self)
        self._worker = Worker(get_status_message, self._thread)
        self._worker.finished.connect(lambda msg: self.status_bar.showMessage(msg, 3000))
        self._thread.start()

        # Main procedure buttons
        self.create_main_buttons()

        # Reload window button
        self.reload = QtWidgets.QPushButton('Reload')
        self.reload.clicked.connect(
            lambda: os.execl(sys.executable, sys.executable, '-m', 'laser_setup', *sys.argv[1:])
        )   # TODO: fix bug where the terminal misbehaves after reload
        self.reload.setShortcut('Ctrl+R')
        self.status_bar.addPermanentWidget(self.reload)

    def create_main_buttons(self):
        """Creates the main buttons for the most common procedures."""
        # Use stored procedure types
        procedure_types = self.procedure_types

        # Define main procedures to show as buttons
        main_procedures = ['IVg', 'It', 'IV', 'LaserCalibration']

        # Create a grid for buttons
        self._button_widget = QtWidgets.QWidget(parent=self)
        button_layout = QtWidgets.QGridLayout(self._button_widget)
        button_layout.setSpacing(15)
        button_layout.setContentsMargins(50, 50, 50, 30)

        # Store button references for theme updates
        self._proc_buttons: dict[str, QtWidgets.QPushButton] = {}

        # Create buttons in a 2x2 grid
        for i, proc_name in enumerate(main_procedures):
            if proc_name not in procedure_types:
                continue

            cls = procedure_types[proc_name]
            name = getattr(cls, 'name', cls.__name__)

            # Create button
            button = QtWidgets.QPushButton(name, parent=self._button_widget)
            button.setMinimumSize(180, 80)
            button.setMaximumSize(250, 100)
            button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            button.setStyleSheet(get_procedure_button_style(proc_name))
            button.clicked.connect(partial(self.open_procedure, cls))

            # Store reference for theme updates
            self._proc_buttons[proc_name] = button

            # Add to grid (2 columns)
            row = i // 2
            col = i % 2
            button_layout.addWidget(button, row, col)

        # Add a label at the bottom
        self._info_label = QtWidgets.QLabel(
            "Select a measurement procedure to begin\n"
            "Additional options available in the menu bar",
            parent=self._button_widget
        )
        self._info_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._apply_info_label_style()
        button_layout.addWidget(self._info_label, (len(main_procedures) + 1) // 2, 0, 1, 2)

        # Connect to theme changes
        theme_manager().theme_changed.connect(self._on_theme_changed)

        self._layout.addWidget(self._button_widget)

    def _apply_info_label_style(self):
        """Apply styling to the info label based on current theme."""
        c = theme_manager().colors
        self._info_label.setStyleSheet(f"""
            font-size: 13px;
            color: {c.fg_secondary};
            margin-top: 25px;
            font-weight: 500;
        """)

    def _on_theme_changed(self, _colors=None):
        """Handle theme changes by updating button styles."""
        for proc_name, button in self._proc_buttons.items():
            button.setStyleSheet(get_procedure_button_style(proc_name))
        self._apply_info_label_style()

    def open_sequence(self, cls: type[Sequence]):
        self.windows[cls] = SequenceWindow(cls, parent=self)
        self.windows[cls].show()

    def open_sequence_creator(self):
        """Opens the sequence creator window."""
        from .sequence_creator_window import SequenceCreatorWindow
        if 'sequence_creator' not in self.windows:
            self.windows['sequence_creator'] = SequenceCreatorWindow(parent=self)
        self.windows['sequence_creator'].show()
        self.windows['sequence_creator'].raise_()

    def open_sequence_editor(self):
        """Opens a dialog to select a sequence to edit."""
        from .sequence_creator_window import SequenceCreatorWindow

        # Get list of available sequences (excluding _types)
        sequence_names = [
            name for name in self.sequences.keys()
            if name != '_types' and name in self.sequence_types
        ]

        if not sequence_names:
            QtWidgets.QMessageBox.information(
                self,
                "No Sequences",
                "No sequences available to edit."
            )
            return

        # Show selection dialog
        sequence_name, ok = QtWidgets.QInputDialog.getItem(
            self,
            "Edit Sequence",
            "Select a sequence to edit:",
            sequence_names,
            0,  # Default selection
            False  # Not editable
        )

        if ok and sequence_name:
            # Close existing creator window if open
            if 'sequence_creator' in self.windows:
                self.windows['sequence_creator'].close()
                del self.windows['sequence_creator']

            # Open creator with sequence loaded for editing
            self.windows['sequence_creator'] = SequenceCreatorWindow(
                parent=self,
                sequence_name=sequence_name
            )
            self.windows['sequence_creator'].show()
            self.windows['sequence_creator'].raise_()

    def open_procedure(self, cls: type[Procedure]):
        self.windows[cls] = ExperimentWindow(cls)
        self.windows[cls].show()

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
        self.reload.setStyleSheet('background-color: red;')
        self.reload.setText('Reload to apply changes')
        self.reload.setShortcut('Ctrl+R')

    def error_dialog(self, message: str):
        error_dialog = QtWidgets.QMessageBox(parent=self)
        error_dialog.setText(f"An error occurred:\n{message}\nPlease reload the program.")
        error_dialog.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        self.open_widget(error_dialog, 'Error')
        error_dialog.exec()
        self.reload.click()

    def select_from_list(self, title: str, items: list[str], label: str = '') -> str | None:
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
        """Displays a text window with the given title and text. adds a scroll bar"""
        text_edit = QtWidgets.QTextEdit(parent=self)
        text_edit.setReadOnly(True)
        text_edit.setMarkdown(text)
        self.open_widget(text_edit, title)

    def open_camera(self):
        """Opens the camera widget."""
        self.camera_widget = CameraWidget(parent=self)
        self.open_widget(self.camera_widget, 'Cameras')

    def open_terminal(self):
        """Opens an interactive console. Loads common modules and instruments."""
        from ...instruments import FakeAdapter  # noqa: F401
        instruments = InstrumentManager()

        header = (
            "Interactive console. To instantiate an instrument, use the "
            "'instruments.connect' method.\n"
        )
        if '-d' in sys.argv or '--debug' in sys.argv:
            header += (
                "\nDebug mode (the InstrumentManager will use a FakeAdapter if "
                "it can't connect to an instrument).\n"
            )
        self.console_widget = ConsoleWidget(
            namespace=globals() | locals(), text=header, parent=self
        )
        self.open_widget(self.console_widget, 'Console')

    def open_database(self, db_name: str):
        db_path = Path(CONFIG.Dir.data_dir) / db_name
        if not db_path.exists():
            ans = self.question_box(
                'Database not found', f'Database {db_path} not found. Create new database?'
            )
            if not ans:
                return
            parameters_to_db.create_db(parent=self)

        self.db_widget = SQLiteWidget(db_path.as_posix(), parent=self)
        self.open_widget(self.db_widget, db_name)

    def closeEvent(self, event):
        """Ensures all running threads are properly stopped."""
        for child in self.findChildren(QtCore.QThread):
            if child.isRunning():
                child.quit()
                child.wait()
        super().closeEvent(event)

    # ═══════════════════════════════════════════════════════════════════
    # Processing Menu Handlers
    # ═══════════════════════════════════════════════════════════════════

    def _open_pipeline_widget(self):
        """Open the data pipeline widget."""
        from ..widgets.processing import PipelineWidget
        if 'pipeline' not in self.windows:
            self.windows['pipeline'] = PipelineWidget(parent=self)
        self.open_widget(self.windows['pipeline'], 'Data Pipeline')

    def _open_history_browser(self):
        """Open the chip history browser widget."""
        from ..widgets.processing import HistoryBrowserWidget
        if 'history_browser' not in self.windows:
            self.windows['history_browser'] = HistoryBrowserWidget(parent=self)
        self.open_widget(self.windows['history_browser'], 'Chip History Browser')

    def _open_plot_builder(self, plot_type: str = None):
        """Open the plot builder widget."""
        from ..widgets.processing import PlotBuilderWidget
        if 'plot_builder' not in self.windows:
            self.windows['plot_builder'] = PlotBuilderWidget(parent=self)
        if plot_type:
            idx = self.windows['plot_builder'].combo_plot_type.findText(
                plot_type, QtCore.Qt.MatchFlag.MatchContains
            )
            if idx >= 0:
                self.windows['plot_builder'].combo_plot_type.setCurrentIndex(idx)
        self.open_widget(self.windows['plot_builder'], 'Plot Builder')

    def _open_batch_plot(self):
        """Open the batch plot widget."""
        from ..widgets.processing import BatchPlotWidget
        if 'batch_plot' not in self.windows:
            self.windows['batch_plot'] = BatchPlotWidget(parent=self)
        self.open_widget(self.windows['batch_plot'], 'Batch Plot')

    def _open_cache_stats(self):
        """Open the cache statistics widget."""
        from ..widgets.processing import CacheStatsWidget
        if 'cache_stats' not in self.windows:
            self.windows['cache_stats'] = CacheStatsWidget(parent=self)
        self.open_widget(self.windows['cache_stats'], 'Cache Statistics')

    def _run_build_histories(self):
        """Run build histories operation directly."""
        self._open_pipeline_widget()
        # Trigger the build histories button
        if 'pipeline' in self.windows:
            self.windows['pipeline']._run_build_histories()

    def _run_derive_metrics(self):
        """Run derive metrics operation directly."""
        self._open_pipeline_widget()
        # Trigger the derive metrics button
        if 'pipeline' in self.windows:
            self.windows['pipeline']._run_derive_metrics()

    def _export_history(self):
        """Export history via the history browser."""
        self._open_history_browser()
        # The browser has an export button

    def _enrich_history(self):
        """Enrich chip histories with derived metrics."""
        from ..widgets.processing import PipelineWidget
        if 'pipeline' not in self.windows:
            self.windows['pipeline'] = PipelineWidget(parent=self)

        # Show info dialog about enrichment
        QtWidgets.QMessageBox.information(
            self,
            'Enrich History',
            'To enrich chip histories with derived metrics:\n\n'
            '1. Open the Pipeline widget\n'
            '2. Run "Derive Metrics" to extract metrics\n'
            '3. Use the CLI command: optothermal-process enrich-history <chip>\n\n'
            'Enriched histories will be saved to:\n'
            'data/03_derived/chip_histories_enriched/'
        )

    def _validate_manifest(self):
        """Validate the manifest file."""
        try:
            from pathlib import Path
            import polars as pl

            # Find manifest file
            current = Path.cwd()
            manifest_path = None
            for parent in [current] + list(current.parents):
                check_path = parent / "data" / "02_stage" / "raw_measurements" / "_manifest" / "manifest.parquet"
                if check_path.exists():
                    manifest_path = check_path
                    break

            if manifest_path is None:
                QtWidgets.QMessageBox.warning(
                    self, 'Manifest Not Found',
                    'Could not find manifest.parquet file.\n\n'
                    'Expected location: data/02_stage/raw_measurements/_manifest/manifest.parquet\n\n'
                    'Run the staging pipeline first to create the manifest.'
                )
                return

            # Load and validate
            df = pl.read_parquet(manifest_path)
            stats = {
                'total_rows': len(df),
                'procedures': df['proc'].n_unique() if 'proc' in df.columns else 0,
                'chips': df['chip_number'].n_unique() if 'chip_number' in df.columns else 0,
            }

            # Count by status
            if 'status' in df.columns:
                status_counts = df.group_by('status').count()
                for row in status_counts.iter_rows(named=True):
                    stats[f'status_{row["status"]}'] = row['count']

            # Build message
            msg = f"Manifest Validation Results\n{'='*40}\n\n"
            msg += f"Location: {manifest_path}\n\n"
            msg += f"Total records: {stats['total_rows']}\n"
            msg += f"Unique procedures: {stats['procedures']}\n"
            msg += f"Unique chips: {stats['chips']}\n"

            if 'status_ok' in stats:
                msg += f"\nStatus OK: {stats.get('status_ok', 0)}"
            if 'status_skipped' in stats:
                msg += f"\nStatus Skipped: {stats.get('status_skipped', 0)}"
            if 'status_error' in stats:
                msg += f"\nStatus Error: {stats.get('status_error', 0)}"

            QtWidgets.QMessageBox.information(self, 'Manifest Validation', msg)

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, 'Validation Error',
                f'Failed to validate manifest:\n\n{str(e)}'
            )

    def create_menu_bar(self) -> QtWidgets.QMenuBar:
        """Creates the menu bar with the following options:
        - Procedures
        - Sequences
        - Scripts
        - View
        - Config
        - Help

        This method can be overridden to add more options.

        :return: The menu bar.
        """
        menu = self.menuBar()

        procedure_menu = menu.addMenu('&Procedures')
        procedure_menu.setToolTipsVisible(True)
        self.procedures.pop('_types', None)  # Remove _types from dict
        for key, item in self.procedures.items():
            cls = self.procedure_types[key]
            name = getattr(cls, 'name', cls.__name__)
            action = QtGui.QAction(name, self)
            doc = cls.__doc__.replace('    ', '').strip()
            action.triggered.connect(partial(self.open_procedure, cls))
            action.setToolTip(doc)
            action.setStatusTip(doc)
            action.setShortcut(f'Ctrl+{len(procedure_menu.actions()) + 1}')
            procedure_menu.addAction(action)

        sequence_menu = menu.addMenu('Se&quences')
        sequence_menu.setToolTipsVisible(True)
        self.sequences.pop('_types', None)  # Remove _types from dict
        for key, item in self.sequences.items():
            # Skip sequences not registered in _types (e.g., manually added)
            if key not in self.sequence_types:
                log.warning(f"Sequence '{key}' not found in _types, skipping menu entry")
                continue
            cls = self.sequence_types[key]
            name = getattr(item, 'name', cls.__name__)
            action = QtGui.QAction(key, self)
            doc = getattr(item, 'description', cls.__doc__.replace('    ', '').strip())
            action.triggered.connect(partial(self.open_sequence, cls))
            action.setToolTip(doc)
            action.setStatusTip(doc)
            action.setShortcut(f'Ctrl+Shift+{len(sequence_menu.actions()) + 1}')
            sequence_menu.addAction(action)

        # Add separator and sequence creator/editor
        sequence_menu.addSeparator()
        new_sequence_action = QtGui.QAction('New Sequence...', self)
        new_sequence_action.triggered.connect(self.open_sequence_creator)
        new_sequence_action.setShortcut('Ctrl+N')
        new_sequence_action.setToolTip('Create a new procedure sequence')
        new_sequence_action.setStatusTip('Create a new procedure sequence')
        sequence_menu.addAction(new_sequence_action)

        edit_sequence_action = QtGui.QAction('Edit Sequence...', self)
        edit_sequence_action.triggered.connect(self.open_sequence_editor)
        edit_sequence_action.setShortcut('Ctrl+E')
        edit_sequence_action.setToolTip('Edit an existing procedure sequence')
        edit_sequence_action.setStatusTip('Edit an existing procedure sequence')
        sequence_menu.addAction(edit_sequence_action)

        script_menu = menu.addMenu('&Scripts')
        script_menu.setToolTipsVisible(True)
        for key, item in self.scripts.items():
            func: Callable = item.target
            action = QtGui.QAction(item.name or func.__doc__, self)
            doc = sys.modules[func.__module__].__doc__ or ''
            doc = doc.replace('    ', '').strip()
            action.triggered.connect(partial(self.run_script, func, **item.kwargs))
            action.setToolTip(doc)
            action.setStatusTip(doc)
            action.setShortcut(f'Alt+{len(script_menu.actions()) + 1}')
            script_menu.addAction(action)

        view_menu = menu.addMenu('&View')
        db_action = view_menu.addAction(
            'Parameter Database', partial(self.open_database, CONFIG.Dir.database)
        )
        db_action.setShortcut('Ctrl+Shift+D')

        video_action = view_menu.addAction('Cameras', self.open_camera)
        video_action.setShortcut('Ctrl+Shift+C')

        self.log_widget = LogsWidget(parent=self)
        self.log_widget.setWindowFlags(QtCore.Qt.WindowType.Dialog)

        self.log = logging.getLogger('laser_setup')
        self.log.addHandler(self.log_widget.handler)

        log_action = view_menu.addAction('Logs', partial(self.open_widget, self.log_widget, 'Logs'))
        log_action.setShortcut('Ctrl+Shift+L')

        console_action = view_menu.addAction('Terminal', self.open_terminal)
        console_action.setShortcut('Ctrl+Shift+T')

        config_menu = menu.addMenu('&Config')
        self.config_widget = ConfigWidget(parent=self)
        self.config_widget.setWindowFlags(QtCore.Qt.WindowType.Dialog)
        config_menu.addAction(
            'Edit config', partial(self.open_widget, self.config_widget, 'Config')
        )
        config_menu.addAction('Load config', self.config_handler.import_config)
        config_menu.addAction('Open config file', self.config_handler.edit_config)

        # Help
        help_menu = menu.addMenu('&Help')
        help_menu.setToolTipsVisible(True)

        instrument_help = help_menu.addMenu('Instruments')
        unique_instruments = {i.target for i in self.instruments.values()}
        for cls in unique_instruments:
            name = getattr(cls, 'name', cls.__name__)
            action = QtGui.QAction(name, self)
            action.triggered.connect(partial(
                self.text_window, name, InstrumentManager.help(cls, return_str=True)
            ))
            instrument_help.addAction(action)

        return menu
