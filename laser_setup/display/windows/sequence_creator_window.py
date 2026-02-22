"""Window for creating custom procedure sequences."""

import logging
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from omegaconf import OmegaConf

from ..Qt import QtCore, QtWidgets
from ..theme import manager, qss
from ...config import CONFIG
from ...config.utils import load_yaml


def _get_chip_group_choices():
    """Get chip group choices from config."""
    try:
        return list(CONFIG.parameters.Chip.chip_group.choices)
    except Exception:
        return ['other']


def _get_sample_choices():
    """Get sample choices from config."""
    try:
        return list(CONFIG.parameters.Chip.sample.choices)
    except Exception:
        return ['other', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']

log = logging.getLogger(__name__)


def _sanitize_value(value: Any) -> Any:
    """Convert value to native Python type for YAML serialization.

    Handles numpy types, nested dicts, and lists.
    """
    if value is None:
        return None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {k: _sanitize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(v) for v in value]
    return value


class SequenceCreatorWindow(QtWidgets.QMainWindow):
    """Window for creating and saving custom procedure sequences.

    Features:
    - Procedure library panel (drag source)
    - Sequence builder panel (drop target)
    - Save to sequences.yaml
    - Optional parameter sweeps via sequencer
    - Edit existing sequences
    """

    def __init__(self, parent=None, sequence_name: str | None = None):
        """Initialize the sequence creator.

        Args:
            parent: Parent widget
            sequence_name: Optional name of existing sequence to edit
        """
        super().__init__(parent)
        self.resize(900, 600)

        # Track editing state
        self._editing_sequence: str | None = None
        self._original_display_name: str = ""
        self._original_description: str = ""

        self._setup_ui()
        self._connect_signals()

        # Load sequence if editing
        if sequence_name:
            self.load_sequence(sequence_name)
        else:
            self.setWindowTitle("Sequence Creator")

    def _setup_ui(self):
        """Build the window UI."""
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        main_layout = QtWidgets.QHBoxLayout(central)

        # Left panel: Procedure library
        left_panel = QtWidgets.QWidget()
        left_panel.setMaximumWidth(250)
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        from ..widgets.procedure_library_widget import ProcedureLibraryWidget
        self.library_widget = ProcedureLibraryWidget()
        left_layout.addWidget(self.library_widget)

        main_layout.addWidget(left_panel)

        # Right panel: Sequence builder
        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_panel)

        # Builder title
        self.builder_title = QtWidgets.QLabel("Sequence Builder")
        right_layout.addWidget(self.builder_title)

        # Common parameters section (inline, not in dialog)
        common_group = QtWidgets.QGroupBox("Common Parameters")
        common_layout = QtWidgets.QFormLayout(common_group)
        common_layout.setContentsMargins(8, 8, 8, 8)

        # Chip group - editable combo box with choices from config
        self.chip_group_input = QtWidgets.QComboBox()
        self.chip_group_input.setEditable(True)
        self.chip_group_input.addItems(_get_chip_group_choices())
        self.chip_group_input.setCurrentText('other')
        self.chip_group_input.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        common_layout.addRow("Chip Group:", self.chip_group_input)

        # Chip number - spin box
        self.chip_number_input = QtWidgets.QSpinBox()
        self.chip_number_input.setMinimum(0)
        self.chip_number_input.setMaximum(10000)
        self.chip_number_input.setValue(1)
        self.chip_number_input.setSpecialValueText("")  # Show empty when 0
        common_layout.addRow("Chip Number:", self.chip_number_input)

        # Sample - editable combo box with choices from config
        self.sample_input = QtWidgets.QComboBox()
        self.sample_input.setEditable(True)
        self.sample_input.addItems(_get_sample_choices())
        self.sample_input.setCurrentText('other')
        self.sample_input.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        common_layout.addRow("Sample:", self.sample_input)

        # Info - free text
        self.info_input = QtWidgets.QLineEdit()
        self.info_input.setPlaceholderText("Common info for all procedures")
        common_layout.addRow("Info:", self.info_input)

        right_layout.addWidget(common_group)

        # Scroll area for builder
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        from ..widgets.sequence_builder_widget import SequenceBuilderWidget
        self.builder_widget = SequenceBuilderWidget()
        self.scroll_area.setWidget(self.builder_widget)
        right_layout.addWidget(self.scroll_area)

        # Bottom buttons
        button_layout = QtWidgets.QHBoxLayout()

        self.clear_btn = QtWidgets.QPushButton("Clear All")
        self.clear_btn.clicked.connect(self._clear_sequence)
        button_layout.addWidget(self.clear_btn)

        button_layout.addStretch()

        self.save_btn = QtWidgets.QPushButton("Save Sequence")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save_sequence)
        button_layout.addWidget(self.save_btn)

        # Apply initial styling
        self._apply_style()

        # Connect to theme changes
        manager().theme_changed.connect(self._apply_style)

        right_layout.addLayout(button_layout)
        main_layout.addWidget(right_panel)

        # Status bar
        self.statusBar().showMessage("Drag procedures from the library to build your sequence")

    def _apply_style(self, _colors=None):
        """Apply styling based on current theme."""
        c = manager().colors
        self.builder_title.setStyleSheet(
            f"font-weight: bold; font-size: 14px; color: {c.fg_primary};"
        )
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {c.border_primary};
                border-radius: 8px;
                background-color: {c.bg_secondary};
            }}
        """)
        self.clear_btn.setStyleSheet(qss('button_secondary'))
        self.save_btn.setStyleSheet(qss('button_primary'))

    def _connect_signals(self):
        """Connect widget signals."""
        self.library_widget.procedureDoubleClicked.connect(
            self.builder_widget.add_procedure
        )
        self.builder_widget.procedureAdded.connect(self._on_sequence_changed)
        self.builder_widget.procedureRemoved.connect(self._on_sequence_changed)

    def _on_sequence_changed(self, *args):
        """Handle sequence changes."""
        has_items = len(self.builder_widget.procedure_widgets) > 0
        self.save_btn.setEnabled(has_items)

        count = len(self.builder_widget.procedure_widgets)
        self.statusBar().showMessage(f"Sequence has {count} procedure(s)")

    def _clear_sequence(self):
        """Clear all procedures from the builder."""
        if not self.builder_widget.procedure_widgets:
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "Clear Sequence",
            "Are you sure you want to clear all procedures?",
            QtWidgets.QMessageBox.StandardButton.Yes |
            QtWidgets.QMessageBox.StandardButton.No
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            # Remove all widgets
            for widget in list(self.builder_widget.procedure_widgets):
                self.builder_widget._on_delete_requested(widget)

    def _get_common_parameters(self) -> dict:
        """Get common parameters from the inline fields."""
        common_parameters = {}

        chip_group = self.chip_group_input.currentText().strip()
        if chip_group and chip_group != 'other':
            common_parameters['chip_group'] = chip_group

        chip_number = self.chip_number_input.value()
        if chip_number > 0:
            common_parameters['chip_number'] = chip_number

        sample = self.sample_input.currentText().strip()
        if sample and sample != 'other':
            common_parameters['sample'] = sample

        info = self.info_input.text().strip()
        if info:
            common_parameters['info'] = info

        return common_parameters

    def load_sequence(self, sequence_name: str):
        """Load an existing sequence for editing.

        Args:
            sequence_name: Name of the sequence to load from CONFIG.sequences
        """
        from omegaconf import OmegaConf

        # Get sequence config
        if sequence_name not in CONFIG.sequences:
            QtWidgets.QMessageBox.warning(
                self,
                "Sequence Not Found",
                f"Sequence '{sequence_name}' not found in configuration."
            )
            return

        seq_config = CONFIG.sequences[sequence_name]

        # Convert to plain dict for easier access
        if hasattr(seq_config, '_content'):
            config = OmegaConf.to_container(seq_config, resolve=False)
        else:
            config = dict(seq_config) if hasattr(seq_config, 'items') else {}

        # Set editing state
        self._editing_sequence = sequence_name
        self._original_display_name = config.get('name', sequence_name)
        self._original_description = config.get('description', '')

        self.setWindowTitle(f"Edit Sequence: {sequence_name}")

        # Clear current builder
        self.builder_widget.clear()

        # Load common parameters
        common_params = config.get('common_parameters', {})
        if common_params:
            if 'chip_group' in common_params:
                self.chip_group_input.setCurrentText(str(common_params['chip_group']))
            if 'chip_number' in common_params:
                self.chip_number_input.setValue(int(common_params['chip_number']))
            if 'sample' in common_params:
                self.sample_input.setCurrentText(str(common_params['sample']))
            if 'info' in common_params:
                self.info_input.setText(str(common_params['info']))

        # Load procedures
        procedures = config.get('procedures', [])
        for proc_entry in procedures:
            if isinstance(proc_entry, str):
                # Simple procedure name
                self.builder_widget.add_procedure(proc_entry)
            elif isinstance(proc_entry, dict):
                # Procedure with config
                for proc_name, proc_config in proc_entry.items():
                    parameters = proc_config.get('parameters', {}) if proc_config else {}
                    sequencer = proc_config.get('sequencer') if proc_config else None
                    self.builder_widget.add_procedure(proc_name, parameters, sequencer)

        self.statusBar().showMessage(f"Loaded sequence '{sequence_name}' for editing")

    def _save_sequence(self):
        """Save the sequence to sequences.yaml."""
        if not self.builder_widget.procedure_widgets:
            QtWidgets.QMessageBox.warning(
                self,
                "Empty Sequence",
                "Add at least one procedure to the sequence."
            )
            return

        # Get metadata via dialog
        from ..widgets.sequence_metadata_dialog import SequenceMetadataDialog
        dialog = SequenceMetadataDialog(
            parent=self,
            editing_name=self._editing_sequence,
            display_name=self._original_display_name,
            description=self._original_description
        )
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        metadata = dialog.get_metadata()
        # Add common parameters from inline fields
        metadata['common_parameters'] = self._get_common_parameters()

        # Build sequence configuration
        sequence_config = self._build_sequence_config(metadata)

        # Save to file
        try:
            self._save_to_yaml(metadata['name'], sequence_config)

            action = "updated" if self._editing_sequence else "saved"
            QtWidgets.QMessageBox.information(
                self,
                "Sequence Saved",
                f"Sequence '{metadata['name']}' {action} successfully!\n\n"
                "Reload the application to see changes in the Sequences menu."
            )

            # Update editing state to the new name
            self._editing_sequence = metadata['name']
            self._original_display_name = metadata['display_name']
            self._original_description = metadata['description']
            self.setWindowTitle(f"Edit Sequence: {metadata['name']}")

            # Suggest reload
            if self.parent() and hasattr(self.parent(), 'suggest_reload'):
                self.parent().suggest_reload()

        except Exception as e:
            log.exception("Failed to save sequence")
            QtWidgets.QMessageBox.critical(
                self,
                "Save Failed",
                f"Failed to save sequence:\n{e}"
            )

    def _build_sequence_config(self, metadata: dict) -> dict:
        """Build sequence configuration dictionary.

        Args:
            metadata: Sequence metadata (name, display_name, description)

        Returns:
            Configuration dictionary for sequences.yaml
        """
        config = {
            'name': metadata['display_name'],
            'description': metadata['description'],
            'common_procedure': {
                '_target_': 'hydra.utils.get_class',
                'path': 'laser_setup.procedures.ChipProcedure'
            },
            'inputs_ignored': ['show_more', 'skip_startup', 'skip_shutdown'],
            'procedures': []
        }
        common_parameters = metadata.get('common_parameters') or {}
        if common_parameters:
            config['common_parameters'] = _sanitize_value(common_parameters)

        for item_model in self.builder_widget.get_procedure_items():
            proc_name = item_model.procedure_class.__name__

            proc_config = {}

            # Add parameters if any (sanitize values for YAML)
            if item_model.parameters:
                proc_config['parameters'] = _sanitize_value(item_model.parameters)

            # Add sequencer if configured
            if item_model.sequencer_config:
                proc_config['sequencer'] = item_model.sequencer_config

            # Build procedure entry
            if proc_config:
                config['procedures'].append({proc_name: proc_config})
            else:
                config['procedures'].append(proc_name)

        return config

    def _save_to_yaml(self, name: str, config: dict):
        """Save sequence to sequences.yaml file.

        Args:
            name: Sequence identifier
            config: Sequence configuration
        """
        # Find sequences.yaml path
        seq_path = Path(CONFIG.Dir.local_config_file).parent / 'sequences.yaml'

        # Load existing sequences
        if seq_path.exists():
            sequences_cfg = load_yaml(seq_path)
            # Convert OmegaConf to plain dict to avoid serialization issues
            # Don't resolve interpolations - we need to preserve ${sequence:X} syntax
            sequences = OmegaConf.to_container(sequences_cfg, resolve=False)
        else:
            sequences = {}

        # Extract _types section (we need to preserve and update it)
        types_section = sequences.pop('_types', {})

        # Add new sequence
        sequences[name] = config

        # Add entry to _types for the new sequence
        # Uses OmegaConf interpolation syntax to register with configurable system
        types_section[name] = f'${{sequence:{name}}}'

        # Add _types back at the end
        sequences['_types'] = types_section

        # Write back
        seq_path.parent.mkdir(parents=True, exist_ok=True)
        with open(seq_path, 'w') as f:
            yaml.dump(sequences, f, default_flow_style=False, sort_keys=False)

        log.info(f"Saved sequence '{name}' to {seq_path}")
