import logging
import os
import time

import pyqtgraph as pg
import pyqtgraph.exporters
from pymeasure.display.curves import ResultsCurve
from pymeasure.display.widgets import PlotFrame, PlotWidget
from pymeasure.display.widgets.dock_widget import DockWidget
from pymeasure.display.windows import ManagedWindowBase
from pymeasure.experiment import Procedure, Results, unique_filename

from ...config import CONFIG, configurable
from ...procedures import BaseProcedure
from ..Qt import QtCore, QtGui, QtWidgets
from ..theme import manager as theme_manager
from ..theme.colors import ThemeColors
from ..widgets import LogWidget, TextWidget

pg.setConfigOptions(antialias=True)


def _apply_plot_style(plot_frame: PlotFrame, colors: ThemeColors) -> None:
    """Apply themed styling to a pyqtgraph PlotFrame."""
    bg, fg = colors.bg, colors.fg
    plot_frame.setStyleSheet(f'background-color: {bg};')
    plot_frame.plot_widget.setBackground(bg)
    axis_pen = pg.mkPen(color=fg, width=1)
    text_pen = pg.mkPen(color=fg)
    for axis_name in ('bottom', 'left'):
        axis = plot_frame.plot.getAxis(axis_name)
        axis.setPen(axis_pen)
        axis.setTextPen(text_pen)
        axis.enableAutoSIPrefix(True)
    plot_frame.plot.showGrid(x=False, y=False)

log = logging.getLogger(__name__)


