"""Widget showing available procedures to drag into the sequence builder."""

from ..Qt import QtCore, QtGui, QtWidgets
from ..theme import manager, qss
from ...config import CONFIG, instantiate


class ProcedureLibraryWidget(QtWidgets.QWidget):
    """Library panel showing available procedures.

    Procedures can be dragged from here into the sequence builder.

    Signals:
        procedureDoubleClicked: Emitted when a procedure is double-clicked (proc_name)
    """

    procedureDoubleClicked = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._populate_procedures()
        self._apply_style()
        manager().theme_changed.connect(self._apply_style)

    def _setup_ui(self):
        """Build the widget UI."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Title
        self.title_label = QtWidgets.QLabel("Available Procedures")
        layout.addWidget(self.title_label)

        # Search box
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Search...")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.textChanged.connect(self._filter_procedures)
        layout.addWidget(self.search_box)

        # List widget
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setDragEnabled(True)
        self.list_widget.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragOnly)
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.list_widget)

        # Instructions
        self.instructions_label = QtWidgets.QLabel(
            "Drag procedures to the builder,\n"
            "or double-click to add"
        )
        self.instructions_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.instructions_label)

    def _apply_style(self, _colors=None):
        c = manager().colors
        self.title_label.setStyleSheet(
            f"font-weight: 600; font-size: 13px; color: {c.fg};"
        )
        self.instructions_label.setStyleSheet(
            f"color: {c.fg_dark}; font-size: 11px;"
        )
        self.search_box.setStyleSheet(qss('input'))
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {c.bg_highlight};
                color: {c.fg};
                border: 1px solid {c.border};
                border-radius: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {c.blue};
                color: #FFFFFF;
            }}
        """)

    def _populate_procedures(self):
        """Populate list with available procedures."""
        try:
            procedure_types = instantiate(CONFIG.procedures._types)
        except Exception:
            procedure_types = {}

        for proc_name, proc_class in sorted(procedure_types.items()):
            item = QtWidgets.QListWidgetItem()
            item.setText(proc_name)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, proc_name)

            # Add tooltip with procedure description
            doc = getattr(proc_class, '__doc__', '') or ''
            if doc:
                item.setToolTip(doc.strip().split('\n')[0])

            # Set icon based on procedure type
            self._set_procedure_icon(item, proc_name)

            self.list_widget.addItem(item)

    def _set_procedure_icon(self, item: QtWidgets.QListWidgetItem, proc_name: str):
        """Set icon for procedure based on type."""
        # Color coding for different procedure types
        colors = {
            'IV': '#E74C3C',      # Red
            'IVg': '#4A90E2',     # Blue
            'It': '#50C878',      # Green
            'Vt': '#9B59B6',      # Purple
            'VVg': '#F39C12',     # Orange
            'Laser': '#F39C12',   # Orange
            'Calibration': '#F39C12',
        }

        color = '#888'  # Default gray
        for key, c in colors.items():
            if key in proc_name:
                color = c
                break

        # Create colored bullet icon
        pixmap = QtGui.QPixmap(16, 16)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setBrush(QtGui.QColor(color))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()

        item.setIcon(QtGui.QIcon(pixmap))

    def _filter_procedures(self, text: str):
        """Filter procedures based on search text."""
        text = text.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            proc_name = item.data(QtCore.Qt.ItemDataRole.UserRole)
            item.setHidden(text not in proc_name.lower())

    def _on_double_click(self, item: QtWidgets.QListWidgetItem):
        """Handle double-click on procedure."""
        proc_name = item.data(QtCore.Qt.ItemDataRole.UserRole)
        self.procedureDoubleClicked.emit(proc_name)

    def startDrag(self, supportedActions):
        """Override to set drag mime data."""
        item = self.list_widget.currentItem()
        if item:
            drag = QtGui.QDrag(self)
            mime_data = QtCore.QMimeData()
            mime_data.setText(item.data(QtCore.Qt.ItemDataRole.UserRole))
            drag.setMimeData(mime_data)
            drag.exec(QtCore.Qt.DropAction.CopyAction)
