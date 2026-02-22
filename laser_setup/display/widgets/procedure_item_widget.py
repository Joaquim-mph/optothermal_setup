"""Widget representing a single procedure in the sequence builder."""

from functools import partial
from pymeasure.experiment import Procedure, Parameter

from ..Qt import QtCore, QtGui, QtWidgets
from ..models import ProcedureItemModel
from ..theme import manager, qss


class ProcedureItemWidget(QtWidgets.QFrame):
    """Widget representing a procedure item in the sequence builder.

    Features:
    - Expandable parameter editor
    - Delete button
    - Sequencer (parameter sweep) configuration
    - Drag handle for reordering (future)

    Signals:
        deleteRequested: Emitted when delete button is clicked (widget)
        configChanged: Emitted when configuration changes
    """

    deleteRequested = QtCore.Signal(object)
    configChanged = QtCore.Signal()

    def __init__(self, procedure_class: type[Procedure], parent=None):
        super().__init__(parent)
        self.procedure_class = procedure_class
        self.parameter_widgets: dict[str, QtWidgets.QWidget] = {}
        self.sequencer_config: str | None = None
        self._is_expanded = False
        self._display_name = getattr(self.procedure_class, 'name', self.procedure_class.__name__)

        self._setup_ui()
        self._apply_style()

        # Connect to theme changes
        manager().theme_changed.connect(self._apply_style)

    def _setup_ui(self):
        """Build the widget UI."""
        self.setFrameStyle(QtWidgets.QFrame.Shape.StyledPanel)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)

        # Header row
        header_layout = QtWidgets.QHBoxLayout()

        # Expand/collapse button
        self.expand_btn = QtWidgets.QToolButton()
        self.expand_btn.setArrowType(QtCore.Qt.ArrowType.RightArrow)
        self.expand_btn.clicked.connect(self._toggle_expand)
        header_layout.addWidget(self.expand_btn)

        # Procedure name
        self.name_label = QtWidgets.QLabel(f"<b>{self._display_name}</b>")
        header_layout.addWidget(self.name_label)

        header_layout.addStretch()

        # Sequence status placeholder
        self.status_label = QtWidgets.QLabel("Queued")
        header_layout.addWidget(self.status_label)

        # Sequencer button
        self.sequencer_btn = QtWidgets.QPushButton("Sweep")
        self.sequencer_btn.setMaximumWidth(60)
        self.sequencer_btn.setToolTip("Configure parameter sweep")
        self.sequencer_btn.clicked.connect(self._open_sequencer)
        header_layout.addWidget(self.sequencer_btn)

        # Delete button
        self.delete_btn = QtWidgets.QPushButton("X")
        self.delete_btn.setMaximumWidth(25)
        self.delete_btn.clicked.connect(lambda: self.deleteRequested.emit(self))
        header_layout.addWidget(self.delete_btn)

        layout.addLayout(header_layout)

        # Parameters panel (hidden by default)
        self.params_widget = QtWidgets.QWidget()
        self.params_layout = QtWidgets.QFormLayout(self.params_widget)
        self.params_layout.setContentsMargins(20, 5, 5, 5)
        self._create_parameter_widgets()
        self.params_widget.hide()
        layout.addWidget(self.params_widget)

        # Sequencer indicator
        self.sequencer_label = QtWidgets.QLabel("")
        self.sequencer_label.hide()
        layout.addWidget(self.sequencer_label)

    def _apply_style(self, _colors=None):
        """Apply styling to the widget based on current theme."""
        self.setStyleSheet(qss('card'))
        self.sequencer_label.setStyleSheet(qss('label_info'))
        self.status_label.setStyleSheet(qss('label_secondary'))
        self.delete_btn.setStyleSheet(qss('button_danger'))

    def _create_parameter_widgets(self):
        """Create widgets for each procedure parameter."""
        # Get inputs to display
        inputs = getattr(self.procedure_class, 'INPUTS', [])

        for attr_name in inputs:
            attr = getattr(self.procedure_class, attr_name, None)
            if not isinstance(attr, Parameter):
                continue

            # Get parameter properties
            label = attr.name if hasattr(attr, 'name') else attr_name
            default = attr.default if hasattr(attr, 'default') else None
            units = getattr(attr, 'units', '')

            # Create appropriate widget based on parameter type
            widget = self._create_widget_for_parameter(attr, default)
            if widget:
                label_text = f"{label}" + (f" ({units})" if units else "")
                self.params_layout.addRow(label_text + ":", widget)
                self.parameter_widgets[attr_name] = widget

    def _create_widget_for_parameter(self, param: Parameter, default) -> QtWidgets.QWidget | None:
        """Create appropriate widget for a parameter type."""
        param_type = type(param).__name__

        if param_type == 'BooleanParameter':
            widget = QtWidgets.QCheckBox()
            widget.setChecked(bool(default))
            return widget

        elif param_type == 'ListParameter':
            widget = QtWidgets.QComboBox()
            choices = getattr(param, 'choices', [])
            widget.addItems([str(c) for c in choices])
            if default is not None:
                idx = widget.findText(str(default))
                if idx >= 0:
                    widget.setCurrentIndex(idx)
            return widget

        elif param_type in ('IntegerParameter', 'FloatParameter'):
            if param_type == 'IntegerParameter':
                widget = QtWidgets.QSpinBox()
                widget.setRange(-999999, 999999)
            else:
                widget = QtWidgets.QDoubleSpinBox()
                widget.setRange(-999999.0, 999999.0)
                widget.setDecimals(4)

            if default is not None:
                widget.setValue(default)
            return widget

        else:
            # Default: line edit
            widget = QtWidgets.QLineEdit()
            if default is not None:
                widget.setText(str(default))
            return widget

    def _toggle_expand(self):
        """Toggle parameter panel visibility."""
        self._is_expanded = not self._is_expanded
        self.params_widget.setVisible(self._is_expanded)
        arrow = QtCore.Qt.ArrowType.DownArrow if self._is_expanded else QtCore.Qt.ArrowType.RightArrow
        self.expand_btn.setArrowType(arrow)

    def _open_sequencer(self):
        """Open sequencer dialog for parameter sweeps."""
        from .sequencer_dialog import SequencerDialog

        dialog = SequencerDialog(self.procedure_class, parent=self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.sequencer_config = dialog.get_sequencer_string()
            self.sequencer_label.setText(f"Sweep: {dialog.num_instances} instances")
            self.sequencer_label.show()
            self.configChanged.emit()

    def get_model(self) -> ProcedureItemModel:
        """Get current configuration as a model.

        Returns:
            ProcedureItemModel with current settings
        """
        params = {}
        for name, widget in self.parameter_widgets.items():
            value = self._get_widget_value(widget)
            if value is not None:
                params[name] = {'value': value}

        return ProcedureItemModel(
            procedure_class=self.procedure_class,
            parameters=params,
            sequencer_config=self.sequencer_config,
            is_expanded=self._is_expanded
        )

    def set_index(self, index: int):
        self.name_label.setText(f"<b>{index}. {self._display_name}</b>")

    def _get_widget_value(self, widget: QtWidgets.QWidget):
        """Extract value from a parameter widget.

        Returns native Python types suitable for YAML serialization.
        """
        if isinstance(widget, QtWidgets.QCheckBox):
            return bool(widget.isChecked())
        elif isinstance(widget, QtWidgets.QComboBox):
            return str(widget.currentText())
        elif isinstance(widget, QtWidgets.QSpinBox):
            return int(widget.value())
        elif isinstance(widget, QtWidgets.QDoubleSpinBox):
            return float(widget.value())
        elif isinstance(widget, QtWidgets.QLineEdit):
            text = widget.text().strip()
            if not text:
                return None
            # Try to convert to int first, then float
            try:
                return int(text)
            except ValueError:
                try:
                    return float(text)
                except ValueError:
                    return str(text)
        return None

    def set_parameters(self, parameters: dict):
        """Set parameter values from a configuration dict.

        Args:
            parameters: Dict of parameter_name -> {'value': value} or parameter_name -> value
        """
        for name, config in parameters.items():
            if name not in self.parameter_widgets:
                continue

            # Extract value from config (handles both {'value': x} and x formats)
            if isinstance(config, dict):
                value = config.get('value', config)
            else:
                value = config

            widget = self.parameter_widgets[name]
            self._set_widget_value(widget, value)

    def _set_widget_value(self, widget: QtWidgets.QWidget, value):
        """Set value on a parameter widget."""
        if isinstance(widget, QtWidgets.QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QtWidgets.QComboBox):
            idx = widget.findText(str(value))
            if idx >= 0:
                widget.setCurrentIndex(idx)
            else:
                # If editable, set the text directly
                if widget.isEditable():
                    widget.setCurrentText(str(value))
        elif isinstance(widget, QtWidgets.QSpinBox):
            widget.setValue(int(value))
        elif isinstance(widget, QtWidgets.QDoubleSpinBox):
            widget.setValue(float(value))
        elif isinstance(widget, QtWidgets.QLineEdit):
            widget.setText(str(value) if value is not None else "")

    def set_sequencer(self, sequencer_config: str):
        """Set the sequencer configuration.

        Args:
            sequencer_config: Sequencer string (e.g., '- "target_T", "arange(35., 71., 5)"')
        """
        self.sequencer_config = sequencer_config
        # Show indicator
        self.sequencer_label.setText(f"Sweep: {sequencer_config}")
        self.sequencer_label.show()
        self.configChanged.emit()