@configurable('Qt.ExperimentWindow', on_definition=False, subclasses=False)
class ExperimentWindow(ManagedWindowBase):
    """The main window for an experiment. It is used to display a
    `pymeasure.experiment.Procedure`, and allows for the experiment to be run
    from the GUI, by queueing it in the manager. It also allows for existing
    data to be loaded and displayed.
    """
    def __init__(
        self,
        cls: type[Procedure],
        title: str = '',
        inputs_in_scrollarea: bool = True,
        enable_file_input: bool = False,
        dock_plot_number: int = 2,
        icon: str | None = None,
        info_file: str | None = None,
        inputs: list[str] | None = None,
        displays: list[str] | None = None,
        sequencer: bool = False,
        sequencer_inputs: list[str] | None = None,
        sequence_file: str | None = None,
        **kwargs
    ):
        self.cls = cls

        colors = theme_manager().colors
        PlotFrame.LABEL_STYLE['color'] = colors.fg

        if not hasattr(cls, 'DATA_COLUMNS') or len(cls.DATA_COLUMNS) < 2:
            raise AttributeError(
                f"Procedure {cls.__name__} must define DATA_COLUMNS with at least 2 columns."
            )

        self.x_axis = cls.DATA_COLUMNS[0]
        self.y_axis = cls.DATA_COLUMNS[1]
        self.log_widget = LogWidget("Experiment Log")
        self.plot_widget = PlotWidget("Results Graph", cls.DATA_COLUMNS, self.x_axis,
                                      self.y_axis)
        self.plot_widget.setMinimumSize(100, 200)

        self.text_widget = TextWidget('Information', file=info_file)
        self.dock_widget = DockWidget(
            'Dock', cls,
            x_axis_labels=[self.x_axis,],
            y_axis_labels=cls.DATA_COLUMNS[1:dock_plot_number+1],
        )
        for pw in (self.plot_widget, *self.dock_widget.plot_frames):
            _apply_plot_style(pw.plot_frame, colors)

        widget_list = (self.plot_widget, self.log_widget, self.text_widget, self.dock_widget)

        super().__init__(
            procedure_class=cls,
            widget_list=widget_list,
            inputs=inputs or getattr(cls, 'INPUTS', []),
            displays=displays or getattr(cls, 'INPUTS', []),
            inputs_in_scrollarea=inputs_in_scrollarea,
            enable_file_input=enable_file_input,
            sequencer=sequencer or hasattr(cls, 'SEQUENCER_INPUTS'),
            sequencer_inputs=sequencer_inputs or getattr(cls, 'SEQUENCER_INPUTS', None),
            sequence_file=sequence_file or getattr(cls, 'SEQUENCE_FILE', None),
            **kwargs
        )
        _splitter = self.tabs.parent()
        if isinstance(_splitter, QtWidgets.QSplitter):
            _splitter.setSizes([600, 150])

        self.setWindowTitle(title or getattr(cls, 'name', cls.__name__))
        self.setWindowIcon(
            QtGui.QIcon(icon) if icon else self.style().standardIcon(
                QtWidgets.QStyle.StandardPixmap.SP_TitleBarMenuButton
            )
        )
        # Add a shutdown all button if the procedure is a BaseProcedure
        if issubclass(self.procedure_class, BaseProcedure):
            self.shutdown_button = QtWidgets.QPushButton('&Shutdown', self)
            self.shutdown_button.clicked.connect(
                lambda: self.procedure_class.instruments.shutdown_all(remove_from_cache=True)
            )
            self.shutdown_button.setToolTip('Shutdown all instruments')
            self.abort_button.parent().layout().children()[0].insertWidget(2, self.shutdown_button)

        self.abort_button.setText('&Abort')
        self.queue_button.setText('&Queue')


        # Keyboard shortcuts
        QtGui.QShortcut(
            QtGui.QKeySequence("Ctrl+Return"), self
        ).activated.connect(self.queue_button.click)
        QtGui.QShortcut(
            QtGui.QKeySequence("Escape"), self
        ).activated.connect(self._shortcut_abort)
        if issubclass(self.procedure_class, BaseProcedure):
            QtGui.QShortcut(
                QtGui.QKeySequence("Ctrl+Shift+K"), self
            ).activated.connect(self.shutdown_button.click)
        QtGui.QShortcut(
            QtGui.QKeySequence("Ctrl+G"), self
        ).activated.connect(self._toggle_grid)
        QtGui.QShortcut(
            QtGui.QKeySequence("Ctrl+B"), self
        ).activated.connect(self._toggle_browser_shortcut)
        QtGui.QShortcut(
            QtGui.QKeySequence("Ctrl+Shift+S"), self
        ).activated.connect(self._save_plot)

        # Status bar with live experiment state
        self._status_bar = self.statusBar()

        self._run_progress_bar = QtWidgets.QProgressBar()
        self._run_progress_bar.setRange(0, 100)
        self._run_progress_bar.setFixedHeight(16)
        self._run_progress_bar.setTextVisible(True)
        self._run_progress_bar.hide()
        self._status_bar.addWidget(self._run_progress_bar, 1)

        self._elapsed_timer = QtCore.QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._on_elapsed_tick)

        self._browser_toggle = QtWidgets.QToolButton()
        self._browser_toggle.setText(' Run Browser')
        self._browser_toggle.setArrowType(QtCore.Qt.ArrowType.DownArrow)
        self._browser_toggle.setToolButtonStyle(
            QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self._browser_toggle.setCheckable(True)
        self._browser_toggle.setChecked(True)
        self._browser_toggle.setStyleSheet('QToolButton { border: none; padding: 2px 6px; }')
        self._browser_toggle.setToolTip('Show/hide run browser (Ctrl+B)')
        self._browser_toggle.toggled.connect(self._toggle_browser)
        self._status_bar.addPermanentWidget(self._browser_toggle)

        self._save_plot_btn = QtWidgets.QToolButton()
        self._save_plot_btn.setText('Save Plot')
        self._save_plot_btn.setStyleSheet('QToolButton { border: none; padding: 2px 6px; }')
        self._save_plot_btn.setToolTip('Save current plot as image (Ctrl+Shift+S)')
        self._save_plot_btn.clicked.connect(self._save_plot)
        self._save_plot_btn.hide()
        self._status_bar.addPermanentWidget(self._save_plot_btn)

        self._elapsed_label = QtWidgets.QLabel()
        self._elapsed_label.setStyleSheet("padding: 2px 6px;")
        self._elapsed_label.hide()
        self._status_bar.addPermanentWidget(self._elapsed_label)

        self._open_folder_btn = QtWidgets.QToolButton()
        self._open_folder_btn.setIcon(
            self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DirOpenIcon)
        )
        self._open_folder_btn.setToolTip('Open folder where last experiment was saved')
        self._open_folder_btn.setStyleSheet('QToolButton { border: none; padding: 2px 6px; }')
        self._open_folder_btn.clicked.connect(self._reveal_last_folder)
        self._open_folder_btn.hide()
        self._status_bar.addPermanentWidget(self._open_folder_btn)

        self.manager.queued.connect(self._on_exp_queued)
        self.manager.running.connect(self._on_exp_running)
        self.manager.finished.connect(self._on_exp_finished)
        self.manager.abort_returned.connect(self._on_exp_aborted)
        self.manager.failed.connect(self._on_exp_failed)

        # Rearrange left panel: inputs fill space; estimator + sequencer as collapsible sections
        _inputs_dock = _seq_dock = _est_dock = None
        for dock in self.findChildren(QtWidgets.QDockWidget):
            if self.use_sequencer and dock.widget() is self.sequencer:
                _seq_dock = dock
            elif self.use_estimator and dock.widget() is self.estimator:
                _est_dock = dock
            elif dock.windowTitle() == 'Input Parameters':
                _inputs_dock = dock

        if _inputs_dock:
            container = _inputs_dock.widget()
            layout = container.layout()

            # Let the inputs widget expand to fill all available vertical space
            layout.setStretch(0, 1)

            # Remove trailing stretch
            last = layout.itemAt(layout.count() - 1)
            if last and last.spacerItem():
                layout.takeAt(layout.count() - 1)

            if _est_dock:
                self._est_toggle = QtWidgets.QToolButton(container)
                self._est_toggle.setText(' Estimator')
                self._est_toggle.setArrowType(QtCore.Qt.ArrowType.RightArrow)
                self._est_toggle.setToolButtonStyle(
                    QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon
                )
                self._est_toggle.setCheckable(True)
                self._est_toggle.setSizePolicy(
                    QtWidgets.QSizePolicy.Policy.Expanding,
                    QtWidgets.QSizePolicy.Policy.Fixed,
                )
                self._est_toggle.setStyleSheet('QToolButton { border: none; padding: 4px 2px; }')
                self._est_toggle.toggled.connect(self._toggle_estimator)

                _est_dock.setWidget(None)
                self.estimator.setParent(container)

                layout.addWidget(self._est_toggle)
                layout.addWidget(self.estimator)

                self.removeDockWidget(_est_dock)
                _est_dock.deleteLater()

                self._est_toggle.setChecked(True)  # fires _toggle_estimator → show

            if _seq_dock:
                self._seq_toggle = QtWidgets.QToolButton(container)
                self._seq_toggle.setText(' Sequencer')
                self._seq_toggle.setArrowType(QtCore.Qt.ArrowType.RightArrow)
                self._seq_toggle.setToolButtonStyle(
                    QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon
                )
                self._seq_toggle.setCheckable(True)
                self._seq_toggle.setChecked(False)
                self._seq_toggle.setSizePolicy(
                    QtWidgets.QSizePolicy.Policy.Expanding,
                    QtWidgets.QSizePolicy.Policy.Fixed,
                )
                self._seq_toggle.setStyleSheet('QToolButton { border: none; padding: 4px 2px; }')
                self._seq_toggle.toggled.connect(self._toggle_sequencer)

                _seq_dock.setWidget(None)
                self.sequencer.setParent(container)
                self.sequencer.hide()

                layout.addWidget(self._seq_toggle)
                layout.addWidget(self.sequencer)

                self.removeDockWidget(_seq_dock)
                _seq_dock.deleteLater()

        self.browser_widget.browser.measured_quantities.update([self.x_axis, self.y_axis])


        self.log = logging.getLogger("laser_setup")
        self.log.addHandler(self.log_widget.handler)
        self.log.debug(f"{type(self).__name__} connected to logging")

        theme_manager().theme_changed.connect(self._on_theme_changed)

        # Ensure continuous auto-range is on from the start.  Counteracts any
        # stale zoom/pan state that DockWidget._layout() may have restored from
        # a saved dock-layout JSON (Bug 4) and ensures the first measurement
        # auto-ranges without the user having to press "View All" first.
        for pw in (self.plot_widget, *self.dock_widget.plot_frames):
            pw.plot_frame.plot.vb.enableAutoRange()

    def _on_theme_changed(self, colors: ThemeColors) -> None:
        PlotFrame.LABEL_STYLE['color'] = colors.fg
        for pw in (self.plot_widget, *self.dock_widget.plot_frames):
            _apply_plot_style(pw.plot_frame, colors)

    def _toggle_estimator(self, checked: bool) -> None:
        self.estimator.setVisible(checked)
        self._est_toggle.setArrowType(
            QtCore.Qt.ArrowType.DownArrow if checked else QtCore.Qt.ArrowType.RightArrow
        )

    def _toggle_sequencer(self, checked: bool) -> None:
        self.sequencer.setVisible(checked)
        self._seq_toggle.setArrowType(
            QtCore.Qt.ArrowType.DownArrow if checked else QtCore.Qt.ArrowType.RightArrow
        )

    def _on_exp_queued(self, experiment):
        name = getattr(type(experiment.procedure), 'name', type(experiment.procedure).__name__)
        try:
            n = sum(
                1 for e in self.manager.experiments
                if e.procedure.status == Procedure.QUEUED
            )
        except Exception:
            n = 1
        suffix = f" (+{n - 1} more)" if n > 1 else ""
        self._run_progress_bar.setFormat(f"Queued: {name}{suffix}")
        self._run_progress_bar.setValue(0)
        self._run_progress_bar.show()
        self._save_plot_btn.show()

    def _on_exp_running(self, experiment):
        name = getattr(type(experiment.procedure), 'name', type(experiment.procedure).__name__)
        self._run_progress_bar.setFormat(f"Running: {name}  %p%")
        self._run_progress_bar.setValue(0)
        self._run_progress_bar.show()
        monitor = getattr(self.manager, '_monitor', None)
        if monitor is not None:
            monitor.progress.connect(self._on_progress)
        self._run_start_time = time.monotonic()
        self._elapsed_label.setText("00m 00s")
        self._elapsed_label.show()
        self._elapsed_timer.start()

    def _on_elapsed_tick(self) -> None:
        elapsed = int(time.monotonic() - self._run_start_time)
        m, s = divmod(elapsed, 60)
        self._elapsed_label.setText(f"{m:02d}m {s:02d}s")

    def _shortcut_abort(self) -> None:
        if self.manager.is_running():
            self.abort_button.click()

    def _toggle_grid(self) -> None:
        self._grid_on = not getattr(self, '_grid_on', False)
        for pw in (self.plot_widget, *self.dock_widget.plot_frames):
            pw.plot_frame.plot.showGrid(x=self._grid_on, y=self._grid_on)

    def _toggle_browser(self, checked: bool) -> None:
        self.browser_widget.setVisible(checked)
        self._browser_toggle.setArrowType(
            QtCore.Qt.ArrowType.DownArrow if checked else QtCore.Qt.ArrowType.RightArrow
        )

    def _toggle_browser_shortcut(self) -> None:
        self._browser_toggle.setChecked(not self._browser_toggle.isChecked())

    def _stop_elapsed_timer(self) -> None:
        self._elapsed_timer.stop()
        self._elapsed_label.hide()
        self._elapsed_label.setText("")

    def _on_progress(self, value: float) -> None:
        self._run_progress_bar.setValue(int(value))

    def _disconnect_progress(self) -> None:
        monitor = getattr(self.manager, '_monitor', None)
        if monitor is not None:
            try:
                monitor.progress.disconnect(self._on_progress)
            except RuntimeError:
                pass

    def _on_exp_finished(self, experiment):
        name = getattr(type(experiment.procedure), 'name', type(experiment.procedure).__name__)
        self._stop_elapsed_timer()
        self._disconnect_progress()
        self._run_progress_bar.hide()
        self._run_progress_bar.setValue(0)
        self._run_progress_bar.setFormat("%p%")
        self._status_bar.showMessage(f"Finished: {name}", 4000)
        self._show_file_path()

    def _on_exp_aborted(self, experiment):
        self._stop_elapsed_timer()
        self._disconnect_progress()
        self._run_progress_bar.hide()
        self._run_progress_bar.setValue(0)
        self._run_progress_bar.setFormat("%p%")
        self._status_bar.showMessage("Aborted — instruments ramped to 0 V", 4000)
        self._show_file_path()

    def _on_exp_failed(self, experiment):
        name = getattr(type(experiment.procedure), 'name', type(experiment.procedure).__name__)
        self._stop_elapsed_timer()
        self._disconnect_progress()
        self._run_progress_bar.hide()
        self._run_progress_bar.setValue(0)
        self._run_progress_bar.setFormat("%p%")
        self._status_bar.showMessage(f"Failed: {name}", 6000)
        self._show_file_path()

    def _show_file_path(self) -> None:
        if getattr(self, '_last_filename', None):
            self._open_folder_btn.show()

    def _reveal_last_folder(self) -> None:
        path = getattr(self, '_last_filename', None)
        if path:
            QtGui.QDesktopServices.openUrl(
                QtCore.QUrl.fromLocalFile(os.path.dirname(os.path.abspath(path)))
            )

    def _save_plot(self) -> None:
        data_dir = os.path.abspath(CONFIG.Dir.data_dir)
        figs_dir = os.path.join(os.path.dirname(data_dir), 'figs')
        os.makedirs(figs_dir, exist_ok=True)

        proc_name = getattr(self.procedure_class, '__name__', 'plot')
        timestamp = time.strftime('%Y-%m-%d_%H%M%S')
        default_path = os.path.join(figs_dir, f'{proc_name}_{timestamp}.png')

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save Plot', default_path,
            'Images (*.png *.jpg *.svg);;All Files (*)'
        )
        if not path:
            return

        self._exporter = pg.exporters.ImageExporter(self.plot_widget.plot_frame.plot)
        self._exporter.export(path)

    def _find_other_running_experiment(self) -> 'ExperimentWindow | None':
        """Return another ExperimentWindow whose manager is currently running, if any.

        Used to prevent two procedures from driving the shared instruments at
        the same time. Scans top-level widgets so it works regardless of how
        the window was opened (main menu, sequence, scripts).
        """
        app = QtWidgets.QApplication.instance()
        if app is None:
            return None
        for w in app.topLevelWidgets():
            if w is self or not isinstance(w, ExperimentWindow):
                continue
            try:
                if w.manager.is_running():
                    return w
            except Exception:
                continue
        return None

    def queue(self, procedure: Procedure | None = None):
        other = self._find_other_running_experiment()
        if other is not None:
            other_name = getattr(other.procedure_class, '__name__', 'another procedure')
            log.warning(
                f"Refusing to queue {self.procedure_class.__name__}: "
                f"{other_name} is already running."
            )
            QtWidgets.QMessageBox.warning(
                self,
                "Experiment already running",
                f"'{other_name}' is currently running.\n"
                "Abort or wait for it to finish before starting a new procedure.",
            )
            other.raise_()
            other.activateWindow()
            return

        if procedure is None:
            procedure = self.make_procedure()

        filename_kwargs = dict(CONFIG.Filename).copy()
        prefix = filename_kwargs.pop('prefix', '') or type(procedure).__name__
        filename = unique_filename(CONFIG.Dir.data_dir,
                                   prefix=prefix, **filename_kwargs)
        self._last_filename = filename
        log.info(f"Saving data to {filename}.")

        if hasattr(procedure, 'patch_parameters') and callable(procedure.patch_parameters):
            # Edits procedure parameters after init but before startup
            procedure.patch_parameters()

        results = Results(procedure, filename)
        experiment = self.new_experiment(results)

        self.manager.queue(experiment)

    def closeEvent(self, event: QtGui.QCloseEvent):
        if self.manager.is_running():
            reply = QtWidgets.QMessageBox.question(
                self, 'Abort Experiment',
                'Do you want to close the window? This will abort the current experiment.',
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
            )
            if reply == QtWidgets.QMessageBox.StandardButton.No:
                event.ignore()
                return

            if self.manager.is_running():  # Check again in case the user took too long
                self.manager.abort()
            if issubclass(self.procedure_class, BaseProcedure):
                self.procedure_class.instruments.shutdown_all(remove_from_cache=True)
            time.sleep(0.5)

        self.log.removeHandler(self.log_widget.handler)
        if self.use_estimator:
            self.estimator.update_thread.join()
            del self.estimator.update_thread

        super().closeEvent(event)

    def open_experiment(self, filename=None):
        """Open an experiment file with proper error handling for column mismatches."""
        try:
            super().open_experiment()
        except KeyError as e:
            column_name = str(e).strip("'")
            log.error(f"Cannot open experiment: column '{column_name}' not found in data file.")
            QtWidgets.QMessageBox.warning(
                self,
                "Incompatible Data File",
                f"Cannot open this experiment file.\n\n"
                f"The file is missing the '{column_name}' column expected by the {self.cls.__name__} procedure.\n\n"
                f"This usually happens when trying to open data from a different procedure type.\n"
                f"For example, IV data has 'Vsd (V)' while IVg data has 'Vg (V)'.\n\n"
                f"Please open this file from the correct procedure window."
            )
        else:
            # manager.load() (used by open) never emits the queued signal, so the
            # show/hide/clear buttons remain disabled unless we enable them here.
            if self.browser.invisibleRootItem().childCount() > 0:
                self.browser_widget.show_button.setEnabled(True)
                self.browser_widget.hide_button.setEnabled(True)
                self.browser_widget.clear_button.setEnabled(True)
                self._save_plot_btn.show()

    def browser_item_changed(self, item, column):
        """Override to guard against load() failures and recover the ViewBox range.

        The base implementation calls curve.wdg.load(curve) directly from the
        itemChanged signal handler with no error handling. If update_data() throws
        (e.g. a pandas KeyError or a race condition on the CSV), addItem() is
        silently skipped and the browser item stays Checked — reproducing the same
        desync that causes plots to disappear. This override catches those failures
        and calls autoRange() after a show operation so a corrupted ViewBox range
        is recovered whenever the user checks an individual experiment back on.
        """
        if column != 0:
            return

        experiment = self.manager.experiments.with_browser_item(item)
        if experiment is None:
            return

        if item.checkState(0) == QtCore.Qt.CheckState.Unchecked:
            for curve in experiment.curve_list:
                if curve:
                    curve.wdg.remove(curve)
        else:
            for curve in experiment.curve_list:
                if curve:
                    try:
                        curve.wdg.load(curve)
                    except Exception as e:
                        log.warning(
                            f"Could not load curve for {experiment.data_filename}: {e}"
                        )
            for pw in (self.plot_widget, *self.dock_widget.plot_frames):
                pw.plot_frame.plot.vb.enableAutoRange()

    def show_experiments(self):
        """Force-reload all curves and reset the view range.

        The base implementation calls setCheckState(Checked) for every browser item.
        Qt only emits itemChanged when the state actually changes, so if curves
        disappear while items remain Checked the base call is a no-op and nothing is
        restored. This override bypasses that by directly calling remove/load on every
        curve and calling autoRange() on every plot, which also recovers from a
        corrupted pyqtgraph ViewBox range.
        """
        # Remove all curves first (safe no-op if a curve is not in the plot)
        for experiment in self.manager.experiments:
            for curve in experiment.curve_list:
                if curve:
                    curve.wdg.remove(curve)

        # Sync browser check states without re-triggering browser_item_changed
        self.browser.blockSignals(True)
        try:
            super().show_experiments()
        finally:
            self.browser.blockSignals(False)

        # Re-add all curves; guard against update_data() failures so addItem() is
        # always reached even when the underlying data file has an issue
        for experiment in self.manager.experiments:
            for curve in experiment.curve_list:
                if curve:
                    try:
                        curve.wdg.load(curve)
                    except Exception as e:
                        log.warning(
                            f"Could not reload curve for {experiment.data_filename}: {e}"
                        )

        # Re-enable continuous auto-range — recovers from a corrupted ViewBox state
        # and ensures a running measurement keeps the view updated after Show All.
        for pw in (self.plot_widget, *self.dock_widget.plot_frames):
            pw.plot_frame.plot.vb.enableAutoRange()

    def hide_experiments(self):
        """Remove all curves from the plots.

        Blocks itemChanged while setting check states to prevent browser_item_changed
        from calling removeItem() a second time on curves we already removed.
        """
        # Sync browser check states without triggering browser_item_changed
        self.browser.blockSignals(True)
        try:
            super().hide_experiments()
        finally:
            self.browser.blockSignals(False)

        # Explicitly remove all curves
        for experiment in self.manager.experiments:
            for curve in experiment.curve_list:
                if curve:
                    curve.wdg.remove(curve)

    def new_curve(self, *args, **kwargs) -> ResultsCurve | list[ResultsCurve] | None:
        curves = super().new_curve(*args, **kwargs)
        if isinstance(curves, list):
            for curve in curves:
                self.update_curve(curve)

        elif curves is not None:
            self.update_curve(curves)

        return curves

    def update_curve(self, curve: ResultsCurve) -> None:
        """Configure the curve style. This is called for each curve in the window.
        Override this method to customize the curve style. The default implementation
        does nothing.

        Example:
            def update_curve(self, curve: ResultsCurve) -> None:
                curve.setSymbol('o')
                curve.setPen(None)  # Disable connecting line
                curve.setSymbolBrush(curve.color)  # filling
                curve.setSymbolPen(curve.pen)  # outline

        :param curve: The curve to update.
        :type curve: pymeasure.display.curves.ResultsCurve
        """
        pass


