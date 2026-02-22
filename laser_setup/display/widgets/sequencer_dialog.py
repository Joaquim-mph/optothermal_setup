"""Dialog for configuring parameter sweeps."""

import ast
import inspect

from pymeasure.experiment import Parameter, Procedure

from ..Qt import QtWidgets
from ..theme import manager, qss


class SequencerDialog(QtWidgets.QDialog):
    """Dialog for configuring parameter sweeps.

    Allows user to select a parameter and specify a list of values
    to create multiple procedure instances with different parameter values.
    """

    def __init__(self, procedure_class: type[Procedure], parent=None):
        super().__init__(parent)
        self.procedure_class = procedure_class
        self.num_instances = 0

        self.setWindowTitle("Configure Parameter Sweep")
        self.resize(500, 300)
        self._setup_ui()

    def _setup_ui(self):
        """Build dialog UI."""
        layout = QtWidgets.QVBoxLayout(self)

        # Instructions
        instructions = QtWidgets.QLabel(
            "Configure a parameter sweep to create multiple procedure instances "
            "with different parameter values."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Parameter selection
        param_layout = QtWidgets.QFormLayout()

        self.param_combo = QtWidgets.QComboBox()
        inputs = self._get_procedure_inputs()
        self.param_combo.addItems(inputs)
        self.param_combo.currentTextChanged.connect(self._on_parameter_changed)
        param_layout.addRow("Parameter:", self.param_combo)

        # Values input
        self.values_text = QtWidgets.QTextEdit()
        self.values_text.setPlaceholderText(
            "Enter values as:\n"
            "  [1, 2, 3, 4, 5]\n"
            "or\n"
            "  1, 2, 3, 4, 5\n"
            "or Python expression:\n"
            "  arange(0, 10, 0.5)"
        )
        self.values_text.setMaximumHeight(100)
        self.values_text.textChanged.connect(self._on_values_changed)
        param_layout.addRow("Values:", self.values_text)

        # Type hint label
        self.type_hint_label = QtWidgets.QLabel("")
        self.type_hint_label.setWordWrap(True)
        param_layout.addRow("", self.type_hint_label)

        layout.addLayout(param_layout)

        # Preview
        self.preview_label = QtWidgets.QLabel("")
        self._apply_style()
        layout.addWidget(self.preview_label)

        # Connect to theme changes
        manager().theme_changed.connect(self._apply_style)

        # Example
        example = QtWidgets.QLabel(
            "<b>Example:</b><br>"
            "Parameter: laser_v<br>"
            "Values: [0, 1, 2, 3, 4, 5]<br>"
            "Result: 6 procedure instances"
        )
        example.setWordWrap(True)
        layout.addWidget(example)

        layout.addStretch()

        # Buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Trigger initial parameter hint update
        if self.param_combo.count() > 0:
            self._on_parameter_changed(self.param_combo.currentText())

    def _apply_style(self, _colors=None):
        """Apply styling based on current theme."""
        # Use info style but add bold - access the color directly
        c = manager().colors
        self.preview_label.setStyleSheet(f"color: {c.info}; font-weight: bold;")

    def _get_procedure_inputs(self) -> list[str]:
        """Get available inputs for sweep.

        Returns:
            List of parameter names (filtered to only laser_v for now)
        """
        # Only allow sweeps on laser_v parameter
        all_params = []
        
        if hasattr(self.procedure_class, 'INPUTS'):
            all_params = list(self.procedure_class.INPUTS)
        else:
            # Fallback: all parameters
            all_params = [
                name for name, attr in inspect.getmembers(self.procedure_class)
                if isinstance(attr, Parameter)
            ]
        
        # Filter to only include laser_v
        return [p for p in all_params if p == 'laser_v']

    def _on_parameter_changed(self, param_name: str):
        """Update UI hints when parameter selection changes."""
        # Simplified - no special handling needed
        self.type_hint_label.setText("")
        self.values_text.setPlaceholderText(
            "Enter numeric values as:\n"
            "  [0, 1, 2, 3, 4, 5]\n"
            "or\n"
            "  0, 1, 2, 3, 4, 5\n"
            "or Python expression:\n"
            "  arange(0, 5, 0.5)"
        )


    def _on_values_changed(self):
        """Update preview when values change."""
        try:
            values_str = self.values_text.toPlainText().strip()
            if not values_str:
                self.preview_label.setText("")
                self.num_instances = 0
                return

            # Try to parse as Python list
            try:
                values = ast.literal_eval(values_str)
                if not isinstance(values, list):
                    values = [values]
            except Exception:
                # Try comma-separated
                values = [v.strip() for v in values_str.split(',') if v.strip()]

            self.num_instances = len(values)
            self.preview_label.setText(
                f"✓ Will create {self.num_instances} procedure instance(s)"
            )
        except Exception as e:
            self.preview_label.setText(f"⚠ Invalid format: {e}")
            self.num_instances = 0

    def get_sequencer_string(self) -> str:
        """Build sequencer string for YAML.

        Returns:
            Sequencer string in PyMeasure SequenceHandler format
        """
        param_name = self.param_combo.currentText()
        values_str = self.values_text.toPlainText().strip()

        # Format as sequencer string (YAML multiline format handled by caller)
        return f'- "{param_name}", "{values_str}"'
