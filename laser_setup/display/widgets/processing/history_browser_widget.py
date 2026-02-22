"""
History browser widget for viewing and filtering chip experiment histories.

Provides a QTableView-based interface for browsing chip histories stored
as Parquet files, with filtering by procedure, light condition, and text search.
"""

import logging
from pathlib import Path
from typing import Optional, List

from qtpy import QtCore, QtWidgets, QtGui

from .base_widget import BaseProcessingWidget

log = logging.getLogger(__name__)


class PolarsTableModel(QtCore.QAbstractTableModel):
    """
    Qt table model that wraps a Polars DataFrame.

    Provides efficient display of large dataframes in a QTableView
    without converting to Python lists (uses direct Polars access).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._df = None
        self._columns: List[str] = []

    def set_dataframe(self, df):
        """Set the Polars DataFrame to display."""
        self.beginResetModel()
        self._df = df
        if df is not None:
            self._columns = df.columns
        else:
            self._columns = []
        self.endResetModel()

    def rowCount(self, parent=None):
        if self._df is None:
            return 0
        return len(self._df)

    def columnCount(self, parent=None):
        return len(self._columns)

    def data(self, index, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or self._df is None:
            return None

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            try:
                col = self._columns[index.column()]
                value = self._df[col][index.row()]

                # Format different types for display
                if value is None:
                    return ""
                elif isinstance(value, bool):
                    return "Yes" if value else "No"
                elif isinstance(value, float):
                    if abs(value) < 0.001 or abs(value) > 10000:
                        return f"{value:.3e}"
                    return f"{value:.4g}"
                else:
                    return str(value)
            except Exception:
                return ""

        elif role == QtCore.Qt.ItemDataRole.EditRole:
            # Return raw value for sorting/editing
            try:
                col = self._columns[index.column()]
                return self._df[col][index.row()]
            except Exception:
                return None

        elif role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            # Numeric columns aligned right
            if self._df is not None and index.column() < len(self._columns):
                col = self._columns[index.column()]
                dtype = str(self._df[col].dtype)
                if "Int" in dtype or "Float" in dtype:
                    return QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter

        return None

    def headerData(self, section, orientation, role=QtCore.Qt.ItemDataRole.DisplayRole):
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if orientation == QtCore.Qt.Orientation.Horizontal:
                if section < len(self._columns):
                    return self._columns[section]
            else:
                return str(section + 1)
        return None

    def get_row_data(self, row: int) -> dict:
        """Get all data for a specific row as a dictionary."""
        if self._df is None or row < 0 or row >= len(self._df):
            return {}
        return self._df.row(row, named=True)


class HistoryBrowserWidget(BaseProcessingWidget):
    """
    Widget for browsing and filtering chip experiment histories.

    Features:
    - Chip selector dropdown
    - Procedure type filter
    - Light condition filter
    - Text search
    - Sortable table view
    - Export to CSV/JSON
    """

    # Emitted when user double-clicks an experiment row
    experiment_selected = QtCore.Signal(dict)  # row data

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._current_df = None
        self._histories_dir: Optional[Path] = None
        self._setup_ui()
        self._connect_signals()
        self._apply_theme()
        self._scan_for_histories()

    def _setup_ui(self):
        """Create the user interface."""
        layout = QtWidgets.QVBoxLayout(self)

        # Title
        self.lbl_title = QtWidgets.QLabel("Chip History Browser")
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.lbl_title)

        # Chip selection row
        chip_layout = QtWidgets.QHBoxLayout()

        chip_layout.addWidget(QtWidgets.QLabel("Chip:"))
        self.combo_chip = QtWidgets.QComboBox()
        self.combo_chip.setMinimumWidth(150)
        chip_layout.addWidget(self.combo_chip)

        self.btn_refresh = QtWidgets.QPushButton("Refresh")
        self.btn_refresh.setMaximumWidth(80)
        chip_layout.addWidget(self.btn_refresh)

        chip_layout.addStretch()
        layout.addLayout(chip_layout)

        # Filters row
        filter_layout = QtWidgets.QHBoxLayout()

        filter_layout.addWidget(QtWidgets.QLabel("Procedure:"))
        self.combo_procedure = QtWidgets.QComboBox()
        self.combo_procedure.addItem("All", None)
        filter_layout.addWidget(self.combo_procedure)

        filter_layout.addWidget(QtWidgets.QLabel("Light:"))
        self.combo_light = QtWidgets.QComboBox()
        self.combo_light.addItems(["All", "Light Only", "Dark Only"])
        filter_layout.addWidget(self.combo_light)

        filter_layout.addWidget(QtWidgets.QLabel("Search:"))
        self.edit_search = QtWidgets.QLineEdit()
        self.edit_search.setPlaceholderText("Search in summary...")
        self.edit_search.setClearButtonEnabled(True)
        filter_layout.addWidget(self.edit_search)

        layout.addLayout(filter_layout)

        # Table view
        self.table_model = PolarsTableModel(self)
        self.proxy_model = QtCore.QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setSortRole(QtCore.Qt.ItemDataRole.EditRole)  # Sort by raw value (numbers)

        self.table_view = QtWidgets.QTableView()
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.verticalHeader().setDefaultSectionSize(24)
        layout.addWidget(self.table_view)

        # Status and export row
        bottom_layout = QtWidgets.QHBoxLayout()

        self.label_status = QtWidgets.QLabel("No history loaded")
        bottom_layout.addWidget(self.label_status)

        bottom_layout.addStretch()

        self.btn_export = QtWidgets.QPushButton("Export...")
        self.btn_export.setEnabled(False)
        bottom_layout.addWidget(self.btn_export)

        layout.addLayout(bottom_layout)

    def _connect_signals(self):
        """Connect signals to slots."""
        self.combo_chip.currentIndexChanged.connect(self._load_selected_history)
        self.btn_refresh.clicked.connect(self._scan_for_histories)
        self.combo_procedure.currentIndexChanged.connect(self._apply_filters)
        self.combo_light.currentIndexChanged.connect(self._apply_filters)
        self.edit_search.textChanged.connect(self._apply_text_filter)
        self.table_view.doubleClicked.connect(self._on_row_double_clicked)
        self.btn_export.clicked.connect(self._export_history)
        
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
        colors = manager().colors
        
        # Update refresh button style
        self.btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors.bg_tertiary};
                color: {colors.fg_primary};
                border: 1px solid {colors.border_primary};
                border-radius: 4px;
                padding: 4px;
            }}
            QPushButton:hover {{
                background-color: {colors.bg_secondary};
                border-color: {colors.accent_primary};
            }}
        """)
        
        # Update export button style (accent color)
        self.btn_export.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors.accent_primary};
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 4px;
                padding: 5px 10px;
            }}
            QPushButton:hover {{
                background-color: {colors.accent_secondary};
            }}
            QPushButton:disabled {{
                background-color: {colors.bg_tertiary};
                color: {colors.fg_disabled};
            }}
        """)

    def _get_histories_dir(self) -> Path:
        """Get the chip histories directory."""
        if self._histories_dir is not None:
            return self._histories_dir

        # Try to find the project root
        current = Path.cwd()
        for parent in [current] + list(current.parents):
            histories_path = parent / "data" / "02_stage" / "chip_histories"
            if histories_path.exists():
                self._histories_dir = histories_path
                return self._histories_dir

        # Fallback
        self._histories_dir = current / "data" / "02_stage" / "chip_histories"
        return self._histories_dir

    def _scan_for_histories(self):
        """Scan for available chip history files."""
        histories_dir = self._get_histories_dir()

        self.combo_chip.clear()

        if not histories_dir.exists():
            self.label_status.setText(f"Histories directory not found: {histories_dir}")
            return

        history_files = sorted(histories_dir.glob("*_history.parquet"))

        if not history_files:
            self.label_status.setText("No history files found")
            return

        for path in history_files:
            # Extract chip name from filename (e.g., "Alisson67_history.parquet" -> "Alisson67")
            chip_name = path.stem.replace("_history", "")
            self.combo_chip.addItem(chip_name, str(path))

        self.label_status.setText(f"Found {len(history_files)} chip histories")

    def _load_selected_history(self):
        """Load the currently selected chip history."""
        path_str = self.combo_chip.currentData()
        if not path_str:
            return

        path = Path(path_str)
        if not path.exists():
            self.show_error(f"History file not found: {path}")
            return

        try:
            import polars as pl
            self._current_df = pl.read_parquet(path)
            self.table_model.set_dataframe(self._current_df)
            self._update_procedure_filter()
            self._apply_filters()
            self.btn_export.setEnabled(True)

            # Resize columns to content
            self.table_view.resizeColumnsToContents()

            self.label_status.setText(f"Loaded {len(self._current_df)} experiments")

        except Exception as e:
            self.show_error(f"Failed to load history: {e}")
            log.exception("Failed to load history")

    def _update_procedure_filter(self):
        """Update procedure dropdown with procedures in current history."""
        self.combo_procedure.blockSignals(True)
        self.combo_procedure.clear()
        self.combo_procedure.addItem("All", None)

        if self._current_df is not None and "proc" in self._current_df.columns:
            procedures = sorted(self._current_df["proc"].unique().to_list())
            for proc in procedures:
                if proc is not None:
                    self.combo_procedure.addItem(proc, proc)

        self.combo_procedure.blockSignals(False)

    def _apply_filters(self):
        """Apply procedure and light filters to the data."""
        if self._current_df is None:
            return

        import polars as pl
        df = self._current_df

        # Procedure filter
        proc = self.combo_procedure.currentData()
        if proc is not None:
            df = df.filter(pl.col("proc") == proc)

        # Light filter
        light_filter = self.combo_light.currentText()
        if "has_light" in df.columns:
            if light_filter == "Light Only":
                df = df.filter(pl.col("has_light") == True)
            elif light_filter == "Dark Only":
                df = df.filter(pl.col("has_light") == False)

        self.table_model.set_dataframe(df)
        self.label_status.setText(f"Showing {len(df)} of {len(self._current_df)} experiments")

    def _apply_text_filter(self, text: str):
        """Apply text search filter."""
        # Find the column index for 'summary' if it exists
        if "summary" in self.table_model._columns:
            col_idx = self.table_model._columns.index("summary")
            self.proxy_model.setFilterKeyColumn(col_idx)
        else:
            # Filter on all columns
            self.proxy_model.setFilterKeyColumn(-1)

        self.proxy_model.setFilterFixedString(text)

    def _on_row_double_clicked(self, index):
        """Handle double-click on a table row."""
        source_index = self.proxy_model.mapToSource(index)
        row_data = self.table_model.get_row_data(source_index.row())
        if row_data:
            self.experiment_selected.emit(row_data)
            log.info(f"Selected experiment: seq={row_data.get('seq')}, proc={row_data.get('proc')}")

    def _export_history(self):
        """Export the current filtered history to a file."""
        if self._current_df is None:
            return

        # Get filename from user
        chip_name = self.combo_chip.currentText()
        default_name = f"{chip_name}_exported"

        file_path, file_type = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export History",
            default_name,
            "CSV Files (*.csv);;JSON Files (*.json);;Parquet Files (*.parquet)"
        )

        if not file_path:
            return

        try:
            # Get currently displayed (filtered) data
            df = self.table_model._df
            if df is None:
                return

            if file_path.endswith(".csv"):
                df.write_csv(file_path)
            elif file_path.endswith(".json"):
                df.write_json(file_path)
            elif file_path.endswith(".parquet"):
                df.write_parquet(file_path)
            else:
                # Default to CSV
                df.write_csv(file_path + ".csv")
                file_path += ".csv"

            self.show_success(f"Exported {len(df)} experiments to:\n{file_path}")

        except Exception as e:
            self.show_error(f"Export failed: {e}")
