"""Widget for displaying available procedures with drag support."""

from ..Qt import QtCore, QtGui, QtWidgets
from ...config import CONFIG, instantiate


class ProcedureLibraryWidget(QtWidgets.QListWidget):
    """Library of available procedures that can be dragged into sequences.

    This widget displays all registered procedures from CONFIG.procedures._types
    and allows them to be dragged into the sequence builder.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragOnly)
        self.setDefaultDropAction(QtCore.Qt.DropAction.CopyAction)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self._populate_procedures()

    def _populate_procedures(self):
        """Load all procedures from CONFIG.procedures._types."""
        procedure_types = instantiate(CONFIG.procedures._types)

        for name, cls in sorted(procedure_types.items()):
            # Skip Sequence and Wait procedures
            if name in ('Sequence', 'Wait'):
                continue

            item = QtWidgets.QListWidgetItem(self)
            display_name = getattr(cls, 'name', name)
            doc = cls.__doc__.strip().split('\n')[0] if cls.__doc__ else ''

            item.setText(display_name)
            item.setToolTip(doc)
            # Store the procedure class name as UserRole data
            item.setData(QtCore.Qt.ItemDataRole.UserRole, name)

    def startDrag(self, supportedActions):
        """Custom drag behavior to include procedure name in mime data."""
        item = self.currentItem()
        if not item:
            return

        drag = QtGui.QDrag(self)
        mime_data = QtCore.QMimeData()

        # Get the procedure name from the item's UserRole data
        proc_name = item.data(QtCore.Qt.ItemDataRole.UserRole)
        mime_data.setText(proc_name)

        drag.setMimeData(mime_data)
        drag.exec(QtCore.Qt.DropAction.CopyAction)
