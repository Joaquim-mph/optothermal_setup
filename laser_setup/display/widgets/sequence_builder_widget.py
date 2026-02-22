"""Widget for building sequences by accepting dropped procedures."""

from ..Qt import QtCore, QtGui, QtWidgets
from ..theme import manager
from ...config import CONFIG, instantiate
from ..models import ProcedureItemModel


class SequenceBuilderWidget(QtWidgets.QWidget):
    """Builder area that accepts dropped procedures and manages the sequence.

    Signals:
        procedureAdded: Emitted when a procedure is added (procedure_name)
        procedureRemoved: Emitted when a procedure is removed (index)
        procedureMoved: Emitted when a procedure is reordered (from_index, to_index)
    """

    procedureAdded = QtCore.Signal(str)
    procedureRemoved = QtCore.Signal(int)
    procedureMoved = QtCore.Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setSpacing(10)
        self.layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        self.procedure_widgets: list = []  # Will be ProcedureItemWidget instances


    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        """Accept drag events with text mime data."""
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent):
        """Accept drag move events."""
        event.acceptProposedAction()

    def dropEvent(self, event: QtGui.QDropEvent):
        """Add procedure when dropped."""
        proc_name = event.mimeData().text()
        self.add_procedure(proc_name)
        event.acceptProposedAction()

    def add_procedure(
        self,
        proc_name: str,
        parameters: dict | None = None,
        sequencer_config: str | None = None
    ):
        """Add a procedure item to the builder.

        Args:
            proc_name: Name of the procedure to add from CONFIG.procedures._types
            parameters: Optional dict of parameter configurations to set
            sequencer_config: Optional sequencer string for parameter sweeps
        """
        # Import here to avoid circular dependency
        from .procedure_item_widget import ProcedureItemWidget

        procedure_types = instantiate(CONFIG.procedures._types)
        if proc_name not in procedure_types:
            return

        proc_class = procedure_types[proc_name]

        # Create widget for the procedure
        item_widget = ProcedureItemWidget(proc_class, parent=self)
        item_widget.deleteRequested.connect(self._on_delete_requested)

        # Apply pre-configured parameters and sequencer if provided
        if parameters:
            item_widget.set_parameters(parameters)
        if sequencer_config:
            item_widget.set_sequencer(sequencer_config)

        self.procedure_widgets.append(item_widget)
        self.layout.addWidget(item_widget)
        self._update_indices()

        self.procedureAdded.emit(proc_name)

    def clear(self):
        """Remove all procedures from the builder."""
        for widget in list(self.procedure_widgets):
            self._on_delete_requested(widget)

    def _on_delete_requested(self, widget):
        """Remove a procedure item.

        Args:
            widget: The ProcedureItemWidget requesting deletion
        """
        index = self.procedure_widgets.index(widget)
        self.procedure_widgets.remove(widget)
        self.layout.removeWidget(widget)
        widget.deleteLater()

        self._update_indices()
        self.procedureRemoved.emit(index)

    def _update_indices(self):
        for idx, widget in enumerate(self.procedure_widgets, start=1):
            widget.set_index(idx)

    def get_procedure_items(self) -> list[ProcedureItemModel]:
        """Get all procedure configurations as models.

        Returns:
            List of ProcedureItemModel instances
        """
        return [w.get_model() for w in self.procedure_widgets]
