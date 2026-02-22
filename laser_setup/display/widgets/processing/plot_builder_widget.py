"""
Plot builder widget for generating plots from experiment data.

Provides a GUI for configuring and generating different plot types
(ITS, IVg, VVg, transconductance, etc.) from chip history data.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

from qtpy import QtCore, QtWidgets

from .base_widget import BaseProcessingWidget

log = logging.getLogger(__name__)


# Plot type configurations with their parameters
PLOT_TYPES = {
    "ITS (Current vs Time)": {
        "command": "plot-its",
        "procedure": "It",
        "parameters": {
            "baseline_mode": {"type": "combo", "options": ["fixed", "auto", "none"], "default": "fixed"},
            "baseline_t": {"type": "float", "default": 60.0, "label": "Baseline Time (s)"},
            "legend_by": {"type": "combo", "options": ["wavelength", "vg", "power", "datetime"], "default": "wavelength"},
            "conductance": {"type": "bool", "default": False, "label": "Plot Conductance (G=I/V)"},
        }
    },
    "IVg (Gate Sweep)": {
        "command": "plot-ivg",
        "procedure": "IVg",
        "parameters": {
            "legend_by": {"type": "combo", "options": ["wavelength", "vg", "power", "datetime"], "default": "wavelength"},
            "conductance": {"type": "bool", "default": False, "label": "Plot Conductance (G=I/V)"},
        }
    },
    "VVg (Drain-Source Voltage vs Gate)": {
        "command": "plot-vvg",
        "procedure": "VVg",
        "parameters": {
            "legend_by": {"type": "combo", "options": ["wavelength", "vg", "power", "datetime"], "default": "wavelength"},
            "resistance": {"type": "bool", "default": False, "label": "Plot Resistance (R=V/I)"},
        }
    },
    "Transconductance (dI/dVg)": {
        "command": "plot-transconductance",
        "procedure": "IVg",
        "parameters": {
            "method": {"type": "combo", "options": ["gradient", "savgol"], "default": "savgol"},
            "window": {"type": "int", "default": 21, "label": "Savgol Window"},
        }
    },
    "Vt (Voltage vs Time)": {
        "command": "plot-vt",
        "procedure": "Vt",
        "parameters": {
            "legend_by": {"type": "combo", "options": ["wavelength", "vg", "power", "datetime"], "default": "vg"},
            "resistance": {"type": "bool", "default": False, "label": "Plot Resistance (R=V/I)"},
        }
    },
}


class PlotBuilderWidget(BaseProcessingWidget):
    """
    Widget for building and generating plots from experiment data.

    Features:
    - Plot type selection
    - Chip and sequence input
    - Dynamic parameters panel based on plot type
    - Auto-select feature for convenience
    - Background plot generation
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._param_widgets: Dict[str, QtWidgets.QWidget] = {}
        self._setup_ui()
        self._connect_signals()
        self._scan_for_chips()

    def _setup_ui(self):
        """Create the user interface."""
        layout = QtWidgets.QVBoxLayout(self)

        # Title
        title = QtWidgets.QLabel("Plot Builder")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Plot type selection
        type_layout = QtWidgets.QHBoxLayout()
        type_layout.addWidget(QtWidgets.QLabel("Plot Type:"))
        self.combo_plot_type = QtWidgets.QComboBox()
        for plot_name in PLOT_TYPES.keys():
            self.combo_plot_type.addItem(plot_name)
        type_layout.addWidget(self.combo_plot_type)
        type_layout.addStretch()
        layout.addLayout(type_layout)

        # Chip and sequence selection
        data_group = QtWidgets.QGroupBox("Data Selection")
        data_layout = QtWidgets.QGridLayout(data_group)

        data_layout.addWidget(QtWidgets.QLabel("Chip:"), 0, 0)
        self.combo_chip = QtWidgets.QComboBox()
        self.combo_chip.setMinimumWidth(150)
        data_layout.addWidget(self.combo_chip, 0, 1)

        data_layout.addWidget(QtWidgets.QLabel("Sequences:"), 1, 0)
        self.edit_sequences = QtWidgets.QLineEdit()
        self.edit_sequences.setPlaceholderText("e.g., 1,2,3 or 1-5 or leave empty for auto")
        data_layout.addWidget(self.edit_sequences, 1, 1)

        self.btn_auto_select = QtWidgets.QPushButton("Auto Select")
        self.btn_auto_select.setToolTip("Automatically select sequences based on filters")
        data_layout.addWidget(self.btn_auto_select, 1, 2)

        layout.addWidget(data_group)

        # Auto-select filters
        auto_group = QtWidgets.QGroupBox("Auto-Select Filters (optional)")
        auto_layout = QtWidgets.QGridLayout(auto_group)

        auto_layout.addWidget(QtWidgets.QLabel("Gate Voltage (Vg):"), 0, 0)
        self.edit_vg = QtWidgets.QLineEdit()
        self.edit_vg.setPlaceholderText("e.g., -0.4")
        auto_layout.addWidget(self.edit_vg, 0, 1)

        auto_layout.addWidget(QtWidgets.QLabel("Wavelength (nm):"), 0, 2)
        self.edit_wavelength = QtWidgets.QLineEdit()
        self.edit_wavelength.setPlaceholderText("e.g., 365")
        auto_layout.addWidget(self.edit_wavelength, 0, 3)

        auto_layout.addWidget(QtWidgets.QLabel("Light:"), 1, 0)
        self.combo_light = QtWidgets.QComboBox()
        self.combo_light.addItems(["Any", "Light", "Dark"])
        auto_layout.addWidget(self.combo_light, 1, 1)

        auto_layout.addWidget(QtWidgets.QLabel("Max Experiments:"), 1, 2)
        self.spin_max = QtWidgets.QSpinBox()
        self.spin_max.setRange(1, 100)
        self.spin_max.setValue(10)
        auto_layout.addWidget(self.spin_max, 1, 3)

        layout.addWidget(auto_group)

        # Dynamic parameters group
        self.params_group = QtWidgets.QGroupBox("Plot Parameters")
        self.params_layout = QtWidgets.QGridLayout(self.params_group)
        layout.addWidget(self.params_group)

        # Output options
        output_group = QtWidgets.QGroupBox("Output")
        output_layout = QtWidgets.QHBoxLayout(output_group)

        output_layout.addWidget(QtWidgets.QLabel("Tag:"))
        self.edit_tag = QtWidgets.QLineEdit()
        self.edit_tag.setPlaceholderText("Optional filename tag")
        self.edit_tag.setMaximumWidth(150)
        output_layout.addWidget(self.edit_tag)

        output_layout.addStretch()

        self.btn_generate = QtWidgets.QPushButton("Generate Plot")
        self.btn_generate.setMinimumHeight(35)
        self.btn_generate.setStyleSheet("""
            QPushButton {
                background-color: #50C878;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #3DA55F;
            }
        """)
        output_layout.addWidget(self.btn_generate)

        layout.addWidget(output_group)

        # Spacer
        layout.addStretch()

        # Initialize parameters for default plot type
        self._update_parameters()

    def _connect_signals(self):
        """Connect signals to slots."""
        self.combo_plot_type.currentIndexChanged.connect(self._update_parameters)
        self.combo_chip.currentIndexChanged.connect(self._on_chip_changed)
        self.btn_auto_select.clicked.connect(self._auto_select_sequences)
        self.btn_generate.clicked.connect(self._generate_plot)

    def _get_project_paths(self) -> dict:
        """Get standard project paths."""
        current = Path.cwd()
        project_root = None

        for parent in [current] + list(current.parents):
            if (parent / "data").exists():
                project_root = parent
                break

        if project_root is None:
            project_root = current

        return {
            "project_root": project_root,
            "histories_dir": project_root / "data" / "02_stage" / "chip_histories",
            "enriched_dir": project_root / "data" / "03_derived" / "chip_histories_enriched",
            "figs_dir": project_root / "figs",
        }

    def _scan_for_chips(self):
        """Scan for available chip history files."""
        paths = self._get_project_paths()
        histories_dir = paths["histories_dir"]

        self.combo_chip.clear()

        if not histories_dir.exists():
            return

        history_files = sorted(histories_dir.glob("*_history.parquet"))

        for path in history_files:
            chip_name = path.stem.replace("_history", "")
            # Extract chip number from name (e.g., "Alisson67" -> 67)
            import re
            match = re.search(r'(\d+)$', chip_name)
            if match:
                chip_num = int(match.group(1))
                self.combo_chip.addItem(chip_name, {"number": chip_num, "path": str(path)})

    def _on_chip_changed(self):
        """Handle chip selection change."""
        # Clear sequences when chip changes
        self.edit_sequences.clear()

    def _update_parameters(self):
        """Update the parameters panel based on selected plot type."""
        # Clear existing parameter widgets
        for widget in self._param_widgets.values():
            widget.deleteLater()
        self._param_widgets.clear()

        # Clear layout
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Get plot type config
        plot_type = self.combo_plot_type.currentText()
        config = PLOT_TYPES.get(plot_type, {})
        parameters = config.get("parameters", {})

        row = 0
        for param_name, param_config in parameters.items():
            label = param_config.get("label", param_name.replace("_", " ").title())
            self.params_layout.addWidget(QtWidgets.QLabel(f"{label}:"), row, 0)

            param_type = param_config.get("type", "str")

            if param_type == "combo":
                widget = QtWidgets.QComboBox()
                for option in param_config.get("options", []):
                    widget.addItem(option)
                default = param_config.get("default")
                if default:
                    idx = widget.findText(default)
                    if idx >= 0:
                        widget.setCurrentIndex(idx)
            elif param_type == "bool":
                widget = QtWidgets.QCheckBox()
                widget.setChecked(param_config.get("default", False))
            elif param_type == "int":
                widget = QtWidgets.QSpinBox()
                widget.setRange(1, 1000)
                widget.setValue(param_config.get("default", 1))
            elif param_type == "float":
                widget = QtWidgets.QDoubleSpinBox()
                widget.setRange(0, 10000)
                widget.setDecimals(2)
                widget.setValue(param_config.get("default", 0.0))
            else:
                widget = QtWidgets.QLineEdit()
                widget.setText(str(param_config.get("default", "")))

            self.params_layout.addWidget(widget, row, 1)
            self._param_widgets[param_name] = widget
            row += 1

    def _get_parameter_values(self) -> Dict[str, Any]:
        """Get current values of all parameter widgets."""
        values = {}
        for name, widget in self._param_widgets.items():
            if isinstance(widget, QtWidgets.QComboBox):
                values[name] = widget.currentText()
            elif isinstance(widget, QtWidgets.QCheckBox):
                values[name] = widget.isChecked()
            elif isinstance(widget, (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox)):
                values[name] = widget.value()
            elif isinstance(widget, QtWidgets.QLineEdit):
                values[name] = widget.text()
        return values

    def _parse_sequences(self, text: str) -> list:
        """Parse sequence input text into a list of sequence numbers."""
        sequences = []
        text = text.strip()
        if not text:
            return sequences

        for part in text.split(","):
            part = part.strip()
            if "-" in part:
                # Range: "1-5" -> [1, 2, 3, 4, 5]
                try:
                    start, end = part.split("-")
                    sequences.extend(range(int(start), int(end) + 1))
                except ValueError:
                    pass
            else:
                # Single number
                try:
                    sequences.append(int(part))
                except ValueError:
                    pass

        return sorted(set(sequences))

    def _auto_select_sequences(self):
        """Automatically select sequences based on filters."""
        chip_data = self.combo_chip.currentData()
        if not chip_data:
            self.show_warning("Please select a chip first")
            return

        history_path = Path(chip_data["path"])
        if not history_path.exists():
            self.show_error(f"History file not found: {history_path}")
            return

        try:
            import polars as pl
            history = pl.read_parquet(history_path)

            # Get procedure for current plot type
            plot_type = self.combo_plot_type.currentText()
            config = PLOT_TYPES.get(plot_type, {})
            procedure = config.get("procedure")

            # Apply filters
            df = history
            if procedure and "proc" in df.columns:
                df = df.filter(pl.col("proc") == procedure)

            # Light filter
            light_filter = self.combo_light.currentText()
            if "has_light" in df.columns:
                if light_filter == "Light":
                    df = df.filter(pl.col("has_light") == True)
                elif light_filter == "Dark":
                    df = df.filter(pl.col("has_light") == False)

            # Gate voltage filter
            vg_text = self.edit_vg.text().strip()
            if vg_text and "vg_fixed_v" in df.columns:
                try:
                    vg = float(vg_text)
                    df = df.filter(pl.col("vg_fixed_v") == vg)
                except ValueError:
                    pass

            # Wavelength filter
            wl_text = self.edit_wavelength.text().strip()
            if wl_text and "wavelength_nm" in df.columns:
                try:
                    wl = float(wl_text)
                    df = df.filter(pl.col("wavelength_nm") == wl)
                except ValueError:
                    pass

            # Limit results
            max_count = self.spin_max.value()
            if len(df) > max_count:
                df = df.head(max_count)

            # Get sequence numbers
            if "seq" in df.columns:
                sequences = df["seq"].to_list()
            else:
                sequences = list(range(1, len(df) + 1))

            if sequences:
                self.edit_sequences.setText(",".join(str(s) for s in sequences))
                self.show_success(f"Selected {len(sequences)} experiments")
            else:
                self.show_warning("No experiments match the filters")

        except Exception as e:
            self.show_error(f"Auto-select failed: {e}")

    def _generate_plot(self):
        """Generate the plot with current settings."""
        chip_data = self.combo_chip.currentData()
        if not chip_data:
            self.show_warning("Please select a chip first")
            return

        sequences = self._parse_sequences(self.edit_sequences.text())
        if not sequences:
            # Try auto-select if no sequences specified
            self._auto_select_sequences()
            sequences = self._parse_sequences(self.edit_sequences.text())
            if not sequences:
                self.show_warning("No sequences specified or found")
                return

        chip_number = chip_data["number"]
        history_path = Path(chip_data["path"])
        plot_type = self.combo_plot_type.currentText()
        config = PLOT_TYPES.get(plot_type, {})
        parameters = self._get_parameter_values()
        tag = self.edit_tag.text().strip() or f"seq_{'_'.join(str(s) for s in sequences[:5])}"

        def run_plot():
            import polars as pl
            from src.core.utils import read_measurement_parquet
            from src.plotting.config import PlotConfig

            # Load history
            history = pl.read_parquet(history_path)

            # Filter to selected sequences
            if "seq" in history.columns:
                filtered = history.filter(pl.col("seq").is_in(sequences))
            else:
                # Fallback: use row index
                filtered = history.head(max(sequences))

            # Filter to procedure
            procedure = config.get("procedure")
            if procedure and "proc" in filtered.columns:
                filtered = filtered.filter(pl.col("proc") == procedure)

            if len(filtered) == 0:
                raise ValueError(f"No experiments found for sequences {sequences}")

            # Get base_dir from history parquet_path
            if "parquet_path" in filtered.columns:
                first_path = filtered["parquet_path"][0]
                base_dir = Path(first_path).parent.parent.parent.parent.parent
            else:
                base_dir = history_path.parent.parent.parent

            # Configure output
            paths = self._get_project_paths()
            plot_config = PlotConfig()
            plot_config.output_dir = paths["figs_dir"]

            # Call appropriate plotting function
            command = config.get("command")

            if command == "plot-its":
                from src.plotting.its import plot_its_overlay
                plot_its_overlay(
                    df=filtered,
                    base_dir=base_dir,
                    tag=tag,
                    baseline_mode=parameters.get("baseline_mode", "fixed"),
                    baseline_t=parameters.get("baseline_t", 60.0),
                    legend_by=parameters.get("legend_by", "wavelength"),
                    conductance=parameters.get("conductance", False),
                    config=plot_config,
                )

            elif command == "plot-ivg":
                from src.plotting.ivg import plot_ivg_sequence
                plot_ivg_sequence(
                    df=filtered,
                    base_dir=base_dir,
                    tag=tag,
                    legend_by=parameters.get("legend_by", "wavelength"),
                    conductance=parameters.get("conductance", False),
                    config=plot_config,
                )

            elif command == "plot-vvg":
                from src.plotting.vvg import plot_vvg_sequence
                plot_vvg_sequence(
                    df=filtered,
                    base_dir=base_dir,
                    tag=tag,
                    legend_by=parameters.get("legend_by", "wavelength"),
                    resistance=parameters.get("resistance", False),
                    config=plot_config,
                )

            elif command == "plot-transconductance":
                from src.plotting.transconductance import plot_transconductance_sequence
                plot_transconductance_sequence(
                    df=filtered,
                    base_dir=base_dir,
                    tag=tag,
                    method=parameters.get("method", "savgol"),
                    window=parameters.get("window", 21),
                    config=plot_config,
                )

            elif command == "plot-vt":
                from src.plotting.vt import plot_vt_sequence
                plot_vt_sequence(
                    df=filtered,
                    base_dir=base_dir,
                    tag=tag,
                    legend_by=parameters.get("legend_by", "vg"),
                    resistance=parameters.get("resistance", False),
                    config=plot_config,
                )

            else:
                raise ValueError(f"Unknown plot command: {command}")

            return f"Plot saved to {paths['figs_dir']}"

        def on_complete(result):
            self.show_success(f"Plot generated successfully!\n{result}")

        self.run_operation(
            name=f"Generate {plot_type}",
            func=run_plot,
            on_complete=on_complete,
            show_progress=True,
            progress_title="Generating Plot",
        )
