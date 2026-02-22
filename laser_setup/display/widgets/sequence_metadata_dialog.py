"""Dialog for entering sequence metadata before saving."""

from pathlib import Path

from ..Qt import QtWidgets
from ...config import CONFIG
from ...config.utils import load_yaml


class SequenceMetadataDialog(QtWidgets.QDialog):
    """Dialog for entering sequence metadata.

    Prompts user for:
    - Sequence name (required, validated)
    - Display name (optional)
    - Description (optional)

    Note: Common parameters (chip_group, chip_number, sample, info) are now
    configured directly in the SequenceCreatorWindow, not in this dialog.
    """

    def __init__(
        self,
        parent=None,
        editing_name: str | None = None,
        display_name: str = "",
        description: str = ""
    ):
        """Initialize the dialog.

        Args:
            parent: Parent widget
            editing_name: If editing, the current sequence name (allows same name)
            display_name: Pre-fill display name field
            description: Pre-fill description field
        """
        super().__init__(parent)
        self._editing_name = editing_name
        self._initial_display_name = display_name
        self._initial_description = description

        if editing_name:
            self.setWindowTitle(f"Save Sequence: {editing_name}")
        else:
            self.setWindowTitle("Save Sequence")
        self.resize(400, 200)
        self._setup_ui()

    def _setup_ui(self):
        """Build dialog UI."""
        layout = QtWidgets.QFormLayout(self)

        # Name (required)
        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setPlaceholderText("e.g., MyCustomSequence (no spaces)")
        self.name_input.textChanged.connect(self._validate_name)
        layout.addRow("Sequence Name*:", self.name_input)

        # Display name (optional)
        self.display_name_input = QtWidgets.QLineEdit()
        self.display_name_input.setPlaceholderText("e.g., My Custom Sequence")
        layout.addRow("Display Name:", self.display_name_input)

        # Description (optional)
        self.description_input = QtWidgets.QTextEdit()
        self.description_input.setPlaceholderText("Brief description of this sequence...")
        self.description_input.setMaximumHeight(80)
        layout.addRow("Description:", self.description_input)

        # Validation message
        self.validation_label = QtWidgets.QLabel("")
        self.validation_label.setStyleSheet("color: red;")
        layout.addRow("", self.validation_label)

        # Buttons
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        ).setEnabled(False)
        layout.addRow(self.button_box)

        # Pre-fill fields if editing (AFTER button_box is created so validation works)
        if self._editing_name:
            self.name_input.setText(self._editing_name)
            self.display_name_input.setText(self._initial_display_name)
            self.description_input.setPlainText(self._initial_description)
            # Trigger validation to enable OK button
            self._validate_name()

    def _validate_name(self):
        """Validate sequence name.

        Returns:
            True if name is valid, False otherwise
        """
        name = self.name_input.text().strip()

        if not name:
            self.validation_label.setText("Name is required")
            self.button_box.button(
                QtWidgets.QDialogButtonBox.StandardButton.Ok
            ).setEnabled(False)
            return False

        # Check for valid Python identifier (no spaces, special chars)
        if not name.isidentifier():
            self.validation_label.setText(
                "Invalid name (use letters, numbers, underscores only)"
            )
            self.button_box.button(
                QtWidgets.QDialogButtonBox.StandardButton.Ok
            ).setEnabled(False)
            return False

        # Check for duplicates (allow same name when editing)
        seq_path = Path(CONFIG.Dir.local_config_file).parent / 'sequences.yaml'
        if seq_path.exists():
            try:
                sequences = load_yaml(seq_path)
                # Allow the same name if we're editing that sequence
                if name in sequences and name != '_types' and name != self._editing_name:
                    self.validation_label.setText("Sequence with this name already exists")
                    self.button_box.button(
                        QtWidgets.QDialogButtonBox.StandardButton.Ok
                    ).setEnabled(False)
                    return False
            except Exception:
                # If we can't load sequences, allow the name
                pass

        self.validation_label.setText("")
        self.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        ).setEnabled(True)
        return True

    def get_metadata(self) -> dict:
        """Get entered metadata.

        Returns:
            Dictionary with name, display_name, and description.
            Note: common_parameters are now handled by SequenceCreatorWindow.
        """
        name = self.name_input.text().strip()
        display_name = self.display_name_input.text().strip() or name
        description = self.description_input.toPlainText().strip()

        return {
            'name': name,
            'display_name': display_name,
            'description': description,
        }
