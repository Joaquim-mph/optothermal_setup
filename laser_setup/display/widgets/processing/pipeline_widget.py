"""
Pipeline widget for data processing operations.

Provides a GUI for running staging, history building, and metric extraction
operations from the optothermal_processing package.
"""

import logging
from pathlib import Path
from typing import Optional

from qtpy import QtCore, QtWidgets

from .base_widget import BaseProcessingWidget

log = logging.getLogger(__name__)


class PipelineWidget(BaseProcessingWidget):
    """
    Widget for running data pipeline operations.

    Operations:
    - Stage raw CSVs to Parquet
    - Build chip histories from manifest
    - Derive metrics from staged measurements
    - Run full pipeline (all of the above)
    
    Processing is executed in separate processes via the `process_and_analyze` CLI
    to ensure stability and isolation from the GUI process.
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
        self._apply_theme()
        
        # Track active process
        self.process: Optional[QtCore.QProcess] = None
        self.current_operation: Optional[str] = None

    def _setup_ui(self):
        """Create the user interface."""
        layout = QtWidgets.QVBoxLayout(self)

        # Title
        self.lbl_title = QtWidgets.QLabel("Data Pipeline Operations")
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.lbl_title)

        # Options group
        options_group = QtWidgets.QGroupBox("Options")
        options_layout = QtWidgets.QGridLayout(options_group)

        # Workers spinbox
        options_layout.addWidget(QtWidgets.QLabel("Workers:"), 0, 0)
        self.spin_workers = QtWidgets.QSpinBox()
        self.spin_workers.setRange(1, 16)
        self.spin_workers.setValue(6)
        self.spin_workers.setToolTip("Number of parallel workers for processing")
        options_layout.addWidget(self.spin_workers, 0, 1)

        # Force checkbox
        self.check_force = QtWidgets.QCheckBox("Force overwrite")
        self.check_force.setToolTip("Overwrite existing staged files")
        options_layout.addWidget(self.check_force, 1, 0)

        # Strict checkbox
        self.check_strict = QtWidgets.QCheckBox("Strict validation")
        self.check_strict.setToolTip("Fail on schema validation errors")
        options_layout.addWidget(self.check_strict, 1, 1)

        layout.addWidget(options_group)

        # Operations group
        ops_group = QtWidgets.QGroupBox("Pipeline Operations")
        ops_layout = QtWidgets.QVBoxLayout(ops_group)

        # Full Pipeline button
        self.btn_full_pipeline = QtWidgets.QPushButton("Run Full Pipeline")
        self.btn_full_pipeline.setToolTip("Run staging + history + metrics extraction")
        self.btn_full_pipeline.setMinimumHeight(40)
        ops_layout.addWidget(self.btn_full_pipeline)

        # Individual operation buttons in a horizontal layout
        individual_layout = QtWidgets.QHBoxLayout()

        self.btn_stage = QtWidgets.QPushButton("Stage CSVs")
        self.btn_stage.setToolTip("Stage raw CSV files to Parquet format")
        individual_layout.addWidget(self.btn_stage)

        self.btn_histories = QtWidgets.QPushButton("Build Histories")
        self.btn_histories.setToolTip("Build chip histories from manifest")
        individual_layout.addWidget(self.btn_histories)

        self.btn_metrics = QtWidgets.QPushButton("Derive Metrics")
        self.btn_metrics.setToolTip("Extract derived metrics from measurements")
        individual_layout.addWidget(self.btn_metrics)

        ops_layout.addLayout(individual_layout)
        layout.addWidget(ops_group)
        
        # Stop button (hidden by default)
        self.btn_stop = QtWidgets.QPushButton("Stop Operation")
        self.btn_stop.hide()
        self.btn_stop.clicked.connect(self._stop_process)
        layout.addWidget(self.btn_stop)

        # Log output area
        log_group = QtWidgets.QGroupBox("Output")
        log_layout = QtWidgets.QVBoxLayout(log_group)

        self.text_log = QtWidgets.QTextEdit()
        self.text_log.setReadOnly(True)
        self.text_log.setMinimumHeight(300)
        log_layout.addWidget(self.text_log)

        # Clear log button
        self.btn_clear_log = QtWidgets.QPushButton("Clear Log")
        self.btn_clear_log.clicked.connect(self.text_log.clear)
        log_layout.addWidget(self.btn_clear_log)

        layout.addWidget(log_group)

        # Spacer
        layout.addStretch()

    def _connect_signals(self):
        """Connect button signals to slots."""
        self.btn_full_pipeline.clicked.connect(self._run_full_pipeline)
        self.btn_stage.clicked.connect(self._run_staging)
        self.btn_histories.clicked.connect(self._run_build_histories)
        self.btn_metrics.clicked.connect(self._run_derive_metrics)
        
        # Connect to theme updates
        from ...theme.manager import manager
        theme = manager()
        theme.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, colors):
        """Handle theme change signal."""
        self._apply_theme()

    def _apply_theme(self):
        """Apply current theme colors to widgets."""
        from ...theme.manager import manager
        theme = manager()
        colors = theme.colors
        
        # Apply button styles
        primary_btn_style = f"""
            QPushButton {{
                background-color: {colors.accent_primary};
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 5px;
                padding: 5px;
            }}
            QPushButton:hover {{
                background-color: {colors.accent_secondary};
            }}
            QPushButton:disabled {{
                background-color: {colors.bg_tertiary};
                color: {colors.fg_disabled};
            }}
        """
        self.btn_full_pipeline.setStyleSheet(primary_btn_style)
        
        stop_btn_style = f"""
            QPushButton {{
                background-color: {colors.danger};
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 5px;
                padding: 5px;
            }}
            QPushButton:hover {{
                background-color: #D32F2F; 
            }}
        """
        self.btn_stop.setStyleSheet(stop_btn_style)
        
        # Log area style
        self.text_log.setStyleSheet(f"""
            QTextEdit {{
                font-family: monospace;
                font-size: 11px;
                background-color: {colors.bg_tertiary};
                color: {colors.fg_primary};
                border: 1px solid {colors.border_primary};
                border-radius: 3px;
            }}
        """)

    def _log(self, message: str, level: str = "info"):
        """Append a message to the log output."""
        from ...theme.manager import manager
        colors = manager().colors
        
        color_map = {
            "info": colors.fg_primary,
            "success": getattr(colors, "success", "#4ec9b0"), # Fallback if success not in theme
            "warning": getattr(colors, "warning", "#dcdcaa"),
            "error": colors.danger,
            "cmd": colors.accent_primary,
        }
        color = color_map.get(level, colors.fg_primary)
        self.text_log.append(f'<span style="color: {color};">{message}</span>')
        # Scroll to bottom
        scrollbar = self.text_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _get_project_paths(self) -> dict:
        """Get standard project paths for processing."""
        # Try to find the project root (look for 'data' directory)
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
            "proc_pkg": project_root / "packages" / "optothermal_processing",
            "cli_script": project_root / "packages" / "optothermal_processing" / "src" / "cli" / "main.py",
        }

    def _run_process(self, args: list[str], description: str):
        """Run a CLI command in a separate process."""
        if self.process is not None and self.process.state() != QtCore.QProcess.ProcessState.NotRunning:
            self.show_error("An operation is already running.")
            return

        paths = self._get_project_paths()
        cli_script = paths["cli_script"]
        
        if not cli_script.exists():
            self._log(f"Error: CLI script not found at {cli_script}", "error")
            return

        # Prepare environment
        env = QtCore.QProcessEnvironment.systemEnvironment()
        python_path = env.value("PYTHONPATH", "")
        # Add the package root to PYTHONPATH
        pkg_root = str(paths["proc_pkg"])
        if pkg_root not in python_path:
            python_path = f"{pkg_root}:{python_path}" if python_path else pkg_root
            env.insert("PYTHONPATH", python_path)
            
        # Disable buffering for real-time output
        env.insert("PYTHONUNBUFFERED", "1")

        self.process = QtCore.QProcess(self)
        self.process.setProcessEnvironment(env)
        self.process.setProgram("python3")
        
        # Add script path as first argument
        full_args = [str(cli_script)] + args
        self.process.setArguments(full_args)
        
        # Connect signals
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.finished.connect(self._handle_finished)
        self.process.errorOccurred.connect(self._handle_error)
        
        # UI updates
        self._set_busy(True)
        self.current_operation = description
        self.btn_stop.show()
        
        cmd_display = f"python3 {' '.join(full_args)}"
        self._log("-" * 50, "info")
        self._log(f"Starting: {description}", "success")
        self._log(f"Command: {cmd_display}", "cmd")
        self._log("-" * 50, "info")
        
        self.process.start()

    def _handle_stdout(self):
        """Handle standard output from process."""
        data = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
        # Filter out some noise if needed, but mostly just print
        if data.strip():
            self.text_log.moveCursor(self.text_log.textCursor().MoveOperation.End)
            self.text_log.insertPlainText(data)
            self.text_log.verticalScrollBar().setValue(self.text_log.verticalScrollBar().maximum())

    def _handle_stderr(self):
        """Handle standard error from process."""
        data = self.process.readAllStandardError().data().decode('utf-8', errors='replace')
        if data.strip():
            # Error output usually warrants red color
            self._log(data.strip(), "error")

    def _handle_finished(self, exit_code, exit_status):
        """Handle process completion."""
        status = "Success" if exit_code == 0 and exit_status == QtCore.QProcess.ExitStatus.NormalExit else "Failed"
        level = "success" if status == "Success" else "error"
        
        self._log("-" * 50, "info")
        self._log(f"Operation finished: {status} (Exit code: {exit_code})", level)
        self._log("-" * 50, "info")
        
        self._set_busy(False)
        self.btn_stop.hide()
        self.process = None
        self.current_operation = None
        
        if status == "Success":
            self.show_success("Operation completed successfully!")
        else:
            self.show_error(f"Operation failed with exit code {exit_code}")

    def _handle_error(self, error):
        """Handle process startup errors."""
        self._log(f"Process error: {self.process.errorString()}", "error")
        self._set_busy(False)
        self.btn_stop.hide()
        self.process = None

    def _stop_process(self):
        """Kill the running process."""
        if self.process and self.process.state() != QtCore.QProcess.ProcessState.NotRunning:
            self._log("Stopping operation...", "warning")
            self.process.terminate()
            if not self.process.waitForFinished(2000):
                self.process.kill()

    def _set_busy(self, busy: bool):
        """Enable/disable UI controls during processing."""
        buttons = [
            self.btn_full_pipeline, 
            self.btn_stage, 
            self.btn_histories, 
            self.btn_metrics,
            self.spin_workers,
            self.check_force,
            self.check_strict
        ]
        for btn in buttons:
            btn.setEnabled(not busy)

    def _run_staging(self):
        """Run staging command."""
        paths = self._get_project_paths()
        
        # Priority 1: Project local config (config/procedures.yaml)
        procedures_yaml = paths["project_root"] / "config" / "procedures.yaml"
        
        # Priority 2: optothermal_common schema
        if not procedures_yaml.exists():
            procedures_yaml = paths["project_root"] / "packages" / "optothermal_common" / "optothermal_common" / "schema" / "procedures.yml"
        
        # Priority 3: optothermal_processing default
        if not procedures_yaml.exists():
             procedures_yaml = paths["project_root"] / "packages" / "optothermal_processing" / "config" / "procedures.yml"

        args = ["stage-all"]
        args.extend(["--workers", str(self.spin_workers.value())])
        args.extend(["--procedures-yaml", str(procedures_yaml)])
        
        if self.check_force.isChecked():
            args.append("--force")
        if self.check_strict.isChecked():
            args.append("--strict")
            
        # Add verbose flag to see progress in log
        args.append("--verbose")
            
        self._run_process(args, "Stage CSVs")

    def _run_build_histories(self):
        """Run history building command."""
        args = ["build-all-histories"]
        self._run_process(args, "Build Histories")

    def _run_derive_metrics(self):
        """Run metric derivation command."""
        args = ["derive-all-metrics"]
        args.extend(["--workers", str(self.spin_workers.value())])
        
        if self.check_force.isChecked():
            args.append("--force")
            
        self._run_process(args, "Derive Metrics")

    def _run_full_pipeline(self):
        """Run full pipeline (sequential chain of commands)."""
        # Note: Running full pipeline via CLI isn't a single command yet in the new CLI structure.
        # Ideally, we would chain them. For now, let's implement a simple chain in Python
        # or just run them sequentially if the CLI supported it.
        # Since we switched to QProcess, we can't easily chain them without a 'pipeline' command in CLI.
        # CHECK: Does the CLI have a full pipeline command? Not explicitly.
        # We'll construct a shell command that runs them in sequence: 
        # python main.py stage-all && python main.py build-all-histories && python main.py derive-all-metrics
        
        paths = self._get_project_paths()
        cli_script = str(paths["cli_script"])
        
        # Build argument strings
        stage_args = f"stage-all --workers {self.spin_workers.value()} --verbose"
        if self.check_force.isChecked():
            stage_args += " --force"
        if self.check_strict.isChecked():
            stage_args += " --strict"
            
        history_args = "build-all-histories"
        
        metrics_args = f"derive-all-metrics --workers {self.spin_workers.value()}"
        if self.check_force.isChecked():
            metrics_args += " --force"
            
        # Chain commands using shell syntax (assuming Linux/MacOS)
        # Note: We need to use "bash -c" to use && operator
        full_cmd = (
            f"python3 {cli_script} {stage_args} && "
            f"python3 {cli_script} {history_args} && "
            f"python3 {cli_script} {metrics_args}"
        )
        
        # Override _run_process logic slightly for this special case
        if self.process is not None and self.process.state() != QtCore.QProcess.ProcessState.NotRunning:
            self.show_error("An operation is already running.")
            return

        # Prepare environment
        env = QtCore.QProcessEnvironment.systemEnvironment()
        python_path = env.value("PYTHONPATH", "")
        pkg_root = str(paths["proc_pkg"])
        if pkg_root not in python_path:
            python_path = f"{pkg_root}:{python_path}" if python_path else pkg_root
            env.insert("PYTHONPATH", python_path)
        env.insert("PYTHONUNBUFFERED", "1")

        self.process = QtCore.QProcess(self)
        self.process.setProcessEnvironment(env)
        self.process.setProgram("/bin/bash")
        self.process.setArguments(["-c", full_cmd])
        
        # Connect signals
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.finished.connect(self._handle_finished)
        self.process.errorOccurred.connect(self._handle_error)
        
        # UI updates
        self._set_busy(True)
        self.current_operation = "Full Pipeline"
        self.btn_stop.show()
        
        self._log("-" * 50, "info")
        self._log("Starting: Full Pipeline (Stage → History → Metrics)", "success")
        self._log(f"Command Chain: {full_cmd}", "cmd")
        self._log("-" * 50, "info")
        
        self.process.start()
