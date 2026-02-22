"""Widget for individual procedure items in sequence builder."""

import inspect

from pymeasure.experiment import Parameter, Procedure

from ..Qt import QtCore, QtWidgets
from ..models import ProcedureItemModel
from .inputs_widget import _InputsWidget


class ProcedureItemWidget(QtWidgets.QWidget):
    """Individual procedure item with expand/collapse functionality.

    Signals:
        deleteRequested: Emitted when delete button is clicked (passes self)
    """

    deleteRequested = QtCore.Signal(object)

    def __init__(self, procedure_class: type[Procedure], parent=None):
        super().__init__(parent)
        self.procedure_class = procedure_class
        self.is_expanded = False
        self.sequencer_str = None
        self.num_sequencer_instances = 0

        self._setup_ui()

    def _setup_ui(self):
        """Build collapsible widget UI."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)

        # Header
        header_widget = QtWidgets.QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background-color: #E8E8E8;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setContentsMargins(8, 8, 8, 8)

        # Drag handle
        drag_label = QtWidgets.QLabel("☰")
        drag_label.setStyleSheet("font-size: 16px; color: #666;")
        header_layout.addWidget(drag_label)

        # Procedure name
        name = getattr(self.procedure_class, 'name', self.procedure_class.__name__)
        self.name_label = QtWidgets.QLabel(name)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.name_label)

        # Sequencer indicator
        self.sequencer_indicator = QtWidgets.QLabel("")
        self.sequencer_indicator.setStyleSheet("color: #4A90E2; font-size: 11px;")
        self.sequencer_indicator.hide()
        header_layout.addWidget(self.sequencer_indicator)

        header_layout.addStretch()

        # Expand/collapse button
        self.expand_button = QtWidgets.QPushButton("▼ Expand")
        self.expand_button.setFlat(True)
        self.expand_button.clicked.connect(self._toggle_expand)
        header_layout.addWidget(self.expand_button)

        # Delete button
        delete_button = QtWidgets.QPushButton("✖")
        delete_button.setFlat(True)
        delete_button.setStyleSheet("color: red; font-weight: bold;")
        delete_button.clicked.connect(lambda: self.deleteRequested.emit(self))
        header_layout.addWidget(delete_button)

        layout.addWidget(header_widget)

        # Body (collapsed by default)
        self.body_widget = QtWidgets.QWidget()
        body_layout = QtWidgets.QVBoxLayout(self.body_widget)
        body_layout.setContentsMargins(10, 10, 10, 10)

        # Parameter inputs
        try:
            self.inputs_widget = _InputsWidget(
                procedure_class=self.procedure_class,
                inputs=self._get_procedure_inputs(),
                hide_groups=False,
                inputs_in_scrollarea=False
            )
            body_layout.addWidget(self.inputs_widget)
        except Exception as e:
            # If inputs widget fails, show error message
            error_label = QtWidgets.QLabel(f"Error creating inputs: {e}")
            error_label.setStyleSheet("color: red;")
            body_layout.addWidget(error_label)
            self.inputs_widget = None

        # Sequencer button
        self.sequencer_button = QtWidgets.QPushButton("Configure Parameter Sweep...")
        self.sequencer_button.clicked.connect(self._on_sequencer_clicked)
        body_layout.addWidget(self.sequencer_button)

        self.body_widget.hide()
        layout.addWidget(self.body_widget)

        self.setStyleSheet("""
            ProcedureItemWidget {
                border: 1px solid #CCC;
                border-radius: 6px;
                margin: 2px;
            }
        """)

    def _toggle_expand(self):
        """Toggle expand/collapse state."""
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.body_widget.show()
            self.expand_button.setText("▲ Collapse")
        else:
            self.body_widget.hide()
            self.expand_button.setText("▼ Expand")

    def _get_procedure_inputs(self) -> list[str]:
        """Get input names for this procedure.

        Returns:
            List of parameter names to display
        """
        if hasattr(self.procedure_class, 'INPUTS'):
            return list(self.procedure_class.INPUTS)

        # Fallback: all parameters
        return [
            name for name, attr in inspect.getmembers(self.procedure_class)
            if isinstance(attr, Parameter)
        ]

    def _on_sequencer_clicked(self):
        """Open sequencer configuration dialog."""
        # Import here to avoid circular dependency
        from .sequencer_dialog import SequencerDialog

        dialog = SequencerDialog(
            procedure_class=self.procedure_class,
            parent=self
        )
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.sequencer_str = dialog.get_sequencer_string()
            self.num_sequencer_instances = dialog.num_instances
            self.sequencer_indicator.setText(
                f"📊 Sweep configured ({self.num_sequencer_instances} runs)"
            )
            self.sequencer_indicator.show()

    def get_model(self) -> ProcedureItemModel:
        """Export configuration as model.

        Returns:
            ProcedureItemModel with current configuration
        """
        parameters = {}

        if self.inputs_widget is not None:
            # Get parameters from inputs_widget
            try:
                procedure = self.inputs_widget.get_procedure()
                for param_name in procedure._parameters:
                    # Get the actual parameter value from the procedure instance
                    param_value = getattr(procedure, param_name)
                    parameters[param_name] = {'value': param_value}

                    # Check if parameter has group_by attribute
                    param_obj = getattr(self.procedure_class, param_name, None)
                    if param_obj and hasattr(param_obj, 'group_by') and param_obj.group_by:
                        parameters[param_name]['group_by'] = param_obj.group_by
            except Exception:
                # If we can't get parameters, continue with empty dict
                pass

        return ProcedureItemModel(
            procedure_class=self.procedure_class,
            parameters=parameters,
            sequencer_config=self.sequencer_str,
            is_expanded=self.is_expanded
        )
