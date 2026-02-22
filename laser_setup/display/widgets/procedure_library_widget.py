"""Widget showing available procedures to drag into the sequence builder."""

from ..Qt import QtCore, QtGui, QtWidgets
from ..theme import manager, qss
from .._procedure_groups import _PROCEDURE_GROUPS
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
        self._groups: list[tuple[QtWidgets.QListWidgetItem, list[QtWidgets.QListWidgetItem]]] = []
        self._header_items: list[QtWidgets.QListWidgetItem] = []
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

        bold_font = QtGui.QFont()
        bold_font.setBold(True)
        header_color = QtGui.QColor(c.fg_dark)
        for header_item in self._header_items:
            header_item.setFont(bold_font)
            header_item.setForeground(header_color)

    def _populate_procedures(self):
        """Populate list with available procedures grouped like the Measurement menu."""
        try:
            procedure_types = instantiate(CONFIG.procedures._types)
        except Exception:
            procedure_types = {}

        self._groups.clear()
        self._header_items.clear()
        self.list_widget.clear()

        added: set[str] = set()

        for group_name, proc_names in _PROCEDURE_GROUPS:
            available = [p for p in proc_names if p in procedure_types]
            if not available:
                continue

            header = QtWidgets.QListWidgetItem(group_name)
            header.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.list_widget.addItem(header)
            self._header_items.append(header)

            group_items: list[QtWidgets.QListWidgetItem] = []
            for proc_name in available:
                item = self._make_proc_item(proc_name, procedure_types[proc_name])
                self.list_widget.addItem(item)
                group_items.append(item)
                added.add(proc_name)

            self._groups.append((header, group_items))

        # Ungrouped procedures go into an "Other" group
        ungrouped = [(n, c) for n, c in sorted(procedure_types.items()) if n not in added]
        if ungrouped:
            header = QtWidgets.QListWidgetItem("Other")
            header.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.list_widget.addItem(header)
            self._header_items.append(header)

            group_items = []
            for proc_name, proc_class in ungrouped:
                item = self._make_proc_item(proc_name, proc_class)
                self.list_widget.addItem(item)
                group_items.append(item)

            self._groups.append((header, group_items))

    def _make_proc_item(self, proc_name: str, proc_class) -> QtWidgets.QListWidgetItem:
        """Create a draggable list item for a procedure."""
        item = QtWidgets.QListWidgetItem()
        item.setText(proc_name)
        item.setData(QtCore.Qt.ItemDataRole.UserRole, proc_name)

        doc = getattr(proc_class, '__doc__', '') or ''
        if doc:
            item.setToolTip(doc.strip().split('\n')[0])

        self._set_procedure_icon(item, proc_name)
        return item

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
        """Filter procedures based on search text, hiding empty group headers."""
        text = text.lower()
        for header, items in self._groups:
            any_visible = False
            for item in items:
                proc_name = item.data(QtCore.Qt.ItemDataRole.UserRole)
                visible = text in proc_name.lower()
                item.setHidden(not visible)
                if visible:
                    any_visible = True
            header.setHidden(not any_visible)

    def _on_double_click(self, item: QtWidgets.QListWidgetItem):
        """Handle double-click on procedure."""
        proc_name = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if proc_name:  # skip header items (UserRole is None)
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
