"""
Batch plot widget for running multiple plots from YAML configuration.

Provides a GUI for selecting and running batch plot configurations
defined in YAML files.
"""

import logging
from pathlib import Path
from typing import Optional

from qtpy import QtCore, QtWidgets

from .base_widget import BaseProcessingWidget

log = logging.getLogger(__name__)


class BatchPlotWidget(BaseProcessingWidget):
    """
    Widget for running batch plot configurations.

    Features:
    - YAML file selection
    - Configuration preview
    - Run with progress tracking
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._current_config_path: Optional[Path] = None
        self._setup_ui()
        self._connect_signals()
        self._scan_for_configs()

    def _setup_ui(self):
        """Create the user interface."""
        layout = QtWidgets.QVBoxLayout(self)

        # Title
        title = QtWidgets.QLabel("Batch Plot Runner")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Config file selection
        file_group = QtWidgets.QGroupBox("Configuration File")
        file_layout = QtWidgets.QHBoxLayout(file_group)

        self.combo_config = QtWidgets.QComboBox()
        self.combo_config.setMinimumWidth(300)
        file_layout.addWidget(self.combo_config)

        self.btn_browse = QtWidgets.QPushButton("Browse...")
        file_layout.addWidget(self.btn_browse)

        self.btn_refresh = QtWidgets.QPushButton("Refresh")
        file_layout.addWidget(self.btn_refresh)

        layout.addWidget(file_group)

        # Config preview
        preview_group = QtWidgets.QGroupBox("Configuration Preview")
        preview_layout = QtWidgets.QVBoxLayout(preview_group)

        self.text_preview = QtWidgets.QTextEdit()
        self.text_preview.setReadOnly(True)
        self.text_preview.setMinimumHeight(200)
        self.text_preview.setStyleSheet("""
            QTextEdit {
                font-family: monospace;
                font-size: 11px;
                background-color: #f5f5f5;
            }
        """)
        preview_layout.addWidget(self.text_preview)

        # Summary label
        self.label_summary = QtWidgets.QLabel("No configuration loaded")
        preview_layout.addWidget(self.label_summary)

        layout.addWidget(preview_group)

        # Options
        options_group = QtWidgets.QGroupBox("Options")
        options_layout = QtWidgets.QHBoxLayout(options_group)

        self.check_parallel = QtWidgets.QCheckBox("Parallel execution")
        self.check_parallel.setToolTip("Run plots in parallel (faster for many plots)")
        options_layout.addWidget(self.check_parallel)

        options_layout.addWidget(QtWidgets.QLabel("Workers:"))
        self.spin_workers = QtWidgets.QSpinBox()
        self.spin_workers.setRange(1, 8)
        self.spin_workers.setValue(4)
        self.spin_workers.setEnabled(False)
        options_layout.addWidget(self.spin_workers)

        self.check_dry_run = QtWidgets.QCheckBox("Dry run")
        self.check_dry_run.setToolTip("Preview what would be executed without generating plots")
        options_layout.addWidget(self.check_dry_run)

        options_layout.addStretch()
        layout.addWidget(options_group)

        # Run button
        run_layout = QtWidgets.QHBoxLayout()
        run_layout.addStretch()

        self.btn_run = QtWidgets.QPushButton("Run Batch Plots")
        self.btn_run.setMinimumHeight(40)
        self.btn_run.setMinimumWidth(150)
        self.btn_run.setEnabled(False)
        self.btn_run.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        run_layout.addWidget(self.btn_run)

        layout.addLayout(run_layout)

        # Spacer
        layout.addStretch()

    def _connect_signals(self):
        """Connect signals to slots."""
        self.combo_config.currentIndexChanged.connect(self._load_config_preview)
        self.btn_browse.clicked.connect(self._browse_config)
        self.btn_refresh.clicked.connect(self._scan_for_configs)
        self.check_parallel.toggled.connect(self.spin_workers.setEnabled)
        self.btn_run.clicked.connect(self._run_batch)

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
            "batch_configs": project_root / "config" / "batch_plots",
            "processing_configs": project_root / "packages" / "optothermal_processing" / "config" / "batch_plots",
        }

    def _scan_for_configs(self):
        """Scan for available batch plot configurations."""
        self.combo_config.clear()

        paths = self._get_project_paths()

        # Check both locations for config files
        config_dirs = [
            paths["batch_configs"],
            paths["processing_configs"],
        ]

        for config_dir in config_dirs:
            if not config_dir.exists():
                continue

            for yaml_file in sorted(config_dir.glob("*.yaml")) + sorted(config_dir.glob("*.yml")):
                # Use relative path from project root for display
                try:
                    rel_path = yaml_file.relative_to(paths["project_root"])
                    display_name = str(rel_path)
                except ValueError:
                    display_name = yaml_file.name

                self.combo_config.addItem(display_name, str(yaml_file))

        if self.combo_config.count() == 0:
            self.label_summary.setText("No batch configuration files found")

    def _browse_config(self):
        """Browse for a YAML configuration file."""
        paths = self._get_project_paths()
        start_dir = paths["batch_configs"] if paths["batch_configs"].exists() else paths["project_root"]

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Batch Plot Configuration",
            str(start_dir),
            "YAML Files (*.yaml *.yml);;All Files (*)"
        )

        if file_path:
            # Add to combo box if not already there
            idx = self.combo_config.findData(file_path)
            if idx < 0:
                self.combo_config.addItem(Path(file_path).name, file_path)
                idx = self.combo_config.count() - 1
            self.combo_config.setCurrentIndex(idx)

    def _load_config_preview(self):
        """Load and display the selected configuration."""
        config_path = self.combo_config.currentData()
        if not config_path:
            self.text_preview.clear()
            self.label_summary.setText("No configuration selected")
            self.btn_run.setEnabled(False)
            self._current_config_path = None
            return

        path = Path(config_path)
        if not path.exists():
            self.text_preview.setPlainText(f"File not found: {path}")
            self.label_summary.setText("Configuration file not found")
            self.btn_run.setEnabled(False)
            self._current_config_path = None
            return

        try:
            import yaml

            with open(path, 'r') as f:
                content = f.read()
                config = yaml.safe_load(content)

            self.text_preview.setPlainText(content)

            # Generate summary
            chip = config.get("chip", "?")
            chip_group = config.get("chip_group", "")
            plots = config.get("plots", [])

            # Count plot types
            plot_types = {}
            for plot in plots:
                ptype = plot.get("type", "unknown")
                plot_types[ptype] = plot_types.get(ptype, 0) + 1

            summary_parts = [f"Chip: {chip_group}{chip}", f"Total plots: {len(plots)}"]
            for ptype, count in sorted(plot_types.items()):
                summary_parts.append(f"  - {ptype}: {count}")

            self.label_summary.setText("\n".join(summary_parts))
            self.btn_run.setEnabled(True)
            self._current_config_path = path

        except Exception as e:
            self.text_preview.setPlainText(f"Error loading configuration:\n{e}")
            self.label_summary.setText("Invalid configuration file")
            self.btn_run.setEnabled(False)
            self._current_config_path = None

    def _run_batch(self):
        """Run the batch plot configuration."""
        if self._current_config_path is None:
            self.show_warning("No configuration file selected")
            return

        config_path = self._current_config_path
        parallel = self.check_parallel.isChecked()
        workers = self.spin_workers.value() if parallel else 1
        dry_run = self.check_dry_run.isChecked()

        def run_batch():
            from src.plotting.batch import execute_sequential, execute_parallel, load_batch_config
            import yaml

            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            if dry_run:
                # Return a summary of what would be executed
                plots = config.get("plots", [])
                return {
                    "dry_run": True,
                    "config_file": str(config_path),
                    "chip": config.get("chip"),
                    "total_plots": len(plots),
                    "plots": [p.get("type") for p in plots]
                }

            # Parse config into plot specs
            _chip, chip_group, plot_specs = load_batch_config(config_path)

            # Run actual batch
            if parallel and workers > 1:
                result = execute_parallel(plot_specs, chip_group, workers)
            else:
                result = execute_sequential(plot_specs, chip_group)

            return result

        def on_complete(result):
            if isinstance(result, dict) and result.get("dry_run"):
                msg = (
                    f"Dry run complete!\n\n"
                    f"Config: {result['config_file']}\n"
                    f"Chip: {result['chip']}\n"
                    f"Total plots: {result['total_plots']}\n\n"
                    f"Plot types:\n"
                )
                for ptype in result['plots']:
                    msg += f"  - {ptype}\n"
                self.show_success(msg)
            else:
                self.show_success(f"Batch plots completed!\n{result}")

        self.run_operation(
            name="Batch Plots",
            func=run_batch,
            on_complete=on_complete,
            show_progress=True,
            progress_title="Running Batch Plots",
        )
