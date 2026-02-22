import logging
import time

from pymeasure.display.curves import ResultsCurve
from pymeasure.display.widgets import PlotFrame, PlotWidget
from pymeasure.display.widgets.dock_widget import DockWidget
from pymeasure.display.windows import ManagedWindowBase
from pymeasure.experiment import Procedure, Results, unique_filename

from ...config import CONFIG, configurable
from ...procedures import BaseProcedure
from ..Qt import QtCore, QtGui, QtWidgets
from ..widgets import LogWidget, TextWidget

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

        if CONFIG.Qt.GUI.dark_mode:
            PlotFrame.LABEL_STYLE['color'] = '#AAAAAA'

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
        if CONFIG.Qt.GUI.dark_mode:
            for plot_widget in (self.plot_widget, *self.dock_widget.plot_frames):
                plot_widget.setAutoFillBackground(True)
                plot_widget.plot_frame.setStyleSheet('background-color: black;')
                plot_widget.plot_frame.plot_widget.setBackground('k')

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
        self.setWindowTitle(title or getattr(cls, 'name', cls.__name__))
        self.setWindowIcon(
            QtGui.QIcon(icon) if icon else self.style().standardIcon(
                QtWidgets.QStyle.StandardPixmap.SP_TitleBarMenuButton
            )
        )
        # Add a shutdown all button if the procedure is a BaseProcedure
        if issubclass(self.procedure_class, BaseProcedure):
            self.shutdown_button = QtWidgets.QPushButton('&Shutdown', self)
            self.shutdown_button.clicked.connect(self.procedure_class.instruments.shutdown_all)
            self.shutdown_button.setToolTip('Shutdown all instruments')
            self.abort_button.parent().layout().children()[0].insertWidget(2, self.shutdown_button)

        self.abort_button.setText('&Abort')
        self.queue_button.setText('&Queue')

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
                self._est_toggle.setChecked(False)
                self._est_toggle.setSizePolicy(
                    QtWidgets.QSizePolicy.Policy.Expanding,
                    QtWidgets.QSizePolicy.Policy.Fixed,
                )
                self._est_toggle.setStyleSheet('QToolButton { border: none; padding: 4px 2px; }')
                self._est_toggle.toggled.connect(self._toggle_estimator)

                _est_dock.setWidget(None)
                self.estimator.setParent(container)
                self.estimator.hide()

                layout.addWidget(self._est_toggle)
                layout.addWidget(self.estimator)

                self.removeDockWidget(_est_dock)
                _est_dock.deleteLater()

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

        self.log = logging.getLogger()
        self.log.addHandler(self.log_widget.handler)
        self.log.debug(f"{type(self).__name__} connected to logging")

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

    def queue(self, procedure: Procedure | None = None):
        if procedure is None:
            procedure = self.make_procedure()

        filename_kwargs = dict(CONFIG.Filename).copy()
        prefix = filename_kwargs.pop('prefix', '') or type(procedure).__name__
        filename = unique_filename(CONFIG.Dir.data_dir,
                                   prefix=prefix, **filename_kwargs)
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
                self.procedure_class.instruments.shutdown_all()
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