class ProgressBar(QtWidgets.QDialog):
    """A simple progress bar dialog."""
    def __init__(self, parent=None, title="Waiting", text=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel(self)
        self.label.setText(text)
        self.progress = QtWidgets.QProgressBar(self)
        self._layout.addWidget(self.label)
        self._layout.addWidget(self.progress)
        self.setLayout(self._layout)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._update_progress)

    def start(self, wait_time: float, fps: float = 30., decimals: int = 0):
        self.wait_time = wait_time
        self.frame_interval = 1 / fps
        self.total_frames = int(fps * wait_time)
        self.start_time = time.perf_counter()
        self.progress.setRange(0, self.total_frames)
        self.show()
        self.timer.start(max(1, round(1000 / fps)))
        self.d = decimals

    def _update_progress(self):
        elapsed_time = time.perf_counter() - self.start_time
        current_frame = int(elapsed_time / self.frame_interval)

        if current_frame >= self.total_frames:
            self.progress.setValue(self.total_frames)
            self.progress.setFormat(
                f"{self.wait_time:.{self.d}f} / {self.wait_time:.{self.d}f} s"
            )
            self.timer.stop()
            self.close()
        else:
            self.progress.setValue(current_frame)
            self.progress.setFormat(
                f"{elapsed_time:.{self.d}f} / {self.wait_time:.{self.d}f} s"
            )
